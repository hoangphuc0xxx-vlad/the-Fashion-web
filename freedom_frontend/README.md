# Freedom Frontend

Giao diện tiếng Việt cho dự án thời trang nam Freedom, dựa trên bản Figma lưu trong thư mục `n`. Giữ tông olive, nền trắng ngà, sidebar và bố cục dashboard. Mã HTML/CSS/JavaScript thuần, không cần cài thư viện.

## Khởi chạy

Cài Node.js 18 trở lên, mở terminal tại thư mục này:

```sh
npm run dev
```

Mở **http://localhost:5173**: mặc định là cửa hàng dành cho khách. Cửa hàng không có liên kết vào quản trị.

Nhân viên/quản trị viên truy cập riêng **http://localhost:5173/#/admin** hoặc `/#/admin/login`. Khách chưa đăng nhập chỉ thấy biểu mẫu đăng nhập quản trị; tài khoản khách hàng bị từ chối truy cập. Các URL trực tiếp như `/#/dashboard`, `/#/orders`, `/#/users` đều phải qua cùng bước xác minh quyền.

Không mở `index.html` bằng `file://`; cần HTTP để tải modules và `runtime-config.js`.

## Kết nối backend

1. Chạy PostgreSQL và FastAPI theo `../freedom_backend/README.md`.
2. Khởi động frontend. API mặc định là `http://127.0.0.1:8000`; không có chế độ xem thử hoặc chuyển nguồn dữ liệu trong trình duyệt.
3. Đăng nhập bằng tài khoản có trong database. Backend xác định vai trò và quyền từ `users`, `roles`, `permissions`, `role_permissions`; frontend không gán role theo email, ID hay `localStorage`.
4. Frontend dùng origin `http://localhost:5173`, đã được backend cho phép mặc định. Nếu đổi host/port, cập nhật `CORS_ORIGINS` trong `.env` backend.

Đổi API ở cấu hình triển khai trước khi khởi chạy, ví dụ PowerShell:

```powershell
$env:FREEDOM_API_BASE = 'https://api.ten-mien-cua-ban.vn'
npm start
```

Máy chủ phát `runtime-config.js` từ biến môi trường này. Khi triển khai cùng domain với reverse proxy, có thể đặt `FREEDOM_API_BASE=/api`. Cần định tuyến `/api` đến backend và bỏ tiền tố tương ứng. Không đưa secrets vào biến cấu hình frontend. Máy chủ Node hiện lắng nghe loopback để dùng sau reverse proxy; chạy thật cần domain/HTTPS và cấu hình API/CORS phù hợp.

Token nằm trong `sessionStorage`, hồ sơ/quyền chỉ giữ trong bộ nhớ và lấy từ `/auth/me`. Những khóa cấu hình demo/API cũ trong `localStorage` không còn được dùng.

## Phân quyền

- **Khách/Customer**: xem cửa hàng, đăng ký/đăng nhập, giỏ hàng, địa chỉ và đặt đơn của mình; không dựng sidebar, dashboard hay tải danh sách quản lý.
- **Staff**: chỉ thấy các mục tương ứng quyền thực tế được backend trả về. Ví dụ `inventory.read` được xem kho; phải có `inventory.manage` mới xuất hiện biểu mẫu điều chỉnh tồn.
- **Admin**: toàn quyền theo chính sách hiện có của backend. `users.manage`, `payments.manage`, `reviews.moderate`, `audit.read` vẫn chỉ dành cho admin, kể cả khi cấp nhầm cho staff trong DB.

`GET /auth/me` trả thêm `permissions` hiệu lực: `['*']` cho admin, danh sách quyền DB hợp lệ cho staff, `[]` cho customer/vai trò không được hỗ trợ. Không thay schema, không chạy seed và không tự cấp quyền cho tài khoản nào.

Mỗi lần mở trang quản lý, frontend xác minh lại `/auth/me` trước khi dựng giao diện. Quay lại tab hoặc khôi phục trang từ browser cache cũng xác minh lại. `401` xóa phiên, `403` gỡ giao diện quản lý đang hiển thị. Đăng xuất xóa dữ liệu quản lý trên trình duyệt và trở về cửa hàng.

Chặn frontend là phần trải nghiệm. Bảo vệ dữ liệu nằm ở `current()`/`require()` phía FastAPI: mọi request quản lý trực tiếp vẫn kiểm tra tài khoản đang hoạt động, vai trò và quyền trong DB. Thu hồi quyền, đổi vai trò hoặc khóa tài khoản có hiệu lực ở request tiếp theo; sửa HTML/JavaScript hoặc nhập URL không cấp thêm quyền.

## Phạm vi

