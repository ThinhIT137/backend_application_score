from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.schemas.admission_schema import CutoffInput, CutoffOutput, Submission
from src.schemas.ho_so_schema import HoSoListItem
from src.services.admission_service import AdmissionService

router = APIRouter(tags=["admission"])

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
