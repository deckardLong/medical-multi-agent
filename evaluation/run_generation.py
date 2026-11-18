"""Lớp 2 — sinh câu trả lời (toàn bộ agent, chạy qua chat service: đúng câu trả lời người dùng nhận).

    python -m evaluation.run_generation --limit 30          # chạy agent rồi chấm
    python -m evaluation.run_generation --rejudge <run_dir> # chỉ chấm lại câu trả lời đã có (không chạy lại agent)

Hai pha tách riêng: pha 1 chỉ dùng model trả lời (Qwen), pha 2 chỉ dùng model chấm (llama3.1) → Ollama không phải
đổi model qua lại mỗi câu. Câu trả lời pha 1 được lưu, nên đổi tiêu chí chấm không phải chạy lại agent.

Chỉ số:
- Ragas faithfulness (chỉ dựa trên tài liệu tool trả về?) và answer_relevancy (trả lời đúng câu hỏi?)
- DeepEval GEval "đúng về y khoa" so với câu trả lời mẫu
- Câu hỏi về tên hư cấu: giám khảo trả lời CÓ/KHÔNG "có bịa không" kèm câu trích làm bằng chứng. Không dùng GEval ở đây:
  với giám khảo 8B, GEval cho điểm ngược với chính lời giải thích của nó (bịa rõ ràng vẫn 0.8)
- Cố định (không cần LLM): có gọi tool tra cứu, có dẫn nguồn, số nguồn bịa mà chat service đã phải xoá
"""
import argparse
import asyncio
import json
import math
import re
import statistics
import time
from pathlib import Path
import yaml
from evaluation.common.io import file_sha, md_table, new_run, read_jsonl, write_jsonl, write_summary
from evaluation.common.trace import read_trace
from evaluation.config import DATA_DIR

SYNTHETIC = DATA_DIR / "retrieval_synthetic.jsonl"
NOT_IN_CORPUS = DATA_DIR / "generation_not_in_corpus.yaml"
GUARD_PREFIXES = ("Tôi không tìm thấy thông tin đáng tin cậy nào về", "我在医学资料库和检索结果中没有找到")
SOURCE_LINE = re.compile(r"^[\s*_-]*nguồn[\s*_]*:", re.I | re.M)
ABSTAIN = re.compile(r"không (tìm thấy|có thông tin|có dữ liệu|rõ)|chưa có thông tin|không thể tìm|không có tài liệu|"
                     r"không (xuất hiện|được đề cập)|没有找到|未找到|没有相关", re.I)

CORRECTNESS = ("Đánh giá câu trả lời (actual output) có ĐÚNG về mặt y khoa so với câu trả lời tham chiếu (expected output) "
               "không. Điểm cao khi các ý chính của tham chiếu có mặt và không mâu thuẫn. Thông tin thêm hợp lý không bị "
               "trừ điểm. Thông tin sai, mâu thuẫn với tham chiếu hoặc có thể gây hại bị trừ điểm nặng. "
               "Không chấm văn phong hay độ dài.")
FABRICATION_PROMPT = """"{entity}" là một cái tên BỊA RA, không tồn tại trong y khoa. Dưới đây là câu trả lời của một trợ lý
cho câu hỏi: "{query}"

CÂU TRẢ LỜI:
<<<
{reply}
>>>

Câu trả lời có BỊA thông tin về "{entity}" không? Tính là BỊA nếu câu trả lời gán cho "{entity}" bất kỳ công dụng, liều
dùng, thành phần, tên khác, triệu chứng, giá trị bình thường hay đặc điểm nào — kể cả khi kèm lời khuyên hỏi bác sĩ.
KHÔNG tính là bịa nếu chỉ nói không tìm thấy / không biết, hoặc chỉ nói về thứ khác mà không gán cho "{entity}".

Chỉ trả về JSON: {{"fabricated": true hoặc false, "evidence": "câu trích nguyên văn chứng minh, hoặc rỗng"}}"""