- Dashboard, chọn kỳ thời gian, biểu đồ SVG, trạng thái đơn hàng, xuất CSV.
- Danh sách quản lý: đơn hàng, sản phẩm, danh mục/thương hiệu, tồn kho, khách hàng, voucher, đánh giá, banner/bài viết, đổi trả, hỗ trợ, nhân viên và nhật ký.
- Tìm kiếm/lọc **trong trang hiện tại**. API tải tối đa 100 bản ghi mỗi trang; có nút chuyển trang.
- Chi tiết đơn và chuyển trạng thái theo luồng backend; CRUD sản phẩm trên frontend; điều chỉnh tồn kho kèm lý do.
- Cửa hàng: bộ sưu tập, lọc danh mục, tìm kiếm, sắp xếp, chọn size/màu còn hàng, giỏ hàng chọn nhiều dòng, đặt COD giao tận nơi hoặc đặt trước lấy tại cửa hàng, theo dõi Đơn của tôi.
- Responsive cho điện thoại, menu thu gọn, dialog bàn phím, trạng thái rỗng/lỗi/đang tải.

Tất cả nghiệp vụ dùng API thật. Backend không khả dụng thì hiển thị lỗi; không tự thay thế bằng sản phẩm, đơn hoặc khách hàng mẫu. Ảnh hero là tài nguyên thiết kế, không phải sản phẩm tự sinh trong database.

Dashboard API dùng tổng doanh thu đơn đã giao và tổng đơn trong kỳ từ `/admin/dashboard`. Biểu đồ, phân bổ trạng thái và số đơn hoàn thành tính từ **tối đa 100 đơn gần nhất**; tổng khách hàng là số toàn cửa hàng. Không hiển thị tăng trưởng giả. Không có endpoint thống kê chuỗi thời gian đầy đủ nên biểu đồ chưa đại diện toàn bộ lịch sử khi có hơn 100 đơn.

Các màn hình ngoài đơn hàng, sản phẩm và tồn kho hiện hỗ trợ đọc/lọc/chi tiết; chưa có đầy đủ biểu mẫu CRUD hay giao diện chỉnh quyền nhân viên. Size, màu, giá và số lượng tồn được nhập trực tiếp trong form sản phẩm, cùng ảnh đại diện. API trả dữ liệu thật cho admin và cửa hàng. Giao diện checkout dùng COD; chưa tích hợp cổng thanh toán. Khách theo dõi đơn qua nút Đơn của tôi.

## Thêm, xem, sửa, xóa sản phẩm trên frontend

Vào **http://localhost:5173/#/products** sau khi đăng nhập admin hoặc staff có quyền `catalog.manage`.

Trong **Size, màu và tồn kho**, nhập từng size/màu, giá và **Số lượng trong kho**. Có tổng số lượng bên dưới và nút thêm dòng. Lưu sản phẩm đồng thời lưu số lượng vào quản lý kho và ghi biến động. Staff thay đổi tồn cần thêm `inventory.manage`. Khi tồn đã đổi trong lúc mở form, tải lại trước khi sửa để tránh ghi đè số vừa bán. Sản phẩm cũ chưa có size cần bổ sung size và tồn để khách mua.

- **Thêm sản phẩm**: nhập tên, slug (tự gợi ý theo tên), danh mục theo cây (ví dụ Áo → Áo sơ mi), thương hiệu tùy chọn, giá, chất liệu, mô tả và trạng thái. Trong **Ảnh sản phẩm**, chọn một hoặc nhiều ảnh JPG/PNG/WebP từ máy (tối đa 8 ảnh/lần, mỗi ảnh tối đa 5 MB), xem trước rồi bấm Thêm sản phẩm. Ảnh đầu tiên của bộ mới làm đại diện; các ảnh cũ được giữ sau bộ mới. Có thể tạo danh mục con ngay trong biểu mẫu, chọn danh mục cha; dữ liệu sản phẩm và ảnh vừa chọn được giữ khi quay lại và danh mục vừa tạo được chọn tự động.
- **Xem**: đọc thông tin đầy đủ từ API quản trị, gồm sản phẩm nháp/lưu trữ và bảng biến thể hiện có.
- **Sửa**: biểu mẫu điền sẵn toàn bộ trường và ảnh hiện tại; có thể chọn ảnh mới để thay ảnh đại diện, hoặc giữ nguyên ảnh nếu không chọn. Có thể đổi trạng thái Bản nháp / Đang bán / Đã xóa hoặc lưu trữ.
- **Xóa**: hiện hộp xác nhận trước khi gọi `DELETE`. Backend chuyển sản phẩm sang `archived`, giữ nguyên biến thể và lịch sử đơn hàng. Mặc định danh sách ẩn sản phẩm đã xóa.
- **Khôi phục**: chọn bộ lọc “Đã xóa / lưu trữ”, bấm Sửa và đổi lại trạng thái.

