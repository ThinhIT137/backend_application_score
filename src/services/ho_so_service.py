from datetime import datetime

from src.core.exceptions import DuLieuKhongHopLe, HoSoNotFound, KhongDuDieuKienCongBo, TrangThaiKhongHopLe
from src.core.security import CurrentUser
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import LoTrinhTuyenSinh
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.diem_repository_interface import DiemRepositoryInterface
from src.repositories.ho_so_repository_interface import HoSoRepositoryInterface
from src.schemas.ho_so_schema import (
    CongBoKetQuaRequest,
    CongBoKetQuaResponse,
    HoSoDetail,
    MinhChungBangDiem,
    MinhChungChungChi,
    MinhChungGiaiThuong,
)
from src.services.adapters.notification import NotificationPublisher
from src.services.interface.ho_so_service_interface import HoSoServiceInterface


def _is_moc_cong_bo(moc: LoTrinhTuyenSinh) -> bool:
    haystack = f"{moc.loai_moc or ''} {moc.ten_moc or ''}".lower()
    return any(token in haystack for token in ("cong_bo", "công bố", "cong bo"))


class HoSoService(HoSoServiceInterface):
    def __init__(
        self,
        ho_so_repo: HoSoRepositoryInterface,
        diem_repo: DiemRepositoryInterface,
        notifier: NotificationPublisher,
    ) -> None:
        self.ho_so_repo = ho_so_repo
        self.diem_repo = diem_repo
        self.notifier = notifier

    def list_ho_so(
        self,
        *,
        trang_thai: TrangThaiDuyet | None,
        nam_tuyen_sinh: int | None,
        ma_chuong_trinh: str | None,
    ) -> list[NguyenVongSinhVien]:
        return self.ho_so_repo.list_ho_so(
            trang_thai=trang_thai,
            nam_tuyen_sinh=nam_tuyen_sinh,
            ma_chuong_trinh=ma_chuong_trinh,
        )

    def get_detail(self, ma_ho_so: str) -> HoSoDetail:
        ho_so = self.ho_so_repo.get_by_ma_ho_so(ma_ho_so)
        if ho_so is None:
            raise HoSoNotFound(f"Không tìm thấy hồ sơ {ma_ho_so}")
        return HoSoDetail.model_validate(ho_so).model_copy(
            update={
                "chung_chi": [
                    MinhChungChungChi.model_validate(item)
                    for item in self.ho_so_repo.list_chung_chi_by_cccd(ho_so.cccd)
                ],
                "giai_thuong": [
                    MinhChungGiaiThuong.model_validate(item)
                    for item in self.ho_so_repo.list_giai_thuong_by_cccd(ho_so.cccd)
                ],
                "bang_diem": [
                    MinhChungBangDiem.model_validate(item)
                    for item in self.ho_so_repo.list_bang_diem_by_cccd(ho_so.cccd)
                ],
            }
        )

    def _require_cho(self, ma_ho_so: str) -> NguyenVongSinhVien:
        ho_so = self.ho_so_repo.get_by_ma_ho_so(ma_ho_so)
        if ho_so is None:
            raise HoSoNotFound(f"Không tìm thấy hồ sơ {ma_ho_so}")
        if ho_so.trang_thai != TrangThaiDuyet.cho:
            raise TrangThaiKhongHopLe(
                f"Hồ sơ đã được xử lý (trạng thái={ho_so.trang_thai.value}), không duyệt lại"
            )
        return ho_so

    def duyet(self, ma_ho_so: str, admin: CurrentUser) -> NguyenVongSinhVien:
        ho_so = self._require_cho(ma_ho_so)
        ho_so.trang_thai = TrangThaiDuyet.hop_le
        ho_so.ma_admin_xu_ly = admin.ma_admin
        return ho_so

    def tu_choi(self, ma_ho_so: str, ly_do: str, admin: CurrentUser) -> NguyenVongSinhVien:
        if not ly_do or not ly_do.strip():
            raise DuLieuKhongHopLe("Từ chối hồ sơ phải kèm lý do")
        ho_so = self._require_cho(ma_ho_so)
        ho_so.trang_thai = TrangThaiDuyet.tu_choi
        ho_so.ket_qua = ly_do.strip()
        ho_so.ma_admin_xu_ly = admin.ma_admin
        return ho_so

    def _trong_moc_cong_bo(self, nam_tuyen_sinh: int, now: datetime) -> bool:
        moc_list = self.diem_repo.list_lo_trinh(nam_tuyen_sinh)
        relevant = [moc for moc in moc_list if _is_moc_cong_bo(moc)] or moc_list
        if not relevant:
            return False
        for moc in relevant:
            start = moc.thoi_gian_bat_dau
            end = moc.thoi_gian_ket_thuc
            if start is None:
                continue
            if start <= now and (end is None or now <= end):
                return True
        return False

    def cong_bo_ket_qua(self, payload: CongBoKetQuaRequest) -> CongBoKetQuaResponse:
        now = datetime.now()
        trong_moc = self._trong_moc_cong_bo(payload.nam_tuyen_sinh, now)
        so_cho = self.ho_so_repo.count_cho(
            nam_tuyen_sinh=payload.nam_tuyen_sinh,
            ma_chuong_trinh=payload.ma_chuong_trinh,
            ma_phuong_thuc=payload.ma_phuong_thuc,
        )
        if not trong_moc:
            raise KhongDuDieuKienCongBo("Chưa đến mốc thời gian công bố trong lộ trình tuyển sinh")
        if so_cho > 0:
            raise KhongDuDieuKienCongBo(
                f"Còn {so_cho} hồ sơ trạng thái 'cho', chưa thể công bố"
            )

        records = self.ho_so_repo.list_for_cong_bo(
            nam_tuyen_sinh=payload.nam_tuyen_sinh,
            ma_chuong_trinh=payload.ma_chuong_trinh,
            ma_phuong_thuc=payload.ma_phuong_thuc,
        )
        for ho_so in records:
            if not ho_so.ket_qua:
                if ho_so.trang_thai == TrangThaiDuyet.hop_le:
                    ho_so.ket_qua = "Đủ điều kiện xét tuyển (đã công bố)"
                elif ho_so.trang_thai == TrangThaiDuyet.tu_choi:
                    ho_so.ket_qua = ho_so.ket_qua or "Không đủ điều kiện (đã công bố)"

        self.notifier.trigger_cong_bo_ket_qua(payload.nam_tuyen_sinh)
        return CongBoKetQuaResponse(
            nam_tuyen_sinh=payload.nam_tuyen_sinh,
            so_ho_so=len(records),
            da_xu_ly_het=True,
            trong_moc_cong_bo=True,
            notification_triggered=True,
            idempotent=True,
        )
