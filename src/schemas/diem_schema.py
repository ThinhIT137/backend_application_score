from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from src.models.trang_thai_ho_so import TrangThaiDuyet

LOAI_CHUNG_CHI_DGNL = "DGNL"


class DiemMonThpt(BaseModel):
    ma_mon: str
    diem_so: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)


class ThiSinhDiemThpt(BaseModel):
    cccd: str
    diem_mon: list[DiemMonThpt] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_subjects(self):
        ids = [m.ma_mon for m in self.diem_mon]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate examination subject")
        return self


class DongBoThptRequest(BaseModel):
    nam_hoc: int = Field(ge=1900, le=2100)


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
    diem: float = Field(ge=0, le=150, allow_inf_nan=False)
    ngay_cap: datetime
    ngay_het_han: datetime | None = None
    file_dinh_kem: str = Field(min_length=1)


    @model_validator(mode="after")
    def validate_dates(self):
        if self.ngay_het_han and self.ngay_het_han < self.ngay_cap:
            raise ValueError("Expiry precedes issue date")
        return self


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


class QuyDoiDiemRequest(BaseModel):
    phuong_thuc: Literal["hoc_ba", "hsa", "tsa"]
    diem: float = Field(allow_inf_nan=False)
    nam_tuyen_sinh: Literal[2026] = 2026


class QuyDoiDiemResponse(BaseModel):
    phuong_thuc: str
    diem_goc: float
    diem_thpt: float
    nam_tuyen_sinh: int
