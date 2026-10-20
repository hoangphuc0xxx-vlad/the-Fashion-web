// Route and interaction checks with a simulated DOM and controlled API responses.
// Backend authorization is tested separately in tests/test_access.py.
import assert from 'node:assert/strict';
import { routePermissions, can, canVisit } from './access.js';
import { slugify, productPayload, productEditorHtml, productDetailsHtml, productImageUrl, validateProductImage, deleteProductHtml } from './products.js';
import { categoryHref, categoryPath, categoryNavHtml, categoryOptionsHtml, categoryFormHtml, visibleCategories } from './categories.js';
import { categoryBannerHtml } from './category-banners.js';
const memory = () => { const data = new Map(); return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)), removeItem: k => data.delete(k) }; };
globalThis.localStorage = memory(); globalThis.sessionStorage = memory();
localStorage.setItem('freedom-mode', 'demo'); localStorage.setItem('freedom-api', 'https://untrusted.invalid'); localStorage.setItem('role', 'admin');
globalThis.location = { hash: '', href: 'http://localhost:5173/' };
const handlers = {}, windowHandlers = {}, elements = new Map();
function element(key) {
  if (!elements.has(key)) elements.set(key, { innerHTML: '', textContent: '', className: '', value: '', open: false, addEventListener() {}, querySelector: s => element(s), querySelectorAll: () => [], classList: { toggle() {} }, showModal() { this.open = true; }, close() { this.open = false; }, scrollIntoView() {} });
  return elements.get(key);
}
globalThis.document = { title: '', querySelector: element, querySelectorAll: () => [], getElementById: key => element('#' + key), addEventListener: (name, cb) => handlers[name] = cb };
globalThis.window = { addEventListener: (name, cb) => windowHandlers[name] = cb, scrollTo() {} };
globalThis.dispatchEvent = event => { windowHandlers[event.type]?.(event); };
let actor = null, expired = false, forceForbidden = false, productError = false, catalogPages = false, imageError = false;
const requests = [];
const categories = [
  { id: 1, name: 'Áo', slug: 'ao', parent_id: null, is_active: true }, { id: 2, name: 'Quần', slug: 'quan', parent_id: null, is_active: true }, { id: 3, name: 'Suit', slug: 'suit', parent_id: null, is_active: true },
  { id: 4, name: 'Áo sơ mi', slug: 'ao-so-mi', parent_id: 1, is_active: true }, { id: 5, name: 'Áo khoác', slug: 'ao-khoac', parent_id: 1, is_active: true },
  { id: 6, name: 'Quần jean', slug: 'quan-jean', parent_id: 2, is_active: true }, { id: 7, name: 'Suit 3 mảnh', slug: 'suit-3-manh', parent_id: 3, is_active: true },
  { id: 8, name: 'Sơ mi Linen', slug: 'so-mi-linen', parent_id: 4, is_active: true },
];
const product = { id: 1, name: 'Áo sơ mi', slug: 'ao-so-mi', category_id: 4, brand_id: 1, category: categories[3], brand: { id: 1, name: 'Freedom' }, description: 'Mô tả gốc', base_price: 549000, material: 'Linen', status: 'active', product_variants: [], product_images: [] };
const productList = [product];
const order = { id: 1, order_code: 'FR-TEST', recipient_name: 'Khách hàng', recipient_phone: '0901234567', status: 'pending', total_amount: 549000, placed_at: new Date().toISOString() };
let testCart = [], testOrders = [], checkoutFailure = false;
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => structuredClone(data) });
globalThis.fetch = async (url, init) => {
  const parsed = new URL(url); const path = parsed.pathname; requests.push({ path, url, ...init });
  assert.equal(parsed.origin, 'http://127.0.0.1:8000');
  if (path === '/auth/me') return actor && !expired ? response(actor) : response({ detail: 'Phiên không hợp lệ' }, 401);
  if (path === '/auth/logout') return response({});
  if (path === '/catalog/lookups/categories') return response(categories);
  if (path.startsWith('/catalog/lookups/')) return response([{ id: 1, name: 'Freedom' }]);
  if (path === '/catalog/products') {
    if (catalogPages) return response(Array.from({ length: parsed.searchParams.get('offset') === '100' ? 1 : 100 }, (_, i) => ({ ...product, id: i + (parsed.searchParams.get('offset') === '100' ? 1100 : 1000) })));
    return response([product]);
  }
  if (path === '/catalog/products/1') return response(product);
  if (path === '/catalog/checkout-config') return response({ shipping_fee: 30000, store_address: 'Số 69 Tràng Tiền, Hà Nội' });
  if (path === '/me/cart') return response(testCart);
  if (path === '/me/cart/items') {
    const body = JSON.parse(init.body), item = testCart.find(row => row.variant_id === body.variant_id);
    if (item) item.quantity = body.quantity;
    else testCart.push({ variant_id: body.variant_id, product_name: product.name, size_name: 'M', color_name: 'Đen', quantity: body.quantity, price: 500000, stock_quantity: 20, reserved_quantity: 0, is_active: true, product_status: 'active' });
    testCart = testCart.filter(item => item.quantity > 0); return response({});
  }
  if (path === '/me/checkout') {
    const body = JSON.parse(init.body);
    if (checkoutFailure) return response({ detail: 'Mạng chậm, vui lòng thử lại' }, 503);
    const existing = testOrders.find(order => order.checkout_key === body.checkout_key);
    if (existing) return response(existing, 201);
    const created = { ...body, id: 100 + testOrders.length, order_code: 'FR-NEW-' + testOrders.length, status: 'pending', total_amount: body.expected_total, shipping_fee: body.fulfillment_method === 'pickup' ? 0 : 30000, subtotal: body.expected_total - (body.fulfillment_method === 'pickup' ? 0 : 30000), order_items: [] };
    testOrders.push(created); testCart = testCart.filter(item => !body.variant_ids.includes(item.variant_id)); return response(created, 201);
  }
  if (path === '/me/orders') return response(testOrders);
  if (/^\/me\/orders\/\d+$/.test(path)) return response(testOrders.find(order => order.id === Number(path.split('/').pop())));
  if (forceForbidden) return response({ detail: 'Không có quyền thực hiện' }, 403);
  if (path === '/admin/dashboard') return response({ orders: 1, delivered_gross_revenue: 0, customers_total: 1, top_products: [] });
  if (path === '/staff/orders') return response([order]);
  if (path === '/staff/orders/1') return response(order);
  if (path === '/staff/orders/1/status') { order.status = JSON.parse(init.body).status; return response(order); }
  if (path === '/staff/inventory') return response([{ id: 1, sku: 'SKU-1', stock_quantity: 3, reserved_quantity: 0 }]);
  if (path === '/staff/catalog/products' && init.method === 'POST') {
    if (productError) return response({ detail: 'Đường dẫn đã tồn tại' }, 409);
    const created = { ...JSON.parse(init.body), id: 2, product_variants: [], product_images: [] }; productList.push(created); return response(created, 201);
  }
  if (path === '/staff/catalog/products') return response(productList);
  if (/^\/staff\/catalog\/products\/\d+\/images$/.test(path)) {
    assert.equal(init.headers['Content-Type'], undefined); // Browser sets the multipart boundary.
    assert.deepEqual(init.body.getAll('files').map(file => file.name), ['shirt.png', 'back.png']);
    if (imageError) return response({ detail: 'Tải ảnh thất bại' }, 503);
    const row = productList.find(p => String(p.id) === path.split('/')[4]);
    row.product_images = ['a', 'b'].map((key, index) => ({ id: 10 + index, product_id: row.id, image_url: '/media/products/' + key.repeat(32) + '.webp', is_primary: index === 0, sort_order: index }));
    return response(row.product_images, 201);
  }
  if (/^\/staff\/catalog\/products\/\d+$/.test(path)) {
    const row = productList.find(p => String(p.id) === path.split('/').pop());
    if (!row) return response({ detail: 'Không tìm thấy' }, 404);
    if (init.method === 'PUT') { Object.assign(row, JSON.parse(init.body)); return response(row); }
    if (init.method === 'DELETE') { row.status = 'archived'; return response(null, 204); }
    return response(row);
  }
  if (path === '/staff/catalog/categories' && init.method === 'POST') { const category = { ...JSON.parse(init.body), id: 50 }; categories.push(category); return response(category, 201); }
  return response([]);
};
const flush = () => new Promise(setImmediate);
const navigate = async route => { location.hash = '#/' + route; windowHandlers.hashchange(); await flush(); };
const click = dataset => handlers.click({ target: { closest: () => ({ dataset }) }, preventDefault() {} });
// Feed actual submit handlers browser-style string values without a full HTML engine.
globalThis.FormData = class {
  constructor(form) { this.values = Object.entries(form?.values || {}); }
  append(key, value) { this.values.push([key, value]); }
  get(key) { return this.values.find(([name]) => name === key)?.[1]; }
  getAll(key) { return this.values.filter(([name]) => name === key).map(([, value]) => value); }
  *[Symbol.iterator]() { yield* this.values; }
};
const submit = async (id, values, dataset = {}) => {
  const form = { id, values, dataset, querySelectorAll: () => [], querySelector: s => element(s === '.form-error' ? '#test-form-error' : '#test-submit-button') };
  await handlers.submit({ preventDefault() {}, target: form });
};
await import('./app.js');
const { api, config } = await import('./api.js');
assert.equal(config.mode, 'api'); assert.equal(Object.isFrozen(config), true);
assert.match(element('#app').innerHTML, /Ít hơn/);
assert.doesNotMatch(element('#app').innerHTML, /#\/admin|#\/dashboard|Quản trị|xem thử|Cài đặt kết nối/i);
assert.match(element('#app').innerHTML, /Áo<span/); assert.match(element('#app').innerHTML, /Quần<span/); assert.match(element('#app').innerHTML, /Suit<span/);
assert.match(element('#app').innerHTML, /href="#\/store\?category=ao-so-mi"/);
assert.match(element('#app').innerHTML, /href="#\/store\?category=quan-jean"/);
assert.match(element('#app').innerHTML, /href="#\/store\?category=suit-3-manh"/);
assert.doesNotMatch(element('#app').innerHTML, /class="category-hero /);
assert.match(element('#app').innerHTML, /class="home-categories"/);
for (const slug of ['ao', 'quan', 'suit']) {
  assert.match(element('#app').innerHTML, new RegExp('class="home-category-card" href="#/store\\?category=' + slug + '"'));
  assert.match(element('#app').innerHTML, new RegExp('assets/home-category-' + slug + '-v1\\.png'));
}
assert.match(element('#app').innerHTML, /Freedom — thương hiệu thời trang nam mạnh mẽ, mang đến sự tự do cho quý ông\./);
assert.match(element('#app').innerHTML, /Số 69 phố Tràng Tiền, TP\. Hà Nội/);
assert.match(element('#app').innerHTML, /href="tel:0123699999">0123699999/);
assert.match(element('#app').innerHTML, /href="mailto:freeshion69trangtien@gmail\.com">freeshion69trangtien@gmail\.com/);
for (const slug of ['ao', 'quan', 'suit']) {
  await navigate('store?category=' + slug);
  assert.match(element('#app').innerHTML, new RegExp('assets/category-' + slug + '-v1\\.png'));
  assert.doesNotMatch(element('#app').innerHTML, /class="home-categories"/);
  assert.match(element('#app').innerHTML, /href="tel:0123699999"/);
}
assert.equal(categoryBannerHtml(categories, undefined), '');
assert.equal(categoryBannerHtml([{ id: 90, slug: 'constructor', parent_id: null }], { id: 90 }), '');
assert.doesNotMatch(categoryBannerHtml(categories, { ...categories[3], name: '<script>alert(1)</script>' }), /<script>/);
await navigate('store?category=ao-so-mi');
assert.match(element('#app').innerHTML, /assets\/category-ao-v1\.png/);
assert.match(element('#app').innerHTML, /id="category-hero-title">Áo sơ mi<\/h1>/);
assert.equal(new URL(requests.findLast(r => r.path === '/catalog/products').url).searchParams.get('category_id'), '4');
assert.match(element('#app').innerHTML, /aria-current="page">Áo sơ mi/);
await handlers.change({ target: { id: 'store-sort', value: 'price_desc' } });
assert.equal(new URL(requests.findLast(r => r.path === '/catalog/products').url).searchParams.get('sort'), 'price_desc');
requests.length = 0; await navigate('store?category=not-found');
assert.match(element('#product-grid').innerHTML, /Danh mục không tồn tại/); assert.equal(requests.filter(r => r.path === '/catalog/products').length, 0);
catalogPages = true; await navigate('store?category=ao'); assert.equal(element('#store-load-more').hidden, false);
await click({ action: 'load-more-products' }); assert.equal(new URL(requests.findLast(r => r.path === '/catalog/products').url).searchParams.get('offset'), '100'); assert.match(element('#product-count').textContent, /101 sản phẩm/); catalogPages = false;
assert.deepEqual(categoryPath(categories, 8).map(c => c.name), ['Áo', 'Áo sơ mi', 'Sơ mi Linen']);
assert.match(categoryOptionsHtml(categories, 8), /Áo → Áo sơ mi → Sơ mi Linen/);
assert.match(categoryFormHtml(categories, 4), /name="parent_id" required/);
assert.match(categoryFormHtml(categories, 4), /value="1" selected/);
assert.equal(categoryHref({ slug: 'áo & đẹp' }), '#/store?category=%C3%A1o%20%26%20%C4%91%E1%BA%B9p');
assert.deepEqual(visibleCategories([{ id: 1, parent_id: null, is_active: false }, { id: 2, parent_id: 1, is_active: true }]), []);
assert.deepEqual(visibleCategories([{ id: 1, parent_id: 2 }, { id: 2, parent_id: 1 }]), []);
assert.doesNotMatch(categoryNavHtml([...categories, { id: 99, parent_id: 1, slug: 'x', name: '<script>alert(1)</script>' }]), /<script>/);
for (const route of [...Object.keys(routePermissions), 'admin', 'admin/login']) {
  requests.length = 0; await navigate(route);
  assert.match(element('#app').innerHTML, /Đăng nhập quản trị/, route);
  assert.doesNotMatch(element('#app').innerHTML, /class="ad-sidebar"|data-register="true"/, route);
  assert.equal(requests.length, 0, `guest route ${route} must not request private data`);
}
actor = { id: 1, role: 'customer', status: 'active', full_name: 'Khách hàng', permissions: ['*', ...Object.values(routePermissions)] };
sessionStorage.setItem('freedom-token', 'customer-token');
for (const route of Object.keys(routePermissions)) {
  requests.length = 0; await navigate(route);
  assert.match(element('#app').innerHTML, /Không có quyền truy cập/, route);
  assert.doesNotMatch(element('#app').innerHTML, /class="ad-sidebar"/, route);
  assert.deepEqual(requests.map(r => r.path), ['/auth/me']);
}
actor = { id: 2, role: 'staff', status: 'active', full_name: 'Nhân viên', permissions: ['orders.manage', 'inventory.read', 'users.manage', 'payments.manage', 'audit.read'] };
sessionStorage.setItem('freedom-token', 'staff-token');
assert.equal(can(actor, 'audit.read'), false); assert.equal(can(actor, 'users.manage'), false); assert.equal(canVisit(actor, 'orders'), true);
await navigate('orders'); assert.match(element('#app').innerHTML, /data-route="orders"/); assert.doesNotMatch(element('#app').innerHTML, /data-route="users"|data-route="products"|data-route="audit"|data-route="settings"/);
await click({ order: '1' }); assert.match(element('#modal').innerHTML, /Xác nhận — Đang đóng gói/);
await click({ transition: '1', status: 'packing' }); assert.match(element('#table-content').innerHTML, /Đang đóng gói/);
await navigate('inventory'); await click({ record: '1' }); assert.doesNotMatch(element('#modal').innerHTML, /stock-form/); // read permission never exposes stock mutation.
await navigate('dashboard'); assert.match(element('#app').innerHTML, /Không có quyền truy cập/);
actor.permissions = [];
requests.length = 0; await navigate('orders'); assert.match(element('#app').innerHTML, /Không có quyền truy cập/); assert.deepEqual(requests.map(r => r.path), ['/auth/me']);
actor = { id: 3, role: 'admin', status: 'active', full_name: 'Admin', permissions: ['*'] };
sessionStorage.setItem('freedom-token', 'admin-token');
for (const route of Object.keys(routePermissions)) {
  await navigate(route); assert.match(element('#app').innerHTML, /class="ad-sidebar"/, route);
  assert.doesNotMatch(element('#content').innerHTML, /Cần kiểm tra kết nối/, route);
}
await navigate('products');
assert.match(element('#table-content').innerHTML, /data-edit-product="1"/);
assert.match(element('#table-content').innerHTML, /data-delete-product="1"/);
await click({ record: '1' }); assert.match(element('#modal').innerHTML, /Mô tả gốc/); assert.match(element('#modal').innerHTML, /Sửa sản phẩm/);
await click({ editProduct: '1' }); assert.match(element('#modal').innerHTML, /data-id="1"/); assert.match(element('#modal').innerHTML, /value="ao-so-mi"/); assert.match(element('#modal').innerHTML, /name="brand_id"/);
const editedValues = { name: 'Sơ mi đã sửa', slug: 'so-mi-da-sua', category_id: '1', brand_id: '', base_price: '600000.25', material: 'Cotton', description: 'Mô tả mới', status: 'draft' };
await submit('product-form', editedValues, { id: '1' });
assert.equal(product.name, 'Sơ mi đã sửa'); assert.equal(product.brand_id, null); assert.equal(product.status, 'draft'); assert.equal(product.base_price, '600000.25');
assert.equal(requests.findLast(r => r.path === '/staff/catalog/products/1' && r.method === 'PUT').headers.Authorization, 'Bearer admin-token');
await click({ action: 'new-product' }); assert.match(element('#modal').innerHTML, /Thêm sản phẩm mới/);
assert.match(element('#modal').innerHTML, /type="file" accept="image\/jpeg,image\/png,image\/webp"/);
const imageForm = { dataset: {}, querySelector: () => element('#test-form-error') };
await handlers.change({ target: { id: 'product-image-file', files: ['shirt.png', 'back.png'].map(name => new File(['image'], name, { type: 'image/png' })), form: imageForm } });
assert.match(element('#product-image-preview').innerHTML, /blob:.*alt="Ảnh sản phẩm 1"/);
assert.match(element('#product-image-preview').innerHTML, /Ảnh sản phẩm 2/);
const createDataset = {}, newValues = { ...editedValues, name: 'Sản phẩm mới', slug: 'san-pham-moi', brand_id: '1', status: 'active' };
imageError = true;
await submit('product-form', newValues, createDataset);
assert.match(element('#test-form-error').textContent, /đã lưu nhưng ảnh chưa tải lên/);
assert.equal(createDataset.id, '2'); assert.equal(element('#modal').open, true);
imageError = false;
await submit('product-form', newValues, createDataset);
assert.equal(productList.length, 2); assert.equal(productList[1].status, 'active'); assert.equal(productList[1].brand_id, 1);
assert.equal(productList[1].product_images.length, 2);
assert.match(element('#table-content').innerHTML, /src="http:\/\/127\.0\.0\.1:8000\/media\/products\//);
assert.equal(requests.filter(r => r.path === '/staff/catalog/products' && r.method === 'POST').length, 1);
assert.match(productDetailsHtml(productList[1]), /data-gallery-count="2"/);
assert.match(productImageUrl(productList[1]), /^http:\/\/127\.0\.0\.1:8000\/media\/products\//);
assert.equal(productImageUrl({ product_images: [{ image_url: 'javascript:alert(1)' }] }), '');
assert.throws(() => validateProductImage({ type: 'image/svg+xml', size: 100 }), /JPG/);
assert.throws(() => validateProductImage({ type: 'image/png', size: 6 * 1024 * 1024 }), /5 MB/);
await click({ deleteProduct: '2' }); assert.match(element('#modal').innerHTML, /Xác nhận xóa/); assert.equal(productList[1].status, 'active');
await click({ action: 'close' }); assert.equal(productList[1].status, 'active'); // Cancel never sends DELETE.
await click({ deleteProduct: '2' }); await submit('delete-product-form', {}, { id: '2' });
assert.equal(productList[1].status, 'archived'); assert.doesNotMatch(element('#table-content').innerHTML, /Sản phẩm mới/);
await handlers.change({ target: { id: 'status-filter', value: 'archived' } }); assert.match(element('#table-content').innerHTML, /Sản phẩm mới/);
await click({ editProduct: '2' }); await submit('product-form', { ...editedValues, name: 'Đã khôi phục', slug: 'da-khoi-phuc', status: 'active' }, { id: '2' }); assert.equal(productList[1].status, 'active');
productError = true; await click({ action: 'new-product' }); await submit('product-form', editedValues); assert.match(element('#test-form-error').textContent, /Đường dẫn đã tồn tại/); assert.equal(element('#modal').open, true); productError = false;
await submit('product-category-form', { name: 'Danh mục mới', slug: 'danh-muc-moi', parent_id: '2' }); assert.match(element('#modal').innerHTML, /value="50" selected/);
assert.equal(requests.findLast(r => r.path === '/staff/catalog/categories' && r.method === 'POST').body.includes('"parent_id":2'), true);
assert.equal(slugify('  Áo Sơ Mi Đẹp! '), 'ao-so-mi-dep');
assert.deepEqual(productPayload({ ...editedValues, material: ' ', description: ' ' }), { ...editedValues, category_id: 1, brand_id: null, material: null, description: null });
const hostile = { ...product, name: '\"><img src=x onerror=alert(1)>', description: '</textarea><script>alert(1)</script>' };
assert.doesNotMatch(productEditorHtml(hostile, [], []), /<script>|<img src=x/);
assert.doesNotMatch(productDetailsHtml(hostile), /<script>|<img src=x/);
await navigate('orders'); expired = true; await navigate('orders'); assert.equal(sessionStorage.getItem('freedom-token'), null); assert.match(element('#app').innerHTML, /Đăng nhập quản trị/); assert.doesNotMatch(element('#app').innerHTML, /class="ad-sidebar"/);
expired = false; sessionStorage.setItem('freedom-token', 'admin-token'); forceForbidden = true; await navigate('orders'); assert.match(element('#app').innerHTML, /Không có quyền truy cập/); assert.doesNotMatch(element('#app').innerHTML, /class="ad-sidebar"/); forceForbidden = false;
await navigate('orders'); await click({ action: 'logout' }); assert.equal(sessionStorage.getItem('freedom-token'), null); assert.equal(location.hash, '#/store'); assert.doesNotMatch(element('#app').innerHTML, /class="ad-sidebar"/);
product.product_images = productList[1].product_images;
await navigate('store'); assert.match(element('#app').innerHTML, /href="#\/store\?category=danh-muc-moi"/);
assert.match(element('#product-grid').innerHTML, /<img src="http:\/\/127\.0\.0\.1:8000\/media\/products\//);
await click({ product: '1' }); assert.match(element('#modal').innerHTML, /Sơ mi đã sửa/);
assert.match(element('#modal').innerHTML, /class="product-gallery gallery-detail" data-gallery-count="2"/);

// Exercise actual delegated handlers for cart selection and both order methods.
actor = { id: 20, role: 'customer', status: 'active', full_name: 'Khách mua thật', email: 'customer@example.com', permissions: [] };
sessionStorage.setItem('freedom-token', 'customer-token');
await navigate('orders'); await navigate('store');
product.product_variants = [{ id: 10, size_name: 'M', color_name: 'Đen', price: 500000, stock_quantity: 20, reserved_quantity: 0, is_active: true }];
await click({ product: '1' }); assert.match(element('#modal').innerHTML, /Size M/);
await submit('add-cart-form', { variant_id: '10', quantity: '2' });
assert.equal(testCart[0].quantity, 2); assert.equal(element('#cart-count').textContent, 2);
testCart.push({ ...testCart[0], variant_id: 11, size_name: 'L', quantity: 1 });
await click({ action: 'cart' });
assert.equal(element('#cart-checkout-actions').hidden, true);
await click({ action: 'checkout-delivery' });
assert.equal(testOrders.length, 0); assert.match(element('#toast').textContent, /Chọn ít nhất/);
await handlers.change({ target: { dataset: { cartSelect: '10' }, checked: true } });
assert.equal(element('#cart-checkout-actions').hidden, false);
await click({ action: 'checkout-delivery' });
assert.match(element('#modal').innerHTML, /Xác nhận đặt hàng/); assert.match(element('#modal').innerHTML, /name="shipping_address"/);
assert.equal(requests.filter(request => request.path === '/me/checkout').length, 0);
const receiver = { recipient_name: 'Người nhận', recipient_phone: '0912345678', shipping_address: '10 Tràng Tiền, Hà Nội', customer_note: '' };
checkoutFailure = true; await submit('checkout-form', receiver);
assert.match(element('#test-form-error').textContent, /Mạng chậm/);
const firstKey = JSON.parse(requests.findLast(request => request.path === '/me/checkout').body).checkout_key;
checkoutFailure = false; await submit('checkout-form', receiver);
assert.equal(testOrders.length, 1); assert.deepEqual(testOrders[0].variant_ids, [10]); assert.equal(testOrders[0].checkout_key, firstKey);
assert.equal(testCart.length, 1); assert.equal(testCart[0].variant_id, 11); assert.equal(element('#cart-count').textContent, 1);
await click({ action: 'cart' }); await handlers.change({ target: { dataset: { cartSelect: '11' }, checked: true } });
await click({ action: 'checkout-pickup' }); assert.match(element('#modal').innerHTML, /name="pickup_date"/); assert.match(element('#modal').innerHTML, /name="pickup_to"/);
await submit('checkout-form', { recipient_name: 'Người lấy', recipient_phone: '0912345678', recipient_email: 'customer@example.com', pickup_date: '2030-01-01', pickup_from: '09:00', pickup_to: '10:00', customer_note: '' });
assert.equal(testOrders.length, 2); assert.equal(testOrders[1].fulfillment_method, 'pickup'); assert.match(testOrders[1].pickup_start, /\+07:00$/);
assert.match(element('#modal').innerHTML, /Đã đặt trước thành công/); assert.equal(element('#cart-count').textContent, 0);
await click({ action: 'my-orders' }); assert.match(element('#modal').innerHTML, /FR-NEW-0/); assert.match(element('#modal').innerHTML, /FR-NEW-1/);
testOrders[0].status = 'packing'; await click({ myOrder: '100' });
assert.match(element('#modal').innerHTML, /status-blue/); assert.match(element('#modal').innerHTML, /Đang đóng gói/);
testOrders[0].status = 'shipping'; await click({ myOrder: '100' }); assert.match(element('#modal').innerHTML, /status-yellow/);
testOrders[0].status = 'failed'; await click({ myOrder: '100' }); assert.match(element('#modal').innerHTML, /status-red/);
testOrders[0].status = 'delivered'; await click({ myOrder: '100' }); assert.match(element('#modal').innerHTML, /status-green/);
globalThis.fetch = async () => { throw new Error('offline'); };
await assert.rejects(api('/ready'), /Không kết nối được cửa hàng/);
console.log('PASS: RBAC, product CRUD, images, selected cart checkout, recipient confirmation, pickup scheduling, retry key, remaining cart and customer order statuses. Simulated DOM/API, not browser QA.');
await import('./verify-gallery.mjs');
process.exit(0);

assert.match(deleteProductHtml(product, true), /value="soft" selected/);
assert.match(deleteProductHtml(product, true), /value="hard"/);
assert.doesNotMatch(deleteProductHtml(product, false), /value="hard"/);
assert.ok(requests.some(r => r.method === 'DELETE' && r.url.endsWith('?mode=soft')));
