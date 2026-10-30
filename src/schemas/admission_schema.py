"""Validate submissions before any persistence; applicant identity comes from JWT."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from src.models.giai_thuong import HangGiaiThuong, CapGiaiThuong, MonHoc
from src.models.trang_thai_ho_so import LoaiBangDiem

class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class CutoffScore(InputModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)
    ma_phuong_thuc: str = Field(min_length=1)
    diem: float = Field(ge=0, allow_inf_nan=False)
    nguyen_vong_toi_da: int | None = Field(default=None, ge=1)
    diem_uu_tien_toi_thieu: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    dieu_kien_mon: dict | None = None

class CutoffInput(InputModel):
    ma_chuong_trinh: str = Field(min_length=1)
    nam: int = Field(ge=1900, le=2100)
    chi_tieu: int = Field(ge=0)
    trung_tuyen: int | None = Field(default=None, ge=0)
    diem_trung_tuyen: list[CutoffScore] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_methods(self):
        methods = [r.ma_phuong_thuc for r in self.diem_trung_tuyen]
        if len(methods) != len(set(methods)):
            raise ValueError("Duplicate admission method")
        return self

class ProgramBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ten_chuong_trinh: str | None = None
    ma_nganh: str | None = None

class MethodBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ten_phuong_thuc: str | None = None
    nhom_xet_tuyen: str | None = None
    diem_toi_thieu: float | None = None
    diem_toi_da: float | None = None

class CutoffScoreOutput(CutoffScore):
    ma_diem_tt: str
    phuong_thuc: MethodBrief | None = None

class CutoffOutput(CutoffInput):
    model_config = ConfigDict(from_attributes=True)
    # A quota may exist before the council has entered any cutoff scores.
    diem_trung_tuyen: list[CutoffScoreOutput] = Field(default_factory=list)
    ma_ls_dc: str
    ma_admin_cap_nhat: str
    create_at: datetime
    chuong_trinh: ProgramBrief | None = None
    diem_trung_tuyen: list[CutoffScoreOutput]

class Grade(InputModel):
    ma_mon: str = Field(min_length=1)
    diem_so: float = Field(ge=0, le=10, allow_inf_nan=False)

class Transcript(InputModel):
    loai_diem: Literal[LoaiBangDiem.lop_10, LoaiBangDiem.lop_11, LoaiBangDiem.lop_12]
    nam_hoc: int = Field(ge=1900, le=2100)
    hoc_ky: int = Field(default=0, ge=0, le=2)
    diem_mon: list[Grade] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_subjects(self):
        ids = [m.ma_mon for m in self.diem_mon]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate subject")
        return self

class Certificate(InputModel):
    loai_chung_chi: str = Field(min_length=1)
    diem_hoac_hang: str = Field(min_length=1)
    ngay_cap: datetime | None = None
    ngay_het_han: datetime | None = None
    file_dinh_kem: str = Field(min_length=1)

    @model_validator(mode="after")
    def dates(self):
        if self.ngay_cap and self.ngay_het_han and self.ngay_het_han < self.ngay_cap:
            raise ValueError("Expiry precedes issue date")
        if self.loai_chung_chi.upper() == "DGNL":
            raise ValueError("Use the DGNL endpoint")
        return self

class Award(InputModel):
    giai_thuong: HangGiaiThuong
    loai_giai_thuong: CapGiaiThuong
    mon_hoc: MonHoc
    file_dinh_kem: str | None = Field(default=None, min_length=1)

class Submission(InputModel):
    ma_chuong_trinh: str = Field(min_length=1)
    ma_phuong_thuc: str = Field(min_length=1)
    ma_to_hop: str | None = None
    nguyen_vong: int = Field(ge=1)
    nam_tuyen_sinh: int = Field(ge=1900, le=2100)
    bang_diem: list[Transcript] = Field(default_factory=list)
    chung_chi: list[Certificate] = Field(default_factory=list)
    giai_thuong: list[Award] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence(self):
        if not (self.bang_diem or self.chung_chi or self.giai_thuong):
            raise ValueError("At least one evidence item is required")
        keys = [(b.loai_diem, b.nam_hoc, b.hoc_ky) for b in self.bang_diem]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate transcript")
        periods = {}
        for b in self.bang_diem:
            periods.setdefault((b.loai_diem, b.nam_hoc), set()).add(b.hoc_ky)
        if any(0 in terms and len(terms) > 1 for terms in periods.values()):
            raise ValueError("Choose annual or semester grades for a class/year, not both")
        return self
