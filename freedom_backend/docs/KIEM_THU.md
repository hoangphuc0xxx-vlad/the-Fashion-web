# Kết quả kiểm thử

Ngày 17/10/2026, trên Linux, Python 3.14, PostgreSQL 18.6 cục bộ tạm. Không dùng SQLite hoặc mock DB cho các bài integration. `database/schema.sql` được import nguyên bản vào DB rỗng trước chạy test. Phiên bản thư viện thực tế nằm trong requirements-lock.txt.

## Phạm vi

- 3 bài không cần DB: health/OpenAPI và kiểu request Swagger; mật khẩu/email và chặn trường role trong đăng ký; tính voucher/hạn lượt.
- 8 bài integration: đăng nhập, khóa user, RBAC, giữ Admin cuối; địa chỉ mặc định/ownership/hỗ trợ; checkout/hủy/hoàn tồn; hai khách đồng thời mua cùng SKU; logout/đổi mật khẩu/điều kiện đánh giá; reset token qua SMTP giả lập dùng một lần; CRUD catalog/ẩn thương hiệu/duyệt ảnh review/thanh toán/đổi trả; rollback voucher sai và quyền staff không được tự phục hồi sau bootstrap.
- Email SMTP được giả lập hộp thư trong test để kiểm tra nội dung link/reset token; chưa gửi tới nhà cung cấp SMTP thật.
- Bài mua đồng thời: hai user mỗi người muốn 4 trong tồn 5, kết quả 201/409, tồn cuối 1 và đúng một order. Đây là kiểm tra một tình huống tranh chấp, không phải load test.
- Bài hoàn tiền kiểm tra đối soát nội bộ sau COD đã thu, không xác nhận giao dịch chuyển tiền ngân hàng.

## Kết quả bản bàn giao

Chạy đầy đủ PostgreSQL: **11 passed**. Chạy không cấu hình DB: **3 passed, 8 skipped**. Có một cảnh báo deprecation từ Starlette TestClient/httpx của bộ thư viện hiện tại; không ảnh hưởng kết quả nhưng nên theo dõi khi nâng phiên bản.

OpenAPI tạo được **73 đường dẫn, 102 thao tác HTTP**; có /docs và /openapi.json khi chạy ứng dụng. Nhiều thao tác được dùng lại cho các chức năng/nhân sự khác nhau; số endpoint không chứng minh hoàn thiện tất cả nghiệp vụ.

## Giới hạn xác minh

Chưa chạy PostgreSQL 12/13/14/15/16/17 hoặc Python 3.12; chưa test triển khai Ubuntu qua systemd/HTTPS, tải lớn, SMTP thật, cổng thanh toán, bên vận chuyển hoặc frontend. Không có dữ liệu production và không thực hiện sửa DB của người dùng. Xem PHAN_TICH.md để biết chức năng còn thiếu và chính sách đang chọn.
