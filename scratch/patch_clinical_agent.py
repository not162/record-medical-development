from pathlib import Path

agent_path = Path(r"c:\Users\user\RAG-model-record\services\ai-api\app\agents\clinical_agent.py")
content = agent_path.read_text(encoding="utf-8")

if "gp_safety_gate" not in content:
    content = content.replace(
        "from app.agents.safety import evaluate_clinical_safety",
        "from app.agents.gp_safety import gp_safety_gate\nfrom app.agents.safety import evaluate_clinical_safety"
    )

    old_contra = """        # 1b. Clinical Contraindications Check
        is_contra, contra_cat, contra_msg = evaluate_contraindications(user_query)
        if is_contra:
            return {
                "content": contra_msg,
                "evidence_context": [],
                "citations": [],
                "triage_department": contra_cat,
                "scanning_deteksi_bahasa": lang_scan,
                "safety_alert": True,
                "model_used": "safety-contraindication-guardrail"
            }"""

    new_contra = """        # 1b. Clinical Contraindications Check
        is_contra, contra_cat, contra_msg = evaluate_contraindications(user_query)
        if is_contra:
            return {
                "content": contra_msg,
                "evidence_context": [],
                "citations": [],
                "triage_department": contra_cat,
                "scanning_deteksi_bahasa": lang_scan,
                "safety_alert": True,
                "model_used": "safety-contraindication-guardrail"
            }

        # 1c. Gaussian Process Safety Boundary Check (LCB = mu - 2.5 * sigma, threshold: -0.5)
        gp_eval = gp_safety_gate.verify_query_safety(user_query, triage_urgency="MERAH" if is_emergency else ("KUNING" if is_contra else "HIJAU"))
        if not gp_eval["is_safe"]:
            logger.warning(f"Gaussian Process Safety Gate triggered: LCB={gp_eval['lcb']} (gate threshold: {gp_eval['safety_gate_threshold']})")"""

    content = content.replace(old_contra.replace("\n", "\r\n"), new_contra.replace("\n", "\r\n"))
    content = content.replace(old_contra, new_contra)
    agent_path.write_text(content, encoding="utf-8")
    print("[OK] clinical_agent.py updated with GP safety gate")
else:
    print("[SKIP] clinical_agent.py already has GP safety gate")

