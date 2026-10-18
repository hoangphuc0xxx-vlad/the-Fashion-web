import { galleryHtml } from './gallery.js';
import { productImageUrl } from './products.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = value => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(value || 0));
const time = value => value ? new Date(value).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'short', timeStyle: 'short' }) : '';
const aliases = { confirmed: 'packing', preparing: 'packing', shipped: 'shipping' };
export const orderStatuses = {
  pending: ['Chờ cửa hàng xác nhận', 'neutral'], packing: ['Đang đóng gói', 'blue'],
  shipping: ['Đang vận chuyển', 'yellow'], delivered: ['Đã giao', 'green'],
  failed: ['Giao thất bại', 'red'], cancelled: ['Đã hủy', 'red'], returned: ['Đã hoàn trả', 'red'],
};
export function orderStatusBadge(order) {
  const status = aliases[order.status] || order.status;
  const [label, color] = orderStatuses[status] || [status, 'neutral'];
  return `<span class="order-status status-${color}">${esc(order.fulfillment_method === 'pickup' && status === 'delivered' ? 'Đã lấy tại cửa hàng' : label)}</span>`;
}
export function orderNextStatuses(order) {
  const current = aliases[order.status] || order.status;
  if (order.fulfillment_method === 'pickup') return current === 'pending' ? ['packing', 'cancelled'] : current === 'packing' ? ['delivered', 'cancelled'] : [];
  return ({ pending: ['packing', 'cancelled'], packing: ['shipping', 'cancelled'], shipping: ['delivered', 'failed'], failed: ['shipping', 'cancelled'] })[current] || [];
}
export function orderActionLabel(order, next) {
  if (next === 'packing') return 'Xác nhận — Đang đóng gói';
  if (order.fulfillment_method === 'pickup' && next === 'delivered') return 'Xác nhận khách đã lấy hàng';
  return { shipping: 'Đang vận chuyển', delivered: 'Đã giao', failed: 'Giao thất bại', cancelled: 'Hủy đơn / hàng đã hoàn về kho' }[next];
}
export function purchaseHtml(product) {
  const options = (product.product_variants || []).filter(v => v.is_active && Number(v.stock_quantity) > Number(v.reserved_quantity));
  return `${galleryHtml(product) || '<p>Sản phẩm chưa có ảnh.</p>'}<strong id="purchase-price" class="detail-price">${money(options[0]?.price ?? product.base_price)}</strong><p>${esc(product.description || 'Thiết kế từ Freedom Menswear.')}</p><form id="add-cart-form" data-id="${product.id}"><label>Chọn size / màu<select name="variant_id" id="purchase-variant" required ${!options.length ? 'disabled' : ''}>${options.map(v => `<option value="${v.id}" data-price="${v.price}" data-stock="${v.stock_quantity - v.reserved_quantity}">Size ${esc(v.size_name || v.size_id)} · ${esc(v.color_name || '')} · ${money(v.price)} · Còn ${v.stock_quantity - v.reserved_quantity}</option>`).join('')}</select></label><label>Số lượng<input id="purchase-quantity" name="quantity" type="number" min="1" max="${Math.min(999, options[0] ? options[0].stock_quantity - options[0].reserved_quantity : 1)}" step="1" value="1" required></label><p class="form-error" role="alert"></p><button type="submit" class="ad-btn ad-btn-primary" ${!options.length ? 'disabled' : ''}>${options.length ? 'Thêm vào giỏ hàng' : 'Tạm hết hàng'}</button><p class="ad-form-note">Chọn sản phẩm trong giỏ hàng để đặt giao hàng hoặc đặt trước lấy tại cửa hàng.</p></form>`;
}
export function cartHtml(items) {
  if (!items.length) return '<div class="cart-empty"><p>Giỏ hàng của bạn đang trống.</p><button class="ad-btn" data-action="close">Tiếp tục mua sắm</button></div>';
  return `<div class="cart-dialog"><p>Chọn sản phẩm muốn đặt. Những sản phẩm chưa chọn sẽ được giữ trong giỏ.</p><div class="cart-lines">${items.map(item => {
    const available = item.is_active && item.product_status === 'active' && item.stock_quantity - item.reserved_quantity >= item.quantity;
    const image = productImageUrl(item);
    return `<article class="cart-line"><label class="cart-select"><input type="checkbox" data-cart-select="${item.variant_id}" aria-label="Chọn ${esc(item.product_name)}, size ${esc(item.size_name)}" ${!available ? 'disabled' : ''}></label>${image ? `<img src="${esc(image)}" alt="${esc(item.product_name)}">` : '<div class="cart-image-placeholder"></div>'}<div class="cart-line-info"><strong>${esc(item.product_name)}</strong><p>Size ${esc(item.size_name)} · ${esc(item.color_name)}</p><span>${money(item.price)}</span><label class="cart-quantity">Số lượng<input type="number" data-cart-quantity="${item.variant_id}" min="1" max="${Math.min(999, Math.max(1, item.stock_quantity - item.reserved_quantity))}" step="1" value="${item.quantity}" aria-label="Số lượng ${esc(item.product_name)}"></label>${!available ? '<p class="form-error">Tạm hết hàng hoặc số lượng không còn đủ.</p>' : ''}<button class="text-action" data-remove-api="${item.variant_id}">Xóa</button></div><strong class="cart-line-total">${money(Number(item.price) * item.quantity)}</strong></article>`;
  }).join('')}</div><div class="cart-bottom"><div class="cart-summary"><span id="cart-selection-count">Chưa chọn sản phẩm</span><strong id="cart-selection-total">${money(0)}</strong></div><div id="cart-checkout-actions" class="cart-checkout-actions" hidden><button class="ad-btn" data-action="checkout-pickup">Đặt trước và lấy tại cửa hàng</button><button class="ad-btn ad-btn-primary" data-action="checkout-delivery">Đặt hàng</button></div></div></div>`;
}
export function checkoutHtml(items, method, user, config) {
  const pickup = method === 'pickup', subtotal = items.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0);
  const fee = pickup ? 0 : Number(config.shipping_fee);
  const vietnamToday = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  return `<form id="checkout-form" data-method="${method}"><div class="checkout-items">${items.map(item => `<p><strong>${esc(item.product_name)}</strong> · Size ${esc(item.size_name)} · ${esc(item.color_name)} × ${item.quantity}<span>${money(item.price * item.quantity)}</span></p>`).join('')}</div><div class="checkout-totals"><p>Tiền hàng <strong>${money(subtotal)}</strong></p><p>${pickup ? 'Lấy tại cửa hàng' : 'Phí giao hàng'} <strong>${money(fee)}</strong></p><p>Tổng tiền dự kiến <strong>${money(subtotal + fee)}</strong></p></div><label>Họ tên người ${pickup ? 'đến lấy' : 'nhận'}<input name="recipient_name" autocomplete="name" maxlength="150" value="${esc(user?.full_name)}" required></label><label>Số điện thoại<input name="recipient_phone" type="tel" autocomplete="tel" pattern="[+0-9][0-9 ()-]{7,19}" minlength="8" maxlength="20" value="${esc(user?.phone)}" required></label>${pickup ? `<label>Email<input name="recipient_email" type="email" autocomplete="email" maxlength="190" value="${esc(user?.email)}" required></label><label>Ngày đến lấy<input name="pickup_date" type="date" min="${vietnamToday}" required></label><div class="form-grid"><label>Giờ đến lấy (từ)<input name="pickup_from" type="time" required></label><label>Đến khoảng<input name="pickup_to" type="time" required></label></div><p class="ad-form-note">Đến lấy tại ${esc(config.store_address)}. Chọn khoảng 15 phút đến 8 giờ trong cùng ngày, giờ Việt Nam. Thanh toán khi lấy hàng.</p>` : '<label>Địa chỉ nhận hàng đầy đủ<textarea name="shipping_address" autocomplete="street-address" rows="3" minlength="5" maxlength="1000" placeholder="Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành phố" required></textarea></label><p class="ad-form-note">Thanh toán khi nhận hàng (COD). Cửa hàng xác nhận và tự sắp xếp vận chuyển.</p>'}<label>Ghi chú<textarea name="customer_note" maxlength="2000" rows="2"></textarea></label><p class="form-error" role="alert"></p><div class="checkout-submit"><button type="button" class="ad-btn" data-action="back-to-cart">Quay lại giỏ</button><button type="submit" class="ad-btn ad-btn-primary">${pickup ? 'Đặt trước' : 'Xác nhận đặt hàng'}</button></div></form>`;
}
export function orderInfoHtml(order) {
  return `<div class="order-info">${orderStatusBadge(order)}<dl class="record-details">${[['Mã đơn', order.order_code], ['Hình thức', order.fulfillment_method === 'pickup' ? 'Đặt trước, lấy tại cửa hàng' : 'Giao hàng tận nơi'], ['Người nhận', order.recipient_name], ['Điện thoại', order.recipient_phone], ['Email', order.recipient_email], [order.fulfillment_method === 'pickup' ? 'Nơi lấy hàng' : 'Địa chỉ', order.shipping_address], ['Đến lấy từ', time(order.pickup_start)], ['Đến khoảng', time(order.pickup_end)], ['Ghi chú', order.customer_note]].filter(([, value]) => value).map(([label, value]) => `<div><dt>${label}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><div class="order-items">${(order.order_items || []).map(item => `<div class="detail-line"><span>${esc(item.product_name_snapshot)} · Size ${esc(item.size_snapshot)} · ${esc(item.color_snapshot)} × ${item.quantity}</span><strong>${money(item.unit_price * item.quantity)}</strong></div>`).join('')}</div><div class="checkout-totals"><p>Tiền hàng <strong>${money(order.subtotal)}</strong></p><p>Phí giao hàng <strong>${money(order.shipping_fee)}</strong></p><p>Giảm giá <strong>${money(order.discount_amount)}</strong></p><p>Tổng thanh toán <strong>${money(order.total_amount)}</strong></p></div>${order.order_status_histories?.length ? `<details class="order-history"><summary>Lịch sử đơn hàng</summary>${order.order_status_histories.map(entry => `<p>${time(entry.created_at)} · ${orderStatusBadge({ ...order, status: entry.new_status })}</p>`).join('')}</details>` : ''}</div>`;
}
export function customerOrdersHtml(orders) {
  return `<div class="customer-orders"><button class="text-action" data-action="my-orders">Làm mới trạng thái</button>${orders.map(order => `<button class="customer-order" data-my-order="${order.id}"><strong>${esc(order.order_code)}</strong>${orderStatusBadge(order)}<span>${order.fulfillment_method === 'pickup' ? 'Lấy tại cửa hàng' : 'Giao tận nơi'} · ${time(order.placed_at)}</span><b>${money(order.total_amount)}</b></button>`).join('') || '<p>Bạn chưa có đơn hàng.</p>'}</div>`;
}
