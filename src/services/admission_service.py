from datetime import datetime
import re
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from src.core.exceptions import DuLieuKhongHopLe, HoSoNotFound, TrangThaiKhongHopLe, ForbiddenError
from src.models.admission import ChuongTrinhDaoTao, PhuongThucXetTuyen, ToHopXetTuyen
from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.models.diem_thi_sinh import BangDiem, DiemChiTiet, ChungChi
from src.models.ho_so import NguyenVongSinhVien
from src.models.giai_thuong import GiaiThuong
from src.models.tham_chieu import ThiSinh, DanhMucMonHoc
from src.models.trang_thai_ho_so import TrangThaiDuyet, NguonDuLieu
from src.schemas.admission_schema import CutoffInput, Submission

def identity():
    return str(uuid4())

# Tầng nghiệp vụ hồ sơ/điểm chuẩn; dùng Session do router cấp, không tự mở kết nối mới.
class AdmissionService:
    def __init__(self, db: Session):
        self.db = db

    def reference(self, model, key):
        if self.db.get(model, key) is None:
            raise DuLieuKhongHopLe(f"Unknown reference: {key}")

    def list_cutoffs(self, year=None, program=None):
        stmt = self._cutoff_query()
        if year is not None:
            stmt = stmt.where(LichSuDiemChuan.nam == year)
        if program is not None:
            stmt = stmt.where(LichSuDiemChuan.ma_chuong_trinh == program)
        return list(self.db.scalars(stmt.order_by(LichSuDiemChuan.nam.desc())).unique().all())

    @staticmethod
    def _cutoff_query():
        # Tải đủ quan hệ mà CutoffOutput cần trong một query. Nếu để lazy load,
        # mỗi dòng và phương thức lại gọi Supabase khi FastAPI serialize JSON.
        return select(LichSuDiemChuan).options(
            joinedload(LichSuDiemChuan.chuong_trinh),
            joinedload(LichSuDiemChuan.diem_trung_tuyen).joinedload(DiemTrungTuyen.phuong_thuc),
        )

    def get_cutoff(self, key):
        row = self.db.scalars(self._cutoff_query().where(LichSuDiemChuan.ma_ls_dc == key)).unique().one_or_none()
        if row is None:
            raise HoSoNotFound("Cutoff history not found")
        return row

    # Tạo/sửa điểm chuẩn theo chương trình-năm, kiểm tra mã tham chiếu và tránh bản ghi trùng.
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
        # Khi thay danh sách điểm theo phương thức, giữ điều kiện cũ nếu payload không gửi lại trường đó.
        previous = {d.ma_phuong_thuc: {field: getattr(d, field) for field in ("nguyen_vong_toi_da", "dieu_kien_mon", "diem_uu_tien_toi_thieu")} for d in row.diem_trung_tuyen}
        # Flush old children before replacement to respect the unique method constraint.
        row.diem_trung_tuyen.clear()
        self.db.flush()
        row.diem_trung_tuyen = [DiemTrungTuyen(ma_diem_tt=identity(),
            ma_phuong_thuc=d.ma_phuong_thuc, diem=d.diem, create_at=datetime.now(),
            **{field: getattr(d, field) if field in d.model_fields_set else previous.get(d.ma_phuong_thuc, {}).get(field)
               for field in ("nguyen_vong_toi_da", "dieu_kien_mon", "diem_uu_tien_toi_thieu")})
            for d in payload.diem_trung_tuyen]
        self.db.flush()
        # Chương trình có thể vừa đổi và danh sách con vừa được thay thế: tải
        # lại quan hệ cho response, tránh giữ cache cũ hoặc lazy query từng con.
        self.db.expire(row, ["chuong_trinh", "diem_trung_tuyen"])
        return self.get_cutoff(row.ma_ls_dc)

    def delete_cutoff(self, key):
        self.db.delete(self.get_cutoff(key))
        self.db.flush()

    # Nhận hồ sơ đã qua schema; chủ hồ sơ luôn là CCCD trong JWT, không lấy danh tính từ payload.
    def submit(self, payload: Submission, user):
        # Serialize submission with evidence replacement in Next.js Storage handler.
        self.db.scalar(select(ThiSinh).where(ThiSinh.cccd == user.cccd).with_for_update())
        self.reference(ThiSinh, user.cccd)
        self.reference(ChuongTrinhDaoTao, payload.ma_chuong_trinh)
        self.reference(PhuongThucXetTuyen, payload.ma_phuong_thuc)
        if payload.ma_to_hop is not None:
            self.reference(ToHopXetTuyen, payload.ma_to_hop)
        # Xác nhận các môn tồn tại trước khi tạo bảng điểm nhiều năm/kỳ.
        for transcript in payload.bang_diem:
            for grade in transcript.diem_mon:
                self.reference(DanhMucMonHoc, grade.ma_mon)
        for cert in [*payload.chung_chi, *payload.giai_thuong]:
            if not cert.file_dinh_kem:
                continue
            # Exact keys generated by /api/evidence. URLs/traversal are never keys.
            match = re.fullmatch(r"([0-9]{12})/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(pdf|jpg|png)", cert.file_dinh_kem)
            if match is None:
                raise DuLieuKhongHopLe("Minh chứng không thuộc định dạng kho lưu trữ được hỗ trợ")
            if match.group(1) != user.cccd:
                raise ForbiddenError("Minh chứng không thuộc thí sinh này")
        # Trong cùng năm, một thí sinh không được gửi trùng số thứ tự nguyện vọng.
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
                loai_diem=transcript.loai_diem, nam_hoc=transcript.nam_hoc, hoc_ky=transcript.hoc_ky)
            self.db.add(bang)
            bang.chi_tiet = [DiemChiTiet(ma_chi_tiet=identity(), ma_mon=g.ma_mon, diem_so=g.diem_so)
                for g in transcript.diem_mon]
        # Lưu riêng chứng chỉ và giải thưởng; chứng chỉ mới ở trạng thái chờ xác minh.
        for cert in payload.chung_chi:
            self.db.add(ChungChi(ma_chung_chi=identity(), cccd=user.cccd,
                **cert.model_dump(), trang_thai_duyet=TrangThaiDuyet.cho, create_at=datetime.now()))
        for award in payload.giai_thuong:
            self.db.add(GiaiThuong(ma_giai_thuong=identity(), cccd=user.cccd, **award.model_dump()))
        # get_db owns commit/rollback: the dossier and its evidence form one transaction.
        self.db.flush()
        return row
