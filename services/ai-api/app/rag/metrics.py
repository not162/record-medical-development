import math
from typing import List, Dict, Any, Set

def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Precision@K = |Retrieved@K intersect Relevant| / K"""
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k

def recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Recall@K = |Retrieved@K intersect Relevant| / |Relevant|"""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)

def mean_reciprocal_rank(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
    """Calculates Reciprocal Rank (1 / rank of first relevant item)."""
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0

def ndcg_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Normalized Discounted Cumulative Gain (nDCG@K)."""
    top_k = retrieved_ids[:k]
    dcg = 0.0
    for rank, doc_id in enumerate(top_k, start=1):
        rel = 1.0 if doc_id in relevant_ids else 0.0
        dcg += rel / math.log2(rank + 1)

    # Ideal DCG
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg

def evaluate_retrieval(retrieved_ids: List[str], relevant_ids: Set[str], k: int = 3) -> Dict[str, float]:
    """Computes a full retrieval benchmark suite for a query."""
    return {
        f"Precision@{k}": round(precision_at_k(retrieved_ids, relevant_ids, k), 4),
        f"Recall@{k}": round(recall_at_k(retrieved_ids, relevant_ids, k), 4),
        "MRR": round(mean_reciprocal_rank(retrieved_ids, relevant_ids), 4),
        f"nDCG@{k}": round(ndcg_at_k(retrieved_ids, relevant_ids, k), 4),
    }
