# Freedom backend Python

Backend FastAPI cho database PostgreSQL đã cung cấp. Ưu tiên phần Phúc và tích hợp API cho Khánh, Tuấn Anh, Dũng. Đây là bản triển khai có kiểm thử, chưa phải sản phẩm thương mại đầy đủ. Xem [phân tích và giới hạn](docs/PHAN_TICH.md) và [bảng phân công 34 dòng](docs/PHAN_CONG.md).

## Chạy Ubuntu 24.04+

Python 3.12+; PostgreSQL 12+ theo SQL gốc (đã kiểm thử trên PostgreSQL 18.6). Các thay đổi bổ sung dùng migration SQL chạy rõ ràng trước khi khởi động.

```bash
sudo apt update
sudo apt install python3 python3-venv postgresql postgresql-client
sudo systemctl enable --now postgresql
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Dán chuỗi vừa tạo vào JWT_SECRET trong `.env`. Thay DATABASE_URL bằng tài khoản database của bạn. Không commit `.env`.

Nếu **chưa có DB**, tạo một database rỗng và import SQL đúng một lần:

```bash
sudo -u postgres psql
```

Trong psql (thay mật khẩu mẫu):

```sql
CREATE ROLE freedom LOGIN PASSWORD 'choose-a-strong-db-password';
CREATE DATABASE freedom OWNER freedom;
\q
```

```bash
psql -h localhost -U freedom -d freedom -v ON_ERROR_STOP=1 -fdatabase/schema.sql
```

Nếu **đã import SQL trước đây**, bỏ qua bước import; chỉ sửa DATABASE_URL. Tệp gốc không phải migration có thể chạy lặp. Khi database được sở hữu bởi user khác, cần cấp quyền CONNECT, USAGE schema, SELECT/INSERT/UPDATE/DELETE trên 31 bảng và USAGE/SELECT trên identity sequences cho user API; reflection cần quyền đọc metadata. Khởi chạy ứng dụng không thực thi DDL.

```bash
python -m app.migrate
python -m app.bootstrap --admin-email phuc@example.com
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Bootstrap hỏi mật khẩu Admin qua màn hình, không lưu mật khẩu rõ trong mã. Chạy lại `python -m app.bootstrap` để seed thiếu role/permission; không tự nâng quyền email cũ. Với database có role code khác admin/staff/customer, cần đối chiếu và ánh xạ dữ liệu trước, tránh tạo hai hệ role song song.

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json` (bản tĩnh ởdocs/openapi.json)
- Health: `/health`, kiểm tra kết nối DB: `/ready`.
- Đăng nhập: POST `/auth/token`, form `username=<email>&password=<mật khẩu>`; nhấn Authorize trên Swagger. Các endpoint khác nhận JSON và Bearer token.

## Ảnh đại diện sản phẩm

Form frontend dùng `POST /staff/catalog/products/{id}/images`, multipart với trường `files` lặp lại để tải tối đa 8 ảnh mỗi lần. Bộ ảnh được kiểm tra trước khi cập nhật DB; file không hợp lệ sẽ hủy cả lần tải. Ảnh đầu tiên làm đại diện, các ảnh khác giữ thứ tự đã gửi; ảnh cũ được giữ sau bộ mới. Frontend tự trượt bộ ảnh trên từng thẻ sản phẩm, tên và giá cố định bên dưới.

Admin hoặc staff có `catalog.manage` tải ảnh bằng `POST /staff/catalog/products/{id}/primary-image`, multipart với trường `file`. Chỉ nhận ảnh tĩnh JPG, PNG, WebP tối đa 5 MB / 24 triệu điểm ảnh; backend kiểm tra nội dung, sửa hướng theo EXIF và chuyển thành WebP có cạnh dài tối đa 1600px. Ảnh lưu vào bảng `product_images` hiện có, đánh dấu `is_primary`; các ảnh cũ được giữ và bỏ cờ đại diện. API danh sách/chi tiết sản phẩm trả `product_images`, gồm ảnh đại diện để frontend hiển thị.

File được lưu trong `freedom_backend/uploads/products` (có thể đổi bằng `MEDIA_ROOT` trong môi trường triển khai) và phục vụ qua `/media/products/{tên-file}.webp`. Cần giữ thư mục này trên ổ lưu trữ bền vững và sao lưu cùng DB khi triển khai. Không commit ảnh tải lên vào Git. Kiểm thử dùng thư mục tạm và SQLite, không tạo sản phẩm trên DB bán hàng.

`GET /catalog/products` hiển thị sản phẩm `active` trong danh mục hoạt động, không bắt buộc đã có biến thể. Lọc size/màu vẫn yêu cầu biến thể tương ứng. Lọc giá dùng giá biến thể đang hoạt động, hoặc giá niêm yết khi chưa có biến thể hoạt động. Thêm vào giỏ/đặt hàng vẫn kiểm tra biến thể, trạng thái và tồn kho.

## Email đặt lại mật khẩu

Cấu hình SMTP_HOST, SMTP_PORT, SMTP_STARTTLS, SMTP_USERNAME/PASSWORD, MAIL_FROM và FRONTEND_RESET_URL. `.env.example` đặt SMTP local port 1025, STARTTLS false để dùng công cụ hộp thư thử nghiệm; dự án không tự chạy SMTP server. Với dịch vụ thật, bật STARTTLS và dùng cổng theo nhà cung cấp. Khi SMTP không hoạt động, forgot-password trả 503; không trả token cho client. Token gửi trong liên kết email và nhập vào POST `/auth/reset-password` cùng new_password. Không có email xác minh đăng ký.

## Thử một luồng trong Swagger

1. Đăng nhập Admin. Tạo danh mục và sản phẩm `active` trong `/staff/catalog/*`; form sản phẩm hỗ trợ `variants` gồm size, màu, giá và số lượng tồn. `PUT` thay toàn bộ dữ liệu sản phẩm cho phép; bỏ `variants` sẽ giữ biến thể hiện có.
2. Số lượng nhập cùng sản phẩm được ghi vào kho. Điều chỉnh bổ sung qua `/staff/inventory/{vid}/adjust` với quantity_change và note.
3. Đăng ký customer, đăng nhập và thêm SKU bằng `PUT /me/cart/items`. quantity=0 xóa dòng.
4. `POST /me/checkout` với `checkout_key`, các `variant_ids` đã chọn, thông tin người nhận và `fulfillment_method` delivery/pickup. Gửi `expected_total`, `expected_quantities` để phát hiện thay đổi trước xác nhận. Chỉ các dòng đã chọn bị xóa khỏi giỏ khi thành công.
5. Customer xem `/me/orders/{oid}`; Admin/staff xử lý pending → packing → shipping → delivered/failed. Đơn pickup đi từ packing đến delivered. Chi tiết trường, trạng thái và quy tắc hoàn kho: [Size, số lượng và đặt hàng](docs/CHECKOUT_SIZE_INVENTORY.md).
6. Admin xác nhận giao dịch thanh toán thực tế bằng confirm-payment; mã transaction_id duy nhất. COD cần delivered. Đổi trả/hoàn tiền là đối soát thủ công theo phân tích.
7. Customer gửi review sau delivered; Admin duyệt approved/hidden/pending. Nhân viên chỉ đọc/flag, không được duyệt.

Mặc định staff có support.manage, reviews.read, inventory.read, orders.manage, returns.read, customers.read. Admin điều chỉnh danh sách quyền **của cả vai trò staff** qua `/admin/roles/{rid}/permissions`; không có quyền cá nhân trong schema. Các tác vụ users.manage, payments.manage, reviews.moderate, audit.read luôn yêu cầu Admin.

## Kiểm thử

Unit/API contract tests không cần PostgreSQL (58 passed, 11 bài tích hợp bỏ qua khi chưa bật DB test):

```bash
python -m pytest -q
python -m app.verify_postgres_checkout
```

`app.verify_postgres_checkout` tạo DB tạm từ cấu trúc DB hiện tại, chạy ba bài kiểm thử checkout thực trên PostgreSQL rồi dọn DB tạm. Cần quyền CREATE DATABASE. Các bài integration còn lại tự bỏ qua nếu chưa bật RUN_PG_TESTS. Để chạy đầy đủ, tạo **DB riêng có tên kết thúc `_test`**, import schema vào DB rỗng và chạy migration. Tests sẽ TRUNCATE toàn bộ bảng public trong DB test mỗi bài, không chạy vào dữ liệu thật.

```bash
createdb -h localhost -U freedom freedom_test
psql -h localhost -U freedom -d freedom_test -v ON_ERROR_STOP=1 -fdatabase/schema.sql
DATABASE_URL=postgresql+psycopg://freedom:your-password@localhost/freedom_test RUN_PG_TESTS=1 python -m pytest -q
```

Xem kết quả thực tế ở [docs/KIEM_THU.md](docs/KIEM_THU.md). `requirements-lock.txt` ghi phiên bản chính xác trong môi trường kiểm thử Python 3.14/Linux; trên Ubuntu Python 3.12 dùng requirements.txt nếu một bản khóa không hỗ trợ interpreter đó.

## Cấu trúc

```text
app/
  config.py             cấu hình env
  db.py                 kết nối, reflection, transaction, audit
  security.py           Argon2, JWT, ownership, quyền
  schemas.py            validation auth/people/commerce/community
  catalog_schemas.py    validation CRUD catalog
  bootstrap.py          seed role/permission, Admin CLI
  main.py               app, CORS, lỗi, giới hạn auth
  routers/
    auth.py             Phúc: đăng ký/đăng nhập/logout/mật khẩu
    people.py           Phúc: users/roles/profile/address/support/moderation
    catalog.py          Dũng: catalog/content/voucher
    commerce.py         Tuấn Anh + theo dõi/hủy đơn của Khánh
    community.py        Khánh + gửi đổi trả của Phúc + tra cứu khách Tuấn Anh
database/schema.sql    bản SQL nguyên gốc
docs/                  phân tích, phân công MD/CSV, OpenAPI, kiểm thử
tests/                 validation, RBAC, ownership, mua/hủy/concurrency
```

## Triển khai thực tế

Dùng database user hạn chế quyền, HTTPS/reverse proxy và một limiter chia sẻ cho nhiều worker; cấu hình CORS đúng domain frontend. Không dùng `--reload` khi vận hành. Khởi chạy ví dụ:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

Đặt tiến trình dưới systemd trong Ubuntu với WorkingDirectory là thư mục dự án, EnvironmentFile trỏ `.env`, ExecStart trỏ `.venv/bin/uvicorn`, chạy bằng user dịch vụ riêng và Restart=on-failure. Backup DB, theo dõi audit và lỗi, kiểm thử restore trước triển khai. Bộ chặn auth trong app chỉ áp dụng từng process và IP trực tiếp; cấu hình trusted proxy/IP thật cùng limiter ở reverse proxy. Dữ liệu audit có mốc logout cần giữ ít nhất đến khi token liên quan hết hạn.

Frontend nằm tại `../freedom_frontend`, gồm tải ảnh đại diện sản phẩm; backend lưu ảnh theo hướng dẫn ở trên. Chưa tích hợp ngân hàng/đơn vị vận chuyển hoặc quản lý sản phẩm theo nhân viên được giao. API ảnh dạng URL vẫn nhận http/https; frontend phải xử lý nội dung HTML bài viết an toàn khi hiển thị. Không sửa database để giả lập các chức năng thiếu.


## Xóa sản phẩm an toàn

`DELETE /staff/catalog/products/{id}` mặc định dùng `?mode=soft`: đổi `status` thành `archived`, cập nhật `updated_at`, giữ nguyên biến thể, ảnh và lịch sử. Sản phẩm bị ẩn khỏi cửa hàng; có thể khôi phục bằng sửa trạng thái trong danh sách “Đã xóa / lưu trữ”.

Admin có thể chọn `?mode=hard` để xóa vĩnh viễn sản phẩm nhập nhầm. API chỉ cho phép nếu mọi biến thể có tồn kho và số lượng đang giữ bằng 0, đồng thời không có tham chiếu từ `order_items`, `inventory_movements`, `cart_items`, `reviews`, `wishlists`. Khi có tham chiếu, trả HTTP 409 và yêu cầu xóa mềm; nhân viên không được xóa cứng (403). Giá trị mode không hợp lệ trả 422.

Xóa cứng xóa bản ghi ảnh, biến thể rồi sản phẩm trong cùng transaction; ghi audit `hard_delete`. Không xóa đơn hàng, lịch sử kho hay nới lỏng khóa ngoại. Các tệp ảnh trên ổ đĩa được giữ lại vì URL có thể dùng chung; việc dọn tệp không thuộc thao tác này. Nếu xảy ra xung đột khóa ngoại, transaction được rollback và trả 409. Không cần migration hoặc import lại schema cho thay đổi này.

Trong mã nguồn trước thay đổi, endpoint đã lưu trữ sản phẩm thay vì DELETE trực tiếp. Do đó chưa xác định được nguyên nhân PostgreSQL thực tế ngừng hoạt động nếu chưa có log từ lần lỗi; lỗi khóa ngoại thường làm thất bại transaction, không đồng nghĩa database server bị sập. Thay đổi được kiểm thử với database SQLite cô lập có bật khóa ngoại; kiểm thử PostgreSQL cần database thử nghiệm riêng, không dùng dữ liệu bán hàng thật.
