from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db
from src.core.security import CurrentUser, get_current_user, require_admin, require_thi_sinh
from src.repositories.diem_chuan_repository import DiemChuanRepository
from src.repositories.diem_repository import DiemRepository
from src.schemas.diem_schema import (
    ChungChiDgnlItem,
    QuyDoiDiemRequest,
    QuyDoiDiemResponse,
    DongBoThptRequest,
    DongBoThptResponse,
    NopDgnlRequest,
    YeuCauBoSungRequest,
)
from src.schemas.quy_doi_schema import QuyDoiRequest, QuyDoiResponse
from src.services.adapters.mock_providers import MockBoGddtProvider, MockDhqgDgnlProvider
from src.services.adapters.http_providers import HttpThptProvider, HttpDgnlProvider, DisabledProvider
from src.services.diem_chuan_service import DiemChuanService
from src.services.diem_service import DiemService
from src.services.conversion_service import convert_to_thpt
from src.schemas.score_preview import ScorePreviewRequest, ScorePreviewResponse
from src.services.score_preview import calculate_preview

router = APIRouter(prefix="/diem", tags=["diem"])


@router.post("/tinh-diem-doi-soat", response_model=ScorePreviewResponse)
def tinh_diem_doi_soat(payload: ScorePreviewRequest, db: Session = Depends(get_db)):
    return calculate_preview(db, payload)


def get_diem_service(db: Session = Depends(get_db)) -> DiemService:
    settings = get_settings()
    thpt = HttpThptProvider(settings.thpt_api_url, settings.thpt_api_token) if settings.thpt_provider == "http" else MockBoGddtProvider() if settings.thpt_provider == "mock" else DisabledProvider()
    dgnl = HttpDgnlProvider(settings.dgnl_api_url, settings.dgnl_api_token) if settings.dgnl_provider == "http" else MockDhqgDgnlProvider() if settings.dgnl_provider == "mock" else DisabledProvider()
    return DiemService(DiemRepository(db), thpt, dgnl)


def get_diem_chuan_service(db: Session = Depends(get_db)) -> DiemChuanService:
    return DiemChuanService(DiemChuanRepository(db))


@router.post("/dong-bo-thpt", response_model=DongBoThptResponse)
def dong_bo_thpt(
    payload: DongBoThptRequest,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemService = Depends(get_diem_service),
) -> DongBoThptResponse:
    result = service.dong_bo_thpt(payload)
    result.nguon = get_settings().thpt_provider
    return result


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


@router.post("/quy-doi", response_model=QuyDoiDiemResponse)
def quy_doi_diem(
    payload: QuyDoiDiemRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> QuyDoiDiemResponse:
    # A pure calculation: no DB dependency and no cross-service file access.
    return QuyDoiDiemResponse(
        phuong_thuc=payload.phuong_thuc,
        diem_goc=payload.diem,
        diem_thpt=convert_to_thpt(payload.phuong_thuc, payload.diem, payload.nam_tuyen_sinh),
        nam_tuyen_sinh=payload.nam_tuyen_sinh,
    )
