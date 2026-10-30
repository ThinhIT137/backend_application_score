from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.models.admission import NganhHoc
from src.models.diem_thi_sinh import BangDiem, ChungChi, DiemChiTiet
from src.models.giai_thuong import CapGiaiThuong, GiaiThuong, HangGiaiThuong, MonHoc
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import Admin, DanhMucMonHoc, LoTrinhTuyenSinh, ThiSinh
from src.models.trang_thai_ho_so import LoaiBangDiem, NguonDuLieu, TrangThaiDuyet

__all__ = [
    "Admin",
    "BangDiem",
    "CapGiaiThuong",
    "ChungChi",
    "DanhMucMonHoc",
    "DiemChiTiet",
    "DiemTrungTuyen",
    "GiaiThuong",
    "HangGiaiThuong",
    "LichSuDiemChuan",
    "LoTrinhTuyenSinh",
    "LoaiBangDiem",
    "MonHoc",
    "NganhHoc",
    "NguonDuLieu",
    "NguyenVongSinhVien",
    "ThiSinh",
    "TrangThaiDuyet",
]

from src.models.submission_operation import SubmissionOperation
from src.models.year_lock import AdmissionYearLock
