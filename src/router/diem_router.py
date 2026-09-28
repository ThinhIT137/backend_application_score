from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.repositories.diem_repository import DiemRepository
from src.schemas.diem_schema import (
    ChungChiDgnlItem,
    DongBoThptRequest,
    DongBoThptResponse,
    NopDgnlRequest,
    YeuCauBoSungRequest,
)
from src.services.adapters.mock_providers import MockBoGddtProvider, MockDhqgDgnlProvider
from src.services.diem_service import DiemService

router = APIRouter(prefix="/diem", tags=["diem"])


def get_diem_service(db: Session = Depends(get_db)) -> DiemService:
    settings = get_settings()
    thpt = MockBoGddtProvider() if settings.thpt_provider == "mock" else MockBoGddtProvider()
    dgnl = MockDhqgDgnlProvider() if settings.dgnl_provider == "mock" else MockDhqgDgnlProvider()
    return DiemService(DiemRepository(db), thpt, dgnl)


@router.post("/dong-bo-thpt", response_model=DongBoThptResponse)
def dong_bo_thpt(
    payload: DongBoThptRequest,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemService = Depends(get_diem_service),
) -> DongBoThptResponse:
    return service.dong_bo_thpt(payload)


@router.post("/dgnl", response_model=ChungChiDgnlItem)
def nop_dgnl(
    payload: NopDgnlRequest,
    user: CurrentUser = Depends(require_thi_sinh),
    service: DiemService = Depends(get_diem_service),
) -> ChungChiDgnlItem:
    return service.nop_dgnl(payload, user)


@router.get("/dgnl/cho-xac-minh", response_model=list[ChungChiDgnlItem])
def list_dgnl_cho(
    _admin: CurrentUser = Depends(require_admin),
    service: DiemService = Depends(get_diem_service),
) -> list[ChungChiDgnlItem]:
    return [ChungChiDgnlItem.model_validate(item) for item in service.list_dgnl_cho()]


@router.patch("/dgnl/{ma_chung_chi}/xac-nhan", response_model=ChungChiDgnlItem)
def xac_nhan_dgnl(
    ma_chung_chi: str,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemService = Depends(get_diem_service),
) -> ChungChiDgnlItem:
    return ChungChiDgnlItem.model_validate(service.xac_nhan_dgnl(ma_chung_chi))


@router.patch("/dgnl/{ma_chung_chi}/yeu-cau-bo-sung", response_model=ChungChiDgnlItem)
def yeu_cau_bo_sung(
    ma_chung_chi: str,
    _payload: YeuCauBoSungRequest = Body(default=YeuCauBoSungRequest()),
    _admin: CurrentUser = Depends(require_admin),
    service: DiemService = Depends(get_diem_service),
) -> ChungChiDgnlItem:
    return ChungChiDgnlItem.model_validate(service.yeu_cau_bo_sung(ma_chung_chi))
