from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.diem_repository import DiemRepository
from src.repositories.ho_so_repository import HoSoRepository
from src.schemas.ho_so_schema import (
    CongBoKetQuaRequest,
    CongBoKetQuaResponse,
    HoSoDetail,
    HoSoListItem,
    TuChoiHoSoRequest,
)
from src.services.adapters.notification import NoOpNotificationPublisher
from src.services.ho_so_service import HoSoService

router = APIRouter(prefix="/ho-so", tags=["ho-so"])


def get_ho_so_service(db: Session = Depends(get_db)) -> HoSoService:
    return HoSoService(HoSoRepository(db), DiemRepository(db), NoOpNotificationPublisher())


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
