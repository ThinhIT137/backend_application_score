# Sprint 2: Xử lý hồ sơ và đồng bộ điểm mô phỏng

Kết quả: **53 test pass**, gồm 35 test service/validation và 18 test tích hợp.

```powershell
& ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests/sprint2 tests/integration/test_sprint2.py -q
```

Nguồn THPT và ĐGNL là **mô phỏng**, không kết nối Bộ GD&ĐT hoặc ĐHQG. Dữ liệu tổng hợp được đóng gói tại `src/data/mock_scores.json`; cấu hình provider chỉ chấp nhận `mock`. THPT có dữ liệu năm 2026 cho CCCD `000000000001`, `000000000002` với môn `TOAN`, `VAN`. ĐGNL tương ứng 100 và 85 điểm. Các mã tham chiếu này phải tồn tại trong DB để đồng bộ thành công. Không tự tạo thí sinh/môn học trong DB thật.

Kiểm thử:
- Duyệt/từ chối và lưu trạng thái, admin xử lý, lý do; chặn xử lý lại và chặn sai quyền.
- Luồng API nộp → tra cứu → duyệt → công bố → tra cứu kết quả; chặn công bố khi còn hồ sơ chờ hoặc sai mốc thời gian. Mốc phải có tên công bố; năm lấy từ thời gian bắt đầu do Prisma không có cột năm tuyển sinh trên bảng mốc.
- Công bố lặp giữ kết quả và không gửi lại thông báo nếu không có kết quả mới; mốc đúng đầu/cuối được phép. Publisher hiện là no-op nên API báo notification_triggered=false; chưa gửi email/thông báo thật.
- Đồng bộ THPT thành công, đồng bộ lặp không nhân bản bảng điểm; timeout, thiếu tham chiếu và lỗi DB từng thí sinh. Savepoint giữ dữ liệu thí sinh khác khi một bản ghi lỗi.
- Nộp ĐGNL, điểm/file/ngày không hợp lệ, nộp trùng; xác minh đúng/sai/thiếu/timeout. Nguồn mô phỏng kiểm tra CCCD + năm + điểm, không chỉ kiểm tra chuỗi không rỗng.
- API yêu cầu bổ sung ĐGNL, danh sách chờ và chặn xác minh lại bản ghi đã xử lý.

Giới hạn: SQLite không thay thế PostgreSQL; chưa kiểm chứng DB triển khai, concurrency và Docker. Công bố xác nhận đủ điều kiện xét tuyển sau duyệt, không thực hiện xếp hạng/chọn trúng tuyển theo chỉ tiêu. Chưa có cột công bố riêng; dữ liệu kết quả hiện theo schema/logic đang có. Một cảnh báo deprecation TestClient không làm test fail.
