"""Sinh ảnh đơn thuốc GIẢ LẬP có đáp án đúng biết trước cho lớp 3 (không dùng đơn thuốc thật của bệnh nhân).

    python -m evaluation.build.vision --n 8        # 8 đơn × 6 biến thể = 48 ảnh

Biến thể: in sạch · viết tay · giả ảnh chụp điện thoại · viết tay + ảnh chụp · quá mờ · quá nhỏ.
Hai biến thể cuối phải bị quality.check_image từ chối (expected_status = "rejected").
Ảnh ghi vào evaluation/data/vision/ (không commit, sinh lại được); đáp án ghi vào evaluation/data/vision_gt.jsonl.
"""
import argparse
import asyncio
import html
import io
import random
from datetime import date, timedelta
import numpy as np
import yaml
from PIL import Image, ImageFilter
from evaluation.common.io import split_of, write_jsonl
from evaluation.config import DATA_DIR, env

CATALOG = yaml.safe_load((DATA_DIR / "drugs_vi.yaml").read_text(encoding="utf-8"))
IMG_DIR = DATA_DIR / "vision"
GT = DATA_DIR / "vision_gt.jsonl"
VARIANTS = ["print_clean", "handwritten", "photo", "handwritten_photo", "too_blurry", "too_small"]

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&family=Patrick+Hand&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; background:#fff; font-family:'Be Vietnam Pro',sans-serif; color:#1b1b1b; }}
  .page {{ width:860px; min-height:1216px; padding:40px 48px; box-sizing:border-box; }}  /* khổ A5 đứng (1:√2) */
  .head {{ display:flex; justify-content:space-between; border-bottom:2px solid #1b1b1b; padding-bottom:12px; }}
  .fac {{ font-weight:700; font-size:20px; text-transform:uppercase; }}
  .sub {{ font-size:13px; color:#444; }}
  h1 {{ text-align:center; font-size:30px; margin:22px 0 14px; letter-spacing:2px; }}
  .info {{ font-size:16px; line-height:1.9; }}
  .rx {{ margin-top:16px; }}
  .med {{ font-size:18px; margin:14px 0 0; }}
  .use {{ font-size:16px; margin-left:28px; color:#222; }}
  .hand {{ font-family:'Patrick Hand',cursive; font-size:24px; color:#123a8c; }}
  .hand .use {{ font-size:22px; color:#123a8c; }}
  .hand .med {{ font-size:24px; }}
  .foot {{ display:flex; justify-content:space-between; margin-top:36px; font-size:16px; }}
  .sign {{ text-align:center; }}
  .sign .name {{ margin-top:56px; font-weight:600; }}
</style></head><body><div class="page">
  <div class="head"><div><div class="fac">{facility}</div><div class="sub">Số 12, đường Hoà Bình · ĐT: 0000 000 000</div></div>
  <div class="sub">Mã đơn: {code}</div></div>
  <h1>ĐƠN THUỐC</h1>
  <div class="info">Họ tên: <b>{patient}</b> &nbsp;&nbsp; Tuổi: {age} &nbsp;&nbsp; Giới: {sex}<br>Chẩn đoán: {diagnosis}</div>
  <div class="rx {hand}">{meds}</div>
  <div class="foot"><div class="sub">Lời dặn: tái khám khi hết thuốc hoặc có dấu hiệu bất thường.</div>
  <div class="sign">Ngày {d} tháng {m} năm {y}<br>Bác sĩ điều trị<div class="name {hand}">{doctor}</div></div></div>
</div></body></html>"""


def make_prescription(rng: random.Random) -> dict:
    drugs = {d["name"]: d for d in CATALOG["drugs"]}
    n = rng.randint(1, 4)
    names: list[str] = []
    if rng.random() < 0.5:                         # một nửa số đơn chứa cặp tên dễ nhầm
        group = rng.choice(CATALOG["confusable"])
        names += rng.sample(group, min(2, len(group), n))
    while len(names) < n:
        name = rng.choice(list(drugs))
        if name not in names:
            names.append(name)
    meds = []
    for name in names:
        d = drugs[name]
        freq = rng.choice([f for f in CATALOG["frequencies"] if ("gói" in f) == (d["unit"] == "gói")])
        meds.append({"name": name, "dose": rng.choice(d["doses"]), "frequency": freq,
                     "duration": rng.choice(CATALOG["durations"]), "qty": rng.choice([10, 14, 20, 28, 30])})
    issued = date(2026, 11, 1) + timedelta(days=rng.randint(0, 40))
    return {"facility": rng.choice(CATALOG["facilities"]), "prescriber": rng.choice(CATALOG["doctors"]),
            "patient": rng.choice(CATALOG["patients"]), "age": rng.randint(18, 80), "sex": rng.choice(["Nam", "Nữ"]),
            "diagnosis": rng.choice(["Viêm họng cấp", "Tăng huyết áp", "Viêm dạ dày", "Đái tháo đường type 2",
                                     "Viêm phế quản", "Viêm mũi dị ứng"]),
            "issued_date": issued.isoformat(), "meds": meds, "code": f"DT-{rng.randint(10000, 99999)}"}


def render_html(p: dict, handwritten: bool) -> str:
    e = html.escape
    meds = "".join(f'<div class="med">{i}. <b>{e(m["name"])} {e(m["dose"])}</b> &nbsp;—&nbsp; SL: {m["qty"]}</div>'
                   f'<div class="use">{e(m["frequency"])} · {e(m["duration"])}</div>' for i, m in enumerate(p["meds"], 1))
    y, mo, d = p["issued_date"].split("-")
    return TEMPLATE.format(facility=e(p["facility"]), code=p["code"], patient=e(p["patient"]), age=p["age"],
                           sex=p["sex"], diagnosis=e(p["diagnosis"]), meds=meds, hand="hand" if handwritten else "",
                           d=d, m=mo, y=y, doctor=e(p["prescriber"]))


def degrade(img: Image.Image, variant: str, rng: random.Random) -> Image.Image:
    img = img.convert("RGB")
    if "photo" in variant:                        # giả ảnh chụp điện thoại
        img = img.rotate(rng.uniform(-3, 3), resample=Image.BICUBIC, expand=True, fillcolor=(235, 232, 225))
        arr = np.asarray(img).astype(np.float32)
        h, w = arr.shape[:2]
        shade = np.linspace(0.82, 1.03, w)[None, :, None] * np.linspace(1.02, 0.9, h)[:, None, None]  # bóng sáng
        arr = arr * shade + np.random.default_rng(rng.randint(0, 2**31)).normal(0, 6, arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=55)
        img = Image.open(buf).convert("RGB")
    if variant == "too_blurry":
        img = img.filter(ImageFilter.GaussianBlur(6))
    if variant == "too_small":
        img = img.resize((520, int(img.height * 520 / img.width)))
    return img


async def render_all(items: list[tuple[str, dict, str]]) -> dict[str, bytes]:
    from playwright.async_api import async_playwright
    out = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 860, "height": 600}, device_scale_factor=1.5)
        for key, p, variant in items:
            await page.set_content(render_html(p, "handwritten" in variant))
            await page.evaluate("document.fonts.ready")
            out[key] = await page.locator(".page").screenshot()
        await browser.close()
    return out


def main():
    ap = argparse.ArgumentParser(description="Sinh ảnh đơn thuốc giả lập có đáp án")
    ap.add_argument("--n", type=int, default=8, help="số đơn thuốc (mỗi đơn × 6 biến thể)")
    args = ap.parse_args()
    rng = random.Random(env.seed)
    prescriptions = [make_prescription(rng) for _ in range(args.n)]
    items = [(f"rx{i:03d}-{v}", p, v) for i, p in enumerate(prescriptions) for v in VARIANTS]
    shots = asyncio.run(render_all(items))
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, p, variant in items:
        img = degrade(Image.open(io.BytesIO(shots[key])), variant, random.Random(f"{env.seed}:{key}"))
        path = IMG_DIR / f"{key}.png"
        img.save(path)
        rows.append({"id": key, "image": f"vision/{key}.png", "variant": variant, "prescription": key[:5],
                     "expected_status": "rejected" if variant in ("too_blurry", "too_small") else "ok",
                     "split": split_of(key[:5]),          # cùng một đơn luôn cùng split, mọi biến thể
                     "truth": {"facility": p["facility"], "prescriber": p["prescriber"], "issued_date": p["issued_date"],
                               "medications": [{k: m[k] for k in ("name", "dose", "frequency", "duration")} for m in p["meds"]]}})
    write_jsonl(GT, rows)
    print(f"{len(rows)} ảnh → {IMG_DIR}; đáp án → {GT}")


if __name__ == "__main__":
    main()
