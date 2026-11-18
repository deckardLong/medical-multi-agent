"""Cấu hình chung cho evaluation. Biến môi trường tiền tố EVAL_ (đọc cả .env ở gốc repo)."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Tắt telemetry trước khi import ragas/deepeval: không thư viện nào được tự gửi dữ liệu ra ngoài
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("DEEPEVAL_UPDATE_WARNING_OPT_OUT", "YES")
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "evaluation"
DATA_DIR = EVAL_DIR / "data"           # bộ dữ liệu (jsonl/yaml) — commit vào git
RESULTS_DIR = EVAL_DIR / "results"     # kết quả từng lần chạy — không commit
CACHE_DIR = EVAL_DIR / ".cache"        # output thô tốn thời gian tính (vd 3 lần đọc ảnh) — không commit


class EvalEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="EVAL_", extra="ignore")

    judge_base_url: str = "http://localhost:11434/v1"
    judge_api_key: str = "ollama"
    # Khác họ với model trả lời (Qwen) để giảm thiên vị "tự chấm mình"
    judge_model: str = "aurelia-judge:latest"   # llama3.1 + num_ctx 8192, tạo bằng evaluation/judge.Modelfile
    # Model dùng để SINH dữ liệu đánh giá (câu hỏi, câu trả lời mẫu) — tiếng Việt tốt hơn llama3.1
    generator_model: str = "qwen2.5:7b-instruct"
    seed: int = 42
    test_ratio: float = 0.7             # phần còn lại là dev (dùng khi tinh chỉnh, không báo cáo)


env = EvalEnv()
