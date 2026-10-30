import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models_graph import GraphNode, GraphEdge
from app.rag.knowledge_graph import (
    ALLOWED_NODE_TYPES, ALLOWED_RELATIONS, seed_graph,
)
from app.security.auth import require_admin

router = APIRouter(prefix="/admin/graph", tags=["Knowledge Graph CRUD"])

_NODE_ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,100}$")


def _check_type(value: str) -> str:
    v = value.strip().upper()
    if v not in ALLOWED_NODE_TYPES:
        raise ValueError(f"type harus salah satu dari: {', '.join(ALLOWED_NODE_TYPES)}")
    return v


class NodeCreate(BaseModel):
    id: str = Field(..., description="Contoh: DIS:Asma_Bronkial")
    label: str = Field(..., min_length=1, max_length=300)
    type: str
    department: Optional[str] = Field(default="", max_length=100)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        v = v.strip()
        if not _NODE_ID_RE.match(v):
            raise ValueError("id hanya boleh huruf, angka, '_', '.', ':', '-' (maks 100 karakter)")
        return v

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        return _check_type(v)


class NodeUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=300)
    type: Optional[str] = None
    department: Optional[str] = Field(default=None, max_length=100)

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v):
        return None if v is None else _check_type(v)


class EdgeCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=100)
    relation: str = Field(..., max_length=50)
    reason: Optional[str] = Field(default="", max_length=2000)

    @field_validator("relation")
    @classmethod
    def _valid_relation(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ALLOWED_RELATIONS:
            raise ValueError(f"relation harus salah satu dari: {', '.join(ALLOWED_RELATIONS)}")
        return v


class SeedRequest(BaseModel):
    reset: bool = False


def _node_dict(n: GraphNode) -> dict:
    return {"id": n.id, "label": n.label, "type": n.type, "department": n.department or ""}


def _edge_dict(e: GraphEdge) -> dict:
    return {"id": e.id, "source": e.source, "target": e.target,
            "relation": e.relation, "reason": e.reason or ""}


@router.get("/schema")
def graph_schema(admin: User = Depends(require_admin)):
    """Daftar tipe simpul dan nama relasi yang diizinkan."""
    return {"node_types": ALLOWED_NODE_TYPES, "relations": ALLOWED_RELATIONS}


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
def create_node(
    payload: NodeCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.get(GraphNode, payload.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Simpul '{payload.id}' sudah ada.")
    node = GraphNode(id=payload.id, label=payload.label.strip(), type=payload.type,
                     department=(payload.department or "").strip())
    db.add(node)
    db.commit()
    return _node_dict(node)


@router.put("/nodes/{node_id}")
def update_node(
    node_id: str,
    payload: NodeUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    node = db.get(GraphNode, node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simpul tidak ditemukan.")
    if payload.label is not None:
        node.label = payload.label.strip()
    if payload.type is not None:
        node.type = payload.type
    if payload.department is not None:
        node.department = payload.department.strip()
    db.commit()
    return _node_dict(node)


@router.delete("/nodes/{node_id}")
def delete_node(
    node_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    node = db.get(GraphNode, node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simpul tidak ditemukan.")
    # Cascade manual (SQLite tidak selalu menegakkan FK ON DELETE CASCADE)
    removed = (
        db.query(GraphEdge)
        .filter((GraphEdge.source == node_id) | (GraphEdge.target == node_id))
        .delete(synchronize_session=False)
    )
    db.delete(node)
    db.commit()
    return {"status": "deleted", "id": node_id, "edges_removed": removed}


@router.post("/edges", status_code=status.HTTP_201_CREATED)
def create_edge(
    payload: EdgeCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    for end in (payload.source, payload.target):
        if db.get(GraphNode, end) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simpul '{end}' tidak ditemukan; relasi harus mereferensikan simpul yang ada.",
            )
    dup = db.query(GraphEdge).filter(
        GraphEdge.source == payload.source,
        GraphEdge.target == payload.target,
        GraphEdge.relation == payload.relation,
    ).first()
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Relasi yang sama sudah ada.")
    edge = GraphEdge(source=payload.source, target=payload.target,
                     relation=payload.relation, reason=(payload.reason or "").strip())
    db.add(edge)
    db.commit()
    return _edge_dict(edge)


@router.delete("/edges/{edge_id}")
def delete_edge(
    edge_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    edge = db.get(GraphEdge, edge_id)
    if edge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relasi tidak ditemukan.")
    db.delete(edge)
    db.commit()
    return {"status": "deleted", "id": edge_id}


@router.post("/seed")
def seed_graph_endpoint(
    payload: Optional[SeedRequest] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Mengisi graf dari data klinis standar (idempoten). reset=true mengosongkan dulu."""
    result = seed_graph(db, reset=bool(payload and payload.reset))
    return {"status": "seeded", **result}
