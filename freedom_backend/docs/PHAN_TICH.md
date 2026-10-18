# Phân tích PostgreSQL và quyết định triển khai

## Schema gốc

31 bảng, bigint identity, timestamptz, NUMERIC(15,2), JSONB cho audit, FK và hành vi xóa theo tệp SQL. Không có dữ liệu INSERT, không có role/permission seed hay enum/CHECK nghiệp vụ. Bản schema.sql trong ZIP giữ nguyên byte so với SQL đã tải lên. API dùng SQLAlchemy Core reflection trên PostgreSQL qua psycopg, không tự tạo hay sửa bảng.

| Bảng | Cột (theo SQL) |
|---|---|
|addresses|id, user_id, recipient_name, phone, province, district, ward, street_address, is_default|
|audit_logs|id, user_id, action, entity_type, entity_id, details, created_at|
|banners|id, title, image_url, target_url, sort_order, is_active, starts_at, expires_at|
|brands|id, name, slug, is_active|
|cart_items|id, cart_id, variant_id, quantity|
|carts|id, user_id, updated_at|
|categories|id, parent_id, name, slug, is_active|
|colors|id, name, hex_code|
|coupons|id, code, discount_type, discount_value, min_order_value, max_discount, usage_limit, used_count, starts_at, expires_at, is_active|
|inventory_movements|id, variant_id, movement_type, quantity_change, reference_type, reference_id, note, created_by, created_at|
|order_items|id, order_id, variant_id, sku_snapshot, product_name_snapshot, size_snapshot, color_snapshot, unit_price, quantity, line_total|
|order_status_histories|id, order_id, old_status, new_status, changed_by, note, created_at|
|orders|id, order_code, user_id, coupon_id, recipient_name, recipient_phone, shipping_address, subtotal, shipping_fee, discount_amount, total_amount, status, payment_method, customer_note, confirmed_by, placed_at, updated_at|
|password_reset_tokens|id, user_id, token_hash, expires_at, used_at, created_at|
|payments|id, order_id, provider, provider_transaction_id, amount, status, paid_at, created_at|
|permissions|id, code, description|
|posts|id, author_id, title, slug, content, status, published_at|
|product_images|id, product_id, variant_id, image_url, alt_text, sort_order, is_primary|
|product_variants|id, product_id, size_id, color_id, sku, price, stock_quantity, reserved_quantity, low_stock_threshold, is_active|
|products|id, category_id, brand_id, name, slug, description, material, base_price, status, created_by, created_at, updated_at|
|return_requests|id, order_item_id, user_id, quantity, reason, type, status, refund_amount, handled_by, created_at|
|review_images|id, review_id, image_url|
|reviews|id, user_id, product_id, order_item_id, rating, comment, status, created_at|
|role_permissions|role_id, permission_id|
|roles|id, code, name|
|shipments|id, order_id, carrier, tracking_number, status, shipped_at, delivered_at|
|sizes|id, name, sort_order|
|support_messages|id, ticket_id, sender_id, content, created_at|
|support_tickets|id, user_id, order_id, subject, message, status, assigned_to, created_at|
|users|id, role_id, full_name, email, phone, password_hash, avatar_url, status, email_verified_at, created_at, updated_at|
|wishlists|user_id, product_id, created_at|

## Ràng buộc đáng chú ý

- users: email và phone UNIQUE; email phân biệt hoa thường trong DB. Backend chuẩn hóa email mới về chữ thường, cần kiểm tra/trộn tài khoản email cũ trước nhập dữ liệu thực. Một user có một role. Quyền gắn theo role qua role_permissions, không có quyền riêng từng nhân viên.
- carts.user_id UNIQUE; cart_items UNIQUE(cart_id,variant_id). wishlist khóa ghép user/product. variants UNIQUE SKU và (product,size,color). reviews UNIQUE order_item_id: mỗi dòng hàng một đánh giá. Backend kiểm tra quyền sở hữu và đơn delivered.
- order_items.line_total là GENERATED ALWAYS STORED; tuyệt đối không ghi trường này. Đơn hàng lưu snapshot tên/SKU/size/màu/giá/địa chỉ, giữ lịch sử khi catalog thay đổi.
- product_images có hai FK độc lập, chưa ràng buộc variant thuộc product: backend kiểm tra. categories có FK cha nhưng chưa chặn chu kỳ: backend kiểm tra và khóa cây khi đổi cha.
- Số lượng/giá/rating/trạng thái chưa có CHECK. Validation tại API và giao dịch có khóa bảo vệ các đường ghi qua API; SQL viết tay vẫn có thể tạo dữ liệu sai. Các giá trị trạng thái do dự án chọn, vì SQL không quy định enum.
- addresses chưa có UNIQUE mặc định/user: khóa dòng user trước đổi mặc định. Không bắt buộc luôn có một địa chỉ mặc định; xóa địa chỉ mặc định có thể để lại 0.
- payments/shipments không UNIQUE(order_id); API quản lý một bản ghi thanh toán và một vận đơn mỗi đơn. Nếu dữ liệu cũ có nhiều bản ghi, trả 409 để đối soát, không tự gộp.
- Tệp DDL có CREATE TABLE IF NOT EXISTS nhưng ADD CONSTRAINT không IF NOT EXISTS. Chỉ import vào DB rỗng một lần; import lại có thể lỗi/rollback. Không dùng làm migration.

