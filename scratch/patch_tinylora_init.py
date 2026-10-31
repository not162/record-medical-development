with open("services/ai-api/app/ml/execution_modes.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

old_str = "self.tinylora = TinyLoRAModel(num_layers=4, d_in=64, d_out=64, rank_n=13)"
new_str = "self.tinylora = TinyLoRAModel(layer_dims=[(64, 64), (64, 64)], rank_n=13)"

assert old_str in text, "old_str not found"
text = text.replace(old_str, new_str)

with open("services/ai-api/app/ml/execution_modes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("TinyLoRAModel init updated!")

