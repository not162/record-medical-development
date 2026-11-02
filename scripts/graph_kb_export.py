"""Ekspor graf pengetahuan klinis (hasil seed dari kode) ke datasets/processed/graph_knowledge.jsonl.

Tidak menyentuh database apa pun: konstanta seed dibaca langsung dari file
services/ai-api/app/rag/knowledge_graph.py lewat importlib (file itu hanya memakai json/typing).
Struktur yang sama persis dengan yang ditulis seed_graph() ke tabel graph_nodes/graph_edges.
"""
import importlib.util
import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
KG_PATH = ROOT / "services" / "ai-api" / "app" / "rag" / "knowledge_graph.py"
OUT = ROOT / "datasets" / "processed" / "graph_knowledge.jsonl"
KB_CHUNKS = ROOT / "datasets" / "raw" / "kb_chunks.json"


def load_seed():
    spec = importlib.util.spec_from_file_location("kg_seed", KG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    kg = load_seed()
    nodes, edges = kg.CLINICAL_GRAPH_NODES, kg.CLINICAL_GRAPH_EDGES
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids)), "id simpul duplikat"
    assert all(n["type"] in kg.ALLOWED_NODE_TYPES for n in nodes)
    assert all(e["relation"] in kg.ALLOWED_RELATIONS for e in edges)
    dangling = [e for e in edges if e["source"] not in ids or e["target"] not in ids]
    assert not dangling, dangling
    keys = [(e["source"], e["target"], e["relation"]) for e in edges]
    assert len(keys) == len(set(keys)), "relasi duplikat"

    g = nx.MultiDiGraph()
    for n in nodes:
        g.add_node(n["id"], **n)
    for e in edges:
        g.add_edge(e["source"], e["target"], relation=e["relation"], reason=e.get("reason", ""))

    kb_docs = {c["doc_id"] for c in json.loads(KB_CHUNKS.read_text(encoding="utf8"))}
    guideline_missing = [n["id"] for n in nodes if n["type"] == "GUIDELINE" and n["id"].split(":", 1)[1] not in kb_docs]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    und = g.to_undirected()
    with OUT.open("w", encoding="utf8", newline="\n") as f:
        for n in nodes:
            rec = {"kind": "node", **n, "degree": g.degree(n["id"]),
                   "in_kb_chunks": n["type"] != "GUIDELINE" or n["id"].split(":", 1)[1] in kb_docs}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        for i, e in enumerate(edges, 1):
            s, t = g.nodes[e["source"]], g.nodes[e["target"]]
            rec = {"kind": "edge", "edge_id": i, **e, "source_label": s["label"], "target_label": t["label"],
                   "source_type": s["type"], "target_type": t["type"],
                   "source_department": s.get("department"), "target_department": t.get("department")}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        summary = {"kind": "summary", "nodes": g.number_of_nodes(), "edges": g.number_of_edges(),
                   "components": nx.number_connected_components(und),
                   "nodes_by_type": {t: sum(1 for n in nodes if n["type"] == t) for t in sorted({n["type"] for n in nodes})},
                   "edges_by_relation": {r: sum(1 for e in edges if e["relation"] == r) for r in sorted({e["relation"] for e in edges})},
                   "isolated_nodes": sorted(nx.isolates(und)),
                   "guidelines_without_kb_chunk": guideline_missing,
                   "seed_source": "services/ai-api/app/rag/knowledge_graph.py (CLINICAL_GRAPH_NODES/EDGES)"}
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