## Quy tắc đang chạy

- role code: admin, staff, customer. Admin toàn quyền; staff kiểm tra permission trên DB mỗi request, không được quản lý role/user, audit, duyệt review hoặc đối soát thanh toán dù được gán mã tương ứng. Customer và mọi /me endpoint chỉ dữ liệu của chính user. Nhân viên chưa có quyền catalog/kho ghi mặc định; Admin cấp theo role staff khi cần.
- Argon2 mật khẩu; JWT HS256 có issuer/audience/expiry và fingerprint hash mật khẩu, đổi/reset mật khẩu vô hiệu hóa token cũ. Logout ghi mốc audit và vô hiệu hóa tất cả token user đã cấp trước đó, có hiệu lực qua nhiều worker. Không có refresh token. Không xóa audit logout nếu còn token sống.
- Reset token ngẫu nhiên 48 byte, lưu SHA-256, hạn 20 phút, khóa khi dùng và vô hiệu hóa các reset token còn lại cùng user. Email qua SMTP, không trả token trong HTTP hoặc log. Giới hạn auth 10 lần/IP/phút tại mỗi process; triển khai thật cần limiter chia sẻ/reverse proxy.
- Giỏ hàng kiểm tra tồn nhưng không giữ hàng. Checkout khóa user/cart rồi SKU theo id; tính lại giá từ DB, dùng Decimal, khóa coupon, tạo order/items/payment/history/movement và xóa giỏ trong một transaction. Đơn thứ hai với giỏ đã xóa báo rỗng; chưa có idempotency key lâu dài.
- Tồn khả dụng = stock_quantity − reserved_quantity; checkout trừ stock_quantity ngay, không tăng reserved_quantity. Hủy pending/confirmed chưa thu tiền hoàn tồn đúng một lần. Đơn đã paid không hủy qua API này. Chưa có job tự hết hạn đơn chuyển khoản chưa trả tiền.
- Đơn: pending → confirmed → preparing → shipped → delivered; pending/confirmed → cancelled. COD đối soát sau delivered; bank_transfer do Admin xác nhận giao dịch thực tế. Chưa có tích hợp cổng thanh toán/webhook/chuyển khoản tự động.
- Giá vận chuyển cố định từ SHIPPING_FEE, không nhận giá từ client; voucher percent hoặc fixed, tính trên subtotal và chặn dùng vượt hạn/lượt. Lượt voucher không hoàn lại khi hủy (chính sách triển khai cần nhóm thống nhất). Không có giới hạn lượt theo user trong schema.
- Đổi trả: requested → received → approved → refunded, hoặc requested/received → rejected. Staff chỉ received, Admin duyệt/từ chối/ghi nhận hoàn tiền. Tổng số lượng yêu cầu chưa bị từ chối không vượt số đã mua. Tự động tính phần tiền hàng sau phân bổ giảm giá; không hoàn phí ship. Chưa tự nhập kho hàng trả do cần kiểm tra tình trạng hàng.
- refunded chỉ là ghi nhận đối soát sau thao tác ngân hàng bên ngoài; API không thực hiện chuyển tiền. Exchange chặn refunded vì chưa có SKU thay thế trong schema. Chưa có tài khoản ngân hàng, upload bằng chứng, video, mã vận chuyển hàng trả hoặc lịch sử từng bước B1–B6. Có thể trao đổi qua support ticket, không thay thế hồ sơ hoàn tiền đầy đủ.
- Dashboard trả tổng doanh số đơn delivered trước hoàn tiền (delivered_gross_revenue), số đơn theo placed_at, tổng khách toàn thời gian và top 10 theo snapshot tên sản phẩm. Không gọi đây là doanh thu thuần/tiền đã thu. Chưa có lọc thời gian cho tổng khách.

## Chưa đủ dữ liệu để khẳng định hoàn thiện sản phẩm

Đã có nền backend và API tích hợp, nhưng chưa thể gọi toàn bộ 34 chức năng là hoàn chỉnh: còn phân công sản phẩm theo từng nhân viên, upload file, email xác minh, cổng thanh toán, vận chuyển ngoài, đổi SKU, quy trình chứng cứ/hoàn tiền B1–B6, tìm kiếm nâng cao và featured flag trang chủ. Schema không có các cấu trúc này. Không thêm DB tùy tiện; cần nhóm xác nhận chính sách rồi thiết kế migration riêng.

## Migration và nguồn kỹ thuật

Không dùng Alembic trong bản này vì chưa có thay đổi schema. Khi cần bổ sung: tạo baseline từ DB đã import, kiểm tra diff thủ công, stamp baseline sau đối chiếu; không chạy create_all hay autogenerate rồi upgrade lên DB thật một cách tự động.

- [FastAPI: JWT và mật khẩu](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [SQLAlchemy: reflection schema có sẵn](https://docs.sqlalchemy.org/en/20/core/reflection.html)