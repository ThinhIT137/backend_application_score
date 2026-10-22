import math
from datetime import datetime
from src.core.constants import DIEM_HOP_LE, DIEM_UU_TIEN_TOI_DA
from src.core.exceptions import DuLieuKhongHopLe
from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.repositories.diem_chuan_repository_interface import DiemChuanRepositoryInterface
from src.schemas.diem_chuan_schema import (
    SuaDiemChuanRequest,
    TaoDiemChuanRequest,
    ThemDiemTrungTuyenRequest,
)
from src.schemas.quy_doi_schema import (
    PhuongThucQuyDoiItem,
    QuyDoiRequest,
    QuyDoiResponse,
)
from src.services.interface.diem_chuan_service_interface import DiemChuanServiceInterface


class DiemChuanService(DiemChuanServiceInterface):
    def __init__(self, diem_chuan_repo: DiemChuanRepositoryInterface) -> None:
        self.repo = diem_chuan_repo

    def list_diem_chuan(
        self, ma_chuong_trinh: str | None = None, nam: int | None = None
    ) -> list[LichSuDiemChuan]:
        return self.repo.list_all(ma_chuong_trinh=ma_chuong_trinh, nam=nam)

    def get_diem_chuan(self, ma_ls_dc: str) -> LichSuDiemChuan:
        record = self.repo.get_by_id(ma_ls_dc)
        if record is None:
            raise DuLieuKhongHopLe(f"Không tìm thấy điểm chuẩn {ma_ls_dc}")
        return record

    def tao_diem_chuan(self, payload: TaoDiemChuanRequest, ma_admin: str) -> LichSuDiemChuan:
        existed = self.repo.get_by_chuong_trinh_nam(payload.ma_chuong_trinh, payload.nam)
        if existed is not None:
            raise DuLieuKhongHopLe(
                f"Điểm chuẩn cho chương trình {payload.ma_chuong_trinh} năm {payload.nam} đã tồn tại"
            )

        record = LichSuDiemChuan(
            ma_ls_dc=payload.ma_ls_dc,
            ma_chuong_trinh=payload.ma_chuong_trinh,
            nam=payload.nam,
            chi_tieu=payload.chi_tieu,
            trung_tuyen=payload.trung_tuyen,
            ma_admin_cap_nhat=ma_admin,
            create_at=datetime.now(),
        )
        return self.repo.create(record)

    def sua_diem_chuan(self, ma_ls_dc: str, payload: SuaDiemChuanRequest) -> LichSuDiemChuan:
        record = self.get_diem_chuan(ma_ls_dc)
        if payload.chi_tieu is not None:
            record.chi_tieu = payload.chi_tieu
        if payload.trung_tuyen is not None:
            record.trung_tuyen = payload.trung_tuyen
        return self.repo.update(record)

    def xoa_diem_chuan(self, ma_ls_dc: str) -> None:
        self.get_diem_chuan(ma_ls_dc)
        self.repo.delete(ma_ls_dc)

    def them_diem_trung_tuyen(
        self, ma_ls_dc: str, payload: ThemDiemTrungTuyenRequest
    ) -> DiemTrungTuyen:
        self.get_diem_chuan(ma_ls_dc)
        existing = self.repo.list_diem_trung_tuyen_by_ls(ma_ls_dc)
        for d in existing:
            if d.ma_phuong_thuc == payload.ma_phuong_thuc:
                raise DuLieuKhongHopLe(
                    f"Phương thức {payload.ma_phuong_thuc} đã có điểm trúng tuyển cho đợt này"
                )

        dtt = DiemTrungTuyen(
            ma_diem_tt=payload.ma_diem_tt,
            ma_ls_dc=ma_ls_dc,
            ma_phuong_thuc=payload.ma_phuong_thuc,
            diem=payload.diem,
            create_at=datetime.now(),
            nguyen_vong_toi_da=payload.nguyen_vong_toi_da,
            dieu_kien_mon=payload.dieu_kien_mon,
            diem_uu_tien_toi_thieu=payload.diem_uu_tien_toi_thieu,
        )
        return self.repo.add_diem_trung_tuyen(dtt)

    def _validate_finite(self, value: float, label: str) -> float:
        if not math.isfinite(value):
            raise DuLieuKhongHopLe(f"{label} phải là số hữu hạn")
        return value

    def _normalize_loai_chung_chi(self, loai: str) -> str:
        return loai.strip().upper().replace("-", "_")

    def _co_quy_tac_ho_tro(self, loai: str) -> bool:
        normalized = self._normalize_loai_chung_chi(loai)
        return normalized in DIEM_HOP_LE

    def _tinh_diem_uu_tien(self, doi_tuong: str | None) -> float:
        if not doi_tuong:
            return 0.0
        dt = doi_tuong.strip().upper()
        mapping = {
            "KV1": 0.75,
            "KV2NT": 0.5,
            "KV2": 0.25,
            "KV3": 0.0,
            "DT01": 2.0,
            "DT02": 2.0,
            "DT03": 2.0,
            "DT04": 2.0,
            "DT05": 1.0,
            "DT06": 1.0,
            "DT07": 1.0,
            "UT1": 2.0,
            "UT2": 1.0,
        }
        score = mapping.get(dt, 0.0)
        return min(score, DIEM_UU_TIEN_TOI_DA)

    def tinh_diem_quy_doi(self, payload: QuyDoiRequest) -> QuyDoiResponse:
        canh_bao: list[str] = []

        if not payload.diem_thpt and not payload.chung_chi:
            raise DuLieuKhongHopLe("Cần ít nhất một điểm THPT hoặc một điểm chứng chỉ để tính quy đổi")

        available_methods = 0

        # 1. Validate diem THPT
        for item in payload.diem_thpt:
            self._validate_finite(item.diem, f"Điểm THPT môn {item.ma_mon}")
            cfg = DIEM_HOP_LE.get("THPT")
            if cfg:
                min_v, max_v, step = cfg
                if not (min_v <= item.diem <= max_v):
                    canh_bao.append(
                        f"Điểm THPT môn {item.ma_mon} ({item.diem}) nằm ngoài dải hợp lệ [{min_v}, {max_v}]"
                    )
                elif step and (round(item.diem / step, 4) % 1 != 0):
                    canh_bao.append(
                        f"Điểm THPT môn {item.ma_mon} ({item.diem}) không đúng bước nhảy {step}"
                    )

        # 2. Validate chung chi
        for cc in payload.chung_chi:
            self._validate_finite(cc.diem, f"Điểm chứng chỉ {cc.loai}")
            key = self._normalize_loai_chung_chi(cc.loai)
            cfg = DIEM_HOP_LE.get(key)
            if not cfg:
                canh_bao.append(
                    f"Loại chứng chỉ {cc.loai} không được hỗ trợ cho quy đổi trong cấu hình hiện tại."
                )
                continue
            available_methods += 1
            min_v, max_v, step = cfg
            if not (min_v <= cc.diem <= max_v):
                canh_bao.append(
                    f"Điểm chứng chỉ {cc.loai} ({cc.diem}) nằm ngoài dải hợp lệ [{min_v}, {max_v}]"
                )

        # 3. Diem uu tien
        diem_ut = self._tinh_diem_uu_tien(payload.doi_tuong_uu_tien)

        if not payload.diem_thpt and available_methods == 0:
            raise DuLieuKhongHopLe(
                "Không có phương thức quy đổi hợp lệ nào cho dữ liệu đã nhập. "
                "Vui lòng kiểm tra loại chứng chỉ hoặc điểm THPT."
            )

        # 4. Tinh diem theo tung phuong thuc
        chi_tiet: list[PhuongThucQuyDoiItem] = []

        # Phg thuc 1: Xet diem THPT (thang 30)
        if payload.diem_thpt:
            diem_mon = [m.diem for m in payload.diem_thpt]
            if len(diem_mon) >= 3:
                diem_raw = sum(sorted(diem_mon, reverse=True)[:3])
            else:
                diem_raw = sum(diem_mon) * (3.0 / len(diem_mon))
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT100",
                    ten_phuong_thuc="Xét điểm thi THPT",
                    diem_quy_doi=diem_qd,
                )
            )

        # Phg thuc 2: Xet DGNL HSA
        hsa_items = [c for c in payload.chung_chi if c.loai.upper() == "HSA"]
        if hsa_items:
            best_hsa = max(hsa_items, key=lambda x: x.diem)
            # Thang 150 quy ve 30
            diem_raw = (best_hsa.diem / 150.0) * 30.0
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT402",
                    ten_phuong_thuc="Xét tuyển kết quả ĐGNL (HSA)",
                    diem_quy_doi=diem_qd,
                )
            )

        # Phg thuc 3: Xet Chung chi quoc te (IELTS, SAT, ACT...)
        cc_map = {self._normalize_loai_chung_chi(c.loai): c.diem for c in payload.chung_chi}
        sat = cc_map.get("SAT")
        act = cc_map.get("ACT")
        ielts = cc_map.get("IELTS")
        toefl = cc_map.get("TOEFL_IBT")

        if sat is not None:
            diem_raw = (sat / 1600.0) * 30.0
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT409_SAT",
                    ten_phuong_thuc="Xét tuyển chứng chỉ SAT",
                    diem_quy_doi=diem_qd,
                )
            )
        if act is not None:
            diem_raw = (act / 36.0) * 30.0
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT409_ACT",
                    ten_phuong_thuc="Xét tuyển chứng chỉ ACT",
                    diem_quy_doi=diem_qd,
                )
            )
        if ielts is not None:
            diem_raw = (ielts / 9.0) * 30.0
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT409_IELTS",
                    ten_phuong_thuc="Xét tuyển chứng chỉ IELTS",
                    diem_quy_doi=diem_qd,
                )
            )
        elif toefl is not None:
            diem_raw = (toefl / 120.0) * 30.0
            diem_qd = min(30.0, round(diem_raw + diem_ut, 2))
            chi_tiet.append(
                PhuongThucQuyDoiItem(
                    ma_phuong_thuc="PT409_TOEFL",
                    ten_phuong_thuc="Xét tuyển chứng chỉ TOEFL",
                    diem_quy_doi=diem_qd,
                )
            )

        # 5. So sanh voi diem trung tuyen lich su neu co chuong trinh & nam
        if payload.ma_chuong_trinh:
            nam_query = payload.nam_so_sanh
            ls_records = self.repo.list_all(
                ma_chuong_trinh=payload.ma_chuong_trinh, nam=nam_query
            )
            if ls_records:
                target_ls = sorted(ls_records, key=lambda x: x.nam, reverse=True)[0]
                dtt_list = self.repo.list_diem_trung_tuyen_by_ls(target_ls.ma_ls_dc)
                dtt_dict = {d.ma_phuong_thuc: d.diem for d in dtt_list}

                for item in chi_tiet:
                    # Tim diem chuan tuong ung hoac tim diem chuan chung
                    dc = dtt_dict.get(item.ma_phuong_thuc)
                    if dc is None and dtt_list:
                        # Lay trung binh hoac diem phuong thuc dau tien
                        dc = dtt_list[0].diem
                    if dc is not None:
                        item.diem_chuan = dc
                        item.chenh_lech = round(item.diem_quy_doi - dc, 2)
                        item.dat_chuan = item.diem_quy_doi >= dc
                        # Tinh phan vi uoc luong
                        if dc > 0:
                            ratio = item.diem_quy_doi / dc
                            item.phan_vi = round(min(100.0, max(0.0, ratio * 50.0)), 1)

        # 6. Phuong thuc tot nhat
        phuong_thuc_tot_nhat: str | None = None
        if chi_tiet:
            # Uu tien phuong thuc co chenh_lech cao nhat, neu khong co thi diem_quy_doi cao nhat
            sorted_pt = sorted(
                chi_tiet,
                key=lambda x: (x.chenh_lech if x.chenh_lech is not None else -999, x.diem_quy_doi),
                reverse=True,
            )
            phuong_thuc_tot_nhat = sorted_pt[0].ma_phuong_thuc

        if not chi_tiet:
            raise DuLieuKhongHopLe(
                "Không có phương thức tính quy đổi hợp lệ nào có thể tạo ra kết quả từ dữ liệu đã nhập."
            )

        return QuyDoiResponse(
            diem_uu_tien=diem_ut,
            phuong_thuc_tot_nhat=phuong_thuc_tot_nhat,
            chi_tiet=chi_tiet,
            canh_bao=canh_bao,
        )
