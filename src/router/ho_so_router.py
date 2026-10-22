from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.models.ho_so import NguyenVongSinhVien
from src.models.admission import ChuongTrinhDaoTao, NganhHoc, PhuongThucXetTuyen

from src.core.database import get_db
from src.core.exceptions import DuLieuKhongHopLe
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.models.trang_thai_ho_so import TrangThaiHoSo as TrangThaiDuyet
from src.repositories.diem_repository import DiemRepository
from src.repositories.ho_so_repository import HoSoRepository
from src.schemas.ho_so_schema import (
    CongBoKetQuaRequest,
    CongBoKetQuaResponse,
    HoSoDetail,
    HoSoListItem,
    TraCuuHoSoItem,
    OwnLookupItem,
    TuChoiHoSoRequest,
)
from src.services.adapters.notification import NoOpNotificationPublisher
from src.services.ho_so_service import HoSoService
from src.schemas.candidate_preferences_schema import ReorderPreferences
from src.services.candidate_preferences_service import CandidatePreferencesService, pending_self_submission
from src.models.workflow import NotificationOutbox
from src.services.result_state import result_label, public_status, published

router = APIRouter(prefix="/ho-so", tags=["ho-so"])


def get_ho_so_service(db: Session = Depends(get_db)) -> HoSoService:
    return HoSoService(HoSoRepository(db), DiemRepository(db), NoOpNotificationPublisher())


# --- Sprint 1: Tra cứu trạng thái hồ sơ (Thí sinh, no auth) ---
@router.get("/cua-toi")
def my_preferences(
    user: CurrentUser = Depends(require_thi_sinh),
    db: Session = Depends(get_db),
):
    if not user.cccd:
        raise DuLieuKhongHopLe("Thiếu định danh thí sinh")
    rows = db.execute(select(NguyenVongSinhVien, ChuongTrinhDaoTao.ten_chuong_trinh,
        NganhHoc.ten_nganh, PhuongThucXetTuyen.ten_phuong_thuc)
        .outerjoin(ChuongTrinhDaoTao, NguyenVongSinhVien.ma_chuong_trinh == ChuongTrinhDaoTao.ma_chuong_trinh)
        .outerjoin(NganhHoc, ChuongTrinhDaoTao.ma_nganh == NganhHoc.ma_nganh)
        .outerjoin(PhuongThucXetTuyen, NguyenVongSinhVien.ma_phuong_thuc == PhuongThucXetTuyen.ma_phuong_thuc)
        .where(NguyenVongSinhVien.cccd == user.cccd)
        .order_by(NguyenVongSinhVien.nam_tuyen_sinh.desc(), NguyenVongSinhVien.nguyen_vong,
            NguyenVongSinhVien.create_at, NguyenVongSinhVien.ma_ho_so)).all()
    notified = set(db.scalars(select(NotificationOutbox.ma_ho_so).where(
        NotificationOutbox.ma_ho_so.in_([r.ma_ho_so for r, *_ in rows]))).all()) if rows else set()
    return [{"ma_ho_so": r.ma_ho_so, "nguyen_vong": r.nguyen_vong, "nam_tuyen_sinh": r.nam_tuyen_sinh,
        "ma_chuong_trinh": r.ma_chuong_trinh, "ten_chuong_trinh": program, "ten_nganh": major,
        "ma_phuong_thuc": r.ma_phuong_thuc, "ten_phuong_thuc": method, "ma_to_hop": r.ma_to_hop,
        "trang_thai": public_status(r), "ket_qua": r.ket_qua if published(r) or r.trang_thai == TrangThaiDuyet.tu_choi else None,
        "create_at": r.create_at,
        "co_the_chinh_sua": pending_self_submission(r) and r.ma_ho_so not in notified} for r, program, major, method in rows]


@router.put("/cua-toi/thu-tu")
def reorder_my_preferences(
    payload: ReorderPreferences,
    user: CurrentUser = Depends(require_thi_sinh),
    db: Session = Depends(get_db),
):
    return CandidatePreferencesService(db).reorder(payload, user)


@router.delete("/cua-toi/{ma_ho_so}")
def withdraw_my_preference(
    ma_ho_so: str,
    user: CurrentUser = Depends(require_thi_sinh),
    db: Session = Depends(get_db),
):
    return CandidatePreferencesService(db).withdraw(ma_ho_so, user)


# Đặt TRƯỚC /{ma_ho_so} để tránh conflict URL path
@router.get("/tra-cuu", response_model=list[OwnLookupItem])
def tra_cuu_ho_so(
    ma_ho_so: str | None = Query(default=None),
    cccd: str | None = Query(default=None),
    nam_tuyen_sinh: int | None = Query(default=None),
    user: CurrentUser = Depends(require_thi_sinh),
    service: HoSoService = Depends(get_ho_so_service),
) -> list[TraCuuHoSoItem]:
    if not ma_ho_so and not cccd:
        raise DuLieuKhongHopLe("Vui lòng cung cấp mã hồ sơ hoặc số CCCD để tra cứu")

    records = service.tra_cuu(
        ma_ho_so=ma_ho_so,
        cccd=cccd,
        nam_tuyen_sinh=nam_tuyen_sinh,
        user_cccd=user.cccd,
    )
    results = []
    for r in records:
        tl = "da_nop"
        if r.trang_thai == TrangThaiDuyet.hop_le:
            tl = "hop_le"
        elif r.trang_thai == TrangThaiDuyet.tu_choi:
            tl = "tu_choi"
        results.append(
            TraCuuHoSoItem(
                ma_ho_so=r.ma_ho_so,
                cccd=r.cccd,
                ma_chuong_trinh=r.ma_chuong_trinh,
                ma_phuong_thuc=r.ma_phuong_thuc,
                nguyen_vong=r.nguyen_vong,
                nam_tuyen_sinh=r.nam_tuyen_sinh,
                trang_thai=public_status(r),
                ket_qua=r.ket_qua if published(r) or r.trang_thai == TrangThaiDuyet.tu_choi else None,
                create_at=r.create_at,
                timeline_trang_thai=str(public_status(r).value if hasattr(public_status(r), "value") else public_status(r)),
            )
        )
    return results


