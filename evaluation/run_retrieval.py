"""Lớp 1 — truy xuất (medical_retrieval_tool).

    python -m evaluation.run_retrieval                     # tập test, chỉ số cấp tài liệu
    python -m evaluation.run_retrieval --ragas --limit 30  # thêm Ragas context_precision / context_recall (chậm)

Dùng đúng embedder + searcher + cấu hình của tool (không qua rerank, agent nhận 5 đoạn đầu), nên số đo ở cột
"tool@5" là thứ agent thật sự nhìn thấy; các cột @10/@20 dùng để phân biệt "không tìm thấy" với "xếp hạng sai".
"""
import argparse
import asyncio
import math
import statistics
import time
from collections import defaultdict
from evaluation.common.io import file_sha, md_table, new_run, read_jsonl, write_jsonl, write_summary
from evaluation.config import DATA_DIR
from evaluation.metrics.retrieval import all_metrics, dedupe

DATASETS = {"synthetic": DATA_DIR / "retrieval_synthetic.jsonl", "real_pooled": DATA_DIR / "retrieval_pooled.jsonl"}
TOOL_CHUNKS = 5                     # medical_retrieval_tool trả candidates[:5]
TOOL_CHARS = 500                    # ... và cắt mỗi đoạn còn 500 ký tự
KS = (1, 3, 5, 10, 20)


def load(split: str, limit: int | None) -> list[dict]:
    rows = []
    for name, path in DATASETS.items():
        if path.exists():
            rows += [r for r in read_jsonl(path) if split == "all" or r["split"] == split]
    return rows[:limit] if limit else rows


def mean(xs: list[float]) -> float:
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return statistics.fmean(xs) if xs else float("nan")


async def ragas_scores(rows: list[dict]) -> None:
    """Ragas cần câu trả lời mẫu → chỉ chạy cho câu có "reference" (bộ tự sinh)."""
    from ragas.metrics.collections import ContextPrecisionWithReference, ContextRecall
    from evaluation.common.llm import ragas_llm, ragas_score
    llm = ragas_llm()
    precision, recall = ContextPrecisionWithReference(llm=llm), ContextRecall(llm=llm)
    todo = [r for r in rows if r.get("reference")]
    for i, r in enumerate(todo, 1):
        for name, metric, kwargs in (
                ("ragas_context_precision", precision,
                 dict(user_input=r["query"], reference=r["reference"], retrieved_contexts=r["_contexts"])),
                ("ragas_context_recall", recall,
                 dict(user_input=r["query"], retrieved_contexts=r["_contexts"], reference=r["reference"]))):
            r[name], err = await ragas_score(metric, **kwargs)
            if err:
                r.setdefault("errors", []).append(f"{name}: {err}")
        print(f"  ragas {i}/{len(todo)}  precision={r['ragas_context_precision']:.2f} recall={r['ragas_context_recall']:.2f}")


