"""Validate submissions before any persistence; applicant identity comes from JWT."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from src.models.tham_chieu import HangGiaiThuong, CapGiaiThuong, MonHoc
from src.models.trang_thai_ho_so import LoaiBangDiem

class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class CutoffScore(InputModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)
    ma_phuong_thuc: str = Field(min_length=1)
    diem: float = Field(ge=0, allow_inf_nan=False)

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

class CutoffOutput(CutoffInput):
    model_config = ConfigDict(from_attributes=True)
    ma_ls_dc: str
    ma_admin_cap_nhat: str
    create_at: datetime

class Grade(InputModel):
    ma_mon: str = Field(min_length=1)
    diem_so: float = Field(ge=0, le=10, allow_inf_nan=False)

class Transcript(InputModel):
    loai_diem: Literal[LoaiBangDiem.lop_10, LoaiBangDiem.lop_11, LoaiBangDiem.lop_12]
    nam_hoc: int = Field(ge=1900, le=2100)
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
        keys = [(b.loai_diem, b.nam_hoc) for b in self.bang_diem]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate transcript")
        return self
