"""Pipeline smoke test for scripts/run_sft.py. Needs no network and no base model.

Builds a TINY RANDOM causal LM + a tokenizer trained locally on the SFT text, then runs the real
train_sft() on the real SFT files. It proves the PIPELINE works (data -> chat template -> LoRA via
peft/trl -> adapter save/reload). It does NOT produce a useful model.
Run: python scripts/sft_smoke_test.py
"""
import importlib.util, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_sft", ROOT / "scripts" / "run_sft.py")
run_sft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_sft)


def build_tokenizer():
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers, decoders
    from transformers import PreTrainedTokenizerFast
    texts = []
    for mode in ("fast", "thinking"):
        for split in ("train", "val"):
            for r in run_sft.load_rows(mode, split):
                texts += [m["content"] for m in r["messages"]]
    tk = Tokenizer(models.BPE(unk_token="<unk>"))
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    tk.train_from_iterator(texts, trainers.BpeTrainer(
        vocab_size=1500, special_tokens=["<pad>", "<unk>", "<eos>"],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
    return PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="<pad>", unk_token="<unk>", eos_token="<eos>")


def build_model(vocab):
    import torch
    from transformers import GPT2Config, GPT2LMHeadModel
    torch.manual_seed(0)
    cfg = GPT2Config(vocab_size=vocab, n_positions=512, n_embd=128, n_layer=2, n_head=4,
                     bos_token_id=2, eos_token_id=2, pad_token_id=0)
    return GPT2LMHeadModel(cfg)


def main():
    import torch
    with tempfile.TemporaryDirectory() as tmp:
        tok = build_tokenizer()
        model = build_model(len(tok))
        n = sum(p.numel() for p in model.parameters())
        print(f"tiny random model: {n/1e6:.2f}M params, vocab {len(tok)}")
        # GPT2 uses Conv1D layers (c_attn/c_proj/c_fc) that 'all-linear' skips, so name them.
        rep = run_sft.train_sft(model, tok, "fast", Path(tmp) / "out", epochs=1, max_steps=40, lr=3e-3,
                                lora_r=16, batch=4, max_len=512,
                                target_modules=["c_attn", "c_proj", "c_fc"], use_gpu=False)
        curve = rep["train_loss_curve"]
        head, tail = sum(curve[:5]) / 5, sum(curve[-5:]) / 5
        print(json.dumps({k: v for k, v in rep.items() if k != "train_loss_curve"}, indent=2))
        print(f"train loss first5 avg {head:.4f} -> last5 avg {tail:.4f}")
        assert rep["train_steps"] == 40, "pipeline did not run the expected steps"
        assert tail < head, "train loss did not decrease"
        adapter = Path(rep["adapter_dir"])
        assert (adapter / "adapter_config.json").exists(), "adapter config missing"
        assert any(adapter.glob("adapter_model.*")), "adapter weights missing"
        from peft import PeftModel
        loaded = PeftModel.from_pretrained(build_model(len(tok)), adapter)
        ids = tok("Halo dokter", return_tensors="pt")
        with torch.no_grad():
            assert torch.isfinite(loaded(input_ids=ids["input_ids"]).logits).all()
        print("adapter saved and reloaded: OK")
        print("SMOKE TEST PASSED (pipeline only; random tiny model is not a useful model)")


if __name__ == "__main__":
    main()