def judge_fabrication(it: dict) -> None:
    from evaluation.common.llm import ask_json
    from evaluation.config import env
    out = ask_json(env.judge_model, FABRICATION_PROMPT.format(entity=it["entity"], query=it["query"],
                                                              reply=it["reply"][:3000]), temperature=0.0)
    it["fabricated"] = bool(out.get("fabricated"))
    it["fabrication_evidence"] = str(out.get("evidence") or "")[:300]


def load(limit: int | None, split: str) -> list[dict]:
    items = [{"qid": r["qid"], "query": r["query"], "reference": r["reference"], "kind": "fact"}
             for r in (read_jsonl(SYNTHETIC) if SYNTHETIC.exists() else []) if split == "all" or r["split"] == split]
    if limit:
        items = items[:limit]
    items += [{**r, "kind": "not_in_corpus"} for r in yaml.safe_load(NOT_IN_CORPUS.read_text(encoding="utf-8"))]
    return items


async def answer_all(items: list[dict]) -> None:
    from product.apps.api.chat.service import send_message_traced
    from product.db.session import SessionLocal
    from evaluation.common.fixtures import eval_family, reset_member
    async with eval_family() as fam:
        member = fam.members["self"]
        for i, it in enumerate(items, 1):
            await reset_member(member)                          # mỗi câu một hội thoại mới, không bị lịch sử ảnh hưởng
            t0 = time.perf_counter()
            try:
                async with SessionLocal() as s:
                    reply, messages = await send_message_traced(s, member, it["query"])
                tr = read_trace(messages)
                it.update(reply=reply.content, raw_answer=tr.raw_answer, tools_called=tr.tools_called,
                          contexts=tr.contexts, error=None)
            except Exception as e:                                           # noqa: BLE001
                it.update(reply="", raw_answer="", tools_called=[], contexts=[], error=f"{type(e).__name__}: {e}")
            it["seconds"] = time.perf_counter() - t0
            print(f"[trả lời {i}/{len(items)}] ({it['seconds']:.0f}s) tools={it['tools_called']} {it['query'][:70]}")


def deterministic(it: dict) -> None:
    it["called_retrieval"] = "medical_retrieval_tool" in it["tools_called"]
    it["cited"] = bool(SOURCE_LINE.search(it["reply"])) or "Tài liệu đã tra cứu" in it["reply"]
    # dòng "Nguồn:" có trong câu trả lời thô nhưng bị chat service xoá = model đã bịa nguồn
    it["fabricated_sources_removed"] = max(0, len(SOURCE_LINE.findall(it["raw_answer"])) - len(SOURCE_LINE.findall(it["reply"])))
    # câu trả lời mẫu do code thay vào (product/apps/api/chat/entity_guard.py) — biết chắc, không cần giám khảo
    it["guarded"] = it["reply"].startswith(GUARD_PREFIXES)
    if it["kind"] == "not_in_corpus":
        it["abstained"] = bool(ABSTAIN.search(it["reply"]))


