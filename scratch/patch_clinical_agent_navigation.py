with open("services/ai-api/app/agents/clinical_agent.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

target_import = "from app.rag.language_scanning import language_scanner"
new_import = "from app.rag.language_scanning import language_scanner\nfrom app.ml.execution_modes import execution_mode_router"

assert target_import in text, "target_import not found"
text = text.replace(target_import, new_import)

old_citations_block = """        # Build verified citations from retrieved evidence
        citations = []
        for e in evidence_context:
            citations.append({
                "chunk_id": e["chunk_id"],
                "doc_id": e["doc_id"],
                "department": e["department"],
                "title": e.get("title", ""),
                "relevance_score": e["relevance_score"]
            })

        # Truncate evidence excerpts to enforce strict context token budget (max 300 chars each)
        truncated_evidence = []
        for e in evidence_context:
            e_copy = dict(e)
            e_copy["excerpt"] = truncate_excerpt(e.get("excerpt", ""), max_chars=300)
            truncated_evidence.append(e_copy)"""

new_citations_block = """        # 3b. Graph & Kernel Optimization + Document Navigation Decision Model (System-Level Runtime)
        exec_result = execution_mode_router.process(
            query=user_query,
            candidate_docs=evidence_context,
            mode=reasoning_mode
        )

        citations = []
        truncated_evidence = []

        if exec_result.retrieval_action != "RETRIEVAL_FREE":
            if exec_result.navigated_docs:
                for d in exec_result.navigated_docs:
                    citations.append({
                        "chunk_id": d["chunk_id"],
                        "doc_id": d["doc_id"],
                        "department": d["department"],
                        "title": "",
                        "relevance_score": round(float(d.get("cross_encoder_score", 0.88)), 2)
                    })
                    truncated_evidence.append({
                        "chunk_id": d["chunk_id"],
                        "doc_id": d["doc_id"],
                        "department": d["department"],
                        "excerpt": truncate_excerpt(d.get("content", ""), max_chars=300),
                        "relevance_score": round(float(d.get("cross_encoder_score", 0.88)), 2)
                    })
            else:
                for e in evidence_context:
                    citations.append({
                        "chunk_id": e["chunk_id"],
                        "doc_id": e["doc_id"],
                        "department": e["department"],
                        "title": e.get("title", ""),
                        "relevance_score": e["relevance_score"]
                    })
                    e_copy = dict(e)
                    e_copy["excerpt"] = truncate_excerpt(e.get("excerpt", ""), max_chars=300)
                    truncated_evidence.append(e_copy)"""

assert old_citations_block in text, "old_citations_block not found"
text = text.replace(old_citations_block, new_citations_block)

with open("services/ai-api/app/agents/clinical_agent.py", "w", encoding="utf-8") as f:
    f.write(text)

print("clinical_agent.py patched successfully with Document Navigator & Kernel Engine!")

