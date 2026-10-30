import sqlite3
import re
from typing import List, Tuple

class FTSStore:
    def init_table(self, conn: sqlite3.Connection):
        """Initializes the FTS5 virtual table for sparse keyword retrieval."""
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                chunk_id UNINDEXED,
                doc_id,
                department,
                title,
                content_text,
                tokenize = 'unicode61 remove_diacritics 2'
            );
        """)
        conn.commit()

    def insert_chunk(
        self,
        conn: sqlite3.Connection,
        chunk_id: str,
        doc_id: str,
        department: str,
        title: str,
        content_text: str
    ):
        """Inserts a chunk into the FTS5 table."""
        # Clean existing record if re-indexing
        conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?;", (chunk_id,))
        conn.execute(
            "INSERT INTO fts_chunks(chunk_id, doc_id, department, title, content_text) VALUES (?, ?, ?, ?, ?);",
            (chunk_id, doc_id, department, title, content_text)
        )
        conn.commit()

    def delete_chunk(self, conn: sqlite3.Connection, chunk_id: str):
        """Menghapus chunk dari tabel FTS5."""
        conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?;", (chunk_id,))
        conn.commit()

    def search(
        self,
        conn: sqlite3.Connection,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Executes BM25 ranking keyword search over FTS5 virtual table.
        Returns list of (chunk_id, bm25_score).
        """
        # Sanitize query for FTS5 (escape special symbols)
        cleaned = re.sub(r"[^\w\s]", " ", query).strip()
        tokens = [t for t in cleaned.split() if len(t) > 1]
        if not tokens:
            return []

        fts_match_query = " OR ".join(tokens)
        try:
            cursor = conn.execute(
                """
                SELECT chunk_id, bm25(fts_chunks) as rank_score
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY rank_score ASC
                LIMIT ?;
                """,
                (fts_match_query, top_k)
            )
            # In SQLite FTS5 bm25(), lower/more negative values indicate higher relevance
            return cursor.fetchall()
        except sqlite3.OperationalError:
            return []

fts_store = FTSStore()
