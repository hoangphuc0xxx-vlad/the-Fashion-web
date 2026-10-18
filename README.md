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

Kết quả gần nhất: backend **45 passed, 8 skipped**; frontend qua kiểm tra phân quyền, CRUD, tải nhiều ảnh và bộ ảnh tự chạy. Kiểm thử PostgreSQL yêu cầu DB test riêng; frontend dùng DOM/API mô phỏng.

`.env`, mật khẩu, ảnh sản phẩm tải lên và bộ nhớ đệm không được đưa lên GitHub. Ảnh tải lên nằm trong `freedom_backend/uploads/`; khi triển khai, giữ thư mục này trên ổ lưu trữ bền vững và sao lưu cùng DB. Hướng dẫn triển khai và các chức năng còn cần hoàn thiện nằm trong README của từng phần.
