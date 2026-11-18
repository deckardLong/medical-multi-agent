"""Chỉ số lớp 3 — đọc ảnh đơn thuốc. Đo cả độ đúng từng trường VÀ độ đúng của chính cơ chế đồng thuận.

Mỗi trường (3 trường đầu đơn + tên/liều/tần suất/thời gian của từng thuốc) rơi vào đúng một loại:
  correct_agree         đồng thuận và đúng
  silent_error          đồng thuận nhưng SAI — nguy hiểm nhất: giá trị sai lọt qua mà không bị đánh dấu
  flagged_recoverable   bị đánh dấu "cần kiểm tra" và đáp án đúng nằm trong các lựa chọn đưa cho người dùng
  flagged_unrecoverable bị đánh dấu nhưng không lựa chọn nào đúng (người dùng phải tự gõ)
  missed                thuốc có trong đơn nhưng không có trong kết quả
Thêm: thuốc bịa (có trong kết quả, không có trong đơn) — tách đã xác nhận / bị đánh dấu.
"""
from rapidfuzz import fuzz
from product.apps.agent.tools.vision_extract_tool.aggregate.field_match import drug_key, norm_dose, norm_text, same_drug

MED_FIELDS = ("name", "dose", "frequency", "duration")
HEADER_FIELDS = ("facility", "prescriber", "issued_date")


def value_ok(field: str, pred, truth) -> bool:
    """So khớp chặt hơn same_drug: đúng tên/liều mới tính là đúng, chỉ bỏ qua khác biệt hoa thường, khoảng trắng, dấu câu."""
    if pred is None or truth is None:
        return pred is None and truth is None
    if field == "name":
        a, b = drug_key(pred) or "", drug_key(truth) or ""
        return a == b or fuzz.ratio(a, b) >= 92
    if field == "dose":
        return norm_dose(pred) == norm_dose(truth)
    a, b = norm_text(pred) or "", norm_text(truth) or ""
    return a == b or fuzz.ratio(a, b) >= 90


def _candidates(v: dict) -> list:
    return [v["value"]] if v["status"] == "agree" else list(v.get("values", []))


def classify(field: str, v: dict, truth, single_reader: bool) -> str:
    """single_reader: thuốc chỉ 1 lần đọc thấy → mọi trường đều bị coi là chưa xác nhận (như propose_from_extraction)."""
    if v["status"] == "agree" and not single_reader:
        return "correct_agree" if value_ok(field, v["value"], truth) else "silent_error"
    return "flagged_recoverable" if any(value_ok(field, c, truth) for c in _candidates(v)) else "flagged_unrecoverable"


def score_consensus(consensus: dict, truth: dict) -> dict:
    """consensus: output của build_consensus (status agree/needs_review). truth: đáp án đúng của ảnh."""
    outcomes: list[tuple[str, str]] = []                     # (trường, loại)
    for f in HEADER_FIELDS:
        outcomes.append((f, classify(f, consensus["fields"][f], truth.get(f), False)))
    unmatched = list(consensus["medications"])
    for med in truth["medications"]:
        match = next((c for c in unmatched if any(same_drug(n, med["name"]) for n in _candidates(c["name"]) if n)), None)
        if match is None:
            outcomes += [(f, "missed") for f in MED_FIELDS]
            continue
        unmatched.remove(match)
        single = match["seen_by"] < 2
        outcomes += [(f, classify(f, match[f], med.get(f), single)) for f in MED_FIELDS]
    hallucinated_confirmed = sum(1 for c in unmatched if c["seen_by"] >= 2 and c["name"]["status"] == "agree")
    counts = {k: sum(1 for _, o in outcomes if o == k) for k in
              ("correct_agree", "silent_error", "flagged_recoverable", "flagged_unrecoverable", "missed")}
    return {"outcomes": outcomes, **counts, "hallucinated_confirmed": hallucinated_confirmed,
            "hallucinated_flagged": len(unmatched) - hallucinated_confirmed,
            # ảnh được hệ thống coi là "an toàn" (agree) nhưng thật ra có sai
            "image_silent_error": consensus["status"] == "agree" and (counts["silent_error"] > 0 or hallucinated_confirmed > 0
                                                                       or counts["missed"] > 0)}


def score_reader(extract: dict | None, truth: dict) -> dict:
    """Độ đúng của MỘT lần đọc (trước đồng thuận) — để biết agent nào kéo kết quả xuống."""
    if extract is None:
        return {"ok": False, "correct": 0, "total": len(HEADER_FIELDS) + len(MED_FIELDS) * len(truth["medications"]),
                "hallucinated": 0}
    correct = sum(value_ok(f, extract.get(f), truth.get(f)) for f in HEADER_FIELDS)
    meds = list(extract.get("medications", []))
    for med in truth["medications"]:
        m = next((x for x in meds if same_drug(x.get("name") or "", med["name"])), None)
        if m:
            meds.remove(m)
            correct += sum(value_ok(f, m.get(f), med.get(f)) for f in MED_FIELDS)
    return {"ok": True, "correct": correct, "total": len(HEADER_FIELDS) + len(MED_FIELDS) * len(truth["medications"]),
            "hallucinated": len(meds)}


def deepeval_metric():
    """Bọc thành metric DeepEval để báo cáo chung; tính toán thuần (không gọi LLM)."""
    from deepeval.metrics import BaseMetric
    from deepeval.test_case import LLMTestCase

    class PrescriptionSafetyMetric(BaseMetric):
        """Điểm = 1 − (trường sai lọt qua đồng thuận) / (trường được đồng thuận). Đạt chỉ khi không có lỗi im lặng."""

        def __init__(self, threshold: float = 1.0):
            self.threshold = threshold

        def measure(self, test_case: LLMTestCase, *_, **__) -> float:
            s = score_consensus(test_case.metadata["consensus"], test_case.metadata["truth"])
            accepted = s["correct_agree"] + s["silent_error"]
            self.score = 1.0 - (s["silent_error"] + s["hallucinated_confirmed"]) / max(1, accepted)
            self.success = self.score >= self.threshold and not s["image_silent_error"]
            self.reason = (f"{s['silent_error']} trường sai được đồng thuận, {s['hallucinated_confirmed']} thuốc bịa được "
                           f"xác nhận, {s['missed']} trường bỏ sót, {s['flagged_recoverable'] + s['flagged_unrecoverable']} "
                           f"trường bị đánh dấu cần kiểm tra")
            return self.score

        async def a_measure(self, test_case: LLMTestCase, *a, **kw) -> float:
            return self.measure(test_case, *a, **kw)

        def is_successful(self) -> bool:
            return bool(self.success)

        @property
        def __name__(self):
            return "Prescription Safety"

    return PrescriptionSafetyMetric()
