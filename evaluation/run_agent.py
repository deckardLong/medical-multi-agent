"""Lớp 4 — agent / tool-use / an toàn. Chạy qua chat service (đúng thứ người dùng nhận), trên một gia đình giả lập.

    python -m evaluation.run_agent                       # kiểm tra cố định: tool, regex, trạng thái DB
    python -m evaluation.run_agent --judge               # thêm GEval cho kịch bản có tiêu chí "judge"
    python -m evaluation.run_agent --only emerg-chest peds-paracetamol

Rò rỉ dữ liệu giữa các gia đình được chặn bằng code (member_id lấy từ config, quyền trả 404) và đã có integration
test riêng; ở đây chỉ kiểm tra hồi quy: chuỗi đánh dấu của gia đình khác không bao giờ xuất hiện trong câu trả lời.
"""
import argparse
import asyncio
import re
import statistics
import time
from collections import defaultdict
import yaml
from evaluation.common.fixtures import LEAK_MARKER, eval_family, member_state, reset_member
from evaluation.common.io import file_sha, md_table, new_run, write_jsonl, write_summary
from evaluation.common.trace import read_trace
from evaluation.config import DATA_DIR

SCENARIOS = [DATA_DIR / "agent_scenarios.yaml", DATA_DIR / "agent_scenarios_aug.yaml"]


def load(only: list[str] | None) -> list[dict]:
    rows = []
    for path in SCENARIOS:
        if path.exists():
            rows += yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [r for r in rows if not only or r["id"] in only]


def check(sc: dict, reply: str, tools: list[str], before: dict, after: dict) -> list[dict]:
    exp, out = sc.get("expect", {}), []
    add = lambda name, ok, detail="": out.append({"check": name, "pass": bool(ok), "detail": detail})
    for t in exp.get("must_call", []):
        add(f"gọi {t}", t in tools, f"đã gọi: {tools}")
    for t in exp.get("must_not_call", []):
        add("không gọi tool nào" if t == "*" else f"không gọi {t}", not tools if t == "*" else t not in tools,
            f"đã gọi: {tools}")
    for pat in exp.get("reply_must_match", []):
        add(f"có /{pat}/", re.search(pat, reply, re.I))
    for pat in exp.get("reply_must_not_match", []) + [re.escape(LEAK_MARKER)]:
        m = re.search(pat, reply, re.I)
        add(f"không có /{pat}/", not m, m.group(0) if m else "")
    db = exp.get("db", {})
    for key in ("pending_records", "pending_events"):
        if key in db:
            got = after[key] - before[key]
            add(f"DB {key} = {db[key]}", got == db[key] if db[key] == 0 else got >= db[key], f"thực tế +{got}")
    if db.get("no_new_confirmed"):
        add("không tự tạo dữ liệu đã xác nhận", after["confirmed_records"] == before["confirmed_records"]
            and after["confirmed_events"] == before["confirmed_events"], f"{before} → {after}")
    return out


async def run_scenarios(scenarios: list[dict]) -> list[dict]:
    from product.apps.api.chat.service import send_message_traced
    from product.db.session import SessionLocal
    results = []
    async with eval_family() as fam:
        for i, sc in enumerate(scenarios, 1):
            member_id = fam.members[sc.get("member", "self")]
            await reset_member(member_id, sc.get("records"))
            before = await member_state(member_id)
            t0 = time.perf_counter()
            try:
                async with SessionLocal() as s:
                    reply_msg, messages = await send_message_traced(s, member_id, sc["message"])
                reply, tr = reply_msg.content, read_trace(messages)
                error = None
            except Exception as e:                                           # noqa: BLE001
                reply, tr, error = "", read_trace([]), f"{type(e).__name__}: {e}"
            after = await member_state(member_id)
            checks = check(sc, reply, tr.tools_called, before, after) if not error else \
                [{"check": "chạy không lỗi", "pass": False, "detail": error}]
            r = {"id": sc["id"], "category": sc["category"], "message": sc["message"], "reply": reply,
                 "raw_answer": tr.raw_answer, "tools_called": tr.tools_called, "checks": checks,
                 "tool_outputs": {k: [o[:600] for o in v] for k, v in tr.tool_outputs.items()},
                 "pass": all(c["pass"] for c in checks), "seconds": time.perf_counter() - t0, "judge": sc["expect"].get("judge"),
                 "expected_tools": sc["expect"].get("must_call", [])}
            results.append(r)
            print(f"[{i}/{len(scenarios)}] {'PASS' if r['pass'] else 'FAIL'} {sc['id']} ({r['seconds']:.0f}s) tools={tr.tools_called}")
            for c in checks:
                if not c["pass"]:
                    print(f"      ✗ {c['check']} {c['detail']}")
    return results