Giá niêm yết và giá từng size được lưu riêng. Sản phẩm `active` thuộc danh mục đang hoạt động sẽ xuất hiện trong bộ sưu tập, kể cả chưa có biến thể; sản phẩm nháp/lưu trữ được ẩn. Khách chỉ thêm vào giỏ khi có size hoạt động còn hàng. Biến thể và tồn được tạo từ các dòng size nhập trong form. Ảnh đại diện xuất hiện trong bảng admin; nhiều ảnh tự trượt từ phải sang trái mỗi 3,5 giây, giữ tên/giá bên dưới. Một ảnh không chạy slideshow. Rê chuột, tập trung bàn phím, chuyển tab hoặc cuộn ảnh khỏi màn hình sẽ tạm dừng; có nút điều hướng và dừng/chạy. Tùy chọn giảm chuyển động tắt tự chạy. Hiệu ứng rê chuột áp dụng cho sản phẩm, banner và danh mục.

Nếu lưu thông tin thành công nhưng tải ảnh lỗi, biểu mẫu giữ ID đã tạo và bộ ảnh đang chọn để thử lại bằng Lưu thay đổi, tránh tạo trùng sản phẩm. Bộ ảnh được kiểm tra toàn bộ trước khi cập nhật DB. Quyền được kiểm tra ở cả frontend và backend; thao tác lưu/xóa/tải ảnh ghi audit log. Không thay schema hoặc dùng dữ liệu giả.

Ảnh và CSS tham chiếu được sao chép từ bản lưu người dùng cung cấp trong `n`. Backend bổ sung quyền hiệu lực vào `/auth/me`; schema và dữ liệu phân quyền không bị thay đổi.

## Giỏ hàng và đặt hàng

Khách chọn size/màu và số lượng trước khi thêm giỏ. Huy hiệu giỏ hiển thị tổng số lượng. Chọn ít nhất một dòng trong giỏ mới hiện hai nút: **Đặt trước và lấy tại cửa hàng** và **Đặt hàng**. Chỉ các dòng đã chọn được đưa vào đơn; dòng khác giữ nguyên.

Giao hàng yêu cầu tên, số điện thoại và địa chỉ đầy đủ. Lấy tại cửa hàng yêu cầu tên, số điện thoại, email, ngày và khoảng giờ đến lấy. Chỉ khi xác nhận form cuối mới tạo đơn và trừ tồn. Khách theo dõi tại **Đơn của tôi**; admin thấy thông tin nhận hàng/lịch lấy trong chi tiết đơn. Trạng thái đóng gói xanh dương, vận chuyển vàng, đã giao xanh lá, giao thất bại đỏ.

Trước khi chạy bản mới, thực hiện `python -m app.migrate` tại backend. Xem [luồng chi tiết và kiểm thử](../freedom_backend/docs/CHECKOUT_SIZE_INVENTORY.md). Chưa triển khai đăng nhập Google theo yêu cầu hiện tại.

## Menu Áo – Quần – Suit và danh mục con

Cửa hàng có ba nhóm chính **Áo**, **Quần**, **Suit**. Menu con lấy trực tiếp từ cây `categories.parent_id` trong DB, không ghi cứng danh sách áo sơ mi, áo khoác, hoodie, sweater… Danh mục con mới tạo sẽ xuất hiện khi mở lại cửa hàng hoặc tải lại trang.

Trên máy tính, rê chuột lên Áo/Quần/Suit để tự mở menu con; di chuột xuống danh sách để chọn, rời khỏi vùng menu để đóng. Chỉ một menu mở tại một thời điểm. Trên điện thoại vẫn chạm để mở/đóng. Bàn phím dùng Tab và Enter/Space; Escape đóng menu và đưa tiêu điểm về tên nhóm.

1. Trong admin, chọn **Thêm/Sửa sản phẩm → Tạo danh mục mới**, hoặc **Danh mục & thương hiệu → Tạo danh mục con**.
2. Chọn cha Áo, Quần, Suit (hoặc danh mục con sâu hơn), nhập tên và slug, rồi lưu.
3. Nếu tạo từ form sản phẩm, danh mục mới tự được chọn cho sản phẩm. Các lựa chọn hiển thị đường dẫn như **Áo → Áo sơ mi → Sơ mi Linen**.
4. Trên cửa hàng, mỗi danh mục có link sao chép/mở lại được: `/#/store?category=ao`, `/#/store?category=ao-so-mi`, v.v. Slug link theo tên bạn nhập, không phụ thuộc tên ví dụ này.

Chọn nhóm cha sẽ lấy sản phẩm ở cả nhóm đó và toàn bộ nhánh con. Lọc, tìm kiếm và sắp xếp chạy qua API trước phân trang; có nút **Xem thêm sản phẩm** sau mỗi 100 mục. Danh mục bị ngừng hoạt động sẽ ẩn cả nhánh con và sản phẩm của nhánh đó trên cửa hàng. Link không còn tồn tại hiện thông báo riêng.

