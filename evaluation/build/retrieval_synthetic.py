"""Sinh bộ câu hỏi truy xuất có đáp án biết trước: lấy mẫu 1 đoạn đã index → LLM viết câu hỏi chỉ trả lời được từ
đoạn đó → tài liệu chứa đoạn là đáp án (mức liên quan 2).

    python -m evaluation.build.retrieval_synthetic --n 300

Chạy tiếp được: lần sau bỏ qua các đoạn đã có trong file output.
"""
import argparse
import json
import random
import re
import time
import pyarrow.parquet as pq
from common.config import Env
from retrieval.settings import load_all
from evaluation.common.io import read_jsonl, split_of, write_jsonl
from evaluation.common.llm import ask_json
from evaluation.config import DATA_DIR, ROOT, env

OUT = DATA_DIR / "retrieval_synthetic.jsonl"
# Đoạn tiếng Anh → câu hỏi tiếng Việt: người dùng thật là người Việt, đo luôn tìm kiếm xuyên ngôn ngữ
QUESTION_LANG = {"vi": "tiếng Việt", "zh": "tiếng Trung (giản thể)", "en": "tiếng Việt"}
LANG_SHARE = {"vi": 0.6, "zh": 0.2, "en": 0.2}
META_REF = re.compile(r"bài viết|đoạn văn|văn bản|tài liệu (này|trên)|theo (bài|đoạn)|nêu trên|本文|文中|上文|该文", re.I)

PROMPT = """Bạn tạo dữ liệu đánh giá cho hệ thống tìm kiếm tài liệu y khoa.

ĐOẠN TÀI LIỆU (ngôn ngữ: {lang}):
\"\"\"{text}\"\"\"

Nếu đoạn trên KHÔNG chứa kiến thức y khoa cụ thể (chỉ là mục lục, quảng cáo, thông tin liên hệ, danh sách tài liệu
tham khảo...), trả về {{"usable": false}}.

Ngược lại, viết MỘT câu hỏi bằng {qlang} mà một người dân bình thường có thể hỏi, và đoạn trên trả lời được:
- Diễn đạt bằng lời của người hỏi, KHÔNG chép nguyên cụm từ dài từ đoạn văn.
- Câu hỏi phải tự đứng được: KHÔNG nhắc tới "bài viết", "đoạn văn", "tài liệu này".
- Hỏi về một ý cụ thể, không hỏi chung chung.
Kèm câu trả lời ngắn (1-3 câu) bằng {qlang}, chỉ dựa trên đoạn văn.

Chỉ trả về JSON: {{"usable": true, "question": "...", "answer": "..."}}"""


def _tokens(s: str, lang: str) -> list[str]:
    s = s.lower()
    return list(re.sub(r"\s+", "", s)) if lang == "zh" else re.findall(r"\w+", s)


def copies_source(question: str, text: str, q_lang: str) -> bool:
    """Câu hỏi chép ≥ n token liên tiếp từ đoạn gốc → quá dễ cho tìm kiếm từ khoá, làm sparse được điểm ảo."""
    n, sep = (12, "") if q_lang == "zh" else (6, " ")
    q, t = _tokens(question, q_lang), sep.join(_tokens(text, q_lang))
    return any(sep.join(q[i:i + n]) in t for i in range(len(q) - n + 1))


CJK = re.compile(r"[一-鿿]")
VI_MARK = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I)
# Câu hỏi về một ca bệnh cụ thể ("Chị M.T.T…", "bệnh nhi Nguyễn Ánh L.") — người dùng thật không hỏi kiểu này
CASE_REF = re.compile(r"\b[A-ZĐ]\.\s?[A-ZĐ]\.|\b(bệnh nhân|bệnh nhi|chị|anh|bé|cụ|ông|bà|cháu)\s+[A-ZĐ]\w*"
                      r"|\b(bệnh nhân|bệnh nhi|người bệnh) (này|đó|ấy|đã)\b|患者[A-Z某]|[该此]患者|患者已|[张王李赵刘陈]某")
# Câu hỏi kể lại nội dung tài liệu (nghiên cứu này, bác sĩ nói gì…) — chỉ trả lời được khi đang cầm đúng bài đó
NARRATIVE_REF = re.compile(r"nghiên cứu này|trong nghiên cứu|trường hợp này|ca (bệnh )?này|nạn nhân|bác sĩ (có )?(nói|cho biết|nhận định)|bác sĩ đã|"
                           r"医生(为什么|认为|是否)|医生说(?!我)|该研究|研究中|病史采集", re.I)


def real_lang(text: str, tagged: str) -> str:
    """Nhãn ngôn ngữ trong corpus có chỗ sai (đoạn 'en' thật ra là tiếng Trung) → đoán lại theo tỉ lệ chữ Hán."""
    letters = [ch for ch in text if ch.isalpha()]
    return "zh" if letters and sum(bool(CJK.match(ch)) for ch in letters) / len(letters) > 0.3 else tagged


