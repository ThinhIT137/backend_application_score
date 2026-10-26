"""UTC GHA 2026 score arithmetic only. Annual matrix: subject x grades 10/11/12."""
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from src.schemas.score_preview import ScorePreviewRequest
from src.services.conversion_service import convert_to_thpt
from src.core.exceptions import DuLieuKhongHopLe


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd')) if c.isalnum())


def calculate_preview(db, request: ScorePreviewRequest):
    combination = None
    if request.method != 'DGNL':
        combination = db.execute(text('SELECT t.ma_mon_1, t.ma_mon_2, t.ma_mon_3, m1.ten_mon AS name1, m2.ten_mon AS name2, m3.ten_mon AS name3 FROM to_hop_xet_tuyen t LEFT JOIN danh_muc_mon_hoc m1 ON m1.ma_mon=t.ma_mon_1 LEFT JOIN danh_muc_mon_hoc m2 ON m2.ma_mon=t.ma_mon_2 LEFT JOIN danh_muc_mon_hoc m3 ON m3.ma_mon=t.ma_mon_3 WHERE t.ma_to_hop=:code'), {'code': request.combination}).mappings().first()
        if not combination:
            raise DuLieuKhongHopLe('Tổ hợp không tồn tại trong danh mục')
        codes = [combination[f'ma_mon_{i}'] for i in range(1, 4)]
        if not all(codes) or len(set(codes)) != 3:
            raise DuLieuKhongHopLe('Tổ hợp thiếu hoặc trùng môn học')
    scores = [sum(row) / 3 for row in request.annual_scores] if request.method == 'HOC_BA' else request.scores
    subjects = [] if combination is None else [dict(code=combination[f'ma_mon_{i}'], name=combination[f'name{i}'] or combination[f'ma_mon_{i}'], score=scores[i-1]) for i in range(1, 4)]
    math_index = next((i for i, item in enumerate(subjects) if normalize(item['name']) in {'toan', 'toanhoc', 'math', 'mathematics'} or normalize(item['code']) in {'toan', 'toanhoc', 'math', 'mathematics'}), None)
    if subjects and math_index is None:
        raise DuLieuKhongHopLe('Tổ hợp chưa xác định được môn Toán để tính hệ số')
    ielts = request.certificate_score
    certificate_bonus = 0 if ielts is None or ielts < 5 else 1.5 if ielts >= 7 else {5: .5, 5.5: .75, 6: 1, 6.5: 1.25}[ielts]
    cap = {'KV3': 0, 'KV2': .25, 'KV2-NT': .5, 'KV1': .75}[request.region] + {'NONE': 0, 'UT1': 2, 'UT2': 1}[request.priority]
    variants = {}
    for kind in ('standard', 'english', 'applied_math'):
        notes = []
        status = 'met'
        if request.method == 'HOC_BA':
            if any(value < 5.5 for row in request.annual_scores for value in row):
                status = 'not_met'
                notes.append('PT2: mỗi môn trong từng năm lớp 10, 11, 12 phải đạt từ 5,5.')
            if kind == 'english':
                if (request.thpt_english_score is None or request.thpt_english_score < 6) and (ielts is None or ielts < 4.5):
                    if request.thpt_english_score is None:
                        if status != 'not_met':
                            status = 'pending'
                        notes.append('Chưa có điểm thi tiếng Anh THPT để kiểm tra điều kiện PT2 Ngôn ngữ Anh (từ 6 hoặc IELTS từ 4,5).')
                    else:
                        status = 'not_met'
                        notes.append('PT2 Ngôn ngữ Anh: điểm thi tiếng Anh THPT từ 6 hoặc IELTS từ 4,5.')
            elif request.thpt_math_score is None:
                if status != 'not_met':
                    status = 'pending'
                notes.append('Chưa có điểm thi Toán THPT; chưa kiểm tra được điều kiện PT2 (Toán từ 5; Toán ứng dụng từ 6).')
            elif request.thpt_math_score < (6 if kind == 'applied_math' else 5):
                status = 'not_met'
                notes.append('PT2: điểm thi Toán THPT từ 6 cho Toán ứng dụng; từ 5 cho các ngành khác.')
        raw = request.exam_score if request.method == 'DGNL' else sum(scores) if kind == 'english' else (sum(scores) + scores[math_index]) * .75
        converted = raw
        if request.method in {'HOC_BA', 'DGNL'}:
            try:
                converted = convert_to_thpt('hoc_ba' if request.method == 'HOC_BA' else request.exam.lower(), raw, request.year)
            except DuLieuKhongHopLe:
                converted = None
                notes.append('Điểm ngoài bảng quy đổi năm 2026; không nội suy ngoài khoảng đã công bố.')
        # Giữ phép cộng/ưu tiên ở dạng thập phân; làm tròn 5 lên ở bước cuối,
        # tránh round(float) làm 27.825 thành 27.82.
        base_decimal = None if converted is None else Decimal(str(converted))
        cap_decimal = Decimal(str(cap))
        priority_decimal = Decimal(0) if base_decimal is None else cap_decimal if base_decimal < Decimal('22.5') else max(Decimal(0), (Decimal(30) - base_decimal) / Decimal('7.5')) * cap_decimal
        final = None if base_decimal is None else float(min(Decimal(30), base_decimal + priority_decimal + Decimal(str(certificate_bonus))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        priority_bonus = float(priority_decimal)
        variants[kind] = dict(rawScore=round(raw, 4), convertedScore=None if converted is None else round(converted, 4), finalScore=final, priorityBonus=round(priority_bonus, 4), passPreliminary=status != 'not_met', eligibilityStatus=status, preliminaryNotes=notes)
    standard = variants['standard']
    return dict(calculation=dict(**standard, contractVersion='utc-gha-2026-v2', variants=variants,
        method='THPT' if request.method == 'CHUNG_CHI' else request.method,
        actualMethod=request.exam if request.method == 'DGNL' else 'PT2' if request.method == 'HOC_BA' else 'PT1',
        certificateBonus=certificate_bonus, maxPriority=cap,
        subDetails=[dict(label='Điểm tương đương THPT / 30', score='Chưa có khoảng quy đổi' if standard['convertedScore'] is None else str(round(standard['convertedScore'], 2))), dict(label='Điểm cộng IELTS (không thay môn)', score=str(certificate_bonus))],
        combinationCode=request.combination), programs=[])
