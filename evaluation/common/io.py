import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from evaluation.config import RESULTS_DIR, ROOT, env


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            n += 1
    return n


def bucket(key: str) -> float:
    """Số trong [0, 1] cố định theo key — chọn mẫu ổn định qua các lần chạy tiếp."""
    return int(hashlib.sha256(f"{env.seed}:{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def split_of(key: str) -> str:
    """Chia dev/test theo hash của id: cố định, không phụ thuộc thứ tự hay số lượng mẫu."""
    return "test" if bucket(key) < env.test_ratio else "dev"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "missing"


def _git_commit() -> str:
    for git in ("git", r"D:\Git\cmd\git.exe"):
        try:
            return subprocess.run([git, "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                  text=True, timeout=10).stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            continue
    return "unknown"


def new_run(layer: str, meta: dict[str, Any]) -> Path:
    """results/<layer>/<thời điểm>/ + meta.json: commit, model, bộ dữ liệu... để so sánh được giữa các lần chạy."""
    run = RESULTS_DIR / layer / datetime.now().strftime("%Y%m%d-%H%M%S")
    run.mkdir(parents=True, exist_ok=True)
    meta = {"layer": layer, "started_at": datetime.now().isoformat(timespec="seconds"), "git_commit": _git_commit(),
            "judge_model": env.judge_model, **meta}
    (run / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return run


def write_summary(run: Path, summary: dict, report_md: str) -> None:
    (run / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (run / "report.md").write_text(report_md, encoding="utf-8")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)
