"""Read-only score calculation and exact-year, same-scale comparison."""
import math
import unicodedata
from sqlalchemy import text
from src.schemas.score_preview import ScorePreviewRequest
from src.services.conversion_service import convert_to_thpt
from src.core.exceptions import DuLieuKhongHopLe


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd')) if c.isalnum())


def calculate_preview(db, request: ScorePreviewRequest):
    if any(not math.isfinite(s) or s < 0 or s > 10 for s in request.scores):
        raise DuLieuKhongHopLe("Điểm môn phải từ 0 đến 10")
    if request.method == 'DGNL' and request.exam == 'TSA' and request.exam_score > 100:
        raise DuLieuKhongHopLe("Điểm TSA phải từ 0 đến 100")
    maximum = {'IELTS': 9, 'TOEFL': 120, 'SAT': 1600}[request.certificate]
    if request.method == 'CHUNG_CHI' and request.certificate_score > maximum:
        raise DuLieuKhongHopLe("Điểm chứng chỉ ngoài thang điểm")
    combination = db.execute(text('SELECT t.ma_mon_1, t.ma_mon_2, t.ma_mon_3, m1.ten_mon AS name1, m2.ten_mon AS name2, m3.ten_mon AS name3 FROM to_hop_xet_tuyen t LEFT JOIN danh_muc_mon_hoc m1 ON m1.ma_mon=t.ma_mon_1 LEFT JOIN danh_muc_mon_hoc m2 ON m2.ma_mon=t.ma_mon_2 LEFT JOIN danh_muc_mon_hoc m3 ON m3.ma_mon=t.ma_mon_3 WHERE t.ma_to_hop=:code'), {'code': request.combination}).mappings().first()
    subjects = [] if not combination or request.method in {'DGNL', 'CHUNG_CHI'} else [dict(code=combination[f'ma_mon_{i}'] or '', name=combination[f'name{i}'] or combination[f'ma_mon_{i}'] or '', score=request.scores[i-1]) for i in range(1, 4)]
    notes = []
    eligible = True
    if request.method == 'CHUNG_CHI' and (request.scores[0] < 5 or sum(request.scores[:2]) < 12):
        eligible = False
        notes.append('Chưa đạt điều kiện sơ bộ tham khảo: Toán từ 5 và tổng hai môn từ 12; cần đối chiếu đề án theo năm.')
    if request.method == 'DGNL' and request.exam_score < (75 if request.exam == 'HSA' else 50):
        eligible = False
        notes.append('Điểm kỳ thi dưới ngưỡng sơ bộ tham khảo; cần kiểm tra điều kiện đề án theo năm.')
    for item in subjects:
        if ({normalize(item['name']), normalize(item['code'])} & {'toan', 'toanhoc', 'math', 'mathematics'}) and item['score'] < 5:
            eligible = False
            notes.append('Điểm Toán dưới 5; chưa đạt điều kiện sơ bộ, không đánh giá cơ hội.')
    original = request.exam_score if request.method == 'DGNL' else sum(request.scores)
    converted = None
    if request.method == 'THPT':
        converted = original
    elif request.method == 'CHUNG_CHI':
        notes.append('Chưa cấu hình quy đổi chứng chỉ và môn thay thế theo năm. Không tự suy diễn điểm.')
    else:
        try:
            converted = convert_to_thpt('hoc_ba' if request.method == 'HOC_BA' else request.exam.lower(), original, request.year)
        except DuLieuKhongHopLe:
            notes.append('Chưa có khoảng quy đổi phù hợp cho phương thức, điểm và năm đã chọn.')
    cap = {'KV3': 0, 'KV2': .25, 'KV2-NT': .5, 'KV1': .75}[request.region] + {'NONE': 0, 'UT1': 2, 'UT2': 1}[request.priority]
    bonus = cap if converted is not None and converted < 22.5 else max(0, (30 - converted) / 7.5) * cap if converted is not None else 0
    final = min(30, converted + bonus) if converted is not None else None
    histories = db.execute(text('SELECT l.ma_chuong_trinh, l.nam, d.diem, d.ma_phuong_thuc, p.ten_phuong_thuc, d.dieu_kien_mon, d.nguyen_vong_toi_da, d.diem_uu_tien_toi_thieu FROM lich_su_diem_chuan l JOIN diem_trung_tuyen d ON d.ma_ls_dc=l.ma_ls_dc JOIN phuong_thuc_xet_tuyen p ON p.ma_phuong_thuc=d.ma_phuong_thuc WHERE l.nam IN (:year, :previous) ORDER BY d.ma_diem_tt'), {'year': request.year, 'previous': request.year-1}).mappings().all()
    # All compared values are equivalent THPT / 30. Never compare an HSA raw score with 30.
    benchmarks = {}
    for h in histories:
        name = normalize(h['ten_phuong_thuc'])
        if ('thpt' in name or 'totnghiep' in name or (not name and h['ma_phuong_thuc'].upper() in {'PT1', '100'})) and 0 < h['diem'] <= 30:
            benchmarks[(h['ma_chuong_trinh'], h['nam'])] = h
    combos = db.execute(text('SELECT ma_chuong_trinh, ma_to_hop FROM ctdt_to_hop WHERE nam=:year'), {'year': request.year}).mappings().all()
    configured = {}
    for c in combos:
        configured.setdefault(c['ma_chuong_trinh'], set()).add(c['ma_to_hop'])
    predictions = db.execute(text('SELECT ma_chuong_trinh, diem_du_doan FROM du_doan_diem_chuan WHERE nam_du_doan=:year ORDER BY ngay_tinh_toan DESC, ma_du_doan_dc DESC'), {'year': request.year}).mappings().all()
    predicted = {}
    for p in predictions:
        value = p['diem_du_doan']
        if value is not None and math.isfinite(value) and value > 0:
            predicted.setdefault(p['ma_chuong_trinh'], value)
    programs = db.execute(text('SELECT c.ma_chuong_trinh, c.ten_chuong_trinh, c.ma_nganh, n.ten_nganh FROM chuong_trinh_dao_tao c LEFT JOIN nganh_hoc n ON n.ma_nganh=c.ma_nganh ORDER BY c.ma_chuong_trinh')).mappings().all()
    rows = []
    for p in programs:
        code = p['ma_chuong_trinh']
        benchmark = benchmarks.get((code, request.year))
        previous = benchmarks.get((code, request.year-1))
        chance, diff, reason = 'unknown', None, 'Chưa đủ dữ liệu chính thức cùng năm và thang điểm. Dự đoán chỉ tham khảo.'
        if not eligible:
            chance, reason = 'ineligible', notes[0]
        elif final is None:
            reason = 'Chưa có cấu hình quy đổi cho dữ liệu đã nhập.'
        elif not configured.get(code):
            reason = 'Chưa có cấu hình tổ hợp cho năm đối chiếu.'
        elif request.combination not in configured[code]:
            chance, reason = 'ineligible', 'Tổ hợp không thuộc chương trình trong năm đối chiếu.'
        elif benchmark:
            unknown = request.method == 'DGNL'
            conditions = benchmark['dieu_kien_mon']
            failed = False
            if conditions is not None:
                if not isinstance(conditions, dict):
                    unknown = True
                else:
                    for key, minimum in conditions.items():
                        subject = next((s for s in subjects if normalize(key) in {normalize(s['code']), normalize(s['name'])}), None)
                        if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or not 0 <= minimum <= 10 or not subject:
                            unknown = True
                        elif subject['score'] < minimum:
                            failed = True
            if benchmark['nguyen_vong_toi_da'] is not None or benchmark['diem_uu_tien_toi_thieu'] not in (None, 0):
                unknown = True
            if failed:
                chance, reason = 'ineligible', 'Chưa đạt điều kiện môn của chương trình.'
            elif unknown:
                reason = 'Chưa đủ điểm môn hoặc thông tin tiêu chí phụ để đánh giá.'
            else:
                diff = round(final - benchmark['diem'], 2)
                chance = 'high' if diff >= .5 else 'medium' if diff >= -.5 else 'low'
                reason = 'Đối chiếu tương đương THPT; không phải kết luận đỗ/trượt.'
        rows.append(dict(p, ma_nganh=p['ma_nganh'] or '', ten_chuong_trinh=p['ten_chuong_trinh'] or code, ten_nganh=p['ten_nganh'] or p['ten_chuong_trinh'] or code, faculty='', benchmarkYear=request.year, benchmarkScore=benchmark['diem'] if benchmark else None, previousScore=previous['diem'] if previous else None, predictionScore=predicted.get(code), matchedMethodName='THPT · thang 30', chance=chance, diff=diff, reason=reason))
    return dict(calculation=dict(method=request.method, rawScore=original, convertedScore=converted, finalScore=final, priorityBonus=round(bonus, 4), maxPriority=cap, subDetails=[dict(label='Điểm tương đương THPT / 30', score=str(round(converted, 2)) if converted is not None else 'Chưa có cấu hình')], passPreliminary=eligible, preliminaryNotes=notes, combinationCode=request.combination), programs=rows)
