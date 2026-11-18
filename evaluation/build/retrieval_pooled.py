"""Gắn nhãn liên quan cho câu hỏi THẬT (queries/query.parquet không có nhãn) theo kiểu TREC pooling:
mỗi câu → tìm bằng dense, sparse, hybrid → gom tài liệu → model chấm mức liên quan 0/1/2 → 20% đánh dấu cho người
kiểm lại (trường "human_review": true — sửa "qrels" trực tiếp trong file nếu nhãn sai).

    python -m evaluation.build.retrieval_pooled --n 100 --depth 10

Hạn chế: tài liệu đúng mà cả 3 cách tìm đều bỏ sót sẽ không có trong nhãn → recall bị ước lượng CAO hơn thực tế.
"""
import argparse
import json
import random
import pyarrow.parquet as pq
from qdrant_client import models as m
from evaluation.common.io import bucket, read_jsonl, split_of
from evaluation.common.llm import ask_json
from evaluation.config import DATA_DIR, ROOT, env

OUT = DATA_DIR / "retrieval_pooled.jsonl"
QUERIES = ROOT / "queries" / "query.parquet"
FIELDS = ["chunk_id", "uid", "doc_id", "start", "end", "p_start", "p_end", "text", "ctx"]

JUDGE = """Bạn chấm mức liên quan giữa một câu hỏi y khoa và một đoạn tài liệu.

CÂU HỎI: {query}

ĐOẠN TÀI LIỆU:
\"\"\"{text}\"\"\"

Thang điểm:
2 = đoạn trả lời trực tiếp, đầy đủ câu hỏi
1 = đoạn liên quan, trả lời được một phần hoặc cung cấp thông tin hữu ích
0 = không liên quan, hoặc chỉ trùng từ khoá mà không giúp trả lời

Chỉ trả về JSON: {{"score": 0|1|2, "reason": "một câu giải thích"}}"""


def single_mode(client, collection: str, query, using: str, k: int, flt) -> list:
    res = client.query_points(collection, query=query, using=using, limit=k, query_filter=flt, with_payload=FIELDS)
    return res.points


def main():
    ap = argparse.ArgumentParser(description="Gắn nhãn liên quan cho câu hỏi thật bằng pooling + model chấm")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--depth", type=int, default=10, help="lấy top-k của mỗi cách tìm để gom")
    args = ap.parse_args()
    if not QUERIES.exists():
        raise SystemExit(f"Thiếu {QUERIES}. Chạy trước: python -m corpus_sync.run_fetch (cần mạng tới HuggingFace).")

    from product.apps.agent.tools.medical_retrieval_tool import _embedder, _searcher, _settings, _client
    from retrieval.index import DENSE, SPARSE

    existing = read_jsonl(OUT) if OUT.exists() else []
    done = {r["qid"] for r in existing}
    queries = pq.read_table(QUERIES).to_pylist()
    rng = random.Random(env.seed)
    rng.shuffle(queries)
    todo = [q for q in queries if f"real-{q['id']}" not in done][: max(0, args.n - len(existing))]
    print(f"{len(existing)} câu đã có; gắn nhãn thêm {len(todo)} câu")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as f:
        for i, q in enumerate(todo, 1):
            text = q["query"]
            enc = _embedder.encode_queries([text])
            dense, sparse = enc.dense[0].tolist(), (enc.sparse[0] if enc.sparse else None)
            runs = {"hybrid": [(c.doc_id, c.text) for c in _searcher.search([(dense, sparse)])[: args.depth]],
                    "dense": [(p.payload["doc_id"], p.payload.get("text")) for p in
                              single_mode(_client, _settings.collection, dense, DENSE, args.depth, _searcher.filter)]}
            if sparse is not None and sparse.indices:
                sv = m.SparseVector(indices=list(sparse.indices), values=list(sparse.values))
                runs["sparse"] = [(p.payload["doc_id"], p.payload.get("text")) for p in
                                  single_mode(_client, _settings.collection, sv, SPARSE, args.depth, _searcher.filter)]
            pool: dict[str, dict] = {}
            for name, hits in runs.items():
                for doc_id, chunk in hits:
                    entry = pool.setdefault(doc_id, {"text": chunk or "", "found_by": []})
                    entry["found_by"].append(name)
            judged = {}
            for doc_id, entry in pool.items():
                try:
                    out = ask_json(env.judge_model, JUDGE.format(query=text, text=entry["text"][:1500]))
                    score = int(out.get("score", 0))
                except Exception as e:                                       # noqa: BLE001
                    score, out = 0, {"reason": f"lỗi judge: {e}"}
                judged[doc_id] = {"score": max(0, min(2, score)), "reason": out.get("reason", ""),
                                  "found_by": entry["found_by"], "text": entry["text"][:400]}
            qid = f"real-{q['id']}"
            row = {"qid": qid, "query": text, "qrels": {d: j["score"] for d, j in judged.items() if j["score"] > 0},
                   "pool": judged, "split": split_of(qid), "origin": "real_pooled",
                   "human_review": bucket("review:" + qid) < 0.2}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{len(existing) + i}] pool={len(pool)} liên quan={len(row['qrels'])}: {text[:80]}")


if __name__ == "__main__":
    main()