def question_problem(q: str, q_lang: str) -> str | None:
    """Lý do loại câu hỏi (None = giữ): sai/trộn ngôn ngữ hoặc hỏi về một ca bệnh cụ thể."""
    if q_lang == "zh":
        letters = [ch for ch in q if ch.isalpha()]
        if not letters or sum(bool(CJK.match(ch)) for ch in letters) / len(letters) < 0.7:
            return "lang"
    elif CJK.search(q) or not VI_MARK.search(q):
        return "lang"
    return "case" if CASE_REF.search(q) or NARRATIVE_REF.search(q) else None


def indexed_shards(collection: str, chunks_dir) -> list:
    rows = [json.loads(l) for l in open(ROOT / "state/retrieval/manifest.jsonl", encoding="utf-8")]
    return [chunks_dir / r["shard"] for r in rows if r["collection"] == collection and (chunks_dir / r["shard"]).exists()]


def sample_chunks(shards: list, n: int, rng: random.Random, skip: set[str]) -> list[dict]:
    """Lấy mẫu phân tầng theo ngôn ngữ, trải đều qua các shard, mỗi bài viết tối đa 1 đoạn."""
    want = {lang: max(1, round(n * share)) for lang, share in LANG_SHARE.items()}
    per_shard = max(2, n // len(shards) + 2)
    picked, docs = [], set()
    for shard in rng.sample(shards, len(shards)):
        if sum(want.values()) <= 0:
            break
        meta = pq.read_table(shard, columns=["chunk_id", "doc_id", "lang", "n_tokens"]).to_pylist()
        order = list(range(len(meta)))
        rng.shuffle(order)
        chosen = []
        for i in order:
            c = meta[i]
            if len(chosen) >= per_shard:
                break
            if (want.get(c["lang"], 0) > 0 and c["chunk_id"] not in skip and c["doc_id"] not in docs
                    and 80 <= (c["n_tokens"] or 0) <= 400):
                chosen.append(i)
                docs.add(c["doc_id"])
                want[c["lang"]] -= 1
        if chosen:   # chỉ đọc cột văn bản (nặng) cho đúng các dòng đã chọn
            picked += pq.read_table(shard, columns=["chunk_id", "doc_id", "lang", "ctx", "text"]).take(chosen).to_pylist()
    rng.shuffle(picked)
    return picked


def main():
    ap = argparse.ArgumentParser(description="Sinh câu hỏi truy xuất có đáp án từ các đoạn đã index")
    ap.add_argument("--n", type=int, default=300, help="số câu cần có trong file (tính cả câu đã sinh trước)")
    ap.add_argument("--clean", action="store_true", help="xoá các câu cũ không qua bộ lọc hiện tại rồi sinh bù")
    args = ap.parse_args()

    s = load_all(Env())
    existing = read_jsonl(OUT) if OUT.exists() else []
    if args.clean:
        keep = [r for r in existing if not question_problem(r["query"], r["query_lang"])]
        for r in existing:
            if r not in keep:
                print(f"  xoá ({question_problem(r['query'], r['query_lang'])}): {r['query'][:90]}")
        write_jsonl(OUT, keep)
        existing = keep
    done = {r["source_chunk_id"] for r in existing}
    need = args.n - len(existing)
    if need <= 0:
        print(f"Đã đủ {len(existing)} câu trong {OUT}")
        return
    rng = random.Random(env.seed + len(existing))
    shards = indexed_shards(s.collection, s.chunks_dir)
    print(f"{len(shards)} shard đã index trong {s.collection}; cần sinh thêm {need} câu")
    pool = sample_chunks(shards, need * 2, rng, done)        # dư gấp đôi vì có đoạn bị loại

    made, rejected = 0, {"unusable": 0, "copy": 0, "meta": 0, "lang": 0, "case": 0, "error": 0}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as f:
        for c in pool:
            if made >= need:
                break
            c["lang"] = real_lang(c["text"], c["lang"])
            q_lang = "zh" if c["lang"] == "zh" else "vi"
            t0 = time.time()
            try:
                out = ask_json(env.generator_model, PROMPT.format(lang=c["lang"], text=c["text"][:2500],
                                                                  qlang=QUESTION_LANG[c["lang"]]), temperature=0.7)
            except Exception as e:                                            # noqa: BLE001
                rejected["error"] += 1
                print("  lỗi LLM:", str(e)[:120])
                continue
            q, a = (out.get("question") or "").strip(), (out.get("answer") or "").strip()
            if not out.get("usable") or not q or not a:
                rejected["unusable"] += 1
                continue
            if META_REF.search(q):
                rejected["meta"] += 1
                continue
            if copies_source(q, c["text"], q_lang):
                rejected["copy"] += 1
                continue
            if problem := question_problem(q, q_lang):
                rejected[problem] += 1
                continue
            qid = f"syn-{c['chunk_id']}"
            row = {"qid": qid, "query": q, "query_lang": q_lang, "doc_lang": c["lang"], "qrels": {c["doc_id"]: 2},
                   "source_chunk_id": c["chunk_id"], "reference": a, "reference_context": c["text"],
                   "title": (c["ctx"] or "").split(" | ")[0], "split": split_of(qid), "origin": "synthetic"}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            made += 1
            print(f"[{len(existing) + made}/{args.n}] ({time.time() - t0:.0f}s) {c['lang']}→{q_lang}: {q[:90]}")
    print(f"Xong: +{made} câu → {OUT}. Bị loại: {rejected}")


if __name__ == "__main__":
    main()
