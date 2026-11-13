from ..schema import MedicationLine, PrescriptionExtract
from .field_match import drug_key, norm_dose, same_drug, vote

def _cluster(reports: list[PrescriptionExtract]) -> list[list[MedicationLine | None]]:
    """Mỗi nhóm = một loại thuốc; vị trí i trong nhóm = cách đọc của agent thứ i (None nếu agent đó không thấy)."""
    n, clusters = len(reports), []
    for i, rep in enumerate(reports):
        for med in rep.medications:
            for cl in clusters:
                anchor = next(m for m in cl if m is not None)
                if cl[i] is None and same_drug(anchor.name, med.name):
                    cl[i] = med
                    break
            else:
                cl = [None] * n
                cl[i] = med
                clusters.append(cl)
    return clusters

def build_consensus(reports: list[PrescriptionExtract]) -> dict:
    fields = {f: vote([getattr(r, f) for r in reports]) for f in ("prescriber", "issued_date", "facility")}
    meds = []
    for cl in _cluster(reports):
        seen = [m for m in cl if m is not None]
        meds.append({
            "seen_by": len(seen),
            "name": vote([m.name for m in seen], norm=drug_key),
            "dose": vote([m.dose for m in seen], norm=norm_dose),
            "frequency": vote([m.frequency for m in seen]),
            "duration": vote([m.duration for m in seen]),
        })
    # Tên + liều phải đồng thuận, và thuốc phải được ≥ 2 lần đọc nhìn thấy (1 lần = có thể ảo giác hoặc bỏ sót)
    # Tần suất/thời gian dùng lệch cũng là sai thuốc trên thực tế (nocte ≠ mỗi 30 giờ) → không được coi là agree
    critical_ok = all(m["seen_by"] >= 2 and all(m[f]["status"] == "agree"
                                                for f in ("name", "dose", "frequency", "duration"))
                      for m in meds)
    all_ok = critical_ok and all(v["status"] == "agree" for v in fields.values())
    return {"status": "agree" if all_ok else "needs_review", "readers_ok": len(reports),
            "fields": fields, "medications": meds}