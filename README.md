# Freedom backend Python

Backend FastAPI cho database PostgreSQL đã cung cấp. Ưu tiên phần Phúc và tích hợp API cho Khánh, Tuấn Anh, Dũng. Đây là bản triển khai có kiểm thử, chưa phải sản phẩm thương mại đầy đủ. Xem [phân tích và giới hạn](docs/PHAN_TICH.md) và [bảng phân công 34 dòng](docs/PHAN_CONG.md).

## Chạy Ubuntu 24.04+

Python 3.12+; PostgreSQL 12+ theo SQL gốc (đã kiểm thử trên PostgreSQL 18.6). Không cần Alembic vì bản này không thay đổi schema.

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
python -m app.bootstrap --admin-email phuc@example.com
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Bootstrap hỏi mật khẩu Admin qua màn hình, không lưu mật khẩu rõ trong mã. Chạy lại `python -m app.bootstrap` để seed thiếu role/permission; không tự nâng quyền email cũ. Với database có role code khác admin/staff/customer, cần đối chiếu và ánh xạ dữ liệu trước, tránh tạo hai hệ role song song.

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json` (bản tĩnh ởdocs/openapi.json)
- Health: `/health`, kiểm tra kết nối DB: `/ready`.
- Đăng nhập: POST `/auth/token`, form `username=<email>&password=<mật khẩu>`; nhấn Authorize trên Swagger. Các endpoint khác nhận JSON và Bearer token.

## Email đặt lại mật khẩu

Cấu hình SMTP_HOST, SMTP_PORT, SMTP_STARTTLS, SMTP_USERNAME/PASSWORD, MAIL_FROM và FRONTEND_RESET_URL. `.env.example` đặt SMTP local port 1025, STARTTLS false để dùng công cụ hộp thư thử nghiệm; dự án không tự chạy SMTP server. Với dịch vụ thật, bật STARTTLS và dùng cổng theo nhà cung cấp. Khi SMTP không hoạt động, forgot-password trả 503; không trả token cho client. Token gửi trong liên kết email và nhập vào POST `/auth/reset-password` cùng new_password. Không có email xác minh đăng ký.

## Thử một luồng trong Swagger

1. Đăng nhập Admin. Tạo categories, sizes, colors, products (status `active`) và product_variants trong `/staff/catalog/*`. `PUT` là thay toàn bộ dữ liệu cho phép, không phải PATCH; dữ liệu thiếu lấy mặc định theo schema request. Stock không được ghi bằng CRUD SKU.
2. Admin nhập tồn bằng `/staff/inventory/{vid}/adjust` với quantity_change dương và note.
3. Đăng ký customer, đăng nhập, thêm địa chỉ qua `/me/addresses`, thêm SKU bằng `PUT /me/cart/items`. quantity=0 xóa dòng.
4. `POST /me/checkout` với address_id, payment_method `cod` hoặc `bank_transfer`; coupon_code tùy chọn. Giá/phí/giảm giá do server tính. Checkout thành công làm rỗng giỏ.
5. Customer xem `/me/orders/{oid}`; Admin/staff xử lý status qua confirmed → preparing → shipped → delivered. Hủy chỉ pending/confirmed chưa thu tiền.
6. Admin xác nhận giao dịch thanh toán thực tế bằng confirm-payment; mã transaction_id duy nhất. COD cần delivered. Đổi trả/hoàn tiền là đối soát thủ công theo phân tích.
7. Customer gửi review sau delivered; Admin duyệt approved/hidden/pending. Nhân viên chỉ đọc/flag, không được duyệt.

Mặc định staff có support.manage, reviews.read, inventory.read, orders.manage, returns.read, customers.read. Admin điều chỉnh danh sách quyền **của cả vai trò staff** qua `/admin/roles/{rid}/permissions`; không có quyền cá nhân trong schema. Các tác vụ users.manage, payments.manage, reviews.moderate, audit.read luôn yêu cầu Admin.

## Kiểm thử

Unit/API contract tests không cần DB:

```bash
python -m pytest -q
```

Các bài integration tự bỏ qua nếu chưa bật RUN_PG_TESTS. Để chạy đầy đủ, tạo **DB riêng có tên kết thúc `_test`**, import schema vào DB rỗng. Tests sẽ TRUNCATE toàn bộ bảng public trong DB test mỗi bài, không chạy vào dữ liệu thật.

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

Chưa cung cấp frontend, lưu ảnh/file, tích hợp ngân hàng/đơn vị vận chuyển hoặc quản lý sản phẩm theo nhân viên được giao. URL ảnh nhận http/https; frontend phải xử lý nội dung HTML bài viết an toàn khi hiển thị. Không sửa database để giả lập các chức năng thiếu.
