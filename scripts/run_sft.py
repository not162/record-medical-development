"""LoRA SFT with peft + trl (SFTTrainer). Runs on CPU or GPU.

Usage (real model, YOU must have it locally, e.g. D:/models/Qwen2.5-0.5B-Instruct):
  python scripts/run_sft.py --base-model D:/models/<model> --mode fast
  python scripts/run_sft.py --base-model D:/models/<model> --mode both --epochs 3 --lora-r 8
Data:   datasets/sft/sft_<mode>_{train,val}.jsonl (chat 'messages': system, user, assistant)
Output: <output-dir>/<mode>/ (LoRA adapter) + run_report.json (real val loss before/after)
Nothing is downloaded unless you pass --allow-download together with a Hugging Face id.
Only the answer (last assistant turn) counts for the loss; the prompt is masked.
Not clinically validated.
"""
import argparse, json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SFT_DIR = ROOT / "datasets" / "sft"
DEFAULT_OUT = ROOT / "services" / "ai-api" / "models" / "sft"

# Fallback when the tokenizer has no chat template.
SIMPLE_TEMPLATE = (
    "{% for m in messages %}<|{{ m['role'] }}|>\n{{ m['content'] }}\n{% endfor %}"
    "{% if add_generation_prompt %}<|assistant|>\n{% endif %}"
)


def load_rows(mode, split, limit=None):
    path = SFT_DIR / f"sft_{mode}_{split}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    rows = []
    with open(path, encoding="utf8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows[:limit] if limit else rows


def to_prompt_completion(rows):
    """Split chat rows so only the final assistant message is trained (completion-only loss)."""
    out = []
    for r in rows:
        m = r["messages"]
        if len(m) < 2 or m[-1]["role"] != "assistant":
            continue
        out.append({"prompt": m[:-1], "completion": [m[-1]]})
    return out


def train_sft(model, tokenizer, mode, output_dir, epochs=3, lr=2e-4, lora_r=8, lora_alpha=None,
              batch=2, max_len=1024, seed=42, max_steps=-1, limit=None, target_modules="all-linear",
              use_gpu=None, grad_accum=1, log=print):
    """Train a LoRA adapter on the SFT files for `mode`. Returns the run report dict.

    `model` and `tokenizer` are already loaded (so tests can pass a tiny random model).
    """
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer
    from transformers import set_seed

    set_seed(seed)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    if not getattr(tokenizer, "chat_template", None):
        tokenizer.chat_template = SIMPLE_TEMPLATE
    gpu = torch.cuda.is_available() if use_gpu is None else use_gpu
    out = Path(output_dir) / mode
    out.mkdir(parents=True, exist_ok=True)

    train_ds = Dataset.from_list(to_prompt_completion(load_rows(mode, "train", limit)))
    val_ds = Dataset.from_list(to_prompt_completion(load_rows(mode, "val", limit)))
    cfg = SFTConfig(
        output_dir=str(out / "ckpt"), num_train_epochs=epochs, max_steps=max_steps, learning_rate=lr,
        per_device_train_batch_size=batch, per_device_eval_batch_size=batch,
        gradient_accumulation_steps=grad_accum, max_length=max_len, completion_only_loss=True,
        eval_strategy="no", save_strategy="no", logging_steps=1, seed=seed, report_to=[],
        use_cpu=not gpu, bf16=bool(gpu and torch.cuda.is_bf16_supported()),
        fp16=bool(gpu and not torch.cuda.is_bf16_supported()),
    )
    lcfg = LoraConfig(r=lora_r, lora_alpha=lora_alpha or 2 * lora_r, lora_dropout=0.05,
                      task_type="CAUSAL_LM", target_modules=target_modules)
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=train_ds, eval_dataset=val_ds,
                         processing_class=tokenizer, peft_config=lcfg)
    t0 = time.time()
    before = float(trainer.evaluate()["eval_loss"])
    log(f"[{mode}] val loss before: {before:.4f}")
    trainer.train()
    after = float(trainer.evaluate()["eval_loss"])
    log(f"[{mode}] val loss after: {after:.4f}")
    trainer.model.save_pretrained(out)
    tl = [h["loss"] for h in trainer.state.log_history if "loss" in h]
    n_params = sum(p.numel() for p in trainer.model.parameters())
    n_train = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    report = {
        "mode": mode, "n_train": len(train_ds), "n_val": len(val_ds), "epochs": epochs,
        "max_steps": max_steps, "lr": lr, "lora_r": lora_r, "batch": batch, "max_len": max_len,
        "seed": seed, "device": "gpu" if gpu else "cpu", "total_params": n_params,
        "trainable_params": n_train, "train_steps": int(trainer.state.global_step),
        "train_loss_first": tl[0] if tl else None, "train_loss_last": tl[-1] if tl else None,
        "train_loss_curve": tl, "val_loss_before": before, "val_loss_after": after,
        "val_ppl_before": math.exp(min(before, 50)), "val_ppl_after": math.exp(min(after, 50)),
        "seconds": round(time.time() - t0, 1), "adapter_dir": str(out),
    }
    (out / "run_report.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


def load_base(path_or_id, allow_download):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    local = Path(path_or_id).exists()
    if not local and not allow_download:
        sys.exit(f"Base model '{path_or_id}' is not a local folder. Download it yourself, "
                 f"or pass --allow-download to let transformers fetch this HF id.")
    kw = {"local_files_only": local or not allow_download}
    tok = AutoTokenizer.from_pretrained(path_or_id, **kw)
    gpu = torch.cuda.is_available()
    dtype = (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if gpu else torch.float32
    model = AutoModelForCausalLM.from_pretrained(path_or_id, dtype=dtype, **kw)
    return model, tok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-model", required=True, help="local folder (or HF id with --allow-download)")
    ap.add_argument("--mode", choices=["fast", "thinking", "both"], required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--allow-download", action="store_true", help="permit fetching a HF model id")
    a = ap.parse_args()
    modes = ["fast", "thinking"] if a.mode == "both" else [a.mode]
    reports = []
    for m in modes:
        model, tok = load_base(a.base_model, a.allow_download)  # fresh base for each mode
        reports.append(dict(train_sft(model, tok, m, a.output_dir, epochs=a.epochs, lr=a.lr,
                                      lora_r=a.lora_r, batch=a.batch, max_len=a.max_len, seed=a.seed),
                            base_model=str(a.base_model)))
        del model
    Path(a.output_dir).mkdir(parents=True, exist_ok=True)
    (Path(a.output_dir) / "run_report.json").write_text(json.dumps(reports, indent=2), encoding="utf8")
    for r in reports:
        print(f"{r['mode']}: val loss {r['val_loss_before']:.4f} -> {r['val_loss_after']:.4f} ({r['device']}, {r['seconds']}s)")


if __name__ == "__main__":
    main()
