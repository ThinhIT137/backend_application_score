# backend_application_score

Microservice FastAPI xử lý hồ sơ và điểm. Sprint 2 dùng nguồn điểm **mô phỏng**, chưa kết nối Bộ GD&ĐT/ĐHQG.

## Môi trường Python

Chạy các lệnh tại thư mục này:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-test.txt
& ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q
& ./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Không bắt buộc activate. `.venv/` đã được gitignore. Test setup đặt cấu hình JWT giả dành riêng cho test và dùng SQLite in-memory; pytest không cần `.env` cá nhân hay DB ngoài. Kết quả hiện tại: **204 passed**, một cảnh báo deprecation của TestClient. Docker chưa chạy trong lần kiểm tra này vì Docker CLI/daemon không có trong môi trường.

Ứng dụng cần DATABASE_URL và JWT_SECRET khi khởi động. JWT phải chứa role admin/thi_sinh, ma_admin/cccd hoặc sub tương ứng. CORS chỉ cho phép các origin trong `CORS_ALLOWED_ORIGINS`, mặc định là hai origin local ở `.env.example`; production phải đặt domain frontend thực tế. CORS không thay thế kiểm tra quyền API. `/health` kiểm tra ứng dụng chạy, không xác nhận kết nối DB.

Service map các bảng Prisma đã có và không tự chạy migration. Catalog DB được kiểm tra chỉ đọc ngày 18/10/2026: chưa có `thi_sinh.email`, bảng kết quả xét tuyển riêng hoặc notification outbox. Có migration email đang chờ xác minh/áp dụng trong repo Prisma riêng; backend không map cột email trước khi DB có thật. Xem đề xuất schema và các quyết định còn thiếu tại [docs/DE_XUAT_SCHEMA_SPRINT3.md](docs/DE_XUAT_SCHEMA_SPRINT3.md).

`cong_bo_ket_qua` hiện từ chối công bố nếu chưa có nguồn kết quả đã được admin xác nhận; không suy ra kết quả từ `hop_le`/`tu_choi` và không gửi email. SMTP adapter có STARTTLS và timeout; chỉ bật luồng gửi sau khi admin có thể cập nhật email, kết quả được lưu bền vững, và có outbox/retry. `EMAIL_PROVIDER=mock` không gửi thư thật.

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
| GET | /ho-so/ket-qua/tra-cuu | công khai, cần CCCD hoặc mã hồ sơ |
| GET | /ho-so/ket-qua | admin |
| POST | /diem/dong-bo-thpt | admin |
| POST | /diem/dgnl | thí sinh |
| GET | /diem/dgnl/cho-xac-minh | admin |
| PATCH | /diem/dgnl/{ma_chung_chi}/xac-nhan hoặc /yeu-cau-bo-sung | admin |

Swagger: http://127.0.0.1:8000/docs. POST /ho-so nhận chương trình, phương thức, nguyện vọng, năm và ít nhất một trong bang_diem/chung_chi/giai_thuong. CCCD lấy từ JWT, không nhận từ body. Hồ sơ và minh chứng được lưu cùng transaction. Chứng chỉ nhận đường dẫn file; chưa triển khai upload. Giải thưởng lưu hạng/cấp/môn theo enum Prisma.

Quy đổi nhận phuong_thuc hoc_ba/hsa/tsa, diem và nam_tuyen_sinh=2026. Bảng `src/data/conversion_scales_2026.json` là bản độc lập trong repo này. Không có quy tắc cộng điểm chứng chỉ/giải thưởng nên chưa tính các điểm cộng đó. Điểm ngoài bảng bị từ chối.

Nguồn mô phỏng nằm tại `src/data/mock_scores.json`, chỉ hỗ trợ THPT_PROVIDER=mock và DGNL_PROVIDER=mock. Phải có các CCCD/mã môn trong DB trước khi đồng bộ; chi tiết trong tests/sprint2/README.md. Chưa có thuật toán xếp hạng theo chỉ tiêu/nguyện vọng; chỉ nguồn kết quả được admin xác nhận mới được công bố. Vì DB hiện chưa lưu nguồn kết quả/công bố, API tra cứu trả `trang_thai_cong_bo=chua_cong_bo` và danh sách rỗng; API công bố trả lỗi có chủ đích.

## Docker

```powershell
docker build --target test -t application-score-sprint-tests .
docker run --rm --network none application-score-sprint-tests
docker build --target runtime -t application-score .
docker run --rm --env-file .env -p 8000:8000 application-score
```

Docker copy toàn bộ src/, gồm bảng quy đổi và nguồn mô phỏng. Target test chứa thư viện test và SQLite, không cần frontend/AI/DB ngoài; runtime không chứa tests hoặc .venv/.env. Khi chạy runtime, DATABASE_URL phải trỏ đến PostgreSQL truy cập được từ container (localhost trong container không phải máy host).

Chưa xác nhận build/run Docker, Prisma migration, SMTP thật, PostgreSQL transaction cạnh tranh hoặc giới hạn tần suất endpoint public. Các phần này cần môi trường nghiệm thu phù hợp.
