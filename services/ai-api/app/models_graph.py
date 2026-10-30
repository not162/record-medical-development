from sqlalchemy import Column, String, Text, Integer, ForeignKey, UniqueConstraint

from app.database import Base


class GraphNode(Base):
    """Simpul graf pengetahuan klinis (penyakit, gejala, obat, pedoman, dll.)."""
    __tablename__ = "graph_nodes"

    id = Column(String(100), primary_key=True)
    label = Column(String(300), nullable=False)
    type = Column(String(30), nullable=False, index=True)
    department = Column(String(100), nullable=True)


class GraphEdge(Base):
    """Relasi berarah antar simpul graf pengetahuan."""
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint("source", "target", "relation", name="uq_graph_edge"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target = Column(String(100), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relation = Column(String(40), nullable=False)
    reason = Column(Text, nullable=True)
