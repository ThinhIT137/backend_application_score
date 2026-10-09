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
    giai_thuong: str
    loai_giai_thuong: str
    mon_hoc: str

    model_config = {"from_attributes": True}


class MinhChungDiemMon(BaseModel):
    ma_mon: str
    diem_so: float | None
    model_config = {"from_attributes": True}

class MinhChungBangDiem(BaseModel):
    ma_bang_diem: str
    loai_diem: str
    nam_hoc: int
    chi_tiet: list[MinhChungDiemMon] = Field(default_factory=list)

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


# --- Sprint 1 schemas ---


class NopChungChiItem(BaseModel):
    loai_chung_chi: str = Field(min_length=1)
    diem_hoac_hang: str | None = None
    ngay_cap: datetime | None = None
    ngay_het_han: datetime | None = None
    file_dinh_kem: str | None = None


class NopGiaiThuongItem(BaseModel):
    giai_thuong: str = Field(description="Hang giai thuong: giai_nhat, giai_nhi, giai_ba, khuyen_khich")
    loai_giai_thuong: str = Field(description="Cap giai thuong: toan_quoc, tinh, mien_bac, mien_nam")
    mon_hoc: str = Field(description="Mon hoc: toan, van, anh...")


class NopHoSoRequest(BaseModel):
    cccd: str = Field(min_length=12, max_length=12, description="So CCCD 12 chu so cua thi sinh")
    ma_chuong_trinh: str = Field(min_length=1)
    ma_phuong_thuc: str = Field(min_length=1)
    nguyen_vong: int = Field(ge=1, default=1)
    nam_tuyen_sinh: int = Field(ge=2000, le=2100)
    ma_to_hop: str | None = None
    diem_uu_tien_ap_dung: float | None = None
    tong_diem_xet_tuyen: float | None = None
    chung_chi: list[NopChungChiItem] = Field(default_factory=list)
    giai_thuong: list[NopGiaiThuongItem] = Field(default_factory=list)


class NopHoSoResponse(BaseModel):
    ma_ho_so: str
    cccd: str
    ma_chuong_trinh: str
    ma_phuong_thuc: str
    trang_thai: TrangThaiDuyet
    message: str


class TraCuuHoSoItem(BaseModel):
    ma_ho_so: str
    cccd: str
    ma_chuong_trinh: str
    ma_phuong_thuc: str
    nguyen_vong: int
    nam_tuyen_sinh: int
    trang_thai: TrangThaiDuyet
    ket_qua: str | None = None
    create_at: datetime
    timeline_trang_thai: str = "da_nop"

    model_config = {"from_attributes": True}
