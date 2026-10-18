# Size, số lượng và đặt hàng

## Cập nhật database

Đã kiểm tra schema: `sizes`, `colors`, `product_variants`, `inventory_movements`, giỏ hàng và đơn hàng đã có sẵn. Size và tồn kho tiếp tục dùng các bảng này. Thông tin lấy tại cửa hàng còn thiếu nên migration bổ sung vào `orders`: `fulfillment_method`, `recipient_email`, `pickup_start`, `pickup_end`, `checkout_key`; đồng thời bổ sung trạng thái giao thất bại và kiểm tra dữ liệu.

Sau khi import schema gốc hoặc cập nhật code, chạy trong `freedom_backend` với `.env` trỏ đúng DB:

```sh
python -m app.migrate
```

Migration có thể chạy lại, không import lại dữ liệu gốc. Ứng dụng không tự thực thi DDL khi khởi động. Tài khoản chạy migration cần quyền sửa bảng/index.

## Sản phẩm và kho

Trong admin → Sản phẩm → Thêm/Sửa, mỗi dòng nhập size, màu, giá bán và **Số lượng trong kho**. Tổng số lượng được cộng bên dưới. Khi lưu, backend tạo/cập nhật biến thể và ghi biến động kho trong cùng giao dịch. Nhân viên cần `catalog.manage` để sửa sản phẩm và `inventory.manage` nếu thay đổi tồn; admin có toàn quyền.

Tồn được quản lý riêng theo size/màu. Màn hình kho hiển thị tên sản phẩm, size, màu, tồn và lượng khả dụng. Size/màu của SKU cũ giữ nguyên để bảo toàn lịch sử; bỏ chọn Đang bán để ngừng bán, thêm dòng mới nếu đổi size/màu. Sản phẩm cũ chưa có size hoặc tồn khả dụng cần được cập nhật trước khi khách mua.

Nếu tồn thay đổi kể từ khi mở form, backend từ chối ghi đè và yêu cầu tải lại. Lượng tồn không được thấp hơn lượng đang giữ chỗ.

## Giỏ hàng và xác nhận

Khách chọn size/màu, số lượng rồi thêm giỏ. Huy hiệu giỏ là tổng số lượng sản phẩm. Trong giỏ, chọn ít nhất một dòng mới hiện hai nút phía dưới; đơn hàng chỉ chứa các dòng được chọn, các dòng khác giữ nguyên.

- **Đặt hàng:** nhập tên, số điện thoại và địa chỉ đầy đủ, kiểm tra tổng tiền rồi xác nhận.
- **Đặt trước và lấy tại cửa hàng:** nhập tên, số điện thoại, email, ngày và giờ bắt đầu/kết thúc đến lấy; khoảng giờ từ 15 phút đến 8 giờ, trong tương lai theo giờ Việt Nam. Không thu phí giao hàng.

Đơn chỉ tạo khi xác nhận form cuối. API yêu cầu `checkout_key` duy nhất cho mỗi lần xác nhận; gửi lại cùng khóa trả về đơn cũ. Server khóa giỏ và biến thể, kiểm tra quyền sở hữu, trạng thái sản phẩm/danh mục, số lượng và giá; trừ tồn và ghi đơn trong một giao dịch. `expected_quantities` và `expected_total` giúp phát hiện thay đổi giỏ/giá trước khi xác nhận.

Giao diện hiện dùng COD. Thêm giỏ chưa giữ hàng; nếu hết hàng trước khi xác nhận, khách nhận lỗi và cần điều chỉnh giỏ.

## Xử lý đơn

Admin mở Đơn hàng để xem tên, điện thoại, địa chỉ hoặc email và lịch lấy, cùng size/màu/số lượng từng sản phẩm. Khách mở **Đơn của tôi** để theo dõi; danh sách/chi tiết đang mở cập nhật mỗi 15 giây khi tab hoạt động.

| Trạng thái | Màu | Hành động |
| --- | --- | --- |
| Chờ xác nhận | Trung tính | Admin xác nhận hoặc hủy |
| Đang đóng gói (`packing`) | Xanh dương | Giao vận chuyển hoặc hoàn tất lấy tại cửa hàng |
| Đang vận chuyển (`shipping`) | Vàng | Đã giao hoặc giao thất bại |
| Đã giao / Đã lấy tại cửa hàng (`delivered`) | Xanh lá | Hoàn tất |
| Giao thất bại (`failed`) | Đỏ | Giao lại hoặc hủy khi hàng đã về kho |

Admin tự tạo vận đơn bên ngoài và nhập đơn vị vận chuyển/mã theo dõi. Đơn lấy tại cửa hàng không có bước vận chuyển. API vẫn đọc các trạng thái cũ `confirmed`, `preparing`, `shipped` và chuyển sang luồng mới khi xử lý.

Hủy đơn chưa thanh toán hoàn lại tồn đúng một lần và ghi biến động kho. Giao thất bại chưa tự hoàn tồn vì hàng có thể chưa quay về; admin chỉ hủy sau khi xác nhận hàng thực tế về kho. Khách chỉ được hủy đơn đang chờ xác nhận.

## Kiểm thử

```sh
python -m pytest -q
python -m app.verify_postgres_checkout
```

Lệnh thứ hai cần PostgreSQL và quyền tạo database. Nó tạo DB `_test` ngẫu nhiên, sao chép cấu trúc không sao chép dữ liệu, chạy ba bài kiểm thử giao hàng/lấy tại cửa hàng/đặt đồng thời rồi xóa DB tạm. Không tạo đơn thử trên DB bán hàng.

Đăng nhập/đăng ký Google được bỏ qua theo yêu cầu hiện tại.
