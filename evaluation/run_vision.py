"""Lớp 3 — đọc ảnh đơn thuốc (vision_extract_tool: 3 lần đọc song song + đồng thuận).

    python -m evaluation.run_vision --limit 6     # chạy 3 agent (≈4 phút/ảnh trên CPU), lưu cache output thô
    python -m evaluation.run_vision --rescore     # chỉ dùng cache: chấm lại sau khi sửa logic đồng thuận (vài giây)

Cache theo hash(ảnh + model + prompt): đổi prompt hoặc model thì tự chạy lại, đổi code đồng thuận thì không cần.
"""
import argparse
import hashlib
import json
import statistics
import time
from collections import Counter, defaultdict
from evaluation.common.io import file_sha, md_table, new_run, read_jsonl, write_jsonl, write_summary
from evaluation.config import CACHE_DIR, DATA_DIR
from evaluation.metrics.vision import HEADER_FIELDS, MED_FIELDS, deepeval_metric, score_consensus, score_reader

GT = DATA_DIR / "vision_gt.jsonl"
CACHE = CACHE_DIR / "vision"


def cache_key(image_bytes: bytes) -> str:
    from product.apps.agent.tools.vision_extract_tool import prompts
    from product.config import ProductEnv
    e = ProductEnv()
    cfg = f"{e.vlm_model}|{e.vlm_transcribe_model}|{e.llm_model}|{prompts.EXTRACT}|{prompts.TRANSCRIBE}|{prompts.STRUCTURE_FROM_TEXT}"
    return hashlib.sha256(image_bytes + cfg.encode()).hexdigest()[:24]


def read_image(item: dict) -> dict:
    """Chạy kiểm tra chất lượng + 3 agent; trả output thô của từng agent (chưa đồng thuận)."""
    from octochains import Engine
    from product.apps.agent.tools.vision_extract_tool.agents.ocr_then_llm import OcrThenLlm
    from product.apps.agent.tools.vision_extract_tool.agents.vlm_direct import VlmDirect
    from product.apps.agent.tools.vision_extract_tool.agents.vlm_transcribe import VlmTranscribe
    from product.apps.agent.tools.vision_extract_tool.aggregate.aggregator import FieldConsensus
    from product.apps.agent.tools.vision_extract_tool.quality import check_image
    path = str(DATA_DIR / item["image"])
    t0 = time.perf_counter()
    problem = check_image(path)
    if problem:
        return {"quality": problem, "traces": {}, "seconds": time.perf_counter() - t0}
    rep = Engine(agents=[VlmDirect(), OcrThenLlm(), VlmTranscribe()], aggregator=FieldConsensus()).run(path)
    traces = {t.agent_role: (t.output if t.status == "success" else json.dumps({"error": t.error_message})) for t in rep.traces}
    return {"quality": None, "traces": traces, "seconds": time.perf_counter() - t0}


def consensus_from(traces: dict) -> tuple[dict, dict]:
    """Dựng lại đồng thuận từ output thô bằng code HIỆN TẠI (đổi logic đồng thuận không cần chạy lại VLM)."""
    from product.apps.agent.tools.vision_extract_tool.aggregate.consensus import build_consensus
    from product.apps.agent.tools.vision_extract_tool.schema import PrescriptionExtract
    parsed = {}
    for role, out in traces.items():
        data = json.loads(out)
        parsed[role] = None if "error" in data else PrescriptionExtract.model_validate(data)
    ok = [p for p in parsed.values() if p is not None]
    if len(ok) < 2:
        return {"status": "insufficient", "readers_ok": len(ok)}, parsed
    return build_consensus(ok), parsed


