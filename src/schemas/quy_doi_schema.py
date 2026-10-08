from pydantic import BaseModel, Field


class DiemThptInput(BaseModel):
    """Diem thi THPT tung mon (0-10, buoc 0.25)."""
    ma_mon: str = Field(min_length=1, description="Ma mon hoc (vi du: toan, van, anh...)")
    diem: float = Field(ge=0.0, description="Diem so mon thi")


class DiemChungChiInput(BaseModel):
    """Diem chung chi quoc te hoac DGNL."""
    loai: str = Field(
        min_length=1,
        description="Loai chung chi: IELTS / TOEFL_IBT / TOEIC / SAT / ACT / HSA / VACT / TSA",
    )
    diem: float = Field(ge=0.0, description="Diem so")


class QuyDoiRequest(BaseModel):
    """Request tinh diem quy doi va so sanh cac phuong thuc."""
    diem_thpt: list[DiemThptInput] = Field(
        default_factory=list,
        description="Danh sach diem THPT tung mon (tuy chon)",
    )
    chung_chi: list[DiemChungChiInput] = Field(
        default_factory=list,
        description="Danh sach chung chi quoc te / DGNL (tuy chon)",
    )
    doi_tuong_uu_tien: str | None = Field(
        default=None,
        description="Ma doi tuong uu tien (KV1 / KV2NT / KV2 / KV3 hoac doi tuong 01-10...)",
    )
    ma_to_hop: str | None = Field(
        default=None,
        description="To hop xet tuyen (vi du: A00, D01...) -- bo trong neu khong ro",
    )
    nam_so_sanh: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
        description="Nam diem chuan dung de tinh phan vi (mac dinh: nam gan nhat co du lieu)",
    )
    ma_chuong_trinh: str | None = Field(
        default=None,
        description="Chuong trinh dao tao muon so sanh (bo trong = tat ca nganh)",
    )


class PhuongThucQuyDoiItem(BaseModel):
    """Ket qua quy doi cho 1 phuong thuc cu the."""
    ma_phuong_thuc: str
    ten_phuong_thuc: str | None = None
    diem_quy_doi: float
    diem_chuan: float | None = None
    chenh_lech: float | None = None
    phan_vi: float | None = Field(
        default=None,
        description="Phan vi 0-100: bao nhieu % nam truoc co diem <= diem_quy_doi",
    )
    dat_chuan: bool | None = None


class QuyDoiResponse(BaseModel):
    """Ket qua tinh diem quy doi."""
    diem_uu_tien: float = Field(description="Diem uu tien duoc cong them")
    phuong_thuc_tot_nhat: str | None = Field(
        default=None,
        description="Ma phuong thuc co diem quy doi/chenh lech tot nhat",
    )
    chi_tiet: list[PhuongThucQuyDoiItem] = Field(default_factory=list)
    canh_bao: list[str] = Field(
        default_factory=list,
        description="Cac canh bao validate (diem ngoai dai hop le, thieu du lieu...)",
    )