# --- Sprint 2: Quản lý & duyệt hồ sơ (Admin) ---
@router.get("/ket-qua/tra-cuu", response_model=list[OwnLookupItem])
def tra_cuu_ket_qua(
    ma_ho_so: str | None = Query(default=None),
    cccd: str | None = Query(default=None),
    nam_tuyen_sinh: int | None = Query(default=None),
    nguyen_vong: int | None = Query(default=None),
    ket_qua: str | None = Query(default=None),
    user: CurrentUser = Depends(require_thi_sinh),
    service: HoSoService = Depends(get_ho_so_service),
) -> list[TraCuuHoSoItem]:
    records = service.tra_cuu_ket_qua(
        ma_ho_so=ma_ho_so,
        cccd=cccd,
        nam_tuyen_sinh=nam_tuyen_sinh,
        nguyen_vong=nguyen_vong,
        ket_qua=ket_qua,
        user_cccd=user.cccd,
    )
    results: list[TraCuuHoSoItem] = []
    for r in records:
        results.append(
            TraCuuHoSoItem(
                ma_ho_so=r.ma_ho_so,
                cccd=r.cccd,
                ma_chuong_trinh=r.ma_chuong_trinh,
                ma_phuong_thuc=r.ma_phuong_thuc,
                nguyen_vong=r.nguyen_vong,
                nam_tuyen_sinh=r.nam_tuyen_sinh,
                trang_thai=public_status(r),
                ket_qua=r.ket_qua if published(r) or r.trang_thai == TrangThaiDuyet.tu_choi else None,
                create_at=r.create_at,
                timeline_trang_thai=result_label(r),
            )
        )
    return results


@router.get("/ket-qua", response_model=list[TraCuuHoSoItem])
def list_ket_qua(
    _admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
    nam_tuyen_sinh: int | None = Query(default=None),
    ma_chuong_trinh: str | None = Query(default=None),
    ma_phuong_thuc: str | None = Query(default=None),
    ket_qua: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[TraCuuHoSoItem]:
    items = service.list_ket_qua(
        nam_tuyen_sinh=nam_tuyen_sinh,
        ma_chuong_trinh=ma_chuong_trinh,
        ma_phuong_thuc=ma_phuong_thuc,
        ket_qua=ket_qua,
        page=page,
        page_size=page_size,
    )
    results: list[TraCuuHoSoItem] = []
    for r in items:
        results.append(
            TraCuuHoSoItem(
                ma_ho_so=r.ma_ho_so,
                cccd=r.cccd,
                ma_chuong_trinh=r.ma_chuong_trinh,
                ma_phuong_thuc=r.ma_phuong_thuc,
                nguyen_vong=r.nguyen_vong,
                nam_tuyen_sinh=r.nam_tuyen_sinh,
                trang_thai=public_status(r),
                ket_qua=r.ket_qua if published(r) or r.trang_thai == TrangThaiDuyet.tu_choi else None,
                create_at=r.create_at,
                timeline_trang_thai=result_label(r),
            )
        )
    return results


@router.get("", response_model=list[HoSoListItem])
def list_ho_so(
    _admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
    trang_thai: TrangThaiDuyet | None = Query(default=None),
    nam_tuyen_sinh: int | None = Query(default=None),
    ma_chuong_trinh: str | None = Query(default=None),
) -> list[HoSoListItem]:
    items = service.list_ho_so(
        trang_thai=trang_thai,
        nam_tuyen_sinh=nam_tuyen_sinh,
        ma_chuong_trinh=ma_chuong_trinh,
    )
    return [HoSoListItem.model_validate(item) for item in items]


@router.post("/cong-bo-ket-qua", response_model=CongBoKetQuaResponse)
def cong_bo_ket_qua(
    payload: CongBoKetQuaRequest,
    _admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
) -> CongBoKetQuaResponse:
    return service.cong_bo_ket_qua(payload)


@router.get("/{ma_ho_so}", response_model=HoSoDetail)
def get_ho_so(
    ma_ho_so: str,
    _admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
) -> HoSoDetail:
    return service.get_detail(ma_ho_so)


@router.patch("/{ma_ho_so}/duyet", response_model=HoSoListItem)
def duyet_ho_so(
    ma_ho_so: str,
    admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
) -> HoSoListItem:
    return HoSoListItem.model_validate(service.duyet(ma_ho_so, admin))


@router.patch("/{ma_ho_so}/tu-choi", response_model=HoSoListItem)
def tu_choi_ho_so(
    ma_ho_so: str,
    payload: TuChoiHoSoRequest,
    admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
) -> HoSoListItem:
    return HoSoListItem.model_validate(service.tu_choi(ma_ho_so, payload.ly_do, admin))


@router.get("/cua-toi/{ma_ho_so}", response_model=HoSoDetail)
def get_my_profile(
    ma_ho_so: str,
    user: CurrentUser = Depends(require_thi_sinh),
    service: HoSoService = Depends(get_ho_so_service),
) -> HoSoDetail:
    return service.get_own_detail(ma_ho_so, user)
