from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.core.exceptions import (
    ChungChiNotFound,
    DuLieuKhongHopLe,
    NguonDuLieuLoi,
    TrangThaiKhongHopLe,
)
from src.core.security import CurrentUser
from src.models.diem_thi_sinh import ChungChi
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.diem_repository_interface import DiemRepositoryInterface
from src.schemas.diem_schema import (
    ChungChiDgnlItem,
    DongBoLoiItem,
    DongBoThptRequest,
    DongBoThptResponse,
    LOAI_CHUNG_CHI_DGNL,
    NopDgnlRequest,
)
from src.services.adapters.score_provider import ExternalDgnlProvider, ExternalScoreProvider
from src.services.interface.diem_service_interface import DiemServiceInterface

ALLOWED_EVIDENCE_EXT = {".pdf", ".jpg", ".jpeg", ".png"}


class DiemService(DiemServiceInterface):
    def __init__(
        self,
        diem_repo: DiemRepositoryInterface,
        thpt_provider: ExternalScoreProvider,
        dgnl_provider: ExternalDgnlProvider,
    ) -> None:
        self.diem_repo = diem_repo
        self.thpt_provider = thpt_provider
        self.dgnl_provider = dgnl_provider

    def dong_bo_thpt(self, payload: DongBoThptRequest) -> DongBoThptResponse:
        loi: list[DongBoLoiItem] = []
        try:
            records = self.thpt_provider.fetch_thpt_scores(payload.nam_hoc)
            ket_noi_ok = True
        except Exception as exc:  # noqa: BLE001 — adapter ngoài, không fail cả service
            return DongBoThptResponse(
                nam_hoc=payload.nam_hoc,
                so_thanh_cong=0,
                so_loi=1,
                ket_noi_nguon_ok=False,
                loi=[DongBoLoiItem(ly_do=f"Lỗi/timeout nguồn Bộ GD&ĐT: {exc}")],
            )

        thanh_cong = 0
        for item in records:
            try:
                if not self.diem_repo.thi_sinh_exists(item.cccd):
                    loi.append(DongBoLoiItem(cccd=item.cccd, ly_do="CCCD không có trong thi_sinh"))
                    continue
                unknown_mon = [m.ma_mon for m in item.diem_mon if not self.diem_repo.mon_exists(m.ma_mon)]
                if unknown_mon:
                    loi.append(
                        DongBoLoiItem(
                            cccd=item.cccd,
                            ly_do=f"Mã môn không tồn tại: {', '.join(unknown_mon)}",
                        )
                    )
                    continue
                self.diem_repo.upsert_bang_diem_tnthpt(item.cccd, payload.nam_hoc, item.diem_mon)
                thanh_cong += 1
            except Exception as exc:  # noqa: BLE001 — lỗi 1 thí sinh không fail cả batch
                loi.append(DongBoLoiItem(cccd=item.cccd, ly_do=str(exc)))

        return DongBoThptResponse(
            nam_hoc=payload.nam_hoc,
            so_thanh_cong=thanh_cong,
            so_loi=len(loi),
            ket_noi_nguon_ok=ket_noi_ok,
            loi=loi,
        )

    def nop_dgnl(self, payload: NopDgnlRequest, user: CurrentUser | None = None) -> ChungChiDgnlItem:
        # TODO: thay bằng JWT khi FE có đăng nhập thí sinh
        cccd = (user.cccd if user else None) or payload.cccd
        if not cccd:
            raise DuLieuKhongHopLe("Thiếu CCCD thí sinh")
        if not self.diem_repo.thi_sinh_exists(cccd):
            raise DuLieuKhongHopLe("CCCD không tồn tại trong hệ thống")

        suffix = Path(payload.file_dinh_kem.split("?")[0]).suffix.lower()
        if suffix not in ALLOWED_EVIDENCE_EXT:
            raise DuLieuKhongHopLe("File minh chứng phải là pdf/jpg/jpeg/png")

        nam = payload.ngay_cap.year
        if self.diem_repo.find_dgnl_trung(cccd, nam):
            raise DuLieuKhongHopLe(f"Đã nộp điểm ĐGNL cho năm {nam}")

        record = ChungChi(
            ma_chung_chi=str(uuid4()),
            cccd=cccd,
            loai_chung_chi=LOAI_CHUNG_CHI_DGNL,
            diem_hoac_hang=str(payload.diem),
            ngay_cap=payload.ngay_cap,
            ngay_het_han=payload.ngay_het_han,
            file_dinh_kem=payload.file_dinh_kem,
            trang_thai_duyet=TrangThaiDuyet.cho,
            create_at=datetime.now(),
        )
        saved = self.diem_repo.create_chung_chi(record)
        return ChungChiDgnlItem.model_validate(saved)

    def list_dgnl_cho(self) -> list[ChungChi]:
        return self.diem_repo.list_dgnl_cho()

    def _require_dgnl_cho(self, ma_chung_chi: str) -> ChungChi:
        record = self.diem_repo.get_chung_chi(ma_chung_chi)
        if record is None or record.loai_chung_chi != LOAI_CHUNG_CHI_DGNL:
            raise ChungChiNotFound(f"Không tìm thấy chứng chỉ ĐGNL {ma_chung_chi}")
        if record.trang_thai_duyet != TrangThaiDuyet.cho:
            raise TrangThaiKhongHopLe("Chứng chỉ ĐGNL đã được xử lý")
        return record

    def xac_nhan_dgnl(self, ma_chung_chi: str) -> ChungChi:
        record = self._require_dgnl_cho(ma_chung_chi)
        try:
            khop = self.dgnl_provider.diem_khop(record.cccd, record.diem_hoac_hang, record.ngay_cap.year if record.ngay_cap else None)
        except Exception as exc:  # noqa: BLE001
            raise NguonDuLieuLoi(f"Không đối soát được với ĐHQG: {exc}") from exc
        if not khop:
            raise DuLieuKhongHopLe("Điểm ĐGNL không khớp nguồn ĐHQG")
        record.trang_thai_duyet = TrangThaiDuyet.hop_le
        return record

    def yeu_cau_bo_sung(self, ma_chung_chi: str) -> ChungChi:
        record = self._require_dgnl_cho(ma_chung_chi)
        record.trang_thai_duyet = TrangThaiDuyet.tu_choi
        return record
