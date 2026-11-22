"""Chat chạy nền: POST trả ngay job_id, client hỏi kết quả theo chu kỳ.

Lý do: khi đưa backend ra Internet qua Cloudflare Tunnel (docs/DEPLOY.md), mọi request bị cắt sau ~100 giây (lỗi 524),
trong khi đọc ảnh đơn thuốc trên CPU mất 3–5 phút và chat có tra web có thể > 100 giây. Với job + polling, không request
nào kéo dài quá vài giây. POST /members/{id}/chat (chờ trực tiếp) vẫn giữ cho client cũ và evaluation.

Job lưu trong bộ nhớ của tiến trình: đúng với cách chạy hiện tại (1 worker). Server khởi động lại thì job đang chạy mất,
GET trả 404 và client tải lại lịch sử chat (câu hỏi đã được lưu trước khi job bắt đầu).
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from uuid import UUID
from product.db.session import SessionLocal
from . import service

log = logging.getLogger(__name__)
JOB_TTL_SECONDS = 3600


@dataclass
class ChatJob:
    id: str
    member_id: UUID
    status: str = "pending"                   # pending | done | error
    reply: object | None = None               # ChatMessage khi done
    error: str | None = None
    created: float = field(default_factory=time.monotonic)


_jobs: dict[str, ChatJob] = {}
_tasks: set[asyncio.Task] = set()            # giữ tham chiếu: asyncio chỉ giữ weakref, task có thể bị GC giữa chừng


class Busy(Exception):
    """Thành viên đang có một câu hỏi chưa trả lời xong."""


def _sweep() -> None:
    now = time.monotonic()
    for k in [k for k, j in _jobs.items() if j.status != "pending" and now - j.created > JOB_TTL_SECONDS]:
        del _jobs[k]


async def _run(job: ChatJob, content: str, document_ids: list[UUID]) -> None:
    try:
        async with SessionLocal() as s:
            job.reply, _ = await service.send_message_traced(s, job.member_id, content, document_ids)
        job.status = "done"
    except ValueError as e:                   # vd document_ids không thuộc thành viên
        job.status, job.error = "error", str(e)
    except Exception:                         # noqa: BLE001 — lỗi model/DB: không lộ chi tiết nội bộ cho client
        log.exception("chat job %s lỗi", job.id)
        job.status, job.error = "error", "AURELIA gặp lỗi khi xử lý câu hỏi, vui lòng thử lại."


def start(member_id: UUID, content: str, document_ids: list[UUID]) -> ChatJob:
    """member_id đã được router kiểm tra quyền ghi (members.deps.writable_member)."""
    _sweep()
    if any(j.member_id == member_id and j.status == "pending" for j in _jobs.values()):
        raise Busy("AURELIA vẫn đang trả lời câu hỏi trước, vui lòng chờ một chút.")
    job = ChatJob(id=uuid.uuid4().hex, member_id=member_id)
    _jobs[job.id] = job
    task = asyncio.create_task(_run(job, content, document_ids))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job


def get(member_id: UUID, job_id: str) -> ChatJob | None:
    """Job của thành viên khác → None (router trả 404, như mọi tài nguyên theo thành viên)."""
    job = _jobs.get(job_id)
    return job if job is not None and job.member_id == member_id else None