def main():
    ap = argparse.ArgumentParser(description="Đánh giá đọc ảnh đơn thuốc")
    ap.add_argument("--split", choices=["test", "dev", "all"], default="all")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--rescore", action="store_true", help="chỉ dùng cache, bỏ qua ảnh chưa có cache")
    args = ap.parse_args()
    if not GT.exists():
        raise SystemExit("Chưa có dữ liệu. Chạy: python -m evaluation.build.vision")
    items = [r for r in read_jsonl(GT) if args.split == "all" or r["split"] == args.split][: args.limit]
    run = new_run("vision", {"n": len(items), "split": args.split, "rescore": args.rescore, "dataset": file_sha(GT)})
    CACHE.mkdir(parents=True, exist_ok=True)
    metric = deepeval_metric()
    from deepeval.test_case import LLMTestCase

    results = []
    for i, it in enumerate(items, 1):
        cpath = CACHE / f"{cache_key((DATA_DIR / it['image']).read_bytes())}.json"
        if cpath.exists():
            raw = json.loads(cpath.read_text(encoding="utf-8"))
        elif args.rescore:
            continue
        else:
            raw = read_image(it)
            cpath.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        r = {"id": it["id"], "variant": it["variant"], "expected_status": it["expected_status"], "seconds": raw["seconds"]}
        if raw["quality"]:
            r.update(status="rejected", quality=raw["quality"])
        else:
            cons, parsed = consensus_from(raw["traces"])
            r.update(status=cons["status"], consensus=cons,
                     readers={role: score_reader(p.model_dump() if p else None, it["truth"]) for role, p in parsed.items()})
            if cons["status"] != "insufficient":
                r["score"] = {k: v for k, v in score_consensus(cons, it["truth"]).items() if k != "outcomes"}
                r["field_outcomes"] = score_consensus(cons, it["truth"])["outcomes"]
                metric.measure(LLMTestCase(input=it["id"], actual_output=cons["status"],
                                           metadata={"consensus": cons, "truth": it["truth"]}))
                r.update(deepeval_score=metric.score, deepeval_pass=metric.is_successful(), deepeval_reason=metric.reason)
        r["gate_ok"] = (r["status"] == "rejected") == (it["expected_status"] == "rejected")
        results.append(r)
        print(f"[{i}/{len(items)}] {it['id']:28} {r['status']:13} ({r['seconds']:.0f}s) "
              f"{'' if r['gate_ok'] else '✗ cổng chất lượng sai '}{r.get('deepeval_reason', r.get('quality', ''))}")

    scored = [r for r in results if "score" in r]
    tot = Counter()
    for r in scored:
        tot.update({k: r["score"][k] for k in ("correct_agree", "silent_error", "flagged_recoverable",
                                               "flagged_unrecoverable", "missed", "hallucinated_confirmed", "hallucinated_flagged")})
    accepted = tot["correct_agree"] + tot["silent_error"]
    flagged = tot["flagged_recoverable"] + tot["flagged_unrecoverable"]
    fields_total = accepted + flagged + tot["missed"]
    per_field = defaultdict(Counter)
    for r in scored:
        for f, o in r["field_outcomes"]:
            per_field[f][o] += 1
    readers = defaultdict(lambda: [0, 0, 0])
    for r in scored:
        for role, s in r["readers"].items():
            readers[role][0] += s["correct"]; readers[role][1] += s["total"]; readers[role][2] += s["hallucinated"]
    by_variant = defaultdict(list)
    for r in scored:
        by_variant[r["variant"]].append(r)

    summary = {
        "images": len(results), "scored": len(scored),
        "quality_gate_accuracy": statistics.fmean(r["gate_ok"] for r in results) if results else None,
        "silent_error_rate": tot["silent_error"] / accepted if accepted else None,
        "images_with_silent_error": sum(r["score"]["image_silent_error"] for r in scored),
        "flag_rate": flagged / fields_total if fields_total else None,
        "flag_recoverable_rate": tot["flagged_recoverable"] / flagged if flagged else None,
        "auto_accepted_correct_rate": tot["correct_agree"] / fields_total if fields_total else None,
        "missed_fields": tot["missed"], "hallucinated_confirmed": tot["hallucinated_confirmed"],
        "deepeval_pass_rate": statistics.fmean(r["deepeval_pass"] for r in scored) if scored else None,
        "reader_field_accuracy": {k: v[0] / v[1] for k, v in readers.items() if v[1]},
        "seconds_p50": statistics.median(r["seconds"] for r in results) if results else None,
    }
    pct = lambda x: "—" if x is None else f"{x:.1%}"
    report = [f"# Đánh giá đọc ảnh đơn thuốc — {run.name}", "",
              f"{len(results)} ảnh ({len(scored)} ảnh được chấm đồng thuận). Thời gian trung vị "
              f"{summary['seconds_p50'] or 0:.0f}s/ảnh.", "", "## An toàn của cơ chế đồng thuận", "",
              md_table(["Chỉ số", "Giá trị", "Ý nghĩa"], [
                  ["**Tỉ lệ lỗi im lặng**", pct(summary["silent_error_rate"]),
                   "Trong các trường được tự đồng thuận, bao nhiêu % sai. Mục tiêu: 0"],
                  ["Ảnh 'an toàn' nhưng có sai", summary["images_with_silent_error"], "Ảnh trạng thái agree mà vẫn có trường sai / thiếu thuốc"],
                  ["Thuốc bịa được xác nhận", tot["hallucinated_confirmed"], "≥2 lần đọc cùng bịa một thuốc"],
                  ["Trường bị đánh dấu cần kiểm tra", pct(summary["flag_rate"]), "Cao = người dùng phải sửa nhiều"],
                  ["... trong đó gỡ được bằng lựa chọn", pct(summary["flag_recoverable_rate"]), "Đáp án đúng có trong các lựa chọn"],
                  ["Tự đồng thuận và đúng", pct(summary["auto_accepted_correct_rate"]), "Không cần người dùng sửa"],
                  ["Trường bỏ sót (thiếu thuốc)", tot["missed"], ""],
                  ["Cổng chất lượng ảnh đúng", pct(summary["quality_gate_accuracy"]), "Ảnh mờ/nhỏ phải bị từ chối"],
                  ["DeepEval PrescriptionSafety đạt", pct(summary["deepeval_pass_rate"]), "Ảnh không có lỗi im lặng"]]),
              "", "## Theo trường", "",
              md_table(["Trường", "Đúng", "Lỗi im lặng", "Đánh dấu (gỡ được)", "Đánh dấu (không gỡ được)", "Bỏ sót"],
                       [[f, c["correct_agree"], c["silent_error"], c["flagged_recoverable"], c["flagged_unrecoverable"],
                         c["missed"]] for f in HEADER_FIELDS + MED_FIELDS if (c := per_field[f])]),
              "", "## Từng agent (trước đồng thuận)", "",
              md_table(["Agent", "Độ đúng từng trường", "Thuốc bịa"],
                       [[k, pct(v[0] / v[1]), v[2]] for k, v in readers.items() if v[1]]),
              "", "## Theo loại ảnh", "",
              md_table(["Loại ảnh", "Số ảnh", "Lỗi im lặng", "Tự đồng thuận đúng"],
                       [[v, len(rs), sum(r["score"]["silent_error"] for r in rs),
                         pct(sum(r["score"]["correct_agree"] for r in rs) /
                             max(1, sum(sum(r["score"][k] for k in ("correct_agree", "silent_error", "flagged_recoverable",
                                                                       "flagged_unrecoverable", "missed")) for r in rs)))]
                        for v, rs in by_variant.items()]),
              "", "## Ảnh có lỗi im lặng", ""]
    report += [f"- `{r['id']}`: {r['deepeval_reason']}" for r in scored if not r["deepeval_pass"]][:20]
    write_jsonl(run / "items.jsonl", results)
    write_summary(run, summary, "\n".join(report) + "\n")
    print("\n".join(report[:18]))


if __name__ == "__main__":
    main()
