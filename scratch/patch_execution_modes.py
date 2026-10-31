with open("services/ai-api/app/ml/execution_modes.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

old_import = "from app.ml.reasoning_engine import GaussianProcessSafetyBoundary, ClinicalGroundTruthVerifier"
new_import = "from app.agents.gp_safety import gp_safety_gate"

assert old_import in text, "old_import not found"
text = text.replace(old_import, new_import)

old_init = "self.safety_boundary = GaussianProcessSafetyBoundary(learned_length_scale=0.231, formal_safety_gate=-0.5)"
new_init = "self.safety_gate = gp_safety_gate"

assert old_init in text, "old_init not found"
text = text.replace(old_init, new_init)

old_eval = "safety_eval = self.safety_boundary.evaluate_state(system_state)"
new_eval = "safety_eval = self.safety_gate.check_safety(system_state)"

assert old_eval in text, "old_eval not found"
text = text.replace(old_eval, new_eval)

with open("services/ai-api/app/ml/execution_modes.py", "w", encoding="utf-8") as f:
    f.write(text)

print("execution_modes.py updated with gp_safety_gate!")

