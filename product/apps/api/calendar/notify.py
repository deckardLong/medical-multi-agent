import asyncio
import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from sqlalchemy.ext.asyncio import AsyncSession
from product.config import ProductEnv
from product.db.models import Family, FamilyMember, User
from .recurrence import TZ

log = logging.getLogger(__name__)
env = ProductEnv()

async def recipient_email(session: AsyncSession, member: FamilyMember, family: Family) -> str | None:
    """Thành viên đã liên kết tài khoản -> mail của chính họ.
    Thành viên chưa liên kết (ví dụ trẻ nhỏ) -> mail của chủ gia đình, vì chỉ người đó có tài khoản thật."""
    user_id = member.linked_user_id or family.owner_user_id
    user = await session.get(User, user_id)
    return user.email if user else None

def _send_sync(msg: EmailMessage) -> None:
    has_login = bool(env.smtp_user and env.smtp_password)
    ctx = ssl.create_default_context()
    if env.smtp_port == 465:                              # SMTPS: TLS ngay từ đầu
        server = smtplib.SMTP_SSL(env.smtp_host, env.smtp_port, timeout=10, context=ctx)
    else:
        server = smtplib.SMTP(env.smtp_host, env.smtp_port, timeout=10)
    with server:
        if env.smtp_port != 465:
            server.ehlo()
            if server.has_extn("starttls"):
                server.starttls(context=ctx)
                server.ehlo()
            elif has_login:
                raise RuntimeError("Máy chủ SMTP không hỗ trợ STARTTLS — không gửi mật khẩu qua kết nối không mã hoá")
        if has_login:
            server.login(env.smtp_user, env.smtp_password.get_secret_value())
        server.send_message(msg)

async def send_reminder_email(to: str, member_name: str, title: str, when: datetime) -> None:
    msg = EmailMessage()
    msg["From"] = env.smtp_from
    msg["To"] = to
    msg["Subject"] = f"Nhắc lịch cho {member_name}: {title}"
    # Giờ đọc từ DB là UTC; phải đổi về giờ địa phương, nếu không lịch 08:00 sẽ hiện "01:00"
    msg.set_content(f"{member_name} có lịch \"{title}\" vào {when.astimezone(TZ):%H:%M %d/%m/%Y}.\n\n"
                    "Đây là email tự động từ hệ thống trợ lý y tế gia đình.")
    await asyncio.to_thread(_send_sync, msg)
