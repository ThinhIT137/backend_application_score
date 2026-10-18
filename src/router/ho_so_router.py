from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from src.core.database import get_db
from src.core.config import get_settings
from src.core.exceptions import DuLieuKhongHopLe
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.diem_repository import DiemRepository
from src.repositories.ho_so_repository import HoSoRepository
from src.schemas.ho_so_schema import (
    CongBoKetQuaRequest,
    CongBoKetQuaResponse,
    DanhSachKetQuaResponse,
    HoSoDetail,
    HoSoListItem,
    KetQuaTraCuuResponse,
    TraCuuHoSoItem,
    TuChoiHoSoRequest,
)
from src.services.adapters.notification import build_notification_publisher
from src.services.ho_so_service import HoSoService

router = APIRouter(prefix="/ho-so", tags=["ho-so"])


def get_ho_so_service(db: Session = Depends(get_db)) -> HoSoService:
    return HoSoService(
        HoSoRepository(db),
        DiemRepository(db),
        build_notification_publisher(get_settings()),
    )


# --- Sprint 1: Tra cứu trạng thái hồ sơ (Thí sinh, no auth) ---
# Đặt TRƯỚC /{ma_ho_so} để tránh conflict URL path
@router.get("/tra-cuu", response_model=list[TraCuuHoSoItem])
def tra_cuu_ho_so(
    ma_ho_so: str | None = Query(default=None),
    cccd: str | None = Query(default=None),
    nam_tuyen_sinh: int | None = Query(default=None),
    service: HoSoService = Depends(get_ho_so_service),
) -> list[TraCuuHoSoItem]:
    if not ma_ho_so and not cccd:
        raise DuLieuKhongHopLe("Vui lòng cung cấp mã hồ sơ hoặc số CCCD để tra cứu")

    records = service.tra_cuu(
        ma_ho_so=ma_ho_so,
        cccd=cccd,
        nam_tuyen_sinh=nam_tuyen_sinh,
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
                trang_thai=r.trang_thai,
                ket_qua=r.ket_qua,
                create_at=r.create_at,
                timeline_trang_thai=tl,
            )
        )
    return results


# --- Sprint 2: Quản lý & duyệt hồ sơ (Admin) ---
@router.get("/ket-qua/tra-cuu", response_model=KetQuaTraCuuResponse)
def tra_cuu_ket_qua(
    ma_ho_so: str | None = Query(default=None),
    cccd: str | None = Query(default=None),
    nam_tuyen_sinh: int | None = Query(default=None),
    nguyen_vong: int | None = Query(default=None),
    ket_qua: Literal["trung_tuyen", "khong_trung_tuyen"] | None = Query(default=None),
    service: HoSoService = Depends(get_ho_so_service),
) -> KetQuaTraCuuResponse:
    service.tra_cuu_ket_qua(
        ma_ho_so=ma_ho_so,
        cccd=cccd,
        nam_tuyen_sinh=nam_tuyen_sinh,
        nguyen_vong=nguyen_vong,
        ket_qua=ket_qua,
    )
    return KetQuaTraCuuResponse(
        trang_thai_cong_bo="chua_cong_bo",
        thong_bao="Chưa có kết quả xét tuyển đã được xác nhận và công bố.",
        items=[],
    )


@router.get("/ket-qua", response_model=DanhSachKetQuaResponse)
def list_ket_qua(
    _admin: CurrentUser = Depends(require_admin),
    service: HoSoService = Depends(get_ho_so_service),
    nam_tuyen_sinh: int | None = Query(default=None),
    ma_chuong_trinh: str | None = Query(default=None),
    ma_phuong_thuc: str | None = Query(default=None),
    ket_qua: Literal["trung_tuyen", "khong_trung_tuyen"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DanhSachKetQuaResponse:
    items = service.list_ket_qua(
        nam_tuyen_sinh=nam_tuyen_sinh,
        ma_chuong_trinh=ma_chuong_trinh,
        ma_phuong_thuc=ma_phuong_thuc,
        ket_qua=ket_qua,
        page=page,
        page_size=page_size,
    )
    return DanhSachKetQuaResponse(
        trang_thai_cong_bo="chua_cong_bo",
        page=page,
        page_size=page_size,
        total=len(items),
        items=[],
    )


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
