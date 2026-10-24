"""Calculate only the submitted score. Catalog comparison belongs to Next.js."""
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
    combination = None if request.method in {'DGNL', 'CHUNG_CHI'} else db.execute(text('SELECT t.ma_mon_1, t.ma_mon_2, t.ma_mon_3, m1.ten_mon AS name1, m2.ten_mon AS name2, m3.ten_mon AS name3 FROM to_hop_xet_tuyen t LEFT JOIN danh_muc_mon_hoc m1 ON m1.ma_mon=t.ma_mon_1 LEFT JOIN danh_muc_mon_hoc m2 ON m2.ma_mon=t.ma_mon_2 LEFT JOIN danh_muc_mon_hoc m3 ON m3.ma_mon=t.ma_mon_3 WHERE t.ma_to_hop=:code'), {'code': request.combination}).mappings().first()
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
    return dict(calculation=dict(method=request.method, rawScore=original, convertedScore=converted, finalScore=final, priorityBonus=round(bonus, 4), maxPriority=cap, subDetails=[dict(label='Điểm tương đương THPT / 30', score=str(round(converted, 2)) if converted is not None else 'Chưa có cấu hình')], passPreliminary=eligible, preliminaryNotes=notes, combinationCode=request.combination), programs=[])
