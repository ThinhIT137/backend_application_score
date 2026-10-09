from datetime import datetime
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.core.exceptions import DuLieuKhongHopLe, HoSoNotFound, TrangThaiKhongHopLe
from src.models.admission import ChuongTrinhDaoTao, PhuongThucXetTuyen, ToHopXetTuyen, LichSuDiemChuan, DiemTrungTuyen
from src.models.diem_chuan import BangDiem, DiemChiTiet, ChungChi
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import ThiSinh, DanhMucMonHoc, GiaiThuong
from src.models.trang_thai_ho_so import TrangThaiDuyet, NguonDuLieu
from src.schemas.admission_schema import CutoffInput, Submission

def identity():
    return str(uuid4())

class AdmissionService:
    def __init__(self, db: Session):
        self.db = db

    def reference(self, model, key):
        if self.db.get(model, key) is None:
            raise DuLieuKhongHopLe(f"Unknown reference: {key}")

    def list_cutoffs(self, year=None, program=None):
        stmt = select(LichSuDiemChuan)
        if year is not None:
            stmt = stmt.where(LichSuDiemChuan.nam == year)
        if program is not None:
            stmt = stmt.where(LichSuDiemChuan.ma_chuong_trinh == program)
        return list(self.db.scalars(stmt.order_by(LichSuDiemChuan.nam.desc())).all())

    def get_cutoff(self, key):
        row = self.db.get(LichSuDiemChuan, key)
        if row is None:
            raise HoSoNotFound("Cutoff history not found")
        return row

    def save_cutoff(self, payload: CutoffInput, admin, key=None):
        self.reference(ChuongTrinhDaoTao, payload.ma_chuong_trinh)
        for item in payload.diem_trung_tuyen:
            self.reference(PhuongThucXetTuyen, item.ma_phuong_thuc)
        duplicate = self.db.scalars(select(LichSuDiemChuan).where(
            LichSuDiemChuan.ma_chuong_trinh == payload.ma_chuong_trinh,
            LichSuDiemChuan.nam == payload.nam)).first()
        if duplicate is not None and duplicate.ma_ls_dc != key:
            raise TrangThaiKhongHopLe("Program/year cutoff already exists")
        row = self.get_cutoff(key) if key else LichSuDiemChuan(ma_ls_dc=identity(), create_at=datetime.now())
        for field in ("ma_chuong_trinh", "nam", "chi_tieu", "trung_tuyen"):
            setattr(row, field, getattr(payload, field))
        row.ma_admin_cap_nhat = admin.ma_admin
        self.db.add(row)
        # Flush old children before replacement to respect the unique method constraint.
        row.diem_trung_tuyen.clear()
        self.db.flush()
        row.diem_trung_tuyen = [DiemTrungTuyen(ma_diem_tt=identity(),
            ma_phuong_thuc=d.ma_phuong_thuc, diem=d.diem, create_at=datetime.now())
            for d in payload.diem_trung_tuyen]
        self.db.flush()
        return row

    def delete_cutoff(self, key):
        self.db.delete(self.get_cutoff(key))
        self.db.flush()

    def submit(self, payload: Submission, user):
        self.reference(ThiSinh, user.cccd)
        self.reference(ChuongTrinhDaoTao, payload.ma_chuong_trinh)
        self.reference(PhuongThucXetTuyen, payload.ma_phuong_thuc)
        if payload.ma_to_hop is not None:
            self.reference(ToHopXetTuyen, payload.ma_to_hop)
        for transcript in payload.bang_diem:
            for grade in transcript.diem_mon:
                self.reference(DanhMucMonHoc, grade.ma_mon)
        for cert in payload.chung_chi:
            if Path(cert.file_dinh_kem.split("?")[0]).suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
                raise DuLieuKhongHopLe("Unsupported evidence file")
        existing = self.db.scalars(select(NguyenVongSinhVien).where(
            NguyenVongSinhVien.cccd == user.cccd,
            NguyenVongSinhVien.nam_tuyen_sinh == payload.nam_tuyen_sinh,
            NguyenVongSinhVien.nguyen_vong == payload.nguyen_vong)).first()
        if existing:
            raise TrangThaiKhongHopLe("Preference already submitted for this year")
        row = NguyenVongSinhVien(ma_ho_so=identity(), cccd=user.cccd,
            ma_chuong_trinh=payload.ma_chuong_trinh, ma_phuong_thuc=payload.ma_phuong_thuc,
            ma_to_hop=payload.ma_to_hop, nguyen_vong=payload.nguyen_vong,
            nam_tuyen_sinh=payload.nam_tuyen_sinh, nguon_du_lieu=NguonDuLieu.tu_nop,
            trang_thai=TrangThaiDuyet.cho, create_at=datetime.now())
        self.db.add(row)
        for transcript in payload.bang_diem:
            bang = BangDiem(ma_bang_diem=identity(), cccd=user.cccd,
                loai_diem=transcript.loai_diem, nam_hoc=transcript.nam_hoc)
            self.db.add(bang)
            bang.chi_tiet = [DiemChiTiet(ma_chi_tiet=identity(), ma_mon=g.ma_mon, diem_so=g.diem_so)
                for g in transcript.diem_mon]
        for cert in payload.chung_chi:
            self.db.add(ChungChi(ma_chung_chi=identity(), cccd=user.cccd,
                **cert.model_dump(), trang_thai_duyet=TrangThaiDuyet.cho, create_at=datetime.now()))
        for award in payload.giai_thuong:
            self.db.add(GiaiThuong(ma_giai_thuong=identity(), cccd=user.cccd, **award.model_dump()))
        # get_db owns commit/rollback: the dossier and its evidence form one transaction.
        self.db.flush()
        return row
