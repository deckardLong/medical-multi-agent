import json
import re
from pydantic import BaseModel, ValidationError, field_validator, model_validator

_EMPTY = {"", "null", "none", "n/a", "na", "-", "[?]", "yyyy-mm-dd"}

def _blank_to_none(v):
    # LLM hay trả "" / "null" / placeholder của khuôn thay cho null; không chuẩn hoá thì vote coi đó là bất đồng
    return None if isinstance(v, str) and v.strip().lower() in _EMPTY else v

class MedicationLine(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    duration: str | None = None

    _blank = field_validator("dose", "frequency", "duration", mode="before")(_blank_to_none)

    @model_validator(mode="after")
    def _strip_dosing_from_name(self):
        # Model nhỏ hay chép lặp liều/tần suất vào cuối tên ("G. Azopt 8hrly") dù đã tách đúng vào field riêng
        name = self.name
        for part in (self.frequency, self.duration, self.dose):
            if part and name.lower().endswith(part.lower()) and len(name) > len(part):
                name = name[: -len(part)].rstrip(" ,-–")
        self.name = name or self.name
        return self

class PrescriptionExtract(BaseModel):
    medications: list[MedicationLine] = []
    prescriber: str | None = None
    issued_date: str | None = None
    facility: str | None = None

    _blank = field_validator("prescriber", "issued_date", "facility", mode="before")(_blank_to_none)

    @field_validator("medications", mode="before")
    @classmethod
    def _drop_unnamed(cls, v):
        return [m for m in v or [] if not (isinstance(m, dict) and _blank_to_none(m.get("name")) is None)]

def parse_extract(text: str) -> PrescriptionExtract | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return PrescriptionExtract.model_validate(json.loads(m.group(0)))
    except (json.JSONDecodeError, ValidationError):
        return None

def to_report(extract: PrescriptionExtract | None, who: str) -> str:
    """All agent return JSON (Octochains transfer string between agent and aggregator)"""
    if extract is None:
        return json.dumps({"error": f"{who}: không đọc được JSON hợp lệ"})
    return extract.model_dump_json()