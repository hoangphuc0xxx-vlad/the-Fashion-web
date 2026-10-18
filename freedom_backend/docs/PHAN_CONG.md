# Đối chiếu chức năng và phân công

Nguồn: PDF1 = QLDA- freedom - Bảng chức năng.pdf; PDF2 = QLDA- freedom - Chức năng & Database.pdf. Đọc văn bản toàn bộ và kiểm tra ảnh trang chứa cột phân công. PDF1 xuất bảng ngang thành các trang rời: ghép cột Người phụ trách trang 3–4 theo thứ tự với chức năng trang 1–2; 32 dòng đầu khớp PDF2. Không suy luận người làm từ vị trí tên bên cạnh ghi chú B1–B6 hoàn tiền.

| STT | Vai trò chuẩn hóa | Chức năng | PDF1 | PDF2 | Module / API |
|---|---|---|---|---|---|
|1|Admin|Dashboard quản trị|Khánh|Khánh|community: `/admin/dashboard`|
|2|Admin|Quản lý tài khoản & phân quyền|Phúc|Phúc|people: `/admin/users; /admin/roles; /admin/permissions`|
|3|Admin|Quản lý nhân viên|Phúc|Phúc|people: `/admin/users?role=staff`|
|4|Admin|Quản lý khách hàng|Tuấn Anh|Tuấn Anh|people/community: `/admin/users?role=customer; /staff/customers/{uid}`|
|5|Admin|Quản lý sản phẩm & biến thể|Dũng|Dũng|catalog: `/staff/catalog/products; product_variants; product_images`|
|6|Admin|Danh mục & thương hiệu|Dũng|Dũng|catalog: `/staff/catalog/categories; brands`|
|7|Admin|Quản lý kho|Khánh|Khánh|community: `/staff/inventory`|
|8|Admin|Quản lý đơn hàng|Tuấn Anh|Tuấn Anh|commerce: `/staff/orders`|
|9|Admin|Thanh toán & vận chuyển|Tuấn Anh|Tuấn Anh|commerce: `/admin/orders/{oid}/confirm-payment; /staff/orders/{oid}/shipment`|
|10|Admin|Voucher / khuyến mãi|Dũng|Dũng|catalog: `/staff/catalog/coupons`|
|11|Admin|Quản lý đánh giá|Phúc|Phúc|people: `/admin/reviews`|
|12|Admin|Đổi trả & hoàn tiền|Khánh|Khánh|community: `/staff/returns`|
|13|Admin|Banner & bài viết|Dũng|Dũng|catalog: `/staff/catalog/banners; posts`|
|14|Admin|Nhật ký hoạt động|Phúc|Phúc|people: `/admin/audit-logs`|
|15|Nhân viên|Đăng nhập & phân quyền|Phúc|Phúc|auth/security: `/auth/token`|
|16|Nhân viên|Xử lý đơn hàng|Tuấn Anh|Tuấn Anh|commerce: `/staff/orders/{oid}/status`|
|17|Nhân viên|Quản lý sản phẩm được giao|Dũng|Dũng|catalog: `/staff/catalog/* (chưa có phạm vi giao từng người)`|
|18|Nhân viên|Kiểm tra kho|Khánh|Khánh|community: `/staff/inventory; /staff/inventory/{vid}/adjust`|
|19|Nhân viên|Hỗ trợ khách hàng|Phúc|Phúc|people: `/staff/support/tickets`|
|20|Nhân viên|Tiếp nhận đổi trả|Khánh|Khánh|community: `/staff/returns/{rid}`|
|21|Nhân viên|Theo dõi đánh giá|Dũng|Dũng|people: `/staff/reviews/{rid}/flag`|
|22|Khách hàng|Đăng ký / đăng nhập|Phúc|Phúc|auth: `/auth/register; token; logout; forgot-password; reset-password`|
|23|Khách hàng|Hồ sơ & địa chỉ|Phúc|Phúc|people/auth: `/me/profile; /me/addresses; /auth/password`|
|24|Khách hàng|Trang chủ|Dũng|Dũng|catalog: `/catalog/home; /catalog/products`|
|25|Khách hàng|Danh mục, tìm kiếm & lọc|Dũng|Dũng|catalog: `/catalog/products; /catalog/lookups/{name}`|
|26|Khách hàng|Chi tiết sản phẩm|Dũng|Dũng|catalog: `/catalog/products/{pid}`|
|27|Khách hàng|Sản phẩm yêu thích|Khánh|Khánh|community: `/me/wishlist`|
|28|Khách hàng|Giỏ hàng|Tuấn Anh|Tuấn Anh|commerce: `/me/cart; /me/cart/items`|
|29|Khách hàng|Đặt hàng & voucher|Tuấn Anh|Tuấn Anh|commerce: `/me/checkout`|
|30|Khách hàng|Thanh toán|Tuấn Anh|Tuấn Anh|commerce: `/me/orders/{oid} (trạng thái); checkout (phương thức)`|
|31|Khách hàng|Theo dõi / hủy đơn|Khánh|Khánh|commerce: `/me/orders; /me/orders/{oid}/cancel`|
|32|Khách hàng|Đánh giá sản phẩm|Khánh|Khánh|community: `/me/reviews`|
|33|Khách hàng|Yêu cầu đổi trả|Phúc|Thiếu dòng|community: `/me/returns`|
|34|Khách hàng|Liên hệ / hỗ trợ|Phúc|Thiếu dòng|people: `/support/tickets`|

## Trách nhiệm theo người

- **Phúc**: dòng 2, 3, 11, 14, 15, 19, 22, 23, 33, 34.
- **Khánh**: dòng 1, 7, 12, 18, 20, 27, 31, 32.
- **Tuấn Anh**: dòng 4, 8, 9, 16, 28, 29, 30.
- **Dũng**: dòng 5, 6, 10, 13, 17, 21, 24, 25, 26.

## Điểm chưa nhất quán

- PDF1 có 34 dòng chức năng; PDF2 chỉ đến dòng 32 (Đánh giá sản phẩm). Hai dòng Yêu cầu đổi trả và Liên hệ/hỗ trợ có tên Phúc ở phần cuối PDF1 nhưng không có dòng tương ứng PDF2. Phân công hai dòng này theo PDF1, cần nhóm xác nhận nếu dùng PDF2 làm chuẩn.
- PDF2 ghi nhãn Admin ở đoạn có chức năng nhân viên và ghi Nhân viên ở đoạn mua hàng/đánh giá. Chuẩn hóa vai trò theo mô tả và PDF1; tên người làm không đổi.
- PDF1 bị chia ngang, nội dung mô tả bên phải bị cắt; phần quy trình hoàn tiền B1–B6 là ghi chú, không phải sáu dòng phân công độc lập. PDF2 có cột Khó khăn để trống.
- Theo dõi/hủy đơn thuộc Khánh nhưng cùng dữ liệu với xử lý đơn của Tuấn Anh; triển khai chung commerce.py để chỉ có một quy tắc trạng thái và hoàn tồn. Quản lý khách hàng dùng lại people.py của Phúc; endpoint chi tiết thuộc community.py. Chủ sở hữu nghiệp vụ vẫn theo bảng trên.
- Chức năng khách hàng gửi đổi trả thuộc Phúc (PDF1); tiếp nhận/duyệt/hoàn tiền thuộc Khánh. Dùng chung community.py để tránh sai số lượng trả.
- Hỗ trợ và đánh dấu đánh giá vi phạm ghi audit_logs; schema không có cột flagged hay bảng phân công sản phẩm cho nhân viên. Không tự thêm cột.