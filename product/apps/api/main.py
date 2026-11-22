# Entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from product.apps.api.auth.router import router as auth_router
from product.apps.api.members.router import router as members_router
from .chat.router import router as chat_router
from .documents.router import router as documents_router
from .records.router import router as records_router
from .calendar.router import router as calendar_router
from .dashboard.router import router as dashboard_router
import logging
from contextlib import asynccontextmanager
from product.config import ProductEnv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .calendar.reminders import scan_and_send

env = ProductEnv()
log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=str(env.timezone))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if env.smtp_host:
        # max_instances=1 + coalesce: lượt quét chậm (SMTP treo) không bị chồng lượt mới lên
        scheduler.add_job(scan_and_send, "interval", minutes=env.reminder_scan_interval_minutes, id="reminders",
                          max_instances=1, coalesce=True, replace_existing=True)
        scheduler.start()
    else:
        log.warning("Chưa cấu hình PRODUCT_SMTP_HOST — tắt job nhắc lịch qua email.")
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="AURELIA API", description="Trợ lý sức khoẻ gia đình — Assisted Understanding & Reasoning "
              "for Evidence-based Life & Integrated Assistance", lifespan=lifespan)
if origins := [o.strip().rstrip("/") for o in env.cors_origins.split(",") if o.strip()]:
    # Frontend ở domain khác (Vercel) gọi thẳng API. Xác thực bằng header Bearer, không dùng cookie.
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"],
                       allow_credentials=False, max_age=600)


@app.get("/health", include_in_schema=False)
async def health():
    """Render health check: không chạm DB/model để không báo lỗi giả khi model đang nạp."""
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(members_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(records_router)
app.include_router(calendar_router)
app.include_router(dashboard_router)
