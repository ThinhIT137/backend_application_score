from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from src.core.security import CurrentUser, require_admin, require_thi_sinh
from src.core.exceptions import DuLieuKhongHopLe, TrangThaiKhongHopLe, KhongDuDieuKienCongBo, ForbiddenError
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.schemas.ho_so_schema import CongBoKetQuaRequest

def test_approve(profile,record):
    service,_,_,_=profile
    assert service.duyet("H1",CurrentUser(role="admin",ma_admin="A1")) is record
    assert record.trang_thai==TrangThaiDuyet.hop_le
    assert record.ma_admin_xu_ly=="A1"

@pytest.mark.parametrize("status",[TrangThaiDuyet.hop_le,TrangThaiDuyet.tu_choi])
def test_no_reapproval(profile,record,status):
    record.trang_thai=status
    with pytest.raises(TrangThaiKhongHopLe):
        profile[0].duyet("H1",CurrentUser(role="admin",ma_admin="A1"))

def test_reject_reason(profile,record):
    profile[0].tu_choi("H1","  Thi?u minh ch?ng  ",CurrentUser(role="admin",ma_admin="A1"))
    assert record.ket_qua=="Thi?u minh ch?ng"
    assert record.trang_thai==TrangThaiDuyet.tu_choi

@pytest.mark.parametrize("reason",["","   "])
def test_reject_requires_reason(profile,reason):
    with pytest.raises(DuLieuKhongHopLe):
        profile[0].tu_choi("H1",reason,CurrentUser(role="admin",ma_admin="A1"))

def publication(profile,record):
    service,repo,scores,notify=profile
    now=datetime.now()
    scores.list_lo_trinh.return_value=[SimpleNamespace(loai_moc="cong_bo",ten_moc="C?ng b?",thoi_gian_bat_dau=now-timedelta(days=1),thoi_gian_ket_thuc=now+timedelta(days=1))]
    repo.count_cho.return_value=0
    repo.list_for_cong_bo.return_value=[record]
    record.trang_thai=TrangThaiDuyet.hop_le
    return service,repo,scores,notify

def test_publish(profile,record):
    service,_,_,notify=publication(profile,record)
    result=service.cong_bo_ket_qua(CongBoKetQuaRequest(nam_tuyen_sinh=2026))
    assert result.so_ho_so==1
    assert record.ket_qua
    notify.trigger_cong_bo_ket_qua.assert_called_once_with(2026)

def test_publish_blocks_pending(profile,record):
    service,repo,_,notify=publication(profile,record)
    repo.count_cho.return_value=1
    with pytest.raises(KhongDuDieuKienCongBo):
        service.cong_bo_ket_qua(CongBoKetQuaRequest(nam_tuyen_sinh=2026))
    notify.trigger_cong_bo_ket_qua.assert_not_called()

def test_publish_requires_milestone(profile,record):
    service,_,scores,notify=publication(profile,record)
    scores.list_lo_trinh.return_value=[]
    with pytest.raises(KhongDuDieuKienCongBo):
        service.cong_bo_ket_qua(CongBoKetQuaRequest(nam_tuyen_sinh=2026))
    notify.trigger_cong_bo_ket_qua.assert_not_called()

def test_role_guards():
    with pytest.raises(ForbiddenError):
        require_admin(CurrentUser(role="thi_sinh",cccd="001"))
    with pytest.raises(ForbiddenError):
        require_thi_sinh(CurrentUser(role="admin",ma_admin="A1"))


def test_repeat_publication_does_not_renotify(profile, record):
    service, _, _, notify = publication(profile, record)
    request = CongBoKetQuaRequest(nam_tuyen_sinh=2026)
    service.cong_bo_ket_qua(request)
    original = record.ket_qua
    result = service.cong_bo_ket_qua(request)
    assert record.ket_qua == original
    assert not result.notification_triggered
    notify.trigger_cong_bo_ket_qua.assert_called_once_with(2026)

@pytest.mark.parametrize("offset,expected", [(-1, False), (0, True), (1, False)])
def test_publication_exact_time_boundary(profile, offset, expected):
    service, _, scores, _ = profile
    boundary = datetime(2026, 7, 1, 12)
    scores.list_lo_trinh.return_value = [SimpleNamespace(loai_moc="cong_bo", ten_moc="",
        thoi_gian_bat_dau=boundary, thoi_gian_ket_thuc=boundary)]
    assert service._trong_moc_cong_bo(2026, boundary+timedelta(seconds=offset)) == expected
