import { categoryOptionsHtml } from './categories.js';
import { imageUrl } from './api.js';
import { galleryHtml } from './gallery.js';
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = v => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(Number(v || 0));
export const productStatuses = { draft: 'Bản nháp', active: 'Đang bán', archived: 'Đã xóa / lưu trữ' };
export function productImageUrl(product) {
  const images = product?.product_images || [];
  return imageUrl(images.find(image => image.is_primary)?.image_url || images[0]?.image_url);
}
export function validateProductImage(file) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP.');
  if (!file.size || file.size > 5 * 1024 * 1024) throw new Error('Chọn ảnh có dung lượng tối đa 5 MB.');
}
export function productImagePreviewHtml(product, pending) {
  const images = pending || (product?.product_images || []).map(image => ({ url: imageUrl(image.image_url), name: image.is_primary ? 'Ảnh đại diện hiện tại' : 'Ảnh đã lưu' })).filter(image => image.url);
  return `${images.length ? `<div class="product-preview-grid">${images.map((image, index) => `<figure><img src="${esc(image.url)}" alt="Ảnh sản phẩm ${index + 1}"><figcaption>${esc(image.name)}${pending && index === 0 ? ' · Ảnh đại diện' : ''}</figcaption></figure>`).join('')}</div>` : '<p class="ad-form-note">Chưa có ảnh sản phẩm.</p>'}${pending ? '<button type="button" class="text-action" data-action="clear-product-image">Bỏ bộ ảnh vừa chọn</button>' : ''}`;
}
export function slugify(value) {
  return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
export function productPayload(values) {
  return {
    name: values.name.trim(), slug: values.slug.trim(), category_id: Number(values.category_id),
    brand_id: values.brand_id ? Number(values.brand_id) : null,
    base_price: values.base_price, material: values.material.trim() || null,
    description: values.description.trim() || null, status: values.status,
  };
}
export function variantRowHtml(variant = {}, price = '') {
  return `<div class="size-editor-row" data-variant-row data-id="${esc(variant.id || '')}" data-stock="${esc(variant.stock_quantity ?? '')}"><div class="form-grid"><label>Size<input data-size-name list="product-size-options" maxlength="30" value="${esc(variant.size_name)}" placeholder="S, M, L, XL, 30, 32…" ${variant.id ? 'readonly' : ''} required></label><label>Màu<input data-color-name maxlength="60" value="${esc(variant.color_name || 'Mặc định')}" ${variant.id ? 'readonly' : ''} required></label></div><div class="form-grid"><label>Giá bán (₫)<input data-variant-price type="number" min="0" max="9999999999999.99" step="0.01" value="${esc(variant.price ?? price)}" required></label><label>Số lượng trong kho<input data-variant-stock type="number" min="${Number(variant.reserved_quantity || 0)}" max="1000000" step="1" value="${esc(variant.stock_quantity ?? 0)}" required></label></div><label class="size-active"><input data-variant-active type="checkbox" ${variant.is_active !== false ? 'checked' : ''}> Đang bán size này</label>${variant.id ? '<small>Size/màu cũ được giữ để bảo toàn lịch sử đơn. Bỏ chọn để ngừng bán.</small>' : '<button type="button" class="text-action" data-action="remove-size-row">Bỏ dòng size</button>'}</div>`;
}
export function readProductVariants(form) {
  const rows = [...form.querySelectorAll('[data-variant-row]')];
  if (!rows.length) return undefined;
  return rows.map(row => ({ ...(row.dataset.id ? { id: Number(row.dataset.id), expected_stock: Number(row.dataset.stock) } : {}), size_name: row.querySelector('[data-size-name]').value.trim(), color_name: row.querySelector('[data-color-name]').value.trim(), price: row.querySelector('[data-variant-price]').value, stock_quantity: Number(row.querySelector('[data-variant-stock]').value), is_active: row.querySelector('[data-variant-active]').checked }));
}
function lookupOptions(items, selected, fallback, empty = false) {
  const choices = [...items];
  if (selected && !choices.some(i => String(i.id) === String(selected))) choices.push({ id: selected, name: fallback || `#${selected} (đã ngừng dùng)` });
  return (empty ? '<option value="">Không có thương hiệu</option>' : '<option value="" disabled>Chọn danh mục</option>') + choices.map(i => `<option value="${esc(i.id)}" ${String(i.id) === String(selected) ? 'selected' : ''}>${esc(i.name)}</option>`).join('');
}
export function productEditorHtml(product, categories, brands, pendingImage = null) {
  const p = product || {};
  return `<form id="product-form" data-id="${esc(p.id || '')}">
    <label>Tên sản phẩm<input name="name" value="${esc(p.name)}" maxlength="255" required></label>
    <label>Đường dẫn (slug)<input name="slug" value="${esc(p.slug)}" data-auto="${!p.slug}" maxlength="280" placeholder="so-mi-linen-essential" required></label>
    <div class="form-grid"><label>Danh mục sản phẩm<select name="category_id" required>${categoryOptionsHtml(categories, p.category_id || categories.find(c => c.slug === 'ao')?.id || categories[0]?.id, p.category?.name)}</select></label><label>Thương hiệu<select name="brand_id">${lookupOptions(brands, p.brand_id, p.brand?.name, true)}</select></label></div>
    <button type="button" class="text-action" data-action="new-product-category">+ Tạo danh mục mới</button>
    <div class="form-grid"><label>Giá niêm yết (₫)<input name="base_price" value="${esc(p.base_price)}" type="number" min="0" max="9999999999999.99" step="0.01" required></label><label>Trạng thái<select name="status">${Object.entries(productStatuses).map(([key, name]) => `<option value="${key}" ${(p.status || 'draft') === key ? 'selected' : ''}>${name}</option>`).join('')}</select></label></div>
    <label>Chất liệu<input name="material" value="${esc(p.material)}" maxlength="150"></label>
    <label>Mô tả<textarea name="description" rows="5" maxlength="50000">${esc(p.description)}</textarea></label>
    <fieldset class="product-size-editor"><legend>Size, màu và tồn kho</legend><p class="ad-form-note">Thêm từng size để khách chọn mua. Nhập tồn thực tế; số lượng sẽ trừ khi khách xác nhận đơn.</p><datalist id="product-size-options">${['XS','S','M','L','XL','XXL','3XL','28','29','30','31','32','33','34','36','38','40','42','44','46','48','50','52'].map(size => `<option value="${size}"></option>`).join('')}</datalist><div id="product-size-rows">${((p.variants || p.product_variants || []).length ? p.variants || p.product_variants : [{}]).map(variant => variantRowHtml(variant, p.base_price)).join('')}</div><p class="stock-total">Tổng số lượng trong kho: <strong id="product-stock-total">${(p.variants || p.product_variants || []).reduce((sum, variant) => sum + Number(variant.stock_quantity || 0), 0)}</strong></p><button type="button" class="text-action" data-action="add-size-row">+ Thêm size / màu</button></fieldset>
    <fieldset class="product-image-editor"><legend>Ảnh sản phẩm</legend><div id="product-image-preview" class="product-image-preview" aria-live="polite">${productImagePreviewHtml(p, pendingImage)}</div><label>Chọn một hoặc nhiều ảnh từ máy<input id="product-image-file" name="image_file" type="file" accept="image/jpeg,image/png,image/webp" multiple aria-describedby="product-image-help"></label><p id="product-image-help" class="ad-form-note">Chọn tối đa 8 ảnh mỗi lần, JPG/PNG/WebP, mỗi ảnh tối đa 5 MB. Ảnh đầu tiên làm ảnh đại diện; các ảnh tự trượt trên thẻ sản phẩm, tên và giá giữ nguyên bên dưới. Bộ ảnh mới được thêm khi lưu, ảnh đã có vẫn được giữ.</p></fieldset>
    <p class="ad-form-note">Chọn Đang bán để hiển thị sản phẩm. Khách mua được những size đang bán và còn tồn kho.</p>
    <p class="form-error" role="alert"></p><div class="inline-actions"><button type="submit" class="ad-btn ad-btn-primary">${p.id ? 'Lưu thay đổi' : 'Thêm sản phẩm'}</button><button type="button" class="ad-btn" data-action="close">Hủy</button></div>
  </form>`;
}
export function productDetailsHtml(p) {
  const status = productStatuses[p.status] || p.status;
  return `<div class="product-details">${galleryHtml(p) || '<p class="ad-form-note">Sản phẩm chưa có ảnh đại diện.</p>'}<div class="product-detail-title"><span class="ad-badge">${esc(status)}</span><strong>${money(p.base_price)}</strong></div>
    <dl class="record-details">${[['Mã sản phẩm', '#' + p.id], ['Tên sản phẩm', p.name], ['Đường dẫn', p.slug], ['Danh mục', p.category?.name || '#' + p.category_id], ['Thương hiệu', p.brand?.name || 'Không có'], ['Chất liệu', p.material || 'Chưa cập nhật']].map(([name, value]) => `<div><dt>${name}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>
    <h3>Mô tả</h3><p class="product-description">${esc(p.description || 'Chưa có mô tả.')}</p>
    <h3>Biến thể (${p.product_variants?.length || 0})</h3>${p.product_variants?.length ? `<div class="ad-table-scroll"><table class="ad-table"><thead><tr><th>SKU</th><th>Giá bán</th><th>Tồn khả dụng</th><th>Trạng thái</th></tr></thead><tbody>${p.product_variants.map(v => `<tr><td>${esc(v.sku)}</td><td>${money(v.price)}</td><td>${Number(v.stock_quantity) - Number(v.reserved_quantity)}</td><td>${v.is_active ? 'Hoạt động' : 'Ngừng bán'}</td></tr>`).join('')}</tbody></table></div>` : '<p>Chưa có biến thể.</p>'}
    <div class="inline-actions"><button class="ad-btn ad-btn-primary" data-edit-product="${p.id}">Sửa sản phẩm</button>${p.status !== 'archived' ? `<button class="ad-btn danger-outline" data-delete-product="${p.id}">Xóa sản phẩm</button>` : '<small>Để khôi phục, sửa trạng thái về Bản nháp hoặc Đang bán.</small>'}</div></div>`;
}
export function deleteProductHtml(p) {
  return `<form id="delete-product-form" data-id="${p.id}"><p>Bạn muốn xóa sản phẩm <strong>${esc(p.name)}</strong>?</p><p class="ad-form-note">Sản phẩm sẽ ngừng xuất hiện tại cửa hàng và được chuyển sang lưu trữ. Lịch sử đơn hàng được giữ nguyên. Bạn có thể khôi phục trong bộ lọc “Đã xóa / lưu trữ”.</p><p class="form-error" role="alert"></p><div class="inline-actions"><button type="submit" class="ad-btn danger-btn">Xác nhận xóa</button><button type="button" class="ad-btn" data-action="close">Hủy</button></div></form>`;
}
