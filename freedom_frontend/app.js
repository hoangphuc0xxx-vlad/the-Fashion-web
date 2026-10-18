import { api } from './api.js';
import { endpoints, heroImage } from './data.js';
import { can, canVisit, isOperator, firstAdminRoute, routePermissions } from './access.js';
import { productEditorHtml, productDetailsHtml, deleteProductHtml, productPayload, productStatuses, slugify, productImageUrl, productImagePreviewHtml, validateProductImage, variantRowHtml, readProductVariants } from './products.js';
import { categoryNavHtml, categoryFiltersHtml, categoryPath, categoryHref, categoryFormHtml } from './categories.js';
import { categoryBannerHtml } from './category-banners.js';
import { homeCategoryBannersHtml, storeFooterHtml } from './storefront-content.js';
import { galleryHtml, mountGalleries, destroyGalleries } from './gallery.js';
import { purchaseHtml, cartHtml, checkoutHtml, customerOrdersHtml, orderInfoHtml, orderStatusBadge, orderNextStatuses, orderActionLabel } from './checkout-ui.js';

const $ = (s, root = document) => root.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = v => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(v || 0));
const date = v => v ? new Date(v).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '—';
const labels = { pending: 'Chờ xác nhận', confirmed: 'Đã xác nhận', preparing: 'Đang xử lý', shipped: 'Đang giao', delivered: 'Hoàn thành', cancelled: 'Đã hủy', active: 'Đang hoạt động', draft: 'Bản nháp', archived: 'Đã lưu trữ', open: 'Đang mở', in_progress: 'Đang hỗ trợ', closed: 'Đã đóng', approved: 'Đã duyệt', hidden: 'Đã ẩn', requested: 'Yêu cầu mới', received: 'Đã tiếp nhận', rejected: 'Từ chối', refunded: 'Đã hoàn tiền', published: 'Đã xuất bản', blocked: 'Đã khóa' };
Object.assign(labels, { packing: 'Đang đóng gói', shipping: 'Đang vận chuyển', failed: 'Giao thất bại', delivered: 'Đã giao' });
const badge = s => `<span class="ad-badge ${['delivered', 'active', 'approved', 'published'].includes(s) ? 'green' : s === 'shipped' ? 'blue' : s === 'preparing' ? 'purple' : ''}"><i></i>${esc(labels[s] || s)}</span>`;
const iconPaths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  bag: '<path d="M5 7h14l2 14H3L5 7Z"/><path d="M8 8V6a4 4 0 0 1 8 0v2"/>',
  box: '<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10v9M3 8l9 5 9-5M7 5l10 6"/>',
  users: '<circle cx="9" cy="8" r="4"/><path d="M2 21v-3a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v3M17 4a4 4 0 0 1 0 8M19 15a4 4 0 0 1 3 4v2"/>',
  chart: '<path d="M3 3v18h18M7 15l4-5 4 3 6-8"/>',
  tag: '<path d="M3 3h8l10 10-8 8L3 11V3Z"/><circle cx="7" cy="7" r="1"/>',
  truck: '<path d="M3 5h12v12H3zM15 10h4l3 4v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  star: '<path d="m12 3 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-6Z"/>',
  file: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  settings: '<circle cx="12" cy="12" r="4"/><path d="m12 2 2 3 4-1 1 4 3 2-2 4 1 4-4 1-3 3-3-2-4 1-1-4-3-3 2-3-1-4 4-1 2-4Z"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="10" cy="10" r="7"/><path d="m16 16 5 5"/>',
  bell: '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3ZM10 21h4"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>', close: '<path d="m6 6 12 12M6 18 18 6"/>',
  wallet: '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 8h18M15 12h6v5h-6z"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5M12 17h.01"/>',
};
const icon = (name, size = 18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`;
const navGroups = [
  ['TỔNG QUAN', [['dashboard', 'Tổng quan', 'grid']]],
  ['QUẢN LÝ CỬA HÀNG', [['orders', 'Đơn hàng', 'bag'], ['products', 'Sản phẩm', 'box'], ['categories', 'Danh mục & thương hiệu', 'file'], ['inventory', 'Quản lý kho', 'box'], ['customers', 'Khách hàng', 'users'], ['shipping', 'Thanh toán & vận chuyển', 'truck']]],
  ['MARKETING & NỘI DUNG', [['coupons', 'Voucher & khuyến mãi', 'tag'], ['reviews', 'Đánh giá sản phẩm', 'star'], ['banners', 'Banner & bài viết', 'file']]],
  ['VẬN HÀNH', [['returns', 'Đổi trả & hoàn tiền', 'wallet'], ['support', 'Hỗ trợ khách hàng', 'help'], ['users', 'Nhân viên & phân quyền', 'users'], ['audit', 'Nhật ký hoạt động', 'chart']]],
];
const titles = Object.fromEntries(navGroups.flatMap(([, items]) => items.map(([key, title]) => [key, title])));
Object.assign(titles, { settings: 'Trạng thái hệ thống', brands: 'Thương hiệu', posts: 'Bài viết' });
let route, rows = [], dashboardOrders = [], query = '', statusFilter = '', period = 'month', offset = 0, loadingId = 0, shopCategory = '', shopSort = 'newest';
let profile = null;
let productDraft = null;
let productImageFiles = [], productImagePreviews = [];
function clearProductImage() {
  productImagePreviews.forEach(url => URL.revokeObjectURL(url));
  productImageFiles = []; productImagePreviews = [];
}
function pendingProductImage() { return productImageFiles.length ? productImageFiles.map((file, index) => ({ url: productImagePreviews[index], name: file.name })) : null; }
let shopCategories = [], shopOffset = 0, shopHasMore = false, storeCategorySlug = '', storeRequest = 0, storeSearchTimer;
let toastTimer;
let cartItems = [], cartSelected = new Set(), checkoutMethod = 'delivery', checkoutKey = '', checkoutQuote = 0, pendingPurchase = null;
function updateProductStockTotal() { $('#product-stock-total').textContent = [...document.querySelectorAll('[data-variant-stock]')].reduce((sum, input) => sum + Math.max(0, Number(input.value) || 0), 0); }
let customerOrderId = null, customerOrdersOpen = false, orderPollBusy = false;
function updateCartCount(items) { const count = items.reduce((sum, item) => sum + Number(item.quantity), 0); if ($('#cart-count')) { $('#cart-count').textContent = count; $('#cart-count').setAttribute?.('aria-label', `${count} sản phẩm trong giỏ`); } }
function selectedCartItems() { return cartItems.filter(item => cartSelected.has(Number(item.variant_id))); }
function updateCartSelection() {
  const selected = selectedCartItems();
  $('#cart-checkout-actions').hidden = !selected.length;
  $('#cart-selection-count').textContent = selected.length ? `Đã chọn ${selected.length} sản phẩm (${selected.reduce((sum, item) => sum + Number(item.quantity), 0)} món)` : 'Chưa chọn sản phẩm';
  $('#cart-selection-total').textContent = money(selected.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0));
}
function toast(message) { $('#toast').textContent = message; $('#toast').className = 'show'; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').className = '', 4500); }
function modal(title, content) { customerOrderId = null; customerOrdersOpen = false; destroyGalleries($('#modal')); $('#modal').innerHTML = `<div class="dialog-heading"><h2 id="dialog-title">${esc(title)}</h2><button class="icon-btn" data-action="close" aria-label="Đóng">${icon('close')}</button></div><div class="ad-dialog-body">${content}</div>`; $('#modal').showModal(); mountGalleries($('#modal')); }
const btn = (text, action, primary = false, glyph = '') => `<button class="ad-btn ${primary ? 'ad-btn-primary' : ''}" data-action="${action}">${glyph ? icon(glyph, 15) : ''}${text}</button>`;
function requireUiPermission(permission) {
  if (!can(profile, permission)) throw new Error('Bạn không có quyền thực hiện thao tác này.');
}
function hideUnavailableControls() {
  document.querySelectorAll('[data-route], [data-order-filter]').forEach(el => {
    const target = el.dataset.route || 'orders';
    if (!canVisit(profile, target)) el.remove();
  });
}
function accessPage(message = '', login = false) {
  rows = []; dashboardOrders = [];
  if ($('#modal').open) $('#modal').close();
  document.title = login ? 'Freedom — Đăng nhập quản trị' : 'Freedom — Không có quyền truy cập';
  $('#app').innerHTML = `<main class="access-page"><a class="store-logo" href="#/store">freedom<sup>®</sup></a><section class="access-card"><span class="store-eyebrow">FREEDOM WORKSPACE</span><h1>${login ? 'Đăng nhập quản trị' : 'Không có quyền truy cập'}</h1><p>${esc(message || (login ? 'Khu vực dành cho quản trị viên và nhân viên được cấp quyền.' : 'Tài khoản của bạn không được phép truy cập khu vực này.'))}</p>${login ? authForm(false, true) : ''}<div class="inline-actions"><a class="ad-btn" href="#/store">Về cửa hàng</a>${!login && profile ? btn('Đăng xuất', 'logout') : ''}${!login && firstAdminRoute(profile) ? `<a class="ad-btn" href="#/${firstAdminRoute(profile)}">Mở mục được cấp quyền</a>` : ''}</div></section></main>`;
}
async function verifyOperator(id) {
  $('#app').innerHTML = '<main class="access-page" role="status">Đang xác minh quyền truy cập…</main>';
  rows = []; dashboardOrders = [];
  if (!sessionStorage.getItem('freedom-token')) { profile = null; accessPage('', true); return false; }
  try {
    const current = await api('/auth/me');
    if (id !== loadingId) return false;
    profile = current;
    if (!isOperator(profile)) { accessPage(); return false; }
    return true;
  } catch (e) {
    if (id === loadingId) accessPage(e.status === 401 ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.' : e.message, e.status === 401);
    return false;
  }
}
function shell() {
  const user = profile.full_name;
  const visibleGroups = navGroups.map(([title, items]) => [title, items.filter(([key]) => canVisit(profile, key))]).filter(([, items]) => items.length);
  $('#app').innerHTML = `<div class="ad-app"><div class="nav-shade" data-action="menu"></div>
    <aside class="ad-sidebar"><a class="ad-brand" href="#/admin">freedom<span>®</span><small>ADMIN WORKSPACE</small></a>
      <div class="ad-shop"><span class="ad-shop-icon">${icon('bag')}</span><div><strong>Freedom Menswear</strong><small><i></i>Made for better everyday.</small></div></div>
      <nav aria-label="Điều hướng quản trị">${visibleGroups.map(([title, items]) => `<div class="ad-nav-group"><p>${title}</p>${items.map(([key, name, glyph]) => `<button data-route="${key}" class="${route === key ? 'selected' : ''}" ${route === key ? 'aria-current="page"' : ''}>${icon(glyph)}<span>${name}</span></button>`).join('')}</div>`).join('')}</nav>
      <div class="ad-sidebar-bottom">${canVisit(profile, 'settings') ? `<button data-route="settings">${icon('settings')} Hệ thống</button>` : ''}<button data-action="help">${icon('help')} Trung tâm trợ giúp</button><button class="ad-profile" data-action="login"><span class="ad-avatar admin">${esc(user.split(' ').map(x => x[0]).slice(-2).join(''))}</span><span><strong>${esc(user)}</strong><small>${profile.role === 'admin' ? 'Quản trị viên' : 'Nhân viên'}</small></span>${icon('arrow', 15)}</button></div>
    </aside><div class="ad-workspace"><header class="ad-topbar"><div class="ad-crumb"><button class="ad-mobile-toggle icon-btn" data-action="menu" aria-label="Mở menu">${icon('menu')}</button><span>Không gian quản trị</span><span>/</span><strong>${esc(titles[route])}</strong></div><div class="ad-top-actions"><a class="ad-store-link" href="#/store">Xem cửa hàng ${icon('arrow', 14)}</a><span class="ad-top-divider"></span><button data-action="login" class="ad-avatar admin" aria-label="Tài khoản">${esc(user[0])}</button></div></header>
      <main class="ad-main" id="main"><div id="content"></div><footer class="ad-footer"><span>© 2026 Freedom. All rights reserved.</span><span>Made for better everyday. <i></i> Phiên bản 1.0</span></footer></main></div></div>`;
}
function heading(title, subtitle, actions = '') { return `<div class="ad-page-heading"><div><div class="ad-eyebrow">FREEDOM ADMIN / ${esc(route.toUpperCase())}</div><h1>${title}</h1><p>${subtitle}</p></div><div class="ad-heading-actions">${actions}</div></div>`; }
function fail(error) { $('#content').innerHTML = `${heading(titles[route] || 'Freedom', 'Không tải được dữ liệu.')}<div class="ad-card ad-empty">${icon('help', 32)}<h3>Cần kiểm tra kết nối</h3><p>${esc(error.message)}</p><div class="inline-actions">${btn('Thử lại', 'reload')}${btn('Đăng nhập', 'login', true)}${btn('Cài đặt', 'settings')}</div></div>`; }
function loading() { $('#content').innerHTML = '<div class="ad-card ad-empty" role="status"><span class="loader"></span><p>Đang tải dữ liệu…</p></div>'; }
async function getRows(key) { return api(`${endpoints[key]}?limit=100&offset=${offset}`); }
function timeRange() {
  const end = new Date(), start = new Date(end);
  if (period === 'week') start.setDate(end.getDate() - 6);
  else { start.setDate(1); if (period === 'previous') { end.setDate(1); end.setHours(0, 0, 0, 0); start.setMonth(start.getMonth() - 1); } }
  start.setHours(0, 0, 0, 0);
  return { start, end };
}
function inPeriod(o) { const { start, end } = timeRange(); const at = new Date(o.placed_at); return at >= start && at <= end; }
async function render() {
  destroyGalleries($('#app'));
  const id = ++loadingId;
  const previousRoute = route;
  const [hashRoute, hashQuery = ''] = location.hash.replace(/^#\//, '').split('?');
  route = hashRoute || 'store';
  document.body?.setAttribute('data-view', route === 'store' ? 'store' : 'admin');
  storeCategorySlug = route === 'store' ? new URLSearchParams(hashQuery).get('category') || '' : '';
  if (route === 'products' && previousRoute !== 'products') statusFilter = 'not_archived';
  if (route === 'store') { await storefront(id); return; }
  if (!titles[route] && !['admin', 'admin/login'].includes(route)) { location.hash = '#/store'; return; }
  if (!(await verifyOperator(id))) return;
  if (route === 'admin' || route === 'admin/login') {
    const first = firstAdminRoute(profile);
    if (first) location.hash = '#/' + first;
    else accessPage('Tài khoản nhân viên chưa được cấp quyền quản lý nào.');
    return;
  }
  if (!canVisit(profile, route)) { accessPage(); return; }
  shell();
  if (route === 'settings') { settingsView(); return; }
  loading();
  try {
    if (route === 'dashboard') {
      const { start, end } = timeRange();
      const results = await Promise.all([can(profile, 'orders.manage') ? getRows('orders') : Promise.resolve([]), api(`/admin/dashboard?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`)]);
      if (id !== loadingId) return;
      dashboardOrders = results[0].filter(inPeriod); dashboard(results[1]);
    } else {
      const records = await getRows(route === 'shipping' ? 'orders' : route);
      if (id !== loadingId) return;
      rows = records;
      management();
    }
    hideUnavailableControls();
  } catch (e) { if (id === loadingId) { if (e.status === 401 || e.status === 403) accessPage(e.message, e.status === 401); else fail(e); } }
}
function chart(data) {
  const { start, end } = timeRange();
  const days = Math.max(1, Math.ceil((end - start) / 86400000));
  const values = Array.from({ length: days }, (_, i) => data.filter(o => o.status === 'delivered' && Math.floor((new Date(o.placed_at) - start) / 86400000) === i).reduce((s, o) => s + Number(o.total_amount), 0));
  const max = Math.max(...values, 1000000) * 1.15;
  const points = values.map((v, i) => `${45 + i / Math.max(1, days - 1) * 660},${170 - v / max * 150}`);
  return `<svg viewBox="0 0 730 210" width="100%" height="100%" role="img" aria-label="Doanh thu các đơn đã giao theo ngày"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#8da474" stop-opacity=".24"/><stop offset="1" stop-color="#8da474" stop-opacity="0"/></linearGradient></defs>${[0, 1, 2, 3].map(i => `<path d="M45 ${20 + i * 50}H710" stroke="#edf0e8" stroke-dasharray="4 4"/><text x="0" y="${24 + i * 50}" fill="#929b86" font-size="9">${(max * (1 - i / 3) / 1000000).toFixed(1)} tr</text>`).join('')}<path d="M45 170 L${points.join(' L')} L705 170Z" fill="url(#fill)"/><polyline points="${points.join(' ')}" fill="none" stroke="#70865a" stroke-width="2.3" stroke-linejoin="round"/>${values.map((v, i) => v ? `<circle cx="${45 + i / Math.max(1, days - 1) * 660}" cy="${170 - v / max * 150}" r="3" fill="#70865a"><title>${money(v)}</title></circle>` : '').join('')}${[0, .25, .5, .75, 1].map(f => { const d = new Date(start); d.setDate(d.getDate() + Math.floor((days - 1) * f)); return `<text x="${45 + f * 660}" y="200" text-anchor="middle" font-size="9" fill="#929b86">${d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })}</text>`; }).join('')}</svg>`;
}
function dashboard(summary) {
  const data = dashboardOrders, delivered = data.filter(o => o.status === 'delivered');
  const revenue = summary?.delivered_gross_revenue ?? delivered.reduce((s, o) => s + Number(o.total_amount), 0);
  const counts = [['Hoàn thành', 'delivered'], ['Đang giao', 'shipping'], ['Đang xử lý', 'pending'], ['Đã hủy', 'cancelled']].map(([name, status]) => ({ name, status, count: data.filter(o => status === 'pending' ? ['pending', 'confirmed', 'preparing', 'packing'].includes(o.status) : (o.status === status || status === 'shipping' && o.status === 'shipped')).length }));
  let angle = 0; const stops = counts.map((c, i) => { const from = angle; angle += c.count / (data.length || 1) * 100; return `${['#61764e', '#9cac85', '#d9dfcb', '#eaece5'][i]} ${from}% ${angle}%`; }).join(',');
  const pending = data.filter(o => o.status === 'pending').length;
  $('#content').innerHTML = `${heading('Tổng quan kinh doanh', `Chào ${esc(profile.full_name)}, cùng xem cửa hàng của bạn hôm nay thế nào nhé.`, btn('Xuất báo cáo', 'export', false, 'download') + (can(profile, 'catalog.manage') ? btn('Thêm sản phẩm', 'new-product', true, 'plus') : ''))}<div class="ad-overview-bar"><div class="ad-section-tabs"><button class="active" data-action="overview">Tổng quan</button><button data-route="audit">Hoạt động gần đây</button></div><div class="ad-period">${icon('file', 13)}<select id="period" aria-label="Khoảng thời gian"><option value="month" ${period === 'month' ? 'selected' : ''}>Tháng này</option><option value="previous" ${period === 'previous' ? 'selected' : ''}>Tháng trước</option><option value="week" ${period === 'week' ? 'selected' : ''}>7 ngày qua</option></select><span>${timeRange().start.toLocaleDateString('vi-VN')} – ${timeRange().end.toLocaleDateString('vi-VN')}</span></div></div><div class="ad-stats">${[['Doanh thu đơn đã giao', money(revenue), 'wallet', 'Tổng tiền đơn đã giao trong kỳ'], ['Tổng đơn hàng', summary?.orders ?? data.length, 'bag', 'Đơn được đặt trong kỳ'], ['Tổng khách hàng', summary?.customers_total ?? 0, 'users', 'Tất cả khách hàng của cửa hàng'], ['Đơn hoàn thành', delivered.length, 'box', 'Trong tối đa 100 đơn gần nhất']].map(([title, value, glyph, note]) => `<article class="ad-stat"><div class="ad-stat-title">${title}<span>${icon(glyph, 16)}</span></div><strong>${value}</strong><div class="stat-note">${note}</div></article>`).join('')}</div><div class="ad-analytics"><section class="ad-card"><div class="ad-card-heading"><div><h2>Doanh thu bán hàng</h2><p>Đơn đã giao · tối đa 100 đơn gần nhất trong kỳ</p></div>${icon('chart', 16)}</div><div class="ad-revenue-summary"><strong>${money(delivered.reduce((s, o) => s + Number(o.total_amount), 0))}</strong><div class="ad-legend"><span><i></i> Doanh thu theo ngày</span></div></div><div class="ad-chart">${chart(data)}</div></section><section class="ad-card ad-order-summary"><div class="ad-card-heading"><div><h2>Trạng thái đơn hàng</h2><p>${data.length} đơn đã tải trong kỳ</p></div></div><div class="ad-donut" style="background:${data.length ? `conic-gradient(${stops})` : '#eaece5'}"><div><strong>${data.length}</strong><small>Tổng đơn hàng</small></div></div><div class="ad-donut-legend">${counts.map((c, i) => `<button data-order-filter="${c.status}"><i class="donut-color-${i}"></i><span>${c.name}</span><strong>${c.count}</strong><small>${(c.count / (data.length || 1) * 100).toFixed(1)}%</small></button>`).join('')}</div></section></div><div class="ad-attention">${icon('bell', 16)}<strong>Cần bạn xử lý</strong><button data-order-filter="pending"><b>${pending}</b> đơn chờ xác nhận ${icon('arrow', 12)}</button><span class="ad-attention-divider"></span><button data-route="returns">Yêu cầu đổi trả ${icon('arrow', 12)}</button><span class="ad-attention-divider"></span><button data-route="inventory">Kiểm tra tồn kho ${icon('arrow', 12)}</button><button class="ad-attention-all" data-route="orders">Xem tất cả ${icon('arrow', 12)}</button></div><section class="ad-card ad-recent"><div class="ad-card-heading"><div><h2>Đơn hàng gần đây <span class="ad-count">${data.length}</span></h2><p>Những đơn hàng mới nhất từ cửa hàng của bạn</p></div><button class="ad-view-all" data-route="orders">Tất cả đơn hàng ${icon('arrow', 13)}</button></div>${orderTable(data.slice(0, 5))}</section><div class="ad-bottom-grid"><section class="ad-card"><div class="ad-card-heading"><div><h2>Sản phẩm bán chạy</h2><p>Từ các đơn đã giao trong kỳ</p></div><button class="ad-view-all" data-route="products">Xem tất cả ${icon('arrow', 12)}</button></div>${summary ? (summary.top_products.length ? summary.top_products.map((p, i) => `<div class="ad-record"><span class="ad-rank">0${i + 1}</span><strong>${esc(p.product_name_snapshot)}</strong><span>${p.quantity} đã bán</span></div>`).join('') : '<div class="small-empty">Chưa có sản phẩm bán trong kỳ.</div>') : ''}</section><section class="ad-card"><div class="ad-card-heading"><div><h2>Một nơi cho mọi hoạt động</h2><p>Quản lý cửa hàng với Freedom Workspace</p></div></div>${[['orders', 'bag', 'Theo dõi đơn hàng', 'Xác nhận, chuẩn bị và giao hàng'], ['products', 'box', 'Chăm chút sản phẩm', 'Thông tin, chất liệu và giá bán'], ['support', 'help', 'Kết nối với khách hàng', 'Tiếp nhận và theo dõi yêu cầu hỗ trợ']].map(([key, glyph, title, text]) => `<button class="ad-timeline timeline-link" data-route="${key}"><span>${icon(glyph, 14)}</span><div><strong>${title}</strong><p>${text}</p></div>${icon('arrow', 14)}</button>`).join('')}</section></div>`;
}
function orderTable(data) {
  return `<div class="ad-table-scroll"><table class="ad-table"><thead><tr><th>Mã đơn hàng</th><th>Khách hàng</th><th>Ngày đặt</th><th>Tổng tiền</th><th>Phương thức</th><th>Trạng thái</th><th></th></tr></thead><tbody>${data.map(o => `<tr><td><button class="ad-order-id" data-order="${o.id}">#${esc(o.order_code)}</button></td><td><div class="ad-person"><span class="ad-avatar">${esc((o.recipient_name || '?').split(' ').slice(-2).map(n => n[0]).join(''))}</span><div><strong>${esc(o.recipient_name)}</strong><small>${esc(o.recipient_phone)}</small></div></div></td><td class="ad-date">${date(o.placed_at)}</td><td><strong>${money(o.total_amount)}</strong></td><td>${o.fulfillment_method === 'pickup' ? 'Lấy tại cửa hàng' : o.payment_method === 'cod' ? 'COD' : 'Chuyển khoản'}</td><td>${orderStatusBadge(o)}</td><td><button data-order="${o.id}" class="icon-btn" aria-label="Chi tiết đơn ${esc(o.order_code)}">${icon('arrow', 14)}</button></td></tr>`).join('') || '<tr><td colspan="7" class="small-empty">Chưa có đơn hàng phù hợp.</td></tr>'}</tbody></table></div>`;
}
const columns = {
  products: [['name', 'Sản phẩm'], ['base_price', 'Giá bán'], ['material', 'Chất liệu'], ['status', 'Trạng thái']],
  inventory: [['product_name', 'Sản phẩm'], ['size_name', 'Size'], ['color_name', 'Màu'], ['sku', 'Mã SKU'], ['stock_quantity', 'Số lượng trong kho'], ['reserved_quantity', 'Đã giữ'], ['available_quantity', 'Có thể bán']],
  customers: [['full_name', 'Khách hàng'], ['email', 'Email'], ['phone', 'Điện thoại'], ['status', 'Trạng thái']],
  users: [['full_name', 'Họ tên'], ['email', 'Email'], ['role_id', 'ID vai trò'], ['status', 'Trạng thái']],
  categories: [['name', 'Danh mục'], ['slug', 'Đường dẫn'], ['parent_id', 'Danh mục cha'], ['is_active', 'Hoạt động']],
  brands: [['name', 'Thương hiệu'], ['slug', 'Đường dẫn'], ['is_active', 'Hoạt động']],
  coupons: [['code', 'Mã voucher'], ['discount_type', 'Loại giảm'], ['discount_value', 'Mức giảm'], ['used_count', 'Đã sử dụng'], ['is_active', 'Hoạt động']],
  reviews: [['product_id', 'ID sản phẩm'], ['rating', 'Số sao'], ['comment', 'Nhận xét'], ['status', 'Trạng thái']],
  banners: [['title', 'Tiêu đề banner'], ['image_url', 'Đường dẫn ảnh'], ['is_active', 'Hoạt động']],
  posts: [['title', 'Bài viết'], ['slug', 'Đường dẫn'], ['status', 'Trạng thái']],
  returns: [['order_item_id', 'ID dòng đơn hàng'], ['reason', 'Lý do'], ['type', 'Loại yêu cầu'], ['quantity', 'Số lượng'], ['status', 'Trạng thái']],
  support: [['subject', 'Yêu cầu hỗ trợ'], ['user_id', 'ID khách hàng'], ['status', 'Trạng thái']],
  audit: [['action', 'Thao tác'], ['entity_type', 'Đối tượng'], ['entity_id', 'ID đối tượng'], ['user_id', 'ID người dùng'], ['created_at', 'Thời gian']],
};
function filtered() { return rows.filter(r => (!query || JSON.stringify(r).toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi'))) && (!statusFilter || statusFilter === 'not_archived' && r.status !== 'archived' || r.status === statusFilter || statusFilter === 'pending' && ['confirmed', 'preparing', 'packing'].includes(r.status))); }
function statusSelect(statuses) {
  if (route === 'products') return `<select id="status-filter" class="ad-btn" aria-label="Lọc trạng thái sản phẩm"><option value="not_archived" ${statusFilter === 'not_archived' ? 'selected' : ''}>Chưa xóa</option><option value="" ${!statusFilter ? 'selected' : ''}>Tất cả sản phẩm</option>${Object.entries(productStatuses).map(([key, name]) => `<option value="${key}" ${statusFilter === key ? 'selected' : ''}>${name}</option>`).join('')}</select>`;
  return statuses.length ? `<select id="status-filter" class="ad-btn" aria-label="Lọc trạng thái"><option value="">Tất cả trạng thái</option>${statuses.map(s => `<option value="${esc(s)}" ${statusFilter === s ? 'selected' : ''}>${esc(labels[s] || s)}</option>`).join('')}</select>` : '';
}
function recordActions(row) {
  const view = `<button data-record="${row.id}" class="ad-btn" aria-label="Xem chi tiết ${esc(row.name || row.id)}">Xem</button>`;
  if (route !== 'products') return view;
  return `<div class="product-row-actions">${view}<button class="ad-btn" data-edit-product="${row.id}">Sửa</button>${row.status !== 'archived' ? `<button class="ad-btn danger-outline" data-delete-product="${row.id}">Xóa</button>` : ''}</div>`;
}
function management() {
  const statuses = [...new Set(rows.map(r => r.status).filter(Boolean))];
  $('#content').innerHTML = `${heading(esc(titles[route]), 'Theo dõi và quản lý thông tin cửa hàng tại một nơi.', btn('Xuất CSV', 'export', false, 'download') + (route === 'products' ? (can(profile, 'catalog.manage') ? btn('Thêm sản phẩm', 'new-product', true, 'plus') : '') : '') + (route === 'categories' ? btn('Tạo danh mục con', 'new-category', true, 'plus') : ''))}${route === 'categories' ? '<div class="resource-tabs"><a href="#/categories">Danh mục</a><a href="#/brands">Thương hiệu</a></div>' : route === 'banners' ? '<div class="resource-tabs"><a href="#/banners">Banner</a><a href="#/posts">Bài viết</a></div>' : ''}<section class="ad-card"><div class="ad-management-tools"><label class="ad-search">${icon('search', 16)}<input id="search" placeholder="Tìm kiếm trong trang hiện tại…" value="${esc(query)}" aria-label="Tìm kiếm"></label>${statusSelect(statuses)}<span class="ad-demo-label">DỮ LIỆU CỬA HÀNG</span></div><div id="table-content"></div><div class="ad-table-footer"><span id="row-count"></span><div>${btn('Trang trước', 'previous')}<span class="current">${offset / 100 + 1}</span>${btn('Trang sau', 'next')}</div></div></section>`;
  tableContent();
}
function tableContent() {
  const list = filtered();
  $('#row-count').textContent = `Hiển thị ${list.length} / ${rows.length} bản ghi trên trang ${offset / 100 + 1}`;
  if (route === 'orders' || route === 'shipping') { $('#table-content').innerHTML = orderTable(list); return; }
  const fields = columns[route] || [];
  $('#table-content').innerHTML = `<div class="ad-table-scroll"><table class="ad-table"><thead><tr><th>ID</th>${fields.map(([, title]) => `<th>${title}</th>`).join('')}<th></th></tr></thead><tbody>${list.map(r => `<tr><td>#${esc(r.id)}</td>${fields.map(([key]) => `<td>${key === 'status' ? badge(r[key]) : key === 'base_price' ? money(r[key]) : key === 'created_at' ? date(r[key]) : key === 'name' && route === 'products' ? `<div class="ad-product-cell">${productImageUrl(r) ? `<img src="${esc(productImageUrl(r))}" alt="" loading="lazy">` : `<span class="product-placeholder">${icon('box')}</span>`}<div><strong>${esc(r.name)}</strong><small>${esc(r.slug)}</small></div></div>` : typeof r[key] === 'boolean' ? badge(r[key] ? 'active' : 'archived') : key === 'stock_quantity' && r[key] <= r.low_stock_threshold ? `<span class="stock-low">${esc(r[key])} · Sắp hết</span>` : `<span class="cell-text">${esc(r[key] ?? '—')}</span>`}</td>`).join('')}<td>${recordActions(r)}</td></tr>`).join('') || `<tr><td colspan="${fields.length + 2}" class="small-empty">Không có bản ghi phù hợp.</td></tr>`}</tbody></table></div>`;
}
async function orderDetail(id) {
  try {
    requireUiPermission('orders.manage');
    const row = await api(`/staff/orders/${id}`);
    if (!row) throw new Error('Không tìm thấy đơn hàng.');
    modal(`Đơn hàng #${row.order_code}`, `${orderInfoHtml(row)}<div class="order-admin-actions">${orderNextStatuses(row).map(next => `<button type="button" class="ad-btn ${next === 'cancelled' || next === 'failed' ? 'danger-outline' : 'ad-btn-primary'}" data-transition="${row.id}" data-status="${next}">${orderActionLabel(row, next)}</button>`).join('')}</div>${row.fulfillment_method !== 'pickup' && !['pending','cancelled'].includes(row.status) ? `<form id="shipment-form" data-id="${row.id}"><h3>Vận đơn do cửa hàng tạo</h3><label>Đơn vị vận chuyển<input name="carrier" maxlength="100" value="${esc(row.shipments?.[0]?.carrier)}" required></label><label>Mã vận đơn<input name="tracking_number" maxlength="120" value="${esc(row.shipments?.[0]?.tracking_number)}" required></label><p class="form-error" role="alert"></p><button class="ad-btn" type="submit">Lưu vận đơn</button></form>` : ''}<p class="ad-form-note">Chỉ hủy đơn đã giao thất bại sau khi hàng thực tế đã được hoàn về kho. Tồn kho được hoàn lại khi hủy.</p>`);
  } catch (e) { toast(e.message); }
}
function recordDetail(id) {
  requireUiPermission(routePermissions[route]);
  const row = rows.find(r => r.id === Number(id)); if (!row) return;
  modal(`${titles[route]} #${id}`, `<dl class="record-details">${Object.entries(row).map(([key, value]) => `<div><dt>${esc(key)}</dt><dd>${esc(typeof value === 'object' ? JSON.stringify(value) : value)}</dd></div>`).join('')}</dl>${route === 'inventory' && can(profile, 'inventory.manage') ? `<form id="stock-form" data-id="${id}"><label>Số lượng điều chỉnh (+ nhập / − xuất)<input name="quantity_change" type="number" min="-1000000" max="1000000" step="1" required></label><label>Lý do<input name="note" maxlength="500" required></label><button class="ad-btn ad-btn-primary">Lưu điều chỉnh</button></form>` : ''}`);
}
async function newProduct() { productDraft = null; clearProductImage(); await openProductEditor(); }
async function openProductEditor(id = null) {
  try {
    requireUiPermission('catalog.manage');
    const [categories, brands, product] = await Promise.all([api('/catalog/lookups/categories'), api('/catalog/lookups/brands'), id ? api(`/staff/catalog/products/${id}`) : Promise.resolve(productDraft)]);
    requireUiPermission('catalog.manage');
    productDraft = product;
    modal(product?.id ? `Sửa sản phẩm #${product.id}` : 'Thêm sản phẩm mới', productEditorHtml(product, categories, brands, pendingProductImage()));
  } catch (e) { toast(e.message); }
}
async function adminProductDetail(id, deleting = false) {
  try {
    requireUiPermission('catalog.manage');
    const product = await api(`/staff/catalog/products/${id}`);
    requireUiPermission('catalog.manage');
    modal(deleting ? 'Xác nhận xóa sản phẩm' : product.name, deleting ? deleteProductHtml(product) : productDetailsHtml(product));
  } catch (e) { toast(e.message); }
}
async function newProductCategory(returnToProduct = true) {
  try {
    requireUiPermission('catalog.manage');
    const form = returnToProduct ? $('#product-form') : null;
    if (form) productDraft = { ...productDraft, ...Object.fromEntries(new FormData(form)), variants: readProductVariants(form), id: form.dataset.id || undefined };
    const categories = await api('/catalog/lookups/categories');
    requireUiPermission('catalog.manage');
    modal('Tạo danh mục con', categoryFormHtml(categories, returnToProduct ? productDraft?.category_id : null, returnToProduct));
  } catch (e) { toast(e.message); }
}
function settingsView() {
  $('#content').innerHTML = `${heading('Trạng thái hệ thống', 'Thông tin vận hành dành cho quản trị viên.')}<section class="ad-card settings-card"><div class="ad-dialog-body"><p>Đang sử dụng dữ liệu từ Freedom API.</p><p>Quyền truy cập được xác minh từ tài khoản và vai trò trong database.</p>${btn('Kiểm tra kết nối', 'check-api')}</div></section>`;
}
function authForm(register = false, admin = false) {
  return `<form id="login-form" data-register="${register}" data-admin="${admin}">${register ? '<label>Họ và tên<input name="full_name" maxlength="150" autocomplete="name" required></label>' : ''}<label>Email<input name="email" type="email" autocomplete="username" required></label><label>Mật khẩu<input name="password" type="password" autocomplete="${register ? 'new-password' : 'current-password'}" ${register ? 'minlength="12" maxlength="128"' : ''} required></label><p class="form-error" role="alert"></p><button type="submit" class="ad-btn ad-btn-primary">${register ? 'Đăng ký' : 'Đăng nhập'}</button></form>`;
}
function loginDialog(register = false) {
  if (profile) { modal('Tài khoản Freedom', `<p>${esc(profile.full_name)}</p><p>${esc(profile.email)}</p>${btn('Đơn hàng của tôi', 'my-orders', true)}${btn('Đăng xuất', 'logout')}`); return; }
  modal(register ? 'Tạo tài khoản Freedom' : 'Đăng nhập Freedom', authForm(register) + btn(register ? 'Đã có tài khoản? Đăng nhập' : 'Khách hàng mới? Đăng ký', register ? 'login' : 'register'));
}
function exportCsv() {
  requireUiPermission(routePermissions[route]);
  const list = route === 'dashboard' ? dashboardOrders : filtered();
  if (!list.length) { toast('Không có dữ liệu để xuất.'); return; }
  const keys = [...new Set(list.flatMap(r => Object.keys(r)))];
  const safe = v => { let str = String(v ?? ''); if (/^[=+@\-\t\r]/.test(str)) str = "'" + str; return '"' + str.replace(/"/g, '""') + '"'; };
  const csv = '\uFEFF' + [keys.map(safe).join(','), ...list.map(r => keys.map(k => safe(typeof r[k] === 'object' ? JSON.stringify(r[k]) : r[k])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' })); const a = document.createElement('a'); a.href = url; a.download = `freedom-${route}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('Đã xuất dữ liệu trên trang hiện tại.');
}
async function storefront(id) {
  document.title = 'Freedom — Made for better everyday';
  $('#app').innerHTML = '<div class="store-loading">Đang mở cửa hàng Freedom…</div>';
  try {
    const cats = await api('/catalog/lookups/categories');
    if (id !== loadingId) return;
    shopCategories = cats;
    const selected = cats.find(c => c.slug === storeCategorySlug);
    shopCategory = selected ? String(selected.id) : '';
    document.title = selected ? `${selected.name} — Freedom Menswear` : 'Freedom — Made for better everyday';
    const breadcrumbs = `<nav class="category-breadcrumb" aria-label="Đường dẫn danh mục"><a href="#/store">Tất cả sản phẩm</a>${categoryPath(cats, selected?.id).map(c => `<span aria-hidden="true">/</span><a href="${categoryHref(c)}" ${c.id === selected.id ? 'aria-current="page"' : ''}>${esc(c.name)}</a>`).join('')}</nav>`;
    $('#app').innerHTML = `<div class="store" data-category-selected="${Boolean(storeCategorySlug)}"><div class="store-announcement">FREEDOM MENSWEAR <span>Trang phục đơn giản. Phong cách của riêng bạn.</span></div><header class="store-nav"><a class="store-logo" href="#/store">freedom<sup>®</sup></a>${categoryNavHtml(cats, selected)}<nav class="store-info-nav" aria-label="Điều hướng cửa hàng"><a href="#/store" data-scroll="collection">Bộ sưu tập</a><a href="#/store" data-scroll="story">Về Freedom</a></nav><div class="inline-actions"><button class="store-orders-link" data-action="my-orders" aria-label="Theo dõi đơn hàng">Đơn của tôi</button><button class="icon-btn" data-action="login" aria-label="Tài khoản">${icon('users')}</button><button class="cart-button" data-action="cart" aria-label="Giỏ hàng">${icon('bag')}<span id="cart-count">0</span></button></div></header><main>${categoryBannerHtml(cats, selected)}<section class="hero"><div class="hero-copy"><span class="store-eyebrow">THE EVERYDAY COLLECTION / 2026</span><h1>Ít hơn.<br><em>Nhưng tốt hơn.</em></h1><p>Những thiết kế vượt qua mùa mốt.<br>Để bạn thoải mái là chính mình, mỗi ngày.</p><a class="store-primary" href="#/store" data-scroll="collection">Khám phá bộ sưu tập ${icon('arrow')}</a><small>THIẾT KẾ TỐI GIẢN. CHẤT LIỆU CHỌN LỌC.</small></div><div class="hero-visual"><img src="${heroImage}" alt="Phong cách Freedom: áo linen màu kem và quần olive" width="1254" height="1254" loading="eager" fetchpriority="high" decoding="async"><div class="hero-caption"><span>01 / EVERYDAY ESSENTIALS</span><span>Freedom, by nature.</span></div></div></section><div class="store-values"><span>${icon('box')} Thiết kế cho mỗi ngày</span><span>${icon('star')} Chất liệu chọn lọc</span><span>${icon('help')} Tư vấn kích cỡ tận tình</span></div>${storeCategorySlug ? '' : homeCategoryBannersHtml()}<section id="collection" class="collection">${breadcrumbs}<div class="collection-heading"><div><span class="store-eyebrow">CURATED FOR YOU</span><h2>${storeCategorySlug && !selected ? 'Không tìm thấy danh mục' : esc(selected?.name || 'Tủ đồ của bạn, tinh gọn hơn.')}</h2></div><span id="product-count"></span></div><div class="store-filters"><div id="category-tabs">${categoryFiltersHtml(cats, selected)}</div><label class="store-search">${icon('search', 16)}<input id="store-search" placeholder="Tìm sản phẩm…" aria-label="Tìm sản phẩm"></label><select id="store-sort" aria-label="Sắp xếp"><option value="newest">Mới nhất</option><option value="price_asc">Giá tăng dần</option><option value="price_desc">Giá giảm dần</option></select></div><div id="product-grid" class="product-grid"></div><div class="store-pagination"><button id="store-load-more" class="ad-btn" data-action="load-more-products" hidden>Xem thêm sản phẩm</button></div></section><section id="story" class="store-story"><span class="store-eyebrow">MADE FOR BETTER EVERYDAY</span><h2>Thoải mái trong từng lựa chọn.</h2><p>Freedom tin rằng phong cách bắt đầu từ cảm giác thoải mái. Những thiết kế tối giản, gam màu dễ phối và chất liệu gần gũi tạo nên tủ đồ dành riêng cho cuộc sống của bạn.</p><a href="#/store" data-scroll="collection">Tìm phong cách của bạn ${icon('arrow', 16)}</a></section></main>${storeFooterHtml()}</div>`;
    shopSort = 'newest'; shopOffset = 0; rows = [];
    if (storeCategorySlug && !selected) {
      $('#product-grid').innerHTML = '<p class="small-empty">Danh mục không tồn tại hoặc đã ngừng hoạt động. Bạn có thể chọn Áo, Quần hoặc Suit trong menu.</p>';
      $('#product-count').textContent = '0 sản phẩm'; $('#store-load-more').hidden = true;
    } else await loadStoreProducts(true);
    if (sessionStorage.getItem('freedom-token')) {
      try { const items = await api('/me/cart'); if (id === loadingId && $('#cart-count')) $('#cart-count').textContent = items.reduce((sum, item) => sum + item.quantity, 0); } catch { /* The cart dialog presents authentication/connection errors on request. */ }
    }
  } catch (e) { if (id === loadingId) $('#app').innerHTML = `<main class="store-error"><h1>Freedom Menswear</h1><p>Cửa hàng tạm thời chưa tải được dữ liệu. Vui lòng thử lại sau.</p>${btn('Thử lại', 'reload')}</main>`; }
}
async function loadStoreProducts(reset = false) {
  const version = ++storeRequest, pageId = loadingId;
  if (storeCategorySlug && !shopCategory) return;
  const nextOffset = reset ? 0 : shopOffset + 100;
  const params = new URLSearchParams({ limit: '100', offset: String(nextOffset), sort: shopSort });
  if (shopCategory) params.set('category_id', shopCategory);
  const term = $('#store-search')?.value.trim() || ''; if (term) params.set('q', term);
  if (reset) $('#product-grid').innerHTML = '<p class="small-empty" role="status">Đang tải sản phẩm…</p>';
  $('#store-load-more').disabled = true;
  try {
    const list = await api('/catalog/products?' + params);
    if (version !== storeRequest || pageId !== loadingId || route !== 'store') return;
    rows = reset ? list : [...rows, ...list]; shopOffset = nextOffset; shopHasMore = list.length === 100;
    storeProducts();
  } catch (e) {
    if (version !== storeRequest || pageId !== loadingId || route !== 'store') return;
    if (reset) { rows = []; $('#product-count').textContent = ''; $('#product-grid').innerHTML = `<div class="small-empty"><p>${esc(e.message)}</p>${btn('Thử lại', 'reload')}</div>`; }
    else toast(e.message);
  } finally { if (version === storeRequest && pageId === loadingId && $('#store-load-more')) $('#store-load-more').disabled = false; }
}
function storeProducts() {
  const term = $('#store-search')?.value.toLowerCase() || '';
  const list = rows.filter(p => p.name.toLowerCase().includes(term));
  $('#product-count').textContent = `${list.length} sản phẩm`;
  $('#store-load-more').hidden = !shopHasMore;
  destroyGalleries($('#product-grid'));
  $('#product-grid').innerHTML = list.map((p, i) => `<article class="product-card"><div class="product-image">${galleryHtml(p, { card: true }) || `<button class="product-image-empty" data-product="${p.id}" aria-label="Xem ${esc(p.name)}">${icon('box', 45)}<small>Sản phẩm chưa có ảnh</small></button>`}<span class="product-label">${i === 0 ? 'ESSENTIAL' : 'FREEDOM'}</span><button class="product-quick" data-product="${p.id}">Xem sản phẩm ${icon('arrow', 17)}</button></div><div class="product-meta"><div><small>${esc(p.material || 'Freedom Collection')}</small><button data-product="${p.id}"><h3>${esc(p.name)}</h3></button></div><strong>${money(p.base_price)}</strong></div></article>`).join('') || '<p class="small-empty">Chưa có sản phẩm phù hợp.</p>';
  mountGalleries($('#product-grid'));
}
async function productDetail(id) {
  try { const product = await api(`/catalog/products/${id}`); modal(product.name, purchaseHtml(product)); }
  catch (e) { toast(e.message); }
}
async function addCartPurchase(purchase) {
  const items = await api('/me/cart');
  const old = items.find(item => Number(item.variant_id) === purchase.variant_id);
  await api('/me/cart/items', { method: 'PUT', body: { variant_id: purchase.variant_id, quantity: Number(old?.quantity || 0) + purchase.quantity } });
  updateCartCount(await api('/me/cart'));
  pendingPurchase = null; $('#modal').close(); toast('Đã thêm sản phẩm vào giỏ hàng.');
}
async function cartDialog(reset = false) {
  try {
    if (!sessionStorage.getItem('freedom-token')) { loginDialog(); return; }
    cartItems = await api('/me/cart'); updateCartCount(cartItems);
    if (reset) cartSelected.clear();
    cartSelected = new Set([...cartSelected].filter(id => cartItems.some(item => Number(item.variant_id) === id && item.is_active && item.product_status === 'active' && item.stock_quantity - item.reserved_quantity >= item.quantity)));
    modal('Giỏ hàng của bạn', cartHtml(cartItems));
    document.querySelectorAll('[data-cart-select]').forEach(input => { input.checked = cartSelected.has(Number(input.dataset.cartSelect)); });
    if (cartItems.length) updateCartSelection();
  } catch (e) { toast(e.message); }
}
async function checkoutDialog(method = 'delivery') {
  try {
    if (!selectedCartItems().length) throw new Error('Chọn ít nhất một sản phẩm trong giỏ hàng.');
    checkoutMethod = method; checkoutKey = crypto.randomUUID();
    const config = await api('/catalog/checkout-config');
    checkoutQuote = selectedCartItems().reduce((sum, item) => sum + Number(item.price) * item.quantity, 0) + (method === 'pickup' ? 0 : Number(config.shipping_fee));
    modal(method === 'pickup' ? 'Đặt trước, lấy tại cửa hàng' : 'Thông tin nhận hàng', checkoutHtml(selectedCartItems(), method, profile, config));
  } catch (e) { toast(e.message); }
}
async function myOrdersDialog() {
  try {
    if (!sessionStorage.getItem('freedom-token')) { loginDialog(); return; }
    const orders = await api('/me/orders?limit=100');
    modal('Đơn hàng của tôi', customerOrdersHtml(orders)); customerOrdersOpen = true;
  } catch (e) { toast(e.message); }
}
async function myOrderDetail(id) {
  try {
    const order = await api(`/me/orders/${id}`);
    modal(`Đơn hàng ${order.order_code}`, `<div id="customer-order-live">${orderInfoHtml(order)}</div><button class="ad-btn" data-action="my-orders">Tất cả đơn hàng</button>`);
    customerOrderId = order.id;
  } catch (e) { toast(e.message); }
}
document.addEventListener('click', async e => {
  const el = e.target.closest('button, a'); if (!el) return;
  if (el.dataset.scroll) { e.preventDefault(); document.getElementById(el.dataset.scroll)?.scrollIntoView({ behavior: 'smooth' }); return; }
  if (el.dataset.route) { query = ''; statusFilter = ''; offset = 0; location.hash = '#/' + el.dataset.route; return; }
  if (el.dataset.order) { await orderDetail(el.dataset.order); return; }
  if (el.dataset.myOrder) { await myOrderDetail(el.dataset.myOrder); return; }
  if (el.dataset.product) { await productDetail(el.dataset.product); return; }
  if (el.dataset.record) { if (route === 'products') await adminProductDetail(el.dataset.record); else recordDetail(el.dataset.record); return; }
  if (el.dataset.editProduct) { productDraft = null; clearProductImage(); await openProductEditor(el.dataset.editProduct); return; }
  if (el.dataset.deleteProduct) { await adminProductDetail(el.dataset.deleteProduct, true); return; }
  if (el.dataset.orderFilter) { statusFilter = el.dataset.orderFilter; query = ''; offset = 0; location.hash = '#/orders'; return; }
  if (el.dataset.transition) {
    try {
      requireUiPermission('orders.manage');
      el.disabled = true;
      await api(`/staff/orders/${el.dataset.transition}/status`, { method: 'PATCH', body: { status: el.dataset.status } });
      $('#modal').close(); toast('Đã cập nhật trạng thái đơn hàng.'); await render();
    } catch (e) { el.disabled = false; toast(e.message); } return;
  }
  if (el.dataset.removeApi) { try { await api('/me/cart/items', { method: 'PUT', body: { variant_id: Number(el.dataset.removeApi), quantity: 0 } }); await cartDialog(); } catch (e) { toast(e.message); } return; }
  const action = el.dataset.action;
  if (action === 'add-size-row') {
    $('#product-size-rows').insertAdjacentHTML('beforeend', variantRowHtml({}, $('#product-form').elements.namedItem('base_price').value)); return;
  }
  if (action === 'remove-size-row') { el.closest('[data-variant-row]')?.remove(); updateProductStockTotal(); return; }
  if (action === 'checkout-delivery') { await checkoutDialog('delivery'); return; }
  if (action === 'checkout-pickup') { await checkoutDialog('pickup'); return; }
  if (action === 'back-to-cart') { await cartDialog(); return; }
  if (action === 'my-orders') { await myOrdersDialog(); return; }
  if (action === 'clear-product-image') {
    if ($('#product-form')?.dataset.submitting === 'true') return;
    clearProductImage(); $('#product-image-file').value = '';
    $('#product-image-preview').innerHTML = productImagePreviewHtml(productDraft, null);
    return;
  }
  if (action === 'close') $('#modal').close();
  if (action === 'menu') { $('.ad-sidebar').classList.toggle('open'); $('.nav-shade').classList.toggle('visible'); }
  if (action === 'settings') location.hash = '#/settings';
  if (action === 'reload') await render();
  if (action === 'export') exportCsv();
  if (action === 'new-product') await newProduct();
  if (action === 'new-product-category') await newProductCategory();
  if (action === 'new-category') await newProductCategory(false);
  if (action === 'load-more-products') await loadStoreProducts();
  if (action === 'back-product-editor') await openProductEditor();
  if (action === 'login') loginDialog();
  if (action === 'register') loginDialog(true);
  if (action === 'cart') await cartDialog(true);
  if (action === 'checkout') await checkoutDialog();
  if (action === 'previous' && offset > 0) { offset -= 100; await render(); }
  if (action === 'next') { if (rows.length < 100) toast('Đây là trang cuối.'); else { offset += 100; await render(); } }
  if (action === 'notifications') modal('Công việc cần xử lý', `<p>Kiểm tra đơn chờ xác nhận, yêu cầu đổi trả và tình trạng tồn kho.</p>${btn('Mở danh sách đơn hàng', 'open-orders', true)}`);
  if (action === 'open-orders') { $('#modal').close(); location.hash = '#/orders'; }
  if (action === 'help') modal('Trung tâm trợ giúp', '<p>Menu chỉ hiển thị các nghiệp vụ được cấp quyền cho tài khoản của bạn.</p><p>Để thay đổi quyền, liên hệ quản trị viên của cửa hàng.</p>');
  if (action === 'logout') {
    try { await api('/auth/logout', { method: 'POST' }); }
    catch (e) { if (e.status !== 401) toast('Đã thoát trên trình duyệt này; chưa xác nhận đăng xuất trên máy chủ.'); }
    finally { sessionStorage.removeItem('freedom-token'); profile = null; pendingPurchase = null; cartSelected.clear(); rows = []; dashboardOrders = []; if ($('#modal').open) $('#modal').close(); location.hash = '#/store'; await render(); }
  }
  if (action === 'check-api') { try { await api('/ready'); toast('Backend và database kết nối thành công.'); } catch (e) { toast(e.message); } }
});
document.addEventListener('input', e => {
  if (e.target.matches?.('[data-variant-stock]')) updateProductStockTotal();
  if (e.target.id === 'search') { query = e.target.value; tableContent(); }
  if (e.target.id === 'store-search') { clearTimeout(storeSearchTimer); storeSearchTimer = setTimeout(() => { if (route === 'store') loadStoreProducts(true); }, 300); }
  const form = e.target.form;
  if (['product-form', 'product-category-form'].includes(form?.id)) {
    const slug = form.elements.namedItem('slug');
    if (e.target.name === 'name' && slug.dataset.auto === 'true') slug.value = slugify(e.target.value);
    if (e.target.name === 'slug') slug.dataset.auto = 'false';
  }
});
document.addEventListener('change', async e => {
  if (e.target.id === 'purchase-variant') {
    const selected = e.target.selectedOptions[0];
    $('#purchase-price').textContent = money(selected.dataset.price);
    $('#purchase-quantity').max = Math.min(999, Number(selected.dataset.stock));
    $('#purchase-quantity').value = Math.min(Number($('#purchase-quantity').value) || 1, Number($('#purchase-quantity').max));
  }
  if (e.target.dataset?.cartSelect) {
    const id = Number(e.target.dataset.cartSelect);
    if (e.target.checked) cartSelected.add(id); else cartSelected.delete(id);
    updateCartSelection();
  }
  if (e.target.dataset?.cartQuantity) {
    try {
      const quantity = Number(e.target.value);
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 999) throw new Error('Số lượng phải từ 1 đến 999.');
      e.target.disabled = true;
      await api('/me/cart/items', { method: 'PUT', body: { variant_id: Number(e.target.dataset.cartQuantity), quantity } });
      await cartDialog();
    } catch (error) { toast(error.message); await cartDialog(); }
  }
  if (e.target.id === 'product-image-file') {
    if (e.target.form?.dataset.submitting === 'true') return;
    const files = [...(e.target.files || [])]; if (!files.length) return;
    try {
      if (files.length > 8) throw new Error('Chọn tối đa 8 ảnh mỗi lần.');
      files.forEach(validateProductImage);
      clearProductImage(); productImageFiles = files; productImagePreviews = files.map(file => URL.createObjectURL(file));
      $('#product-image-preview').innerHTML = productImagePreviewHtml(productDraft, pendingProductImage());
      $('.form-error', e.target.form).textContent = '';
    } catch (error) { e.target.value = ''; $('.form-error', e.target.form).textContent = error.message; }
    return;
  }
  if (e.target.id === 'status-filter') { statusFilter = e.target.value; tableContent(); }
  if (e.target.id === 'period') { period = e.target.value; await render(); }
  if (e.target.id === 'store-sort') { shopSort = e.target.value; await loadStoreProducts(true); }
});
document.addEventListener('submit', async e => {
  e.preventDefault(); const form = e.target;
  if (form.dataset.submitting === 'true') return;
  form.dataset.submitting = 'true';
  const body = Object.fromEntries(new FormData(form));
  const submit = e.submitter || form.querySelector('button[type="submit"]') || form.querySelector('button:not([type])');
  if (submit) submit.disabled = true;
  const previousError = $('.form-error', form); if (previousError) previousError.textContent = '';
  try {
    if (form.id === 'login-form') {
      if (form.dataset.register === 'true' && form.dataset.admin !== 'true') await api('/auth/register', { method: 'POST', body });
      const token = await api('/auth/token', { method: 'POST', form: new URLSearchParams({ username: body.email, password: body.password }) });
      sessionStorage.setItem('freedom-token', token.access_token); profile = await api('/auth/me');
      if ($('#modal').open) $('#modal').close();
      if (form.dataset.admin === 'true') {
        const first = firstAdminRoute(profile);
        if (!first) { accessPage('Tài khoản này không có quyền quản lý cửa hàng.'); return; }
        location.hash = '#/' + first;
        if (route === first) await render();
      } else { location.hash = '#/store'; await render(); }
      toast('Đăng nhập thành công.');
      if (pendingPurchase && form.dataset.admin !== 'true') await addCartPurchase(pendingPurchase);
    }
    if (form.id === 'product-form') {
      requireUiPermission('catalog.manage');
      const product = productPayload(body), editing = Boolean(form.dataset.id);
      const variants = readProductVariants(form);
      if (variants !== undefined) product.variants = variants;
      const imageFiles = [...productImageFiles];
      imageFiles.forEach(validateProductImage);
      const saved = await api('/staff/catalog/products' + (editing ? `/${form.dataset.id}` : ''), { method: editing ? 'PUT' : 'POST', body: product });
      // Keep the saved ID if image upload fails, so retry updates instead of duplicating.
      form.dataset.id = String(saved.id); productDraft = { ...productDraft, ...saved };
      if (variants !== undefined) {
        // Refresh expected stock and IDs before any retry following an image error.
        const refreshed = await api(`/staff/catalog/products/${saved.id}`);
        productDraft = { ...productDraft, ...refreshed };
        $('#product-size-rows').innerHTML = (refreshed.product_variants || []).map(variant => variantRowHtml(variant, refreshed.base_price)).join('');
      }
      if (imageFiles.length) {
        if (submit) submit.textContent = 'Lưu thay đổi';
        const upload = new FormData(); imageFiles.forEach(file => upload.append('files', file));
        try { await api(`/staff/catalog/products/${saved.id}/images`, { method: 'POST', form: upload, timeout: 120000 }); }
        catch (error) { throw new Error(`Sản phẩm #${saved.id} đã lưu nhưng ảnh chưa tải lên: ${error.message} Bấm Lưu để thử lại.`); }
      }
      clearProductImage();
      productDraft = null; $('#modal').close(); query = ''; statusFilter = product.status === 'archived' ? 'archived' : 'not_archived'; offset = 0;
      if (route === 'products') await render(); else location.hash = '#/products';
      toast(editing ? 'Đã cập nhật sản phẩm.' : 'Đã thêm sản phẩm.');
    }
    if (form.id === 'delete-product-form') {
      requireUiPermission('catalog.manage');
      await api(`/staff/catalog/products/${form.dataset.id}`, { method: 'DELETE' });
      $('#modal').close(); statusFilter = 'not_archived'; await render(); toast('Đã xóa sản phẩm khỏi danh sách đang sử dụng.');
    }
    if (form.id === 'product-category-form') {
      requireUiPermission('catalog.manage');
      const parent = Number(body.parent_id);
      if (!Number.isInteger(parent) || parent <= 0) throw new Error('Chọn danh mục cha: Áo, Quần hoặc Suit.');
      const category = await api('/staff/catalog/categories', { method: 'POST', body: { name: body.name, slug: body.slug, parent_id: parent, is_active: true } });
      if (form.dataset.returnProduct !== 'false') { productDraft = { ...productDraft, category_id: category.id }; await openProductEditor(); }
      else { $('#modal').close(); await render(); }
      toast('Đã tạo danh mục con. Menu cửa hàng sẽ tự cập nhật từ database.');
    }
    if (form.id === 'stock-form') {
      requireUiPermission('inventory.manage');
      const quantity = Number(body.quantity_change); if (!quantity) throw new Error('Số lượng điều chỉnh phải khác 0.');
      await api(`/staff/inventory/${form.dataset.id}/adjust`, { method: 'POST', body: { quantity_change: quantity, note: body.note } });
      $('#modal').close(); await render(); toast('Đã điều chỉnh tồn kho.');
    }
    if (form.id === 'add-cart-form') {
      const purchase = { variant_id: Number(body.variant_id), quantity: Number(body.quantity || 1) };
      if (!Number.isInteger(purchase.quantity) || purchase.quantity < 1 || purchase.quantity > 999 || !purchase.variant_id) throw new Error('Chọn size và số lượng hợp lệ.');
      if (!sessionStorage.getItem('freedom-token')) { pendingPurchase = purchase; loginDialog(); return; }
      await addCartPurchase(purchase);
    }
    if (form.id === 'address-form') { await api('/me/addresses', { method: 'POST', body }); await checkoutDialog(); }
    if (form.id === 'checkout-form') {
      const chosen = selectedCartItems();
      if (!chosen.length) throw new Error('Chọn ít nhất một sản phẩm.');
      const payload = { variant_ids: chosen.map(item => Number(item.variant_id)), expected_quantities: Object.fromEntries(chosen.map(item => [item.variant_id, item.quantity])), expected_total: checkoutQuote.toFixed(2), fulfillment_method: checkoutMethod, checkout_key: checkoutKey, recipient_name: body.recipient_name, recipient_phone: body.recipient_phone, payment_method: 'cod', customer_note: body.customer_note || null };
      if (checkoutMethod === 'pickup') {
        payload.recipient_email = body.recipient_email;
        payload.pickup_start = `${body.pickup_date}T${body.pickup_from}:00+07:00`;
        payload.pickup_end = `${body.pickup_date}T${body.pickup_to}:00+07:00`;
        if (!Number.isFinite(Date.parse(payload.pickup_start)) || !Number.isFinite(Date.parse(payload.pickup_end)) || Date.parse(payload.pickup_start) <= Date.now() || Date.parse(payload.pickup_end) <= Date.parse(payload.pickup_start)) throw new Error('Chọn ngày và khoảng thời gian lấy hàng hợp lệ trong tương lai.');
      } else payload.shipping_address = body.shipping_address;
      const order = await api('/me/checkout', { method: 'POST', body: payload });
      cartSelected.clear(); checkoutKey = '';
      modal(checkoutMethod === 'pickup' ? 'Đã đặt trước thành công' : 'Đặt hàng thành công', `<p>Cửa hàng đã nhận yêu cầu và sẽ xác nhận đơn của bạn.</p>${orderInfoHtml(order)}<button class="ad-btn ad-btn-primary" data-my-order="${order.id}">Theo dõi đơn hàng</button>`);
      updateCartCount(await api('/me/cart'));
    }
    if (form.id === 'shipment-form') {
      requireUiPermission('orders.manage');
      await api(`/staff/orders/${form.dataset.id}/shipment`, { method: 'PUT', body: { carrier: body.carrier, tracking_number: body.tracking_number } });
      await orderDetail(form.dataset.id); toast('Đã lưu vận đơn.');
    }
  } catch (e) { const error = $('.form-error', form); if (error) error.textContent = e.message; else toast(e.message); }
  finally { form.dataset.submitting = 'false'; if (submit) submit.disabled = false; }
});
$('#modal').addEventListener('close', () => { customerOrderId = null; customerOrdersOpen = false; clearProductImage(); destroyGalleries($('#modal')); });
$('#modal').addEventListener('click', e => { if (e.target === $('#modal')) { const r = $('#modal').getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) $('#modal').close(); } });
// Pointer events keep native details/summary click and keyboard behavior on touch.
document.addEventListener('pointerover', e => {
  if (e.pointerType !== 'mouse') return;
  const menu = e.target.closest?.('.category-menu');
  if (!menu || menu.contains(e.relatedTarget)) return;
  document.querySelectorAll('.category-menu[open]').forEach(other => { if (other !== menu) other.open = false; });
  menu.open = true;
});
document.addEventListener('pointerout', e => {
  if (e.pointerType !== 'mouse') return;
  const menu = e.target.closest?.('.category-menu');
  if (!menu || menu.contains(e.relatedTarget)) return;
  menu.open = false;
});
document.addEventListener('pointerdown', e => {
  if (!e.target.closest?.('.store-category-nav')) document.querySelectorAll('.category-menu[open]').forEach(menu => { menu.open = false; });
});
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const menu = e.target.closest?.('.category-menu');
  if (!menu?.open) return;
  menu.open = false; menu.querySelector('summary')?.focus(); e.preventDefault();
});
document.addEventListener('focusout', e => {
  const menu = e.target.closest?.('.category-menu');
  if (menu && !menu.contains(e.relatedTarget) && !menu.matches(':hover')) menu.open = false;
});
document.addEventListener('toggle', e => { if (e.target.matches?.('.category-menu') && e.target.open) document.querySelectorAll('.category-menu[open]').forEach(menu => { if (menu !== e.target) menu.open = false; }); }, true);
window.addEventListener('hashchange', () => { if ($('#modal').open) $('#modal').close(); document.title = 'Freedom — Thời trang nam'; render(); window.scrollTo(0, 0); });
window.addEventListener('freedom:session-expired', () => { profile = null; if ($('#modal').open) $('#modal').close(); if (route !== 'store') accessPage('Phiên đăng nhập đã hết hạn.', true); });
window.addEventListener('freedom:access-denied', () => { if (route !== 'store') accessPage('Quyền truy cập đã thay đổi hoặc tài khoản không được cấp quyền cho thao tác này.'); });
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && route !== 'store') render(); });
window.addEventListener('pageshow', e => { if (e.persisted && route !== 'store') render(); });
if (sessionStorage.getItem('freedom-token')) { try { profile = await api('/auth/me'); } catch { profile = null; } }
await render();
// Refresh customer status without closing their dialog; refresh staff lists when idle.
setInterval(async () => {
  if (document.hidden || orderPollBusy || !sessionStorage.getItem('freedom-token')) return;
  orderPollBusy = true;
  try {
    if ($('#modal').open && customerOrderId) {
      const id = customerOrderId, order = await api(`/me/orders/${id}`);
      if (customerOrderId === id && $('#modal').open) $('#customer-order-live').innerHTML = orderInfoHtml(order);
    } else if ($('#modal').open && customerOrdersOpen) {
      const orders = await api('/me/orders?limit=100');
      if (customerOrdersOpen && $('#modal').open) $('#modal .ad-dialog-body').innerHTML = customerOrdersHtml(orders);
    } else if (!$('#modal').open && ['orders','shipping'].includes(route) && can(profile, 'orders.manage')) {
      const pageId = loadingId, list = await api('/staff/orders?limit=100&offset=' + offset);
      if (pageId === loadingId && !$('#modal').open) { rows = list; tableContent(); }
    }
  } catch { /* Existing controls provide manual refresh and authentication handling. */ }
  finally { orderPollBusy = false; }
}, 15000);


