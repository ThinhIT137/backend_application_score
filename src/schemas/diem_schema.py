import math
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.models.trang_thai_ho_so import TrangThaiDuyet

LOAI_CHUNG_CHI_DGNL = "DGNL"


class DiemMonThpt(BaseModel):
    ma_mon: str
    diem_so: float | None = None


class ThiSinhDiemThpt(BaseModel):
    cccd: str
    diem_mon: list[DiemMonThpt] = Field(default_factory=list)


class DongBoThptRequest(BaseModel):
    nam_hoc: int


class DongBoLoiItem(BaseModel):
    cccd: str | None = None
    ly_do: str


class DongBoThptResponse(BaseModel):
    nam_hoc: int
    so_thanh_cong: int
    so_loi: int
    ket_noi_nguon_ok: bool
    loi: list[DongBoLoiItem] = Field(default_factory=list)


class NopDgnlRequest(BaseModel):
    # TODO: bỏ field cccd khi FE có đăng nhập thí sinh và lấy CCCD từ JWT token
    cccd: str = Field(min_length=9, max_length=12, description="Số CCCD của thí sinh nộp điểm ĐGNL")
    diem: float = Field(ge=0, le=150)
    ngay_cap: datetime
    ngay_het_han: datetime | None = None
    file_dinh_kem: str = Field(min_length=1)

    @field_validator("cccd", "file_dinh_kem", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None, info):
        if value is None:
            return value
        value = str(value).strip()
        if not value:
            raise ValueError(f"{info.field_name} không được để trống")
        return value

    @field_validator("diem", mode="before")
    @classmethod
    def validate_diem(cls, value: float | str | None) -> float | None:
        if value is None:
            return value
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Điểm ĐGNL phải là số hợp lệ") from exc
        if not math.isfinite(numeric):
            raise ValueError("Điểm ĐGNL phải là số hữu hạn")
        return numeric


class ChungChiDgnlItem(BaseModel):
    ma_chung_chi: str
    cccd: str
    loai_chung_chi: str
    diem_hoac_hang: str | None
    ngay_cap: datetime | None
    file_dinh_kem: str | None
    trang_thai_duyet: TrangThaiDuyet
    create_at: datetime

    model_config = {"from_attributes": True}


class YeuCauBoSungRequest(BaseModel):
    ly_do: str | None = None
