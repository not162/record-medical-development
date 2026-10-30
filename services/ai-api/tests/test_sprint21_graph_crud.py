"""Sprint 21: graf pengetahuan berbasis DB + CRUD admin."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models_graph import GraphNode, GraphEdge
from app.rag import knowledge_graph as kg_module
from app.rag.knowledge_graph import (
    ClinicalKnowledgeGraph, CLINICAL_GRAPH_NODES, CLINICAL_GRAPH_EDGES,
)
from app.routes import graph_crud
from app.security.auth import require_admin


@pytest.fixture()
def env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'graph.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=[GraphNode.__table__, GraphEdge.__table__])
    Session = sessionmaker(bind=engine, autoflush=False)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(graph_crud.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_admin] = lambda: object()
    graph = ClinicalKnowledgeGraph(session_factory=Session)
    yield TestClient(app), graph, app, Session
    engine.dispose()


def test_seed_on_first_use_and_methods(env):
    _, graph, _, Session = env
    data = graph.get_all_graph_data()
    assert data["node_count"] == len(CLINICAL_GRAPH_NODES)
    assert data["edge_count"] == len(CLINICAL_GRAPH_EDGES)
    assert graph.find_node("asma")["id"] == "DIS:Asma_Bronkial"
    sub = graph.get_subgraph("Asma Bronkial")
    assert sub["found"] and len(sub["edges"]) == 4
    assert graph.extract_reasoning_triples("pasien asma bronkial")
    assert graph.optimize_15_percent_code_of_product()["status"] == "SUCCESS"
    assert graph.get_algorithmic_framework("fast")["ml_count"] == 5
    # Seed tidak menggandakan data pada pemanggilan kedua
    graph.get_all_graph_data()
    with Session() as db:
        assert db.query(GraphNode).count() == len(CLINICAL_GRAPH_NODES)


def test_static_fallback_when_db_unavailable():
    def broken():
        raise RuntimeError("db down")
    graph = ClinicalKnowledgeGraph(session_factory=broken)
    data = graph.get_all_graph_data()
    assert data["node_count"] == len(CLINICAL_GRAPH_NODES)
    assert graph.find_node("stemi") is not None


def test_node_crud_and_validation(env):
    client, graph, _, _ = env
    body = {"id": "DIS:Tes", "label": "Penyakit Tes", "type": "disease", "department": "Umum"}
    r = client.post("/api/v1/admin/graph/nodes", json=body)
    assert r.status_code == 201 and r.json()["type"] == "DISEASE"
    assert client.post("/api/v1/admin/graph/nodes", json=body).status_code == 409
    assert client.post("/api/v1/admin/graph/nodes", json={**body, "id": "bad id!"}).status_code == 422
    assert client.post("/api/v1/admin/graph/nodes", json={**body, "id": "DIS:X", "type": "ALIEN"}).status_code == 422

    r = client.put("/api/v1/admin/graph/nodes/DIS:Tes", json={"label": "Baru"})
    assert r.status_code == 200 and r.json()["label"] == "Baru"
    assert client.put("/api/v1/admin/graph/nodes/NOPE", json={"label": "x"}).status_code == 404
    assert graph.find_node("Baru") is not None


def test_edge_crud_and_cascade(env):
    client, graph, _, Session = env
    client.post("/api/v1/admin/graph/seed")
    base = "/api/v1/admin/graph"
    # Referensi simpul tidak ada
    r = client.post(f"{base}/edges", json={"source": "DIS:STEMI", "target": "MED:Tidak_Ada", "relation": "RECOMMENDS"})
    assert r.status_code == 404
    # Relasi tidak valid
    r = client.post(f"{base}/edges", json={"source": "DIS:STEMI", "target": "MED:Ibuprofen", "relation": "LOVES"})
    assert r.status_code == 422
    ok = {"source": "DIS:STEMI", "target": "MED:Ibuprofen", "relation": "CONTRAINDICATES", "reason": "NSAID"}
    r = client.post(f"{base}/edges", json=ok)
    assert r.status_code == 201
    edge_id = r.json()["id"]
    assert client.post(f"{base}/edges", json=ok).status_code == 409

    assert client.delete(f"{base}/edges/{edge_id}").status_code == 200
    assert client.delete(f"{base}/edges/{edge_id}").status_code == 404

    # Hapus simpul menghapus relasinya
    before = graph.get_all_graph_data()["edge_count"]
    r = client.delete(f"{base}/nodes/DIS:STEMI")
    assert r.status_code == 200 and r.json()["edges_removed"] == 5
    after = graph.get_all_graph_data()
    assert after["edge_count"] == before - 5
    with Session() as db:
        assert db.query(GraphEdge).filter(
            (GraphEdge.source == "DIS:STEMI") | (GraphEdge.target == "DIS:STEMI")
        ).count() == 0
    assert client.delete(f"{base}/nodes/DIS:STEMI").status_code == 404


def test_seed_idempotent_and_reset(env):
    client, graph, _, _ = env
    base = "/api/v1/admin/graph"
    r = client.post(f"{base}/seed")
    assert r.json()["nodes_added"] == len(CLINICAL_GRAPH_NODES)
    r = client.post(f"{base}/seed")
    assert r.json() == {"status": "seeded", "nodes_added": 0, "edges_added": 0}
    client.delete(f"{base}/nodes/DIS:DBD")
    r = client.post(f"{base}/seed")
    assert r.json()["nodes_added"] == 1
    r = client.post(f"{base}/seed", json={"reset": True})
    assert r.json()["nodes_added"] == len(CLINICAL_GRAPH_NODES)


def test_admin_only(env):
    client, _, app, _ = env

    def deny():
        raise HTTPException(status_code=403, detail="no")
    app.dependency_overrides[require_admin] = deny
    assert client.post("/api/v1/admin/graph/nodes", json={"id": "A", "label": "A", "type": "DRUG"}).status_code == 403
    assert client.delete("/api/v1/admin/graph/nodes/A").status_code == 403
    assert client.post("/api/v1/admin/graph/seed").status_code == 403
