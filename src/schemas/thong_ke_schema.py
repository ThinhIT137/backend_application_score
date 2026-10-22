from datetime import date, datetime

from pydantic import BaseModel, Field


class XuHuongNgayItem(BaseModel):
    ngay: date
    so_luong: int


class ThongKeTongQuanResponse(BaseModel):
    nam_tuyen_sinh: int
    tong_ho_so: int
    cho_xu_ly: int
    hop_le: int
    tu_choi: int
    da_cong_bo: int
    trung_tuyen: int
    tong_chi_tieu: int
    tong_nganh: int
    ty_le_hoan_tat: float
    ty_le_trung_tuyen: float
    xu_huong_theo_ngay: list[XuHuongNgayItem] = Field(default_factory=list)


class ThongKeNganhItem(BaseModel):
    ma_nganh: str
    ten_nganh: str
    chi_tieu: int
    tong_ho_so: int
    hop_le: int
    tu_choi: int
    trung_tuyen: int
    ty_le_canh_tranh: float
    ty_le_lap_day: float


class ThongKePhuongThucItem(BaseModel):
    ma_phuong_thuc: str
    ten_phuong_thuc: str
    tong_ho_so: int
    hop_le: int
    trung_tuyen: int
    ty_trong: float
    ty_le_trung_tuyen: float


class ThongKeToHopItem(BaseModel):
    ma_to_hop: str
    tong_ho_so: int
    hop_le: int
    trung_tuyen: int
    ty_trong: float
    ty_le_trung_tuyen: float


class ThongKeXetTuyenResponse(BaseModel):
    nam_tuyen_sinh: int
    theo_phuong_thuc: list[ThongKePhuongThucItem] = Field(default_factory=list)
    theo_to_hop: list[ThongKeToHopItem] = Field(default_factory=list)


class BaoCaoTrungTuyenItem(BaseModel):
    ma_ho_so: str
    cccd: str
    ho_ten: str
    so_dien_thoai: str | None = None
    khu_vuc: str | None = None
    doi_tuong_uu_tien: str | None = None
    ma_nganh: str
    ten_nganh: str
    ma_chuong_trinh: str
    ten_chuong_trinh: str
    ma_phuong_thuc: str
    ten_phuong_thuc: str
    ma_to_hop: str | None = None
    nguyen_vong: int
    tong_diem_xet_tuyen: float | None = None
    diem_chuan: float | None = None
    trang_thai: str
    ket_qua: str | None = None
    ngay_nop: datetime


class BaoCaoTongHop(BaseModel):
    tong_ho_so: int
    trung_tuyen: int
    khong_trung_tuyen: int
    chua_cong_bo: int


class PhanTrang(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class BaoCaoTrungTuyenResponse(BaseModel):
    nam_tuyen_sinh: int
    tong_hop: BaoCaoTongHop
    phan_trang: PhanTrang
    du_lieu: list[BaoCaoTrungTuyenItem] = Field(default_factory=list)