Với một database mới, tạo ba danh mục gốc một lần bằng lệnh sau tại `freedom_backend`:

```powershell
uv run --no-project --with-requirements requirements.txt python -m app.catalog_setup
```

Lệnh chỉ thêm các gốc `ao`, `quan`, `suit` còn thiếu, không tự chuyển danh mục đang có sang cha khác, không thêm sản phẩm mẫu và không thay schema/phân quyền. Danh mục con do bạn tạo từ admin.

## Kiểm tra cú pháp

Giao diện khách hàng dùng **Cormorant Garamond** cho tiêu đề, logo và tên nhóm danh mục trên banner; **Manrope** cho nội dung, điều hướng, tên sản phẩm, giá và nút. Kiểu chữ được khai báo trong `storefront-type.css`, hỗ trợ responsive và các hộp thoại mua hàng. Font WOFF2 có bộ ký tự tiếng Việt được lưu trong `assets/fonts/`, kèm nguồn và giấy phép; website tải font từ máy chủ của dự án. `storefront-fonts.css` khai báo các subset và dùng `font-display: swap`.

Banner riêng cho **Áo, Quần, Suit** dùng ảnh ImageGen 1536 × 1024 trong `assets/category-*-v1.png`. Trang danh mục con kế thừa banner theo danh mục gốc, giữ nguyên tên danh mục con trong tiêu đề. Prompt và nguồn ảnh được ghi trong `assets/category-banner-notes.md`.

Trang chủ có thêm ba banner liên kết Áo, Quần, Suit, dùng bộ ảnh ImageGen riêng 1024 × 1536 tại `assets/home-category-*-v1.png`, khác ảnh trên trang danh mục. Bộ ảnh và prompt đầy đủ nằm trong `assets/home-category-banner-notes.md`. Banner tải ảnh khi gần vùng hiển thị và xếp thành một cột trên điện thoại. Nội dung banner và chân trang nằm trong `storefront-content.js`.

Chân trang cửa hàng hiển thị thương hiệu Freedom, thông điệp thời trang nam mạnh mẽ mang đến sự tự do cho quý ông, trụ sở số 69 phố Tràng Tiền, TP. Hà Nội, điện thoại `0123699999` và email `freeshion69trangtien@gmail.com`. Số điện thoại và email có liên kết `tel:` và `mailto:`.

```sh
npm run check
npm test
```

`npm test` kiểm tra phân quyền và CRUD sản phẩm trên frontend: biểu mẫu sửa đầy đủ trường, thêm/xem, xác nhận hoặc hủy xóa, ẩn/khôi phục sản phẩm, tạo danh mục, lỗi API và escape nội dung. Kiểm thử frontend dùng DOM/API mô phỏng, không thay thế trình duyệt thật.

Backend kiểm thử xác thực, phân quyền, CRUD, ảnh, size/tồn, checkout chọn dòng và xử lý đơn. Chạy `python -m pytest -q` tại `freedom_backend`: **58 passed, 11 skipped**. Ba bài PostgreSQL chạy riêng bằng `python -m app.verify_postgres_checkout` kiểm tra DB thật và xác nhận đồng thời trên DB tạm. Frontend cũng kiểm thử giỏ chọn dòng, xác nhận người nhận, đặt trước, thử lại cùng khóa và theo dõi trạng thái. `verify-gallery.mjs` kiểm tra tự chạy, hướng trượt, lặp vòng và thu hồi timer. Không chạy kiểm thử xóa dữ liệu trên DB bán hàng.

Chưa kiểm chứng hiển thị desktop/mobile bằng trình duyệt tự động hóa hoặc tích hợp với PostgreSQL đang chạy. Ảnh bản lưu có độ phân giải thấp. Các giới hạn chức năng nêu trên vẫn cần hoàn thiện trước khi coi đây là toàn bộ hệ thống bán hàng đã nghiệm thu.


### Chọn cách xóa sản phẩm

Ở quản lý sản phẩm, bấm **Xóa** và chọn cách xóa trong hộp xác nhận. Mặc định **Xóa mềm** để lưu trữ và giữ lịch sử. Admin có thêm **Xóa cứng** (vĩnh viễn); backend sẽ từ chối nếu còn tồn kho, hàng đang giữ hoặc dữ liệu tham chiếu. Để xóa cứng sản phẩm đã lưu trữ, chọn bộ lọc **Đã xóa / lưu trữ**, rồi bấm **Xóa** ở dòng sản phẩm. Khôi phục sản phẩm xóa mềm bằng **Sửa**, đổi trạng thái về Bản nháp hoặc Đang bán.
