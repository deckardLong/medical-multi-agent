import re
import unicodedata
from collections import Counter
from rapidfuzz import fuzz

CLUSTER_THRESHOLD = 80

def norm_text(s: str | None) -> str | None:
    if s is None or not s.strip():
        return None
    s = unicodedata.normalize("NFC", s).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s/.]", " ", s)).strip()


def norm_dose(s: str | None) -> str | None:
    """'500mg' = '500 mg' = '500 MG'; '0,5g' = '0.5 g'. Không đổi đơn vị (g ≠ mg) — đổi đơn vị là việc của bác sĩ."""
    t = norm_text(s)
    if t is None:
        return None
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([a-zµ]+)", t)
    return f"{m.group(1).replace(',', '.')} {m.group(2)}" if m else t


_FORM_PREFIX = re.compile(
    r"^(?:(?:g|gtt|tab|tabs|cap|caps|syr|inj|susp|sol|oint|viên|thuốc|siro|ống|gói|chai|lọ)\.?\s+)+")


def drug_key(s: str | None) -> str | None:
    """Bỏ tiền tố dạng bào chế ('G. Azopt' → 'azopt'): cùng một thuốc nhưng lần đọc có/không chép tiền tố."""
    t = norm_text(s)
    if t is None:
        return None
    return _FORM_PREFIX.sub("", t).strip() or t


def _marker_tokens(key: str) -> set[str]:
    # Token ngắn/có số phân biệt thuốc khác nhau dù tên gần giống: "vitamin c" ≠ "vitamin d", "b1" ≠ "b6"
    return {t for t in key.split() if len(t) <= 2 or any(ch.isdigit() for ch in t)}


def same_drug(a: str, b: str) -> bool:
    ka, kb = drug_key(a) or "", drug_key(b) or ""
    return _marker_tokens(ka) == _marker_tokens(kb) and fuzz.ratio(ka, kb) >= CLUSTER_THRESHOLD


def vote(values: list[str | None], norm=norm_text) -> dict:
    """Đồng thuận khi ≥ 2 lần đọc cho CÙNG giá trị sau chuẩn hoá (kể cả cùng 'không đọc được' = None).
    Không đạt thì trả đủ các giá trị đã đọc để người dùng tự chọn — không tự lấy đa số thay họ."""
    normed = [norm(v) for v in values]
    top, count = Counter(normed).most_common(1)[0]
    if count >= 2:
        return {"status": "agree", "value": values[normed.index(top)]}
    return {"status": "disagree", "values": sorted({v for v in values if v is not None})}