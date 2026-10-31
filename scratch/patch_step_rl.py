with open("services/ai-api/app/ml/execution_modes.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

old_call = "self.tinylora.update_v_with_gradient(reward_grad, learning_rate=effective_lr)"
new_call = "self.tinylora.step_rl(reward_grad, learning_rate=effective_lr)"

assert old_call in text, "old_call not found"
text = text.replace(old_call, new_call)

with open("services/ai-api/app/ml/execution_modes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("step_rl updated in execution_modes.py")

