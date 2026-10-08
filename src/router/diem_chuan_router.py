from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import CurrentUser, require_admin
from src.repositories.diem_chuan_repository import DiemChuanRepository
from src.schemas.diem_chuan_schema import (
    DiemTrungTuyenItem,
    LichSuDiemChuanItem,
    SuaDiemChuanRequest,
    TaoDiemChuanRequest,
    ThemDiemTrungTuyenRequest,
)
from src.services.diem_chuan_service import DiemChuanService

router = APIRouter(prefix="/diem-chuan", tags=["diem-chuan"])


def get_diem_chuan_service(db: Session = Depends(get_db)) -> DiemChuanService:
    return DiemChuanService(DiemChuanRepository(db))


@router.get("", response_model=list[LichSuDiemChuanItem])
def list_diem_chuan(
    _admin: CurrentUser = Depends(require_admin),
    service: DiemChuanService = Depends(get_diem_chuan_service),
    ma_chuong_trinh: str | None = Query(default=None),
    nam: int | None = Query(default=None),
) -> list[LichSuDiemChuanItem]:
    records = service.list_diem_chuan(ma_chuong_trinh=ma_chuong_trinh, nam=nam)
    return [LichSuDiemChuanItem.model_validate(r) for r in records]


@router.post("", response_model=LichSuDiemChuanItem)
def tao_diem_chuan(
    payload: TaoDiemChuanRequest,
    admin: CurrentUser = Depends(require_admin),
    service: DiemChuanService = Depends(get_diem_chuan_service),
) -> LichSuDiemChuanItem:
    record = service.tao_diem_chuan(payload, ma_admin=admin.ma_admin)
    return LichSuDiemChuanItem.model_validate(record)


@router.put("/{ma_ls_dc}", response_model=LichSuDiemChuanItem)
def sua_diem_chuan(
    ma_ls_dc: str,
    payload: SuaDiemChuanRequest,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemChuanService = Depends(get_diem_chuan_service),
) -> LichSuDiemChuanItem:
    record = service.sua_diem_chuan(ma_ls_dc, payload)
    return LichSuDiemChuanItem.model_validate(record)


@router.delete("/{ma_ls_dc}")
def xoa_diem_chuan(
    ma_ls_dc: str,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemChuanService = Depends(get_diem_chuan_service),
) -> dict[str, str]:
    service.xoa_diem_chuan(ma_ls_dc)
    return {"message": f"Đã xoá điểm chuẩn {ma_ls_dc}"}


@router.post("/{ma_ls_dc}/diem-trung-tuyen", response_model=DiemTrungTuyenItem)
def them_diem_trung_tuyen(
    ma_ls_dc: str,
    payload: ThemDiemTrungTuyenRequest,
    _admin: CurrentUser = Depends(require_admin),
    service: DiemChuanService = Depends(get_diem_chuan_service),
) -> DiemTrungTuyenItem:
    record = service.them_diem_trung_tuyen(ma_ls_dc, payload)
    return DiemTrungTuyenItem.model_validate(record)
