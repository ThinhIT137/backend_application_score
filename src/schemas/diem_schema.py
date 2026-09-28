from datetime import datetime

from pydantic import BaseModel, Field

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
    diem: float = Field(ge=0, le=150)
    ngay_cap: datetime
    ngay_het_han: datetime | None = None
    file_dinh_kem: str = Field(min_length=1)


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
