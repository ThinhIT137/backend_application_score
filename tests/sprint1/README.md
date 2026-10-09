# Sprint 1: Xử lý hồ sơ và điểm

Kết quả: **125 test pass**, gồm 91 test service/quy đổi và 34 test tích hợp API/JWT/SQLite.

Chạy từ backend_application_score:

```powershell
& ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests/sprint1 tests/integration/test_sprint1.py -q
```

Phạm vi kiểm thử:
- CRUD lịch sử điểm chuẩn theo chương trình/năm và điểm từng phương thức: tạo, đọc, lọc, sửa, xóa; dữ liệu trùng, tham chiếu thiếu, validation và quyền admin.
- Quy đổi học bạ/HSA/TSA sang THPT: các đầu mút và trung điểm của mọi khoảng, điểm ngoài bảng, NaN/vô cực, phương thức/năm không hỗ trợ, xác thực API và đường dẫn độc lập thư mục chạy.
- Nộp hồ sơ học bạ/chứng chỉ/giải thưởng: từng loại và kết hợp; dữ liệu sai, thiếu minh chứng, trùng nguyện vọng, JWT sai/hết hạn, giả mạo CCCD, quyền truy cập và lưu DB.
- Tra cứu chi tiết/trạng thái hồ sơ: thí sinh chỉ xem hồ sơ của mình, admin xem chi tiết, hồ sơ thiếu và lỗi repository.
- Transaction: lỗi khi lưu điểm chi tiết phải rollback cả hồ sơ và học bạ.

Bảng quy đổi nằm trong `src/data/conversion_scales_2026.json`, được copy từ backend_ai_ml và đọc bằng đường dẫn từ `__file__`. Không cần microservice AI để tính điểm. Bảng chỉ áp dụng năm 2026, nội suy tuyến tính theo từng khoảng, không ngoại suy.

Giới hạn: chưa có công thức cộng/quy đổi điểm chứng chỉ và giải thưởng; API lưu thông tin để duyệt, không tự tính điểm cộng. File chứng chỉ là đường dẫn minh chứng, chưa có dịch vụ upload/lưu trữ file. Minh chứng thuộc thí sinh và được dùng chung khi đọc các hồ sơ của thí sinh đó, phù hợp schema hiện có.

DB tích hợp là SQLite in-memory với FK bật, repository và commit/rollback thật. Chưa xác nhận PostgreSQL triển khai, truy cập đồng thời hoặc dữ liệu thực tế. Schema tối thiểu của test không thay thế migration Prisma. Docker chưa được xác nhận vì daemon không phản hồi. Các test pass không chứng minh những giới hạn trên đã được xử lý.
