from typing import Annotated, Literal

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.exceptions import ForbiddenError, UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)

Role = Literal["admin", "thi_sinh"]


class CurrentUser(BaseModel):
    role: Role
    ma_admin: str | None = None
    cccd: str | None = None


def _normalize_role(raw: str | None) -> Role | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in {"admin", "quan_ly", "quanly", "administrator"}:
        return "admin"
    if value in {"thi_sinh", "thisinh", "student", "candidate"}:
        return "thi_sinh"
    return None


def decode_token(credentials: HTTPAuthorizationCredentials | None) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Thiếu token xác thực")

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience or None,
            options={"verify_aud": bool(settings.jwt_audience)},
        )
    except JWTError as exc:
        raise UnauthorizedError("Token không hợp lệ") from exc

    role = _normalize_role(payload.get("role") or payload.get("vai_tro"))
    if role is None:
        raise UnauthorizedError("Token thiếu vai trò")

    ma_admin = payload.get("ma_admin") or (payload.get("sub") if role == "admin" else None)
    cccd = payload.get("cccd") or (payload.get("sub") if role == "thi_sinh" else None)
    return CurrentUser(role=role, ma_admin=ma_admin, cccd=cccd)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    return decode_token(credentials)


def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != "admin" or not user.ma_admin:
        raise ForbiddenError("Chỉ quản lý mới được gọi API này")
    return user


def require_thi_sinh(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != "thi_sinh" or not user.cccd:
        raise ForbiddenError("Chỉ thí sinh mới được gọi API này")
    return user
