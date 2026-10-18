# Freedom — Website thời trang nam

Mã nguồn đang phát triển nằm trong **`freedom_frontend/`** và **`freedom_backend/`**.

- Frontend: trang cửa hàng, danh mục Áo / Quần / Suit và danh mục con, banner, thông tin Freedom, quản trị sản phẩm và tải nhiều ảnh. Bộ ảnh tự trượt từ phải sang trái trên thẻ sản phẩm; tên và giá giữ nguyên bên dưới.
- Backend: FastAPI, PostgreSQL, đăng nhập và phân quyền theo DB, CRUD sản phẩm, lưu ảnh, giỏ hàng, đơn hàng và các API quản lý.
- Sản phẩm Đang bán xuất hiện trong danh mục hoạt động ngay cả khi chưa có biến thể. Khách chỉ có thể thêm vào giỏ khi có biến thể hoạt động còn hàng.

Các file HTML và tài nguyên ở thư mục gốc từ phiên bản trước vẫn được giữ để tham khảo. Chạy ứng dụng hiện tại theo hướng dẫn bên dưới.

## Chạy backend

Cần Python 3.12+ và PostgreSQL đã có schema của dự án.

```sh
cd freedom_backend
python -m venv .venv
```

Kích hoạt môi trường ảo:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

```sh
# Linux / macOS
source .venv/bin/activate
cp .env.example .env
```

Điền `DATABASE_URL` và `JWT_SECRET` riêng trong `.env`. Không ghi đè `.env` nếu đã cấu hình. Với database mới, đọc hướng dẫn import schema và tạo admin tại [freedom_backend/README.md](freedom_backend/README.md); không import lại vào database đang có dữ liệu bán hàng.

```sh
pip install -r requirements.txt
python -m app.migrate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger: http://127.0.0.1:8000/docs

## Chạy frontend

Cần Node.js 18+. Mở terminal khác tại thư mục dự án:

```sh
cd freedom_frontend
npm start
```

- Cửa hàng: http://localhost:5173/#/store
- Đăng nhập quản trị: http://localhost:5173/#/admin
- Quản lý sản phẩm: http://localhost:5173/#/products (cần tài khoản có quyền).

Chi tiết sử dụng và cấu hình: [freedom_frontend/README.md](freedom_frontend/README.md).

## Kiểm thử

```sh
cd freedom_backend
python -m pytest -q
```

```sh
cd freedom_frontend
npm run check
npm test
```

Kết quả gần nhất: backend **58 passed, 11 skipped**; ba bài kiểm thử checkout PostgreSQL thực chạy riêng bằng `python -m app.verify_postgres_checkout` đều qua. Frontend qua kiểm tra phân quyền, CRUD, ảnh tự chạy, giỏ hàng chọn dòng, giao hàng và đặt trước lấy tại cửa hàng; frontend dùng DOM/API mô phỏng.

Admin nhập size, màu và **số lượng trong kho** ngay trong form sản phẩm. Khách chọn size, thêm giỏ và chọn các dòng cần thanh toán trước khi nhập thông tin xác nhận. Xem [luồng đặt hàng và quản lý kho](freedom_backend/docs/CHECKOUT_SIZE_INVENTORY.md).

`.env`, mật khẩu, ảnh sản phẩm tải lên và bộ nhớ đệm không được đưa lên GitHub. Ảnh tải lên nằm trong `freedom_backend/uploads/`; khi triển khai, giữ thư mục này trên ổ lưu trữ bền vững và sao lưu cùng DB. Hướng dẫn triển khai và các chức năng còn cần hoàn thiện nằm trong README của từng phần.
