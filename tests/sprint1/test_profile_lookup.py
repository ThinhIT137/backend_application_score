import pytest
from src.core.exceptions import HoSoNotFound
from src.models.trang_thai_ho_so import TrangThaiDuyet

def test_detail_returns_status_and_evidence(profile):
    service,repo,_,_=profile
    result=service.get_detail("H1")
    assert result.ma_ho_so=="H1"
    assert result.trang_thai==TrangThaiDuyet.cho
    assert result.chung_chi==result.giai_thuong==result.bang_diem==[]
    repo.list_chung_chi_by_cccd.assert_called_once_with("001")

def test_detail_missing(profile):
    service,repo,_,_=profile
    repo.get_by_ma_ho_so.return_value=None
    with pytest.raises(HoSoNotFound):
        service.get_detail("missing")

def test_detail_db_failure(profile):
    service,repo,_,_=profile
    repo.get_by_ma_ho_so.side_effect=RuntimeError("DB unavailable")
    with pytest.raises(RuntimeError,match="DB unavailable"):
        service.get_detail("H1")


def test_student_reads_own_profile(profile):
    from src.core.security import CurrentUser
    result = profile[0].get_own_detail("H1", CurrentUser(role="thi_sinh", cccd="001"))
    assert result.cccd == "001"

def test_student_cannot_read_other_profile(profile):
    from src.core.security import CurrentUser
    with pytest.raises(HoSoNotFound):
        profile[0].get_own_detail("H1", CurrentUser(role="thi_sinh", cccd="other"))

def test_student_lookup_requires_identity(profile):
    from src.core.security import CurrentUser
    from src.core.exceptions import DuLieuKhongHopLe
    with pytest.raises(DuLieuKhongHopLe):
        profile[0].get_own_detail("H1", CurrentUser(role="thi_sinh"))
