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
    admin_role: Literal["super_admin", "chuyen_vien"] | None = None
    ma_admin: str | None = None
    cccd: str | None = None


def _normalize_role(raw: str | None) -> Role | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in {"super_admin", "chuyen_vien", "admin", "quan_ly", "quanly", "administrator"}:
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

    raw_role = payload.get("role") or payload.get("vai_tro")
    role = _normalize_role(raw_role)
    admin_role: Literal["super_admin", "chuyen_vien"] | None = (
        raw_role.strip().lower()
        if raw_role and raw_role.strip().lower() in {"super_admin", "chuyen_vien"}
        else None
    )

    # FE thật dùng SignJWT({ userId }) -> payload có userId, sub
    # Nếu token không có claim role nhưng có userId/ma_admin thì suy luận là admin
    ma_admin = payload.get("ma_admin") or payload.get("userId") or (payload.get("sub") if role == "admin" else None)
    if role is None and (payload.get("ma_admin") or payload.get("userId")):
        role = "admin"
        admin_role = admin_role or "chuyen_vien"

    if role is None:
        raise UnauthorizedError("Token thiếu vai trò")

    if role == "admin" and not ma_admin and payload.get("sub"):
        ma_admin = payload.get("sub")

    cccd = payload.get("cccd") or (payload.get("sub") if role == "thi_sinh" else None)
    return CurrentUser(role=role, admin_role=admin_role, ma_admin=ma_admin, cccd=cccd)


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