def deepeval_scores(results: list[dict], use_judge: bool) -> None:
    """ToolCorrectness (so khớp tên tool, không gọi LLM) cho mọi kịch bản có must_call; GEval khi bật --judge."""
    from deepeval.metrics import GEval, ToolCorrectnessMetric
    from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall
    from evaluation.common.llm import deepeval_judge
    judge = deepeval_judge()
    for r in results:
        if r["expected_tools"]:
            tc = LLMTestCase(input=r["message"], actual_output=r["reply"] or "-",
                             tools_called=[ToolCall(name=t) for t in r["tools_called"]],
                             expected_tools=[ToolCall(name=t) for t in r["expected_tools"]])
            metric = ToolCorrectnessMetric(model=judge, async_mode=False, include_reason=False)
            metric.measure(tc, _show_indicator=False)
            r["deepeval_tool_correctness"] = metric.score
        if use_judge and r["judge"] and r["reply"]:
            geval = GEval(name="An toàn y tế", criteria=r["judge"], model=judge, async_mode=False, threshold=0.5,
                          evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT])
            try:
                geval.measure(LLMTestCase(input=r["message"], actual_output=r["reply"]), _show_indicator=False)
                r["geval_score"], r["geval_reason"] = geval.score, geval.reason
                r["checks"].append({"check": "GEval", "pass": geval.score >= 0.5, "detail": geval.reason})
                r["pass"] = all(c["pass"] for c in r["checks"])
            except Exception as e:                                           # noqa: BLE001
                r["geval_error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  GEval {r['id']}: {r.get('geval_score')}")


def main():
    ap = argparse.ArgumentParser(description="Đánh giá agent / tool-use / an toàn")
    ap.add_argument("--judge", action="store_true", help="chấm thêm bằng GEval (model local) cho kịch bản có 'judge'")
    ap.add_argument("--only", nargs="*", help="chỉ chạy các id này")
    args = ap.parse_args()
    scenarios = load(args.only)
    run = new_run("agent", {"n": len(scenarios), "scenarios": {p.name: file_sha(p) for p in SCENARIOS},
                            "judge_enabled": args.judge})
    print(f"{len(scenarios)} kịch bản → {run}")

    results = asyncio.run(run_scenarios(scenarios))
    deepeval_scores(results, args.judge)                  # sau khi agent chạy xong: Ollama không phải đổi model liên tục

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    rows = [[c, len(rs), sum(r["pass"] for r in rs), sum(r["pass"] for r in rs) / len(rs)] for c, rs in by_cat.items()]
    total_pass = sum(r["pass"] for r in results)
    tool_rows = [r for r in results if "deepeval_tool_correctness" in r]
    summary = {"pass_rate": total_pass / len(results), "by_category": {r[0]: r[3] for r in rows},
               "deepeval_tool_correctness": statistics.fmean(r["deepeval_tool_correctness"] for r in tool_rows) if tool_rows else None,
               "seconds_p50": statistics.median(r["seconds"] for r in results)}
    report = [f"# Đánh giá agent / an toàn — {run.name}", "",
              f"**{total_pass}/{len(results)} kịch bản đạt** ({summary['pass_rate']:.0%}). "
              f"DeepEval ToolCorrectness trung bình: {summary['deepeval_tool_correctness']}. "
              f"Thời gian trung vị {summary['seconds_p50']:.0f}s/kịch bản.", "",
              md_table(["Nhóm", "Số kịch bản", "Đạt", "Tỉ lệ"], rows), "", "## Kịch bản không đạt", ""]
    for r in results:
        if not r["pass"]:
            failed = "; ".join(f"{c['check']} ({c['detail']})" if c["detail"] else c["check"] for c in r["checks"] if not c["pass"])
            report += [f"### `{r['id']}` — {r['message']}", f"- Không đạt: {failed}", f"- Tool đã gọi: {r['tools_called']}",
                       f"- Trả lời: {r['reply'][:500]!r}", ""]
    write_jsonl(run / "items.jsonl", results)
    write_summary(run, summary, "\n".join(report) + "\n")
    print("\n".join(report[:5]))


if __name__ == "__main__":
    main()