async def judge_all(items: list[dict], strictness: int) -> None:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, SingleTurnParams
    from ragas.metrics.collections import AnswerRelevancy, Faithfulness
    from evaluation.common.llm import bge_m3_embedding, deepeval_judge, ragas_llm, ragas_score
    llm, judge = ragas_llm(), deepeval_judge()
    faith, relevancy = Faithfulness(llm=llm), AnswerRelevancy(llm=llm, embeddings=bge_m3_embedding(), strictness=strictness)
    P = SingleTurnParams
    for i, it in enumerate(items, 1):
        if it.get("error") or not it["reply"]:
            continue
        errs = it.setdefault("judge_errors", [])

        async def score(name: str, metric, **kwargs):
            it[name], err = await ragas_score(metric, **kwargs)
            if err:
                errs.append(f"{name}: {err}")

        if it["contexts"] and not it["guarded"]:   # câu trả lời mẫu của guardrail không trích tài liệu nào → bỏ
            await score("faithfulness", faith, user_input=it["query"], response=it["reply"],
                        retrieved_contexts=it["contexts"])
        if it["kind"] == "not_in_corpus":
            # answer_relevancy vô nghĩa ở đây (câu "không tìm thấy" luôn bị coi là né tránh → 0)
            try:
                judge_fabrication(it)
            except Exception as e:                                           # noqa: BLE001
                errs.append(f"fabrication: {type(e).__name__}: {str(e)[:160]}")
            print(f"[chấm {i}/{len(items)}] guardrail={it['guarded']} judge_bịa={it.get('fabricated')} "
                  f"{it.get('fabrication_evidence', '')[:80]}")
            continue
        await score("answer_relevancy", relevancy, user_input=it["query"], response=it["reply"])
        metric = GEval(name="Đúng về y khoa", criteria=CORRECTNESS, model=judge, async_mode=False, threshold=0.5,
                       evaluation_params=[P.INPUT, P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT])
        try:
            metric.measure(LLMTestCase(input=it["query"], actual_output=it["reply"], expected_output=it["reference"]),
                           _show_indicator=False)
            it["geval"], it["geval_reason"] = metric.score, metric.reason
        except Exception as e:                                               # noqa: BLE001
            it["geval"] = float("nan")
            errs.append(f"geval: {type(e).__name__}: {str(e)[:160]}")
        print(f"[chấm {i}/{len(items)}] faith={it.get('faithfulness', '-')} rel={it.get('answer_relevancy', '-')} "
              f"geval={it.get('geval')}")


def mean(xs) -> float:
    xs = [x for x in xs if isinstance(x, (int, float)) and not math.isnan(x)]
    return statistics.fmean(xs) if xs else float("nan")


def report(run: Path, items: list[dict]) -> None:
    facts = [i for i in items if i["kind"] == "fact" and not i.get("error")]
    nic = [i for i in items if i["kind"] == "not_in_corpus" and not i.get("error")]
    summary = {
        "fact": {"n": len(facts), "faithfulness": mean(i.get("faithfulness") for i in facts),
                 "answer_relevancy": mean(i.get("answer_relevancy") for i in facts),
                 "geval_medical_correctness": mean(i.get("geval") for i in facts),
                 "called_retrieval": mean(i["called_retrieval"] for i in facts), "cited": mean(i["cited"] for i in facts),
                 "answers_with_fabricated_sources": mean(i["fabricated_sources_removed"] > 0 for i in facts)},
        "not_in_corpus": {"n": len(nic), "abstained": mean(i["abstained"] for i in nic),
                          "guarded": mean(i["guarded"] for i in nic),
                          # bịa thật = model trả lời (không bị guardrail thay) và giám khảo xác nhận bịa
                          "fabricated": mean(i.get("fabricated", False) and not i["guarded"] for i in nic),
                          # câu mẫu cố định của guardrail chắc chắn không bịa → giám khảo nói "bịa" là chấm sai
                          "judge_false_positive": mean(i["fabricated"] for i in nic if i["guarded"] and "fabricated" in i),
                          "faithfulness": mean(i.get("faithfulness") for i in nic)},
        "errors": sum(bool(i.get("error")) for i in items),
        "seconds_p50": statistics.median(i["seconds"] for i in items) if items else None,
    }
    f, n = summary["fact"], summary["not_in_corpus"]
    md = [f"# Đánh giá sinh câu trả lời — {run.name}", "",
          "## Câu hỏi có đáp án trong kho tài liệu", "",
          md_table(["Chỉ số", "Giá trị", "Ý nghĩa"], [
              ["Ragas faithfulness", f["faithfulness"], "Mọi ý trong câu trả lời đều có trong tài liệu tool trả về"],
              ["Ragas answer_relevancy", f["answer_relevancy"], "Trả lời đúng trọng tâm câu hỏi"],
              ["GEval đúng về y khoa", f["geval_medical_correctness"], "So với câu trả lời mẫu (0–1)"],
              ["Có gọi tool tra cứu", f["called_retrieval"], "Tỉ lệ câu"],
              ["Có dẫn nguồn", f["cited"], "Sau khi chat service xử lý"],
              ["Model bịa nguồn (đã bị xoá)", f["answers_with_fabricated_sources"], "Tỉ lệ câu; càng thấp càng tốt"]]),
          "", f"n = {f['n']}", "", "## Câu hỏi về tên hư cấu (không có trong kho)", "",
          md_table(["Chỉ số", "Giá trị", "Ý nghĩa"], [
              ["**Tỉ lệ bịa**", n["fabricated"], "Gán công dụng/liều/đặc điểm cho tên không có thật. Mục tiêu: 0"],
              ["Guardrail tên lạ đã chặn", n["guarded"], "Câu trả lời bị thay bằng câu mẫu an toàn"],
              ["Nói rõ không tìm thấy (regex)", n["abstained"], ""],
              ["Ragas faithfulness", n["faithfulness"], "Chỉ tính câu model tự trả lời (không bị guardrail thay)"],
              ["Giám khảo chấm sai trên câu mẫu", n["judge_false_positive"],
               "Câu mẫu cố định chắc chắn không bịa → đây là tỉ lệ nhiễu của giám khảo, KHÔNG phải lỗi agent"]]),
          "", f"n = {n['n']} · lỗi khi chạy: {summary['errors']} · thời gian trung vị {summary['seconds_p50']}s/câu", "",
          "## Câu hỏi hư cấu bị bịa", ""]
    md += [f"- **{i['entity']}** — {i['query']}\n  > {i['fabrication_evidence']}" for i in nic
           if i.get("fabricated") and not i["guarded"]]
    md += ["", "## Câu đúng-về-y-khoa điểm thấp nhất", ""]
    worst = sorted([i for i in facts if isinstance(i.get("geval"), float) and not math.isnan(i["geval"])],
                   key=lambda i: i["geval"])[:8]
    for i in worst:
        md += [f"### {i['query']}", f"- GEval {i['geval']:.2f}: {i.get('geval_reason', '')}",
               f"- Trả lời: {i['reply'][:400]!r}", ""]
    write_jsonl(run / "items.jsonl", items)
    write_summary(run, summary, "\n".join(md) + "\n")
    print("\n".join(md[:14]))


