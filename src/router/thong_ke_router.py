from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import CurrentUser, require_admin
from src.repositories.thong_ke_repository import ThongKeRepository
from src.schemas.thong_ke_schema import (
    BaoCaoTrungTuyenResponse,
    ThongKeNganhItem,
    ThongKeTongQuanResponse,
    ThongKeXetTuyenResponse,
)
from src.services.thong_ke_service import ThongKeService

router = APIRouter(tags=["thong-ke-bao-cao"])


def get_thong_ke_service(db: Session = Depends(get_db)) -> ThongKeService:
    return ThongKeService(ThongKeRepository(db))


@router.get("/thong-ke/tong-quan", response_model=ThongKeTongQuanResponse)
def thong_ke_tong_quan(
    _admin: CurrentUser = Depends(require_admin),
    service: ThongKeService = Depends(get_thong_ke_service),
    nam_tuyen_sinh: int = Query(default=datetime.now().year, ge=2000, le=2100),
    tu_ngay: date | None = Query(default=None),
    den_ngay: date | None = Query(default=None),
) -> ThongKeTongQuanResponse:
    return service.tong_quan(
        nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
    )


@router.get("/thong-ke/nganh-hoc", response_model=list[ThongKeNganhItem])
def thong_ke_theo_nganh(
    _admin: CurrentUser = Depends(require_admin),
    service: ThongKeService = Depends(get_thong_ke_service),
    nam_tuyen_sinh: int = Query(default=datetime.now().year, ge=2000, le=2100),
    tu_ngay: date | None = Query(default=None),
    den_ngay: date | None = Query(default=None),
) -> list[ThongKeNganhItem]:
    return service.theo_nganh(
        nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
    )


@router.get("/thong-ke/xet-tuyen", response_model=ThongKeXetTuyenResponse)
def thong_ke_theo_xet_tuyen(
    _admin: CurrentUser = Depends(require_admin),
    service: ThongKeService = Depends(get_thong_ke_service),
    nam_tuyen_sinh: int = Query(default=datetime.now().year, ge=2000, le=2100),
    tu_ngay: date | None = Query(default=None),
    den_ngay: date | None = Query(default=None),
) -> ThongKeXetTuyenResponse:
    return service.theo_xet_tuyen(
        nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
    )


@router.get("/bao-cao/trung-tuyen", response_model=BaoCaoTrungTuyenResponse)
def bao_cao_trung_tuyen(
    _admin: CurrentUser = Depends(require_admin),
    service: ThongKeService = Depends(get_thong_ke_service),
    nam_tuyen_sinh: int = Query(default=datetime.now().year, ge=2000, le=2100),
    ma_nganh: str | None = Query(default=None),
    ma_chuong_trinh: str | None = Query(default=None),
    ma_phuong_thuc: str | None = Query(default=None),
    ma_to_hop: str | None = Query(default=None),
    ket_qua: Literal[
        "trung_tuyen", "khong_trung_tuyen", "chua_cong_bo"
    ]
    | None = Query(default=None),
    tu_ngay: date | None = Query(default=None),
    den_ngay: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> BaoCaoTrungTuyenResponse:
    return service.bao_cao_trung_tuyen(
        nam_tuyen_sinh=nam_tuyen_sinh,
        ma_nganh=ma_nganh,
        ma_chuong_trinh=ma_chuong_trinh,
        ma_phuong_thuc=ma_phuong_thuc,
        ma_to_hop=ma_to_hop,
        ket_qua=ket_qua,
        tu_ngay=tu_ngay,
        den_ngay=den_ngay,
        page=page,
        page_size=page_size,
    )
