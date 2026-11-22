# Backend AURELIA (FastAPI + agent + retrieval) cho Render. Frontend deploy riêng trên Vercel.
#   docker build -t aurelia-api .
#   docker run -p 8000:8000 --env-file .env aurelia-api
FROM python:3.12-slim

# libgl1/libglib2.0-0: OpenCV (PaddleOCR); libgomp1: Paddle/torch CPU
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf PRODUCT_STORAGE_DIR=/var/data/storage \
    PADDLE_PDX_CACHE_HOME=/var/data/paddlex
WORKDIR /app

# torch bản CPU (index PyPI mặc định kéo bản CUDA ~3GB vô ích trên Render, không có GPU)
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Đóng gói sẵn BGE-M3 vào image: khởi động không phải tải ~4GB mỗi lần deploy/restart.
# ignore_patterns PHẢI giống hệt lời gọi snapshot_download bên trong FlagEmbedding: bỏ bớt file (vd bản ONNX)
# thì ở chế độ offline nó coi snapshot là thiếu và không khởi động được. Không đổi `model` trong configs/embed.yaml
# để trỏ thư mục khác: đổi cấu hình là đổi hash → đổi tên collection Qdrant.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-m3', ignore_patterns=['flax_model.msgpack', 'rust_model.ot', 'tf_model.h5'])"

# BGE-M3 đã nằm trong image → không gọi HuggingFace lúc chạy (nhanh hơn, không dính rate limit)
ENV HF_HUB_OFFLINE=1

COPY alembic.ini ./
COPY configs ./configs
COPY common ./common
COPY retrieval ./retrieval
COPY product ./product

EXPOSE 8000
# 1 worker: model nằm trong RAM của tiến trình, và job nhắc lịch (APScheduler) chỉ nên chạy ở một nơi.
# Migration chạy trước mỗi lần khởi động (idempotent: đã ở head thì không làm gì).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn product.apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
