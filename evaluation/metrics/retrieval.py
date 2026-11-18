"""Chỉ số truy xuất ở cấp TÀI LIỆU. qrels: {doc_id: mức liên quan 0|1|2}; 0 = không liên quan."""
import math


def dedupe(doc_ids: list[str]) -> list[str]:
    """Nhiều đoạn của cùng một bài chỉ tính một lần, giữ thứ hạng của đoạn đầu tiên."""
    seen, out = set(), []
    for d in doc_ids:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def hit_at_k(ranked: list[str], qrels: dict[str, int], k: int) -> float:
    return float(any(qrels.get(d, 0) > 0 for d in ranked[:k]))


def recall_at_k(ranked: list[str], qrels: dict[str, int], k: int) -> float:
    relevant = {d for d, g in qrels.items() if g > 0}
    return len(relevant & set(ranked[:k])) / len(relevant) if relevant else 0.0


def mrr(ranked: list[str], qrels: dict[str, int], k: int) -> float:
    for i, d in enumerate(ranked[:k], 1):
        if qrels.get(d, 0) > 0:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], qrels: dict[str, int], k: int) -> float:
    gain = lambda g: 2 ** g - 1                            # mức 2 (rất liên quan) nặng gấp 3 mức 1
    dcg = sum(gain(qrels.get(d, 0)) / math.log2(i + 1) for i, d in enumerate(ranked[:k], 1))
    ideal = sorted((g for g in qrels.values() if g > 0), reverse=True)[:k]
    idcg = sum(gain(g) / math.log2(i + 1) for i, g in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def all_metrics(ranked: list[str], qrels: dict[str, int], ks: tuple[int, ...]) -> dict[str, float]:
    out = {}
    for k in ks:
        out[f"hit@{k}"] = hit_at_k(ranked, qrels, k)
        out[f"recall@{k}"] = recall_at_k(ranked, qrels, k)
        out[f"mrr@{k}"] = mrr(ranked, qrels, k)
        out[f"ndcg@{k}"] = ndcg_at_k(ranked, qrels, k)
    return out
