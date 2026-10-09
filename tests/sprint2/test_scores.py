from datetime import datetime
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from src.core.security import CurrentUser
from src.core.exceptions import DuLieuKhongHopLe, NguonDuLieuLoi, ChungChiNotFound
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.schemas.diem_schema import NopDgnlRequest,DongBoThptRequest,ThiSinhDiemThpt,DiemMonThpt

def test_thpt_success(scoring):
    service,repo,provider,_=scoring
    provider.fetch_thpt_scores.return_value=[ThiSinhDiemThpt(cccd="001",diem_mon=[DiemMonThpt(ma_mon="T",diem_so=8)])]
    result=service.dong_bo_thpt(DongBoThptRequest(nam_hoc=2026))
    assert (result.so_thanh_cong,result.so_loi)==(1,0)
    repo.upsert_bang_diem_tnthpt.assert_called_once()

def test_thpt_timeout(scoring):
    service,repo,provider,_=scoring
    provider.fetch_thpt_scores.side_effect=TimeoutError("timeout")
    result=service.dong_bo_thpt(DongBoThptRequest(nam_hoc=2026))
    assert not result.ket_noi_nguon_ok
    assert result.so_loi==1
    repo.upsert_bang_diem_tnthpt.assert_not_called()

@pytest.mark.parametrize("failure",["candidate","subject","database"])
def test_thpt_record_failure(scoring,failure):
    service,repo,provider,_=scoring
    provider.fetch_thpt_scores.return_value=[ThiSinhDiemThpt(cccd="001",diem_mon=[DiemMonThpt(ma_mon="T",diem_so=8)])]
    if failure=="candidate": repo.thi_sinh_exists.return_value=False
    if failure=="subject": repo.mon_exists.return_value=False
    if failure=="database": repo.upsert_bang_diem_tnthpt.side_effect=RuntimeError("DB error")
    result=service.dong_bo_thpt(DongBoThptRequest(nam_hoc=2026))
    assert (result.so_thanh_cong,result.so_loi)==(0,1)

def payload(file="evidence.pdf",score=100):
    return NopDgnlRequest(diem=score,ngay_cap=datetime(2026,1,1),file_dinh_kem=file)

def test_dgnl_submit(scoring):
    result=scoring[0].nop_dgnl(payload(),CurrentUser(role="thi_sinh",cccd="001"))
    assert result.cccd=="001"
    assert result.trang_thai_duyet==TrangThaiDuyet.cho
    assert result.loai_chung_chi=="DGNL"

@pytest.mark.parametrize("failure",["identity","candidate","duplicate","file"])
def test_dgnl_reject_invalid(scoring,failure):
    service,repo,_,_=scoring
    user=CurrentUser(role="thi_sinh",cccd=None if failure=="identity" else "001")
    if failure=="candidate": repo.thi_sinh_exists.return_value=False
    if failure=="duplicate": repo.find_dgnl_trung.return_value=object()
    with pytest.raises(DuLieuKhongHopLe):
        service.nop_dgnl(payload("evidence.exe" if failure=="file" else "evidence.pdf"),user)
    repo.create_chung_chi.assert_not_called()

@pytest.mark.parametrize("score",[-1,151])
def test_dgnl_schema_bounds(score):
    with pytest.raises(ValidationError): payload(score=score)

@pytest.mark.parametrize("outcome",["match","mismatch","timeout","missing"])
def test_dgnl_verification(scoring,outcome):
    service,repo,_,provider=scoring
    record=SimpleNamespace(ngay_cap=datetime(2026,1,1),cccd="001",diem_hoac_hang="100",loai_chung_chi="DGNL",trang_thai_duyet=TrangThaiDuyet.cho)
    repo.get_chung_chi.return_value=None if outcome=="missing" else record
    provider.diem_khop.return_value=outcome=="match"
    if outcome=="timeout": provider.diem_khop.side_effect=TimeoutError()
    errors={"mismatch":DuLieuKhongHopLe,"timeout":NguonDuLieuLoi,"missing":ChungChiNotFound}
    if outcome=="match":
        assert service.xac_nhan_dgnl("C1").trang_thai_duyet==TrangThaiDuyet.hop_le
    else:
        with pytest.raises(errors[outcome]): service.xac_nhan_dgnl("C1")


@pytest.mark.parametrize("score", [-1, 11, float("nan"), float("inf")])
def test_thpt_schema_rejects_invalid_score(score):
    with pytest.raises(ValidationError):
        DiemMonThpt(ma_mon="TOAN", diem_so=score)

def test_dgnl_expiry_cannot_precede_issue():
    with pytest.raises(ValidationError):
        NopDgnlRequest(diem=100, ngay_cap=datetime(2026, 1, 1),
            ngay_het_han=datetime(2025, 1, 1), file_dinh_kem="e.pdf")
