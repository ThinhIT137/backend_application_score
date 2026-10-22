from collections import Counter, defaultdict
from datetime import date
from math import ceil

from src.core.exceptions import DuLieuKhongHopLe
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiHoSo as TrangThaiDuyet
from src.repositories.thong_ke_repository import ThongKeRepository
from src.schemas.thong_ke_schema import (
    BaoCaoTongHop,
    BaoCaoTrungTuyenItem,
    BaoCaoTrungTuyenResponse,
    PhanTrang,
    ThongKeNganhItem,
    ThongKePhuongThucItem,
    ThongKeToHopItem,
    ThongKeTongQuanResponse,
    ThongKeXetTuyenResponse,
    XuHuongNgayItem,
)


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator * 100 / denominator, 2) if denominator else 0.0


from src.services.result_state import published as _is_published, result_label as _result_label

def _is_admitted(record):
    return _result_label(record) == "trung_tuyen"


class ThongKeService:
    def __init__(self, repo: ThongKeRepository) -> None:
        self.repo = repo

    @staticmethod
    def _validate_dates(tu_ngay: date | None, den_ngay: date | None) -> None:
        if tu_ngay and den_ngay and tu_ngay > den_ngay:
            raise DuLieuKhongHopLe("Từ ngày không được lớn hơn đến ngày")

    def tong_quan(
        self,
        *,
        nam_tuyen_sinh: int,
        tu_ngay: date | None = None,
        den_ngay: date | None = None,
    ) -> ThongKeTongQuanResponse:
        self._validate_dates(tu_ngay, den_ngay)
        records = self.repo.list_ho_so(
            nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
        )
        programs = self.repo.list_chuong_trinh()
        quotas = self.repo.list_chi_tieu(nam_tuyen_sinh)
        status = Counter(record.trang_thai for record in records)
        trend = Counter(record.create_at.date() for record in records)
        admitted = sum(_is_admitted(record) for record in records)
        published = sum(_is_published(record) for record in records)
        completed = len(records) - status[TrangThaiDuyet.cho]
        industries = {
            program.ma_nganh or program.ma_chuong_trinh for program, _ in programs
        }
        return ThongKeTongQuanResponse(
            nam_tuyen_sinh=nam_tuyen_sinh,
            tong_ho_so=len(records),
            cho_xu_ly=status[TrangThaiDuyet.cho] + status[TrangThaiDuyet.dang_xu_ly],
            hop_le=sum(status[state] for state in (TrangThaiDuyet.hop_le, TrangThaiDuyet.dang_xu_ly, TrangThaiDuyet.do, TrangThaiDuyet.truot)),
            tu_choi=status[TrangThaiDuyet.tu_choi],
            da_cong_bo=published,
            trung_tuyen=admitted,
            tong_chi_tieu=sum(item.chi_tieu for item in quotas),
            tong_nganh=len(industries),
            ty_le_hoan_tat=_percent(completed, len(records)),
            ty_le_trung_tuyen=_percent(admitted, len(records)),
            xu_huong_theo_ngay=[
                XuHuongNgayItem(ngay=day, so_luong=count)
                for day, count in sorted(trend.items())
            ],
        )

    def theo_nganh(
        self,
        *,
        nam_tuyen_sinh: int,
        tu_ngay: date | None = None,
        den_ngay: date | None = None,
    ) -> list[ThongKeNganhItem]:
        self._validate_dates(tu_ngay, den_ngay)
        records = self.repo.list_ho_so(
            nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
        )
        programs = self.repo.list_chuong_trinh()
        program_info = {
            program.ma_chuong_trinh: (
                program.ma_nganh or program.ma_chuong_trinh,
                ten_nganh or program.ten_chuong_trinh or program.ma_chuong_trinh,
            )
            for program, ten_nganh in programs
        }
        quota_by_program = {
            item.ma_chuong_trinh: item.chi_tieu
            for item in self.repo.list_chi_tieu(nam_tuyen_sinh)
        }
        grouped: dict[str, dict[str, object]] = {}
        for program, ten_nganh in programs:
            ma_nganh = program.ma_nganh or program.ma_chuong_trinh
            current = grouped.setdefault(
                ma_nganh,
                {
                    "ten_nganh": ten_nganh
                    or program.ten_chuong_trinh
                    or ma_nganh,
                    "chi_tieu": 0,
                    "records": [],
                },
            )
            current["chi_tieu"] = int(current["chi_tieu"]) + quota_by_program.get(
                program.ma_chuong_trinh, 0
            )
        for record in records:
            ma_nganh, ten_nganh = program_info.get(
                record.ma_chuong_trinh,
                (record.ma_chuong_trinh, record.ma_chuong_trinh),
            )
            current = grouped.setdefault(
                ma_nganh,
                {"ten_nganh": ten_nganh, "chi_tieu": 0, "records": []},
            )
            current["records"].append(record)

        result: list[ThongKeNganhItem] = []
        for ma_nganh, data in grouped.items():
            items: list[NguyenVongSinhVien] = data["records"]
            quota = int(data["chi_tieu"])
            admitted = sum(_is_admitted(item) for item in items)
            result.append(
                ThongKeNganhItem(
                    ma_nganh=ma_nganh,
                    ten_nganh=str(data["ten_nganh"]),
                    chi_tieu=quota,
                    tong_ho_so=len(items),
                    hop_le=sum(
                        item.trang_thai in {TrangThaiDuyet.hop_le, TrangThaiDuyet.dang_xu_ly, TrangThaiDuyet.do, TrangThaiDuyet.truot} for item in items
                    ),
                    tu_choi=sum(
                        item.trang_thai == TrangThaiDuyet.tu_choi for item in items
                    ),
                    trung_tuyen=admitted,
                    ty_le_canh_tranh=(round(len(items) / quota, 2) if quota else 0),
                    ty_le_lap_day=_percent(admitted, quota),
                )
            )
        return sorted(result, key=lambda item: (-item.tong_ho_so, item.ma_nganh))

    def theo_xet_tuyen(
        self,
        *,
        nam_tuyen_sinh: int,
        tu_ngay: date | None = None,
        den_ngay: date | None = None,
    ) -> ThongKeXetTuyenResponse:
        self._validate_dates(tu_ngay, den_ngay)
        records = self.repo.list_ho_so(
            nam_tuyen_sinh=nam_tuyen_sinh, tu_ngay=tu_ngay, den_ngay=den_ngay
        )
        by_method: dict[str, list[NguyenVongSinhVien]] = defaultdict(list)
        by_combination: dict[str, list[NguyenVongSinhVien]] = defaultdict(list)
        for record in records:
            by_method[record.ma_phuong_thuc].append(record)
            if record.ma_to_hop:
                by_combination[record.ma_to_hop].append(record)
        method_names = {
            item.ma_phuong_thuc: item.ten_phuong_thuc or item.ma_phuong_thuc
            for item in self.repo.list_phuong_thuc()
        }
        method_names.update({key: key for key in by_method if key not in method_names})
        combinations = {item.ma_to_hop for item in self.repo.list_to_hop()}
        combinations.update(by_combination)

        method_result: list[ThongKePhuongThucItem] = []
        for code, name in method_names.items():
            items = by_method[code]
            admitted = sum(_is_admitted(item) for item in items)
            method_result.append(
                ThongKePhuongThucItem(
                    ma_phuong_thuc=code,
                    ten_phuong_thuc=name,
                    tong_ho_so=len(items),
                    hop_le=sum(
                        item.trang_thai in {TrangThaiDuyet.hop_le, TrangThaiDuyet.dang_xu_ly, TrangThaiDuyet.do, TrangThaiDuyet.truot} for item in items
                    ),
                    trung_tuyen=admitted,
                    ty_trong=_percent(len(items), len(records)),
                    ty_le_trung_tuyen=_percent(admitted, len(items)),
                )
            )

        combination_result: list[ThongKeToHopItem] = []
        for code in combinations:
            items = by_combination[code]
            admitted = sum(_is_admitted(item) for item in items)
            combination_result.append(
                ThongKeToHopItem(
                    ma_to_hop=code,
                    tong_ho_so=len(items),
                    hop_le=sum(
                        item.trang_thai in {TrangThaiDuyet.hop_le, TrangThaiDuyet.dang_xu_ly, TrangThaiDuyet.do, TrangThaiDuyet.truot} for item in items
                    ),
                    trung_tuyen=admitted,
                    ty_trong=_percent(len(items), len(records)),
                    ty_le_trung_tuyen=_percent(admitted, len(items)),
                )
            )
        return ThongKeXetTuyenResponse(
            nam_tuyen_sinh=nam_tuyen_sinh,
            theo_phuong_thuc=sorted(
                method_result, key=lambda item: (-item.tong_ho_so, item.ma_phuong_thuc)
            ),
            theo_to_hop=sorted(
                combination_result, key=lambda item: (-item.tong_ho_so, item.ma_to_hop)
            ),
        )

    def bao_cao_trung_tuyen(
        self,
        *,
        nam_tuyen_sinh: int,
        ma_nganh: str | None = None,
        ma_chuong_trinh: str | None = None,
        ma_phuong_thuc: str | None = None,
        ma_to_hop: str | None = None,
        ket_qua: str | None = None,
        tu_ngay: date | None = None,
        den_ngay: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BaoCaoTrungTuyenResponse:
        self._validate_dates(tu_ngay, den_ngay)
        records = self.repo.list_ho_so(
            nam_tuyen_sinh=nam_tuyen_sinh,
            tu_ngay=tu_ngay,
            den_ngay=den_ngay,
            ma_chuong_trinh=ma_chuong_trinh,
            ma_phuong_thuc=ma_phuong_thuc,
            ma_to_hop=ma_to_hop,
        )
        programs = {
            program.ma_chuong_trinh: (
                program.ma_nganh or program.ma_chuong_trinh,
                ten_nganh or program.ten_chuong_trinh or program.ma_chuong_trinh,
                program.ten_chuong_trinh or program.ma_chuong_trinh,
            )
            for program, ten_nganh in self.repo.list_chuong_trinh()
        }
        if ma_nganh:
            records = [
                record
                for record in records
                if programs.get(record.ma_chuong_trinh, (None, None, None))[0]
                == ma_nganh
            ]
        if ket_qua:
            records = [record for record in records if _result_label(record) == ket_qua]
        counts = Counter(_result_label(record) for record in records)
        candidates = {
            item.cccd: item
            for item in self.repo.list_thi_sinh({record.cccd for record in records})
        }
        methods = {
            item.ma_phuong_thuc: item.ten_phuong_thuc or item.ma_phuong_thuc
            for item in self.repo.list_phuong_thuc()
        }
        cutoffs = {
            (program, method): score
            for program, method, score in self.repo.list_diem_chuan(
                nam_tuyen_sinh
            )
        }
        total = len(records)
        start = (page - 1) * page_size
        page_records = records[start : start + page_size]
        data: list[BaoCaoTrungTuyenItem] = []
        for record in page_records:
            candidate = candidates.get(record.cccd)
            program = programs.get(
                record.ma_chuong_trinh,
                (
                    record.ma_chuong_trinh,
                    record.ma_chuong_trinh,
                    record.ma_chuong_trinh,
                ),
            )
            data.append(
                BaoCaoTrungTuyenItem(
                    ma_ho_so=record.ma_ho_so,
                    cccd=record.cccd,
                    ho_ten=(candidate.ho_ten if candidate else None)
                    or "Chưa cập nhật",
                    so_dien_thoai=(candidate.so_dien_thoai if candidate else None),
                    khu_vuc=(candidate.khu_vuc if candidate else None),
                    doi_tuong_uu_tien=(
                        candidate.doi_tuong_uu_tien if candidate else None
                    ),
                    ma_nganh=program[0],
                    ten_nganh=program[1],
                    ma_chuong_trinh=record.ma_chuong_trinh,
                    ten_chuong_trinh=program[2],
                    ma_phuong_thuc=record.ma_phuong_thuc,
                    ten_phuong_thuc=methods.get(
                        record.ma_phuong_thuc, record.ma_phuong_thuc
                    ),
                    ma_to_hop=record.ma_to_hop,
                    nguyen_vong=record.nguyen_vong,
                    tong_diem_xet_tuyen=record.tong_diem_xet_tuyen,
                    diem_chuan=cutoffs.get(
                        (record.ma_chuong_trinh, record.ma_phuong_thuc)
                    ),
                    trang_thai=_result_label(record),
                    ket_qua=record.ket_qua,
                    ngay_nop=record.create_at,
                )
            )
        return BaoCaoTrungTuyenResponse(
            nam_tuyen_sinh=nam_tuyen_sinh,
            tong_hop=BaoCaoTongHop(
                tong_ho_so=total,
                trung_tuyen=counts["trung_tuyen"],
                khong_trung_tuyen=counts["khong_trung_tuyen"],
                chua_cong_bo=counts["chua_cong_bo"],
            ),
            phan_trang=PhanTrang(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=ceil(total / page_size) if total else 0,
            ),
            du_lieu=data,
        )
