# backend_application_score

Microservice FastAPI xử lý hồ sơ và điểm. Sprint 2 dùng nguồn điểm **mô phỏng**, chưa kết nối Bộ GD&ĐT/ĐHQG.

## Môi trường Python

Chạy các lệnh tại thư mục này:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-test.txt
& ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q
& ./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100 --reload
```

Không bắt buộc activate. `.venv/` đã được gitignore. Kết quả kiểm thử hiện tại: **203 pass, 0 fail**, một cảnh báo deprecation TestClient. Tests dùng JWT khóa công khai dành riêng cho test và SQLite in-memory; không truy cập `.env`/DB thật.

Ứng dụng cần DATABASE_URL, JWT_SECRET và tùy chọn JWT_AUDIENCE trong `.env` khi gọi các API cần xác thực/DB. JWT phải chứa role admin/thi_sinh, ma_admin/cccd hoặc sub tương ứng. Xem cấu hình tại `.env.example`. Không dùng khóa test cho triển khai. `/health` kiểm tra ứng dụng chạy, không xác nhận kết nối DB.

Service map các bảng Prisma đã có, không tạo migration hay bảng production tự động. Mapping mới gồm lịch sử điểm chuẩn, điểm trúng tuyển và thông tin giải thưởng; mốc tuyển sinh dùng ma_su_kien/ten_su_kien theo schema Prisma.

## API chính

| Method | Đường dẫn | Quyền |
|---|---|---|
| GET/POST | /diem-chuan | admin |
| GET/PUT/DELETE | /diem-chuan/{key} | admin |
| POST | /diem/quy-doi | JWT hợp lệ |
| POST | /ho-so | thí sinh |
| GET | /ho-so/cua-toi/{ma_ho_so} | chủ hồ sơ |
| GET | /ho-so và /ho-so/{ma_ho_so} | admin |
| PATCH | /ho-so/{ma_ho_so}/duyet hoặc /tu-choi | admin |
| POST | /ho-so/cong-bo-ket-qua | admin |
| POST | /diem/dong-bo-thpt | admin |
| POST | /diem/dgnl | thí sinh |
| GET | /diem/dgnl/cho-xac-minh | admin |
| PATCH | /diem/dgnl/{ma_chung_chi}/xac-nhan hoặc /yeu-cau-bo-sung | admin |
| GET | /thong-ke/tong-quan | admin |
| GET | /thong-ke/nganh-hoc | admin |
| GET | /thong-ke/xet-tuyen | admin |
| GET | /bao-cao/trung-tuyen | admin |

Swagger khi chạy local: http://127.0.0.1:8100/docs. POST /ho-so nhận chương trình, phương thức, nguyện vọng, năm và ít nhất một trong bang_diem/chung_chi/giai_thuong. CCCD lấy từ JWT, không nhận từ body. Hồ sơ và minh chứng được lưu cùng transaction. Chứng chỉ nhận đường dẫn file; chưa triển khai upload. Giải thưởng lưu hạng/cấp/môn theo enum Prisma.

Quy đổi nhận phuong_thuc hoc_ba/hsa/tsa, diem và nam_tuyen_sinh=2026. Bảng `src/data/conversion_scales_2026.json` là bản độc lập trong repo này. Không có quy tắc cộng điểm chứng chỉ/giải thưởng nên chưa tính các điểm cộng đó. Điểm ngoài bảng bị từ chối.

Nguồn mô phỏng nằm tại `src/data/mock_scores.json`, chỉ hỗ trợ THPT_PROVIDER=mock và DGNL_PROVIDER=mock. Phải có các CCCD/mã môn trong DB trước khi đồng bộ; chi tiết trong tests/sprint2/README.md. Công bố hiện xác nhận điều kiện sau duyệt, chưa xếp hạng trúng tuyển theo chỉ tiêu; thông báo ngoài hệ thống là no-op.

## Docker

```powershell
docker build --target test -t application-score-sprint-tests .
docker run --rm --network none application-score-sprint-tests
docker build --target runtime -t application-score .
docker run --rm --env-file .env -p 8000:8000 application-score
```

Docker copy toàn bộ src/, gồm bảng quy đổi và nguồn mô phỏng. Target test chứa thư viện test và SQLite, không cần frontend/AI/DB ngoài; runtime không chứa tests hoặc .venv/.env. Khi chạy runtime, DATABASE_URL phải trỏ đến PostgreSQL truy cập được từ container (localhost trong container không phải máy host).

**Chưa xác nhận build/run Docker:** Docker Desktop daemon không phản hồi tại thời điểm kiểm tra; docker version timeout, lệnh build bị treo và đã hủy. Các lệnh trên cần chạy lại khi daemon hoạt động. Chưa kiểm thử trên PostgreSQL hoặc request đồng thời.
