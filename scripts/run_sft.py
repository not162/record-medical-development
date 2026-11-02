"""Ready-to-run SFT (LoRA) script. NOT executed in this repo yet: no local causal LM, peft, or trl was available.

Needs:  pip install transformers peft trl datasets accelerate  (plus a LOCAL base model folder)
Usage:  python scripts/run_sft.py --base-model D:/models/<causal-lm> --mode fast
        python scripts/run_sft.py --base-model D:/models/<causal-lm> --mode thinking --epochs 3
Data:   datasets/sft/sft_<mode>_{train,val}.jsonl (chat format: messages[system,user,assistant])
Output: services/ai-api/models/sft/<mode>/ (LoRA adapter) + metrics.json (val loss before/after)
Works on CPU (slow, use a <=1B model) or GPU (bf16/fp16 auto). Not clinically validated.
"""
import argparse, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", required=True, help="local path to a causal LM (no download is done)")
    ap.add_argument("--mode", choices=["fast", "thinking"], required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
        from peft import LoraConfig, get_peft_model
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}. Install transformers, peft, accelerate first.")
    base = Path(a.base_model)
    if not base.exists():
        sys.exit(f"Base model path not found: {base}")
    set_seed(a.seed)
    tok = AutoTokenizer.from_pretrained(base, local_files_only=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    gpu = torch.cuda.is_available()
    dtype = torch.bfloat16 if gpu and torch.cuda.is_bf16_supported() else (torch.float16 if gpu else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True, torch_dtype=dtype)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
                                             target_modules="all-linear"))

    def load(split):
        rows = [json.loads(l) for l in open(ROOT / "datasets/sft" / f"sft_{a.mode}_{split}.jsonl", encoding="utf8") if l.strip()]
        out = []
        for r in rows:
            msgs = r["messages"]
            prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
            full = prompt + msgs[-1]["content"] + (tok.eos_token or "")
            p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
            ids = tok(full, add_special_tokens=False, truncation=True, max_length=a.max_len)["input_ids"]
            labels = [-100] * min(len(p_ids), len(ids)) + ids[len(p_ids):]  # loss on the answer only
            out.append({"input_ids": ids, "labels": labels})
        return out

    train, val = load("train"), load("val")

    def collate(b):
        n = max(len(x["input_ids"]) for x in b)
        pad = tok.pad_token_id
        return {"input_ids": torch.tensor([x["input_ids"] + [pad] * (n - len(x["input_ids"])) for x in b]),
                "attention_mask": torch.tensor([[1] * len(x["input_ids"]) + [0] * (n - len(x["input_ids"])) for x in b]),
                "labels": torch.tensor([x["labels"] + [-100] * (n - len(x["labels"])) for x in b])}

    out_dir = ROOT / "services/ai-api/models/sft" / a.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    args = TrainingArguments(output_dir=str(out_dir / "ckpt"), num_train_epochs=a.epochs, learning_rate=a.lr,
                             per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch,
                             eval_strategy="epoch", save_strategy="no", logging_steps=5, seed=a.seed,
                             bf16=(dtype == torch.bfloat16), fp16=(dtype == torch.float16),
                             use_cpu=not gpu, report_to=[], remove_unused_columns=False)
    tr = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val, data_collator=collate)
    before = tr.evaluate()["eval_loss"]
    tr.train()
    after = tr.evaluate()["eval_loss"]
    model.save_pretrained(out_dir)
    m = {"mode": a.mode, "base_model": str(base), "n_train": len(train), "n_val": len(val), "epochs": a.epochs,
         "val_loss_before": before, "val_loss_after": after, "val_ppl_before": math.exp(before),
         "val_ppl_after": math.exp(after), "seed": a.seed, "device": "gpu" if gpu else "cpu"}
    (out_dir / "metrics.json").write_text(json.dumps(m, indent=2), encoding="utf8")
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
