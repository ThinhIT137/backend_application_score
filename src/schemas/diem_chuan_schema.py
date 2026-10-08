from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DiemTrungTuyenItem(BaseModel):
    ma_diem_tt: str
    ma_ls_dc: str
    ma_phuong_thuc: str
    diem: float
    create_at: datetime
    nguyen_vong_toi_da: int | None = None
    dieu_kien_mon: Any = None
    diem_uu_tien_toi_thieu: float | None = None

    model_config = {"from_attributes": True}


class LichSuDiemChuanItem(BaseModel):
    ma_ls_dc: str
    ma_chuong_trinh: str
    nam: int
    chi_tieu: int
    trung_tuyen: int | None = None
    ma_admin_cap_nhat: str
    create_at: datetime
    diem_trung_tuyen: list[DiemTrungTuyenItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TaoDiemChuanRequest(BaseModel):
    ma_ls_dc: str = Field(min_length=1)
    ma_chuong_trinh: str = Field(min_length=1)
    nam: int = Field(ge=2000, le=2100)
    chi_tieu: int = Field(ge=1)
    trung_tuyen: int | None = Field(default=None, ge=0)


class SuaDiemChuanRequest(BaseModel):
    chi_tieu: int | None = Field(default=None, ge=1)
    trung_tuyen: int | None = Field(default=None, ge=0)


class ThemDiemTrungTuyenRequest(BaseModel):
    ma_diem_tt: str = Field(min_length=1)
    ma_phuong_thuc: str = Field(min_length=1)
    diem: float = Field(ge=0.0)
    nguyen_vong_toi_da: int | None = Field(default=None, ge=1)
    dieu_kien_mon: Any = None
    diem_uu_tien_toi_thieu: float | None = Field(default=None, ge=0.0)
