"""Deliberately minimal public status lookup; no identity or dossier identifiers."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PublicLookupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cccd: str = Field(pattern=r'^[0-9]{12}$')
    nam_tuyen_sinh: int | None = Field(default=None, ge=2000, le=2100)


class PublicLookupItem(BaseModel):
    ma_chuong_trinh: str
    ten_chuong_trinh: str | None = None
    ma_phuong_thuc: str
    ten_phuong_thuc: str | None = None
    nam_tuyen_sinh: int
    trang_thai: str
    ket_qua: Literal['trung_tuyen', 'khong_trung_tuyen', 'chua_cong_bo']