def main():
    ap = argparse.ArgumentParser(description="Đánh giá lớp truy xuất")
    ap.add_argument("--split", choices=["test", "dev", "all"], default="test")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ragas", action="store_true", help="thêm Ragas context_precision/context_recall (judge local, chậm)")
    args = ap.parse_args()

    rows = load(args.split, args.limit)
    if not rows:
        raise SystemExit("Chưa có dữ liệu. Chạy: python -m evaluation.build.retrieval_synthetic")
    from product.apps.agent.tools.medical_retrieval_tool import _client, _embedder, _searcher, _settings
    points = _client.get_collection(_settings.collection).points_count
    run = new_run("retrieval", {"collection": _settings.collection, "indexed_points": points, "split": args.split,
                                "n": len(rows), "datasets": {k: file_sha(p) for k, p in DATASETS.items()},
                                "search_cfg": _settings.retrieve.search.model_dump(mode="json")})
    print(f"{len(rows)} câu · collection {_settings.collection} ({points:,} điểm) → {run}")

    for i, r in enumerate(rows, 1):
        t0 = time.perf_counter()
        enc = _embedder.encode_queries([r["query"]])
        cands = _searcher.search([(enc.dense[0].tolist(), enc.sparse[0] if enc.sparse else None)])
        r["latency_ms"] = (time.perf_counter() - t0) * 1000
        pool_docs = dedupe([c.doc_id for c in cands])
        tool_docs = dedupe([c.doc_id for c in cands[:TOOL_CHUNKS]])
        r["_contexts"] = [(c.text or "")[:TOOL_CHARS] for c in cands[:TOOL_CHUNKS]]
        r["metrics"] = all_metrics(pool_docs, r["qrels"], KS)
        r["metrics"].update({f"tool_{k}": v for k, v in all_metrics(tool_docs, r["qrels"], (TOOL_CHUNKS,)).items()})
        gold = [d for d in r["qrels"] if r["qrels"][d] > 0]
        r["gold_rank"] = next((pool_docs.index(d) + 1 for d in pool_docs if d in gold), None)
        r["top_docs"] = pool_docs[:5]
        if i % 20 == 0:
            print(f"  {i}/{len(rows)}")

    if args.ragas:
        asyncio.run(ragas_scores(rows))

    keys = [f"tool_hit@{TOOL_CHUNKS}", f"tool_mrr@{TOOL_CHUNKS}", f"tool_ndcg@{TOOL_CHUNKS}", "hit@1", "hit@10",
            "hit@20", "recall@20", "mrr@20", "ndcg@10"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups["TẤT CẢ"].append(r)
        groups[f"nguồn={r['origin']}"].append(r)
        if r.get("doc_lang"):
            groups[f"tài liệu {r['doc_lang']} → hỏi {r['query_lang']}"].append(r)
    table = {g: {k: mean([r["metrics"][k] for r in rs]) for k in keys} | {"n": len(rs)} for g, rs in groups.items()}
    if args.ragas:
        for g, rs in groups.items():
            table[g]["ragas_context_precision"] = mean([r.get("ragas_context_precision") for r in rs])
            table[g]["ragas_context_recall"] = mean([r.get("ragas_context_recall") for r in rs])

    not_found = [r for r in rows if r["gold_rank"] is None]
    misranked = [r for r in rows if r["gold_rank"] and r["metrics"][f"tool_hit@{TOOL_CHUNKS}"] == 0]
    summary = {"by_group": table, "latency_ms_p50": statistics.median(r["latency_ms"] for r in rows),
               "not_found_in_pool": len(not_found), "found_but_outside_tool_top5": len(misranked)}

    cols = ["Nhóm", "n"] + keys + (["ragas_context_precision", "ragas_context_recall"] if args.ragas else [])
    report = [f"# Đánh giá truy xuất — {run.name}", "",
              f"Collection `{_settings.collection}` ({points:,} điểm), tập `{args.split}`, {len(rows)} câu. "
              f"`tool@5` = 5 đoạn đầu mà agent thật sự nhận (chưa rerank).", "",
              md_table(cols, [[g, t["n"]] + [t[k] for k in cols[2:]] for g, t in table.items()]), "",
              f"- Độ trễ trung vị: {summary['latency_ms_p50']:.0f} ms/câu",
              f"- **Không có trong top-{max(KS)} (lỗi tìm kiếm):** {len(not_found)} câu",
              f"- **Có trong nhóm ứng viên nhưng ngoài 5 đoạn agent nhận (lỗi xếp hạng — rerank có thể cứu):** {len(misranked)} câu",
              "", "## Ví dụ không tìm thấy", ""]
    report += [f"- `{r['qid']}` {r['query']}" for r in not_found[:15]]
    report += ["", "## Ví dụ xếp hạng sai (hạng của tài liệu đúng)", ""]
    report += [f"- hạng {r['gold_rank']}: {r['query']}" for r in misranked[:15]]
    if any(r.get("origin") == "synthetic" for r in rows):
        report += ["", "> Bộ tự sinh chỉ có 1 tài liệu đúng mỗi câu; nếu cùng nội dung có ở bài khác (bài trùng giữa các "
                   "nguồn) thì vẫn bị tính là sai → số đo này là cận dưới."]

    write_jsonl(run / "items.jsonl", ({k: v for k, v in r.items() if k != "_contexts"} for r in rows))
    write_summary(run, summary, "\n".join(report) + "\n")
    print("\n".join(report[:6]))


if __name__ == "__main__":
    main()
