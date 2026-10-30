from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.schemas.admission_schema import CutoffInput, CutoffOutput, Submission
from src.schemas.ho_so_schema import HoSoListItem
from src.services.admission_service import AdmissionService
from src.services.year_lock_service import lock_year
from src.models.year_lock import AdmissionYearLock
from pydantic import BaseModel, Field

router = APIRouter(tags=["admission"])


class YearLockConfirmation(BaseModel):
    confirmation_year: int = Field(strict=True, ge=2000, le=2100)


@router.get('/diem-chuan/nam/{year}/khoa')
def get_year_lock(year: int, _admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(AdmissionYearLock, year)
    return {'nam': year, 'locked': row is not None, 'locked_at': row.locked_at if row else None}


@router.post('/diem-chuan/nam/{year}/khoa')
def lock_year_scores(year: int, payload: YearLockConfirmation,
        admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    result = lock_year(db, year, payload.confirmation_year, admin)
    db.commit()
    return result

def get_admission_service(db: Session = Depends(get_db)):
    return AdmissionService(db)

@router.get("/diem-chuan", response_model=list[CutoffOutput])
def list_cutoffs(nam: int | None = Query(None, ge=1900, le=2100),
                 ma_chuong_trinh: str | None = None,
                 _admin: CurrentUser = Depends(require_admin),
                 service: AdmissionService = Depends(get_admission_service)):
    return service.list_cutoffs(nam, ma_chuong_trinh)

@router.get("/diem-chuan/{key}", response_model=CutoffOutput)
def get_cutoff(key: str, _admin: CurrentUser = Depends(require_admin),
               service: AdmissionService = Depends(get_admission_service)):
    return service.get_cutoff(key)

@router.post("/diem-chuan", response_model=CutoffOutput, status_code=201)
def create_cutoff(payload: CutoffInput, admin: CurrentUser = Depends(require_admin),
                  service: AdmissionService = Depends(get_admission_service)):
    return service.save_cutoff(payload, admin)

@router.put("/diem-chuan/{key}", response_model=CutoffOutput)
def update_cutoff(key: str, payload: CutoffInput, admin: CurrentUser = Depends(require_admin),
                  service: AdmissionService = Depends(get_admission_service)):
    return service.save_cutoff(payload, admin, key)

@router.delete("/diem-chuan/{key}", status_code=204)
def delete_cutoff(key: str, _admin: CurrentUser = Depends(require_admin),
                  service: AdmissionService = Depends(get_admission_service)):
    service.delete_cutoff(key)
    return Response(status_code=204)

@router.post("/ho-so", response_model=HoSoListItem, status_code=201)
def submit(payload: Submission, user: CurrentUser = Depends(require_thi_sinh),
           service: AdmissionService = Depends(get_admission_service)):
    return service.submit(payload, user)
