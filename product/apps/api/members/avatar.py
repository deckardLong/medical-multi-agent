"""Ảnh đại diện thành viên. Ảnh gốc KHÔNG được lưu: chỉ giữ bản đã chuẩn hoá 256×256 WEBP.
- Xoay đúng chiều theo EXIF rồi bỏ toàn bộ EXIF (ảnh chụp điện thoại thường kèm toạ độ GPS — ảnh trẻ em càng nhạy cảm).
- Cắt vuông ở giữa: avatar hiển thị dạng tròn/bo góc, ảnh dọc/ngang không bị méo.
- Phục vụ qua endpoint có kiểm tra quyền (members.deps.readable_member), không qua thư mục tĩnh công khai.
"""
import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession
from product.apps.api.documents.service import InvalidUpload, _detect, _storage
from product.db.models import FamilyMember

MAX_BYTES = 5 * 1024 * 1024
SIZE = 256
MIN_SIDE = 64


async def _read_limited(upload: UploadFile) -> bytes:
    buf = bytearray()
    while chunk := await upload.read(512 * 1024):
        buf += chunk
        if len(buf) > MAX_BYTES:
            raise InvalidUpload(f"Ảnh đại diện vượt quá {MAX_BYTES // (1024 * 1024)}MB", too_large=True)
    return bytes(buf)


def _normalize(data: bytes) -> bytes:
    _detect(data)                                          # định dạng thật (JPEG/PNG/WEBP), không tin Content-Type
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        if min(img.size) < MIN_SIDE:
            raise InvalidUpload(f"Ảnh quá nhỏ ({img.width}×{img.height}px), cần cạnh ngắn ≥ {MIN_SIDE}px")
        if img.mode in ("RGBA", "LA", "P"):                # nền trong suốt → trắng, avatar không bị đen
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.getchannel("A"))
            img = bg
        img = ImageOps.fit(img.convert("RGB"), (SIZE, SIZE), Image.LANCZOS, centering=(0.5, 0.4))
        out = io.BytesIO()
        img.save(out, "WEBP", quality=86, method=4)        # ảnh mới tạo từ pixel → không mang EXIF theo
        return out.getvalue()


async def set_avatar(session: AsyncSession, member: FamilyMember, upload: UploadFile) -> FamilyMember:
    """member đã được router kiểm tra quyền ghi (members.deps.writable_member)."""
    data = await asyncio.to_thread(_normalize, await _read_limited(upload))
    path = _storage / "avatars" / str(member.id) / f"{uuid4()}.webp"
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(path.write_bytes, data)
    old = member.avatar_path
    member.avatar_path, member.avatar_updated_at = str(path), datetime.now(timezone.utc)
    try:
        await session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    if old:
        Path(old).unlink(missing_ok=True)                  # xoá sau commit: lỗi DB thì ảnh cũ vẫn còn dùng được
    await session.refresh(member)
    return member


async def remove_avatar(session: AsyncSession, member: FamilyMember) -> FamilyMember:
    old = member.avatar_path
    member.avatar_path, member.avatar_updated_at = None, None
    await session.commit()
    if old:
        Path(old).unlink(missing_ok=True)
    await session.refresh(member)
    return member


def avatar_file(member: FamilyMember) -> Path | None:
    """Đường dẫn ảnh nếu còn tồn tại và nằm trong thư mục storage (phòng giá trị DB bị sửa trỏ ra ngoài)."""
    if not member.avatar_path:
        return None
    p = Path(member.avatar_path).resolve()
    return p if p.is_file() and p.is_relative_to(_storage) else None
