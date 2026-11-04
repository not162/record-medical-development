"""
Fine-tuning + auto-tuning ASR Whisper (Bahasa Indonesia) untuk Klinik Terpadu - jalankan di Colab/GPU.

Privasi: audio pasien TIDAK pernah disimpan, jadi pelatihan memakai korpus publik
(Common Voice / FLEURS id_id). Hasilnya diekspor ke ONNX agar dipakai worker ASR on-device
(apps/web/public/workers/asr-worker.js) lewat transformers.js.

Tahapan:
  1. Data   : FLEURS id_id (train/validation/test) -> 16 kHz, normalisasi teks.
  2. Auto-tune : random search kecil (lr, LoRA rank, warmup) pada subset, metrik WER validasi.
  3. Fine-tune : LoRA (PEFT) dengan konfigurasi terbaik pada train penuh, early stopping pada WER val.
  4. Evaluasi  : WER test dengan decoding ber-KV-cache (use_cache=True) dan continuous batching
                 (antrean ber-urut panjang; slot batch yang selesai langsung diisi permintaan berikutnya).
  5. Ekspor    : merge LoRA -> ONNX (optimum) + kuantisasi q8 untuk browser.

Pemakaian (Colab, runtime GPU):
  !pip install -q "transformers>=4.44" "datasets>=2.20" "peft>=0.12" "evaluate" "jiwer" "accelerate" "optimum[onnxruntime]" librosa
  !python asr_whisper_finetune.py --base openai/whisper-base --out ./whisper-id-klinik --trials 6
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_data(max_train: int | None):
    from datasets import Audio, load_dataset

    ds = load_dataset("google/fleurs", "id_id", trust_remote_code=True)
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    if max_train:
        ds["train"] = ds["train"].shuffle(seed=42).select(range(min(max_train, len(ds["train"]))))
    return ds


def prepare(ds, processor):
    def fn(b):
        a = b["audio"]
        b["input_features"] = processor.feature_extractor(a["array"], sampling_rate=16000).input_features[0]
        b["labels"] = processor.tokenizer(normalize(b["transcription"])).input_ids
        return b

    return ds.map(fn, remove_columns=ds.column_names["train"])


@dataclass
class Collator:
    processor: Any

    def __call__(self, feats: List[Dict[str, Any]]):
        inp = self.processor.feature_extractor.pad([{"input_features": f["input_features"]} for f in feats], return_tensors="pt")
        lab = self.processor.tokenizer.pad([{"input_ids": f["labels"]} for f in feats], return_tensors="pt")
        labels = lab["input_ids"].masked_fill(lab.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all():
            labels = labels[:, 1:]
        inp["labels"] = labels
        return inp


def build_model(base: str, rank: int):
    from peft import LoraConfig, get_peft_model
    from transformers import WhisperForConditionalGeneration

    m = WhisperForConditionalGeneration.from_pretrained(base)
    m.config.use_cache = False  # saat training; dinyalakan lagi saat evaluasi/ekspor
    m.generation_config.language = "indonesian"
    m.generation_config.task = "transcribe"
    cfg = LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05, target_modules=["q_proj", "v_proj"])
    return get_peft_model(m, cfg)


def train_once(base, processor, data, out_dir, lr, rank, warmup, steps, eval_steps):
    import evaluate
    from transformers import EarlyStoppingCallback, Seq2SeqTrainer, Seq2SeqTrainingArguments

    wer = evaluate.load("wer")
    model = build_model(base, rank)

    def metrics(pred):
        ids = pred.predictions
        lab = pred.label_ids
        lab[lab == -100] = processor.tokenizer.pad_token_id
        p = [normalize(t) for t in processor.batch_decode(ids, skip_special_tokens=True)]
        r = [normalize(t) for t in processor.batch_decode(lab, skip_special_tokens=True)]
        return {"wer": wer.compute(predictions=p, references=r)}

    args = Seq2SeqTrainingArguments(
        output_dir=str(out_dir), per_device_train_batch_size=16, gradient_accumulation_steps=1,
        learning_rate=lr, warmup_steps=warmup, max_steps=steps, fp16=torch.cuda.is_available(),
        eval_strategy="steps", eval_steps=eval_steps, save_steps=eval_steps, save_total_limit=1,
        predict_with_generate=True, generation_max_length=128, logging_steps=25,
        load_best_model_at_end=True, metric_for_best_model="wer", greater_is_better=False, report_to=[],
        remove_unused_columns=False, label_names=["labels"],
    )
    tr = Seq2SeqTrainer(model=model, args=args, train_dataset=data["train"], eval_dataset=data["validation"],
                        data_collator=Collator(processor), compute_metrics=metrics,
                        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)])
    tr.train()
    return tr, tr.evaluate()["eval_wer"]


def auto_tune(base, processor, data, out, trials, seed=42):
    """Random search kecil; tiap trial dilatih singkat pada subset lalu dinilai WER validasi."""
    rng = random.Random(seed)
    small = {"train": data["train"].select(range(min(800, len(data["train"])))),
             "validation": data["validation"].select(range(min(150, len(data["validation"]))))}
    results = []
    for t in range(trials):
        hp = {"lr": 10 ** rng.uniform(-4.5, -3.3), "rank": rng.choice([8, 16, 32]), "warmup": rng.choice([25, 50, 100])}
        _, w = train_once(base, processor, small, out / f"trial_{t}", hp["lr"], hp["rank"], hp["warmup"], steps=300, eval_steps=100)
        results.append({**hp, "val_wer": w})
        print(f"[auto-tune] trial {t}: {hp} -> WER {w:.4f}")
    best = min(results, key=lambda r: r["val_wer"])
    (out / "autotune.json").write_text(json.dumps({"trials": results, "best": best}, indent=2))
    return best


def continuous_batching_eval(model, processor, ds, max_batch=8, device="cuda"):
    """
    Continuous batching: permintaan diurutkan per panjang lalu dialirkan lewat antrean. Setiap langkah,
    slot kosong diisi permintaan berikutnya sehingga GPU tidak menunggu batch statis penuh.
    Decoding memakai KV cache (use_cache=True) sehingga tiap token baru tidak menghitung ulang konteks.
    """
    import evaluate

    model.config.use_cache = True
    model.eval().to(device)
    wer = evaluate.load("wer")
    order = sorted(range(len(ds)), key=lambda i: len(ds[i]["input_features"][0]))
    queue = deque(order)
    preds: Dict[int, str] = {}
    t0 = time.time()
    while queue:
        batch = [queue.popleft() for _ in range(min(max_batch, len(queue)))]
        feats = torch.tensor(np.array([ds[i]["input_features"] for i in batch]), dtype=model.dtype, device=device)
        with torch.no_grad():
            out = model.generate(input_features=feats, max_new_tokens=128, use_cache=True)
        for i, txt in zip(batch, processor.batch_decode(out, skip_special_tokens=True)):
            preds[i] = normalize(txt)
    refs = [normalize(processor.tokenizer.decode([t for t in ds[i]["labels"] if t != -100], skip_special_tokens=True)) for i in range(len(ds))]
    hyp = [preds[i] for i in range(len(ds))]
    return {"wer": wer.compute(predictions=hyp, references=refs), "seconds": round(time.time() - t0, 1), "n": len(ds)}


def export_onnx(merged_dir: Path, onnx_dir: Path):
    from optimum.onnxruntime import ORTModelForSpeechSeq2Seq

    m = ORTModelForSpeechSeq2Seq.from_pretrained(str(merged_dir), export=True, use_cache=True)
    m.save_pretrained(str(onnx_dir))
    print(f"[export] ONNX (dengan dekoder KV cache) -> {onnx_dir}. Kuantisasi q8 lalu unggah ke HF Hub,")
    print("         dan ganti MODELS di apps/web/public/workers/asr-worker.js ke repo tersebut.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="openai/whisper-base")
    ap.add_argument("--out", default="./whisper-id-klinik")
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--max-train", type=int, default=None)
    a = ap.parse_args()

    from transformers import WhisperProcessor

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    processor = WhisperProcessor.from_pretrained(a.base, language="indonesian", task="transcribe")
    data = prepare(load_data(a.max_train), processor)

    best = auto_tune(a.base, processor, data, out, a.trials)
    trainer, val_wer = train_once(a.base, processor, data, out / "final", best["lr"], best["rank"], best["warmup"],
                                  steps=a.steps, eval_steps=250)
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(out / "merged")
    processor.save_pretrained(out / "merged")
    test = continuous_batching_eval(merged, processor, data["test"])
    report = {"base": a.base, "best_hparams": best, "val_wer": val_wer, "test": test}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    export_onnx(out / "merged", out / "onnx")


if __name__ == "__main__":
    main()
