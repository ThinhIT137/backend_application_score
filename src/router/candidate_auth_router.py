"""Candidate sessions; admin authentication remains owned by Next.js."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.core.database import get_db
from src.core import security
from src.core.security import CurrentUser, require_thi_sinh
from src.core.exceptions import UnauthorizedError, DuLieuKhongHopLe
from src.models.tham_chieu import ThiSinh
from src.services.adapters.email_sender import SmtpEmailSender
# Các API tài khoản thí sinh thuộc backend điểm; tài khoản/mật khẩu nằm trực tiếp trên ThiSinh.
router = APIRouter(prefix="/auth/candidate", tags=["candidate-auth"])


class Login(BaseModel):
    cccd: str = Field(pattern=r"^\d{12}$")
    password: str = Field(min_length=10, max_length=128)


class Registration(Login):
    ho_ten: str = Field(min_length=2, max_length=100)
    so_dien_thoai: str = Field(pattern=r"^\d{10,11}$")


class Refresh(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class ActivationRequest(BaseModel):
    cccd: str = Field(pattern=r"^\d{12}$")
    channel: Literal["email", "sms"] = "email"


class ActivationConfirm(Login):
    otp: str = Field(pattern=r"^\d{6}$")


# Lưu dấu kiểm tra HMAC của OTP gắn với CCCD, không lưu mã OTP nguyên văn trong database.
def otp_digest(cccd: str, code: str):
    return hmac.new(security.get_settings().jwt_secret.encode(), f"activate:{cccd}:{code}".encode(), hashlib.sha256).hexdigest()


# Chỉ gửi tới địa chỉ đã đọc từ hồ sơ cũ; email dùng SMTP, SMS dùng gateway đã cấu hình.
def send_activation(channel: str, destination: str, code: str):
    settings = security.get_settings()
    message = f"Ma kich hoat tai khoan tuyen sinh: {code}. Hieu luc 5 phut. Khong chia se ma nay."
    if channel == "email":
        if settings.email_provider != "smtp" or not settings.smtp_host or not settings.smtp_from:
            raise DuLieuKhongHopLe("Chưa cấu hình gửi OTP email")
        SmtpEmailSender(host=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_username,
            password=settings.smtp_password, use_tls=settings.smtp_use_tls, from_addr=settings.smtp_from).send(destination, "Mã kích hoạt tài khoản tuyển sinh", message)
    else:
        if not settings.sms_gateway_url or not settings.sms_gateway_token:
            raise DuLieuKhongHopLe("Chưa cấu hình gửi OTP SMS")
        import httpx
        response = httpx.post(settings.sms_gateway_url, json={"to": destination, "message": message},
            headers={"Authorization": f"Bearer {settings.sms_gateway_token}"}, timeout=15)
        response.raise_for_status()


# Bước 1: hồ sơ cũ chưa có mật khẩu mới được kích hoạt; hạn chế gửi lại trong 60 giây.
@router.post("/activation/request")
def request_activation(payload: ActivationRequest, db: Session = Depends(get_db)):
    # Uniform response avoids disclosing which CCCDs have credentials/contact data.
    response = {"success": True, "message": "Nếu hồ sơ đủ điều kiện, OTP đã được gửi đến liên hệ đã lưu."}
    row = db.scalar(select(ThiSinh).where(ThiSinh.cccd == payload.cccd).with_for_update())
    if not row or row.password:
        return response
    destination = row.email if payload.channel == "email" else row.so_dien_thoai
    if not destination:
        return response
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if row.activation_otp_sent_at and (now - row.activation_otp_sent_at).total_seconds() < 60:
        return response
    code = f"{secrets.randbelow(1000000):06d}"
    row.activation_otp_hash = otp_digest(row.cccd, code)
    row.activation_otp_expires = now + timedelta(minutes=5)
    row.activation_otp_sent_at = now
    row.activation_otp_attempts = 0
    # Keep the row lock during delivery so request/confirm cannot race with resend.
    send_activation(payload.channel, destination, code)
    db.commit()
    return response


# Bước 2: khóa hàng, kiểm tra OTP còn hạn và tối đa 5 lần thử rồi lưu mật khẩu băm.
@router.post("/activation/confirm")
def confirm_activation(payload: ActivationConfirm, db: Session = Depends(get_db)):
    row = db.scalar(select(ThiSinh).where(ThiSinh.cccd == payload.cccd).with_for_update())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not row or row.password or not row.activation_otp_hash or not row.activation_otp_expires or row.activation_otp_expires <= now or row.activation_otp_attempts >= 5:
        raise UnauthorizedError("Mã xác minh không hợp lệ hoặc hết hạn")
    row.activation_otp_attempts += 1
    if not hmac.compare_digest(row.activation_otp_hash, otp_digest(row.cccd, payload.otp)):
        db.commit()  # Failed attempts must persist despite the error response.
        raise UnauthorizedError("Mã xác minh không hợp lệ hoặc hết hạn")
    salt = secrets.token_hex(16)
    row.password = salt + "$" + password_hash(payload.password, salt)
    row.activation_otp_hash = None
    row.activation_otp_expires = None
    row.activation_otp_attempts = 0
    return issue(row, db)


class Profile(BaseModel):
    ho_ten: str = Field(min_length=2, max_length=100)
    so_dien_thoai: str = Field(pattern=r"^\d{10,11}$")
    khu_vuc: str = Field(pattern=r"^(KV1|KV2|KV2_NT|KV3)$")
    doi_tuong_uu_tien: str = Field(max_length=100)
    email: str | None = Field(default=None, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")




@router.get("/me")
def me(user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    student = db.get(ThiSinh, user.cccd)
    if not student:
        raise UnauthorizedError("Tài khoản không tồn tại")
    return {"cccd": student.cccd, "ho_ten": student.ho_ten, "so_dien_thoai": student.so_dien_thoai, "email": student.email}


@router.patch("/me")
def update_profile(payload: Profile, user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from src.models.submission_operation import SubmissionOperation
    from src.core.exceptions import TrangThaiKhongHopLe
    student = db.scalar(select(ThiSinh).where(ThiSinh.cccd == user.cccd).with_for_update())
    if not student:
        raise UnauthorizedError("Tài khoản không tồn tại")
    if db.scalar(select(SubmissionOperation.operation_id).where(SubmissionOperation.cccd == user.cccd,
            SubmissionOperation.status.in_(["pending", "aborting", "cleanup_pending"]))):
        raise TrangThaiKhongHopLe("Cần hoàn tất lần nộp trước khi sửa thông tin")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    return {"success": True}


@router.post("/logout")
def logout(user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    # Browser cookies are cleared by Next.js; no server-side refresh session state.
    return {"success": True}


# PBKDF2 lặp 600.000 lần với salt riêng; database giữ salt và hash, không giữ mật khẩu gốc.
def password_hash(value: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 600000).hex()


# Phát access JWT 15 phút và refresh JWT 7 ngày; refresh là JWT tự xác minh, không có bảng phiên riêng.
def issue(account: ThiSinh, db: Session):
    settings = security.get_settings()
    now = datetime.now(timezone.utc)
    base = {"sub": account.cccd, "cccd": account.cccd, "role": "thi_sinh", "iat": now}
    if settings.jwt_audience:
        base["aud"] = settings.jwt_audience
    access = jwt.encode({**base, "token_type": "access", "exp": now + timedelta(minutes=15)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh = jwt.encode({**base, "token_type": "refresh", "jti": secrets.token_urlsafe(24), "exp": now + timedelta(days=7)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "expires_in": 900}


# Đăng ký mới không được tự nhận CCCD đã tồn tại; hồ sơ cũ phải đi qua bước xác minh OTP.
@router.post("/register", status_code=201)
def register(payload: Registration, db: Session = Depends(get_db)):
    # Existing applicant records require a verified account recovery flow, not self-claim by CCCD.
    if db.get(ThiSinh, payload.cccd):
        raise DuLieuKhongHopLe("Thông tin đã tồn tại. Vui lòng liên hệ bộ phận tuyển sinh để xác minh tài khoản.")
    salt = secrets.token_hex(16)
    account = ThiSinh(cccd=payload.cccd, ho_ten=payload.ho_ten.strip(), so_dien_thoai=payload.so_dien_thoai,
        password=salt + "$" + password_hash(payload.password, salt))
    try:
        db.add(account)
        return issue(account, db)
    except IntegrityError:
        db.rollback()
        raise DuLieuKhongHopLe("Không thể tạo tài khoản với thông tin này")


@router.post("/login")
def login(payload: Login, db: Session = Depends(get_db)):
    account = db.get(ThiSinh, payload.cccd)
    stored = account.password if account else None
    salt, expected = stored.split("$", 1) if stored and "$" in stored else ("invalid", "invalid")
    actual = password_hash(payload.password, salt)
    if not account or not stored or not hmac.compare_digest(expected, actual):
        raise UnauthorizedError("CCCD hoặc mật khẩu không chính xác")
    return issue(account, db)


# Kiểm tra chữ ký/hạn/loại token và tài khoản còn tồn tại trước khi phát cặp JWT mới.
@router.post("/refresh")
def refresh(payload: Refresh, db: Session = Depends(get_db)):
    settings = security.get_settings()
    try:
        claims = jwt.decode(payload.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience or None, options={"verify_aud": bool(settings.jwt_audience)})
    except JWTError:
        raise UnauthorizedError("Phiên đăng nhập hết hạn")
    if claims.get("token_type") != "refresh" or claims.get("role") != "thi_sinh":
        raise UnauthorizedError("Refresh token không hợp lệ")
    account = db.get(ThiSinh, claims.get("cccd"))
    if not account or not account.password or claims.get("sub") != account.cccd:
        raise UnauthorizedError("Phiên đăng nhập không còn hiệu lực")
    return issue(account, db)