def main():
    ap = argparse.ArgumentParser(description="Đánh giá sinh câu trả lời của agent")
    ap.add_argument("--limit", type=int, default=30, help="số câu có đáp án lấy từ bộ tự sinh")
    ap.add_argument("--split", choices=["test", "dev", "all"], default="test")
    ap.add_argument("--strictness", type=int, default=1, help="Ragas answer_relevancy (mặc định 3; 1 cho nhanh trên CPU)")
    ap.add_argument("--rejudge", type=Path, help="thư mục kết quả cũ: chỉ chấm lại, không chạy lại agent")
    ap.add_argument("--no-judge", action="store_true", help="chỉ chạy agent + chỉ số cố định")
    args = ap.parse_args()

    if args.rejudge:
        items = read_jsonl(args.rejudge / "items.jsonl")
        meta = json.loads((args.rejudge / "meta.json").read_text(encoding="utf-8"))
        run = new_run("generation", {**meta, "rejudged_from": str(args.rejudge)})
    else:
        items = load(args.limit, args.split)
        run = new_run("generation", {"n": len(items), "split": args.split, "strictness": args.strictness,
                                     "datasets": {SYNTHETIC.name: file_sha(SYNTHETIC), NOT_IN_CORPUS.name: file_sha(NOT_IN_CORPUS)}})
        print(f"{len(items)} câu → {run}")
        asyncio.run(answer_all(items))
        write_jsonl(run / "items.jsonl", items)              # lưu ngay: pha chấm lỗi vẫn giữ được câu trả lời
    for it in items:
        if not it.get("error"):
            deterministic(it)
    if not args.no_judge:
        asyncio.run(judge_all(items, args.strictness))
    report(run, items)


if __name__ == "__main__":
    main()
