import asyncio
import io
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.config import ProductEnv
from product.db.models import Document, User
from product.apps.api.members.permissions import authorize_member

MAX_BYTES = 10 * 1024 * 1024
# Loại file xác định từ nội dung thật (Pillow), không tin Content-Type/đuôi file do client gửi
_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}

_storage = Path(ProductEnv().storage_dir).resolve()


class InvalidUpload(Exception):
    def __init__(self, message: str, too_large: bool = False):
        super().__init__(message)
        self.too_large = too_large


async def _read_limited(upload: UploadFile) -> bytes:
    buf = bytearray()
    while chunk := await upload.read(1024 * 1024):
        buf += chunk
        if len(buf) > MAX_BYTES:
            raise InvalidUpload(f"File vượt quá {MAX_BYTES // (1024 * 1024)}MB", too_large=True)
    return bytes(buf)


def _detect(data: bytes) -> tuple[str, str]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise InvalidUpload("File không phải ảnh hợp lệ")
    if fmt not in _FORMATS:
        raise InvalidUpload("Chỉ nhận ảnh JPEG, PNG hoặc WEBP")
    return _FORMATS[fmt]


async def save_upload(session: AsyncSession, member_id: UUID, user: User, upload: UploadFile) -> Document:
    await authorize_member(session, member_id, user)
    data = await _read_limited(upload)
    ext, mime = _detect(data)

    path = _storage / "documents" / str(member_id) / f"{uuid4()}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_bytes, data)

    doc = Document(member_id=member_id, storage_path=str(path), mime_type=mime)
    session.add(doc)
    try:
        await session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    await session.refresh(doc)
    return doc


async def list_documents(session: AsyncSession, member_id: UUID, user: User) -> list[Document]:
    await authorize_member(session, member_id, user)
    rows = await session.scalars(
        select(Document).where(Document.member_id == member_id).order_by(Document.created_at.desc()))
    return list(rows)
