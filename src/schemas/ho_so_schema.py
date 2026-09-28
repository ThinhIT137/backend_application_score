from datetime import datetime

from pydantic import BaseModel, Field

from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiDuyet


class MinhChungChungChi(BaseModel):
    ma_chung_chi: str
    loai_chung_chi: str
    diem_hoac_hang: str | None
    file_dinh_kem: str | None
    trang_thai_duyet: TrangThaiDuyet

    model_config = {"from_attributes": True}


class MinhChungGiaiThuong(BaseModel):
    ma_giai_thuong: str
    cccd: str

    model_config = {"from_attributes": True}


class MinhChungBangDiem(BaseModel):
    ma_bang_diem: str
    loai_diem: str
    nam_hoc: int

    model_config = {"from_attributes": True}


class HoSoListItem(BaseModel):
    ma_ho_so: str
    cccd: str
    ma_chuong_trinh: str
    trang_thai: TrangThaiDuyet
    ket_qua: str | None
    ma_phuong_thuc: str
    nguon_du_lieu: NguonDuLieu
    nguyen_vong: int
    nam_tuyen_sinh: int
    ma_admin_xu_ly: str | None
    create_at: datetime

    model_config = {"from_attributes": True}


class HoSoDetail(HoSoListItem):
    diem_uu_tien_ap_dung: float | None
    tong_diem_xet_tuyen: float | None
    ma_to_hop: str | None
    chung_chi: list[MinhChungChungChi] = Field(default_factory=list)
    giai_thuong: list[MinhChungGiaiThuong] = Field(default_factory=list)
    bang_diem: list[MinhChungBangDiem] = Field(default_factory=list)


class TuChoiHoSoRequest(BaseModel):
    ly_do: str = Field(min_length=1)


class CongBoKetQuaRequest(BaseModel):
    nam_tuyen_sinh: int
    ma_chuong_trinh: str | None = None
    ma_phuong_thuc: str | None = None


class CongBoKetQuaResponse(BaseModel):
    nam_tuyen_sinh: int
    so_ho_so: int
    da_xu_ly_het: bool
    trong_moc_cong_bo: bool
    notification_triggered: bool
    idempotent: bool = False
