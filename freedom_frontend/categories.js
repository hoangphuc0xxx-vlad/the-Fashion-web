const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const mainCategories = [{ name: 'Áo', slug: 'ao' }, { name: 'Quần', slug: 'quan' }, { name: 'Suit', slug: 'suit' }];
export const categoryHref = category => '#/store?category=' + encodeURIComponent(category.slug);
export function categoryPath(categories, id) {
  const map = new Map(categories.map(c => [String(c.id), c])); const path = [], seen = new Set();
  let current = map.get(String(id));
  while (current && !seen.has(String(current.id))) { path.unshift(current); seen.add(String(current.id)); current = map.get(String(current.parent_id)); }
  return path;
}
export function visibleCategories(categories) {
  const map = new Map(categories.map(c => [String(c.id), c]));
  return categories.filter(c => {
    const seen = new Set(); let node = c;
    while (node) {
      if (node.is_active === false || seen.has(String(node.id))) return false;
      seen.add(String(node.id));
      if (node.parent_id == null) return true;
      node = map.get(String(node.parent_id));
    }
    return false;
  });
}
function descendants(categories, parent, depth = 0, seen = new Set()) {
  if (seen.has(String(parent))) return [];
  const visited = new Set(seen).add(String(parent));
  return categories.filter(c => String(c.parent_id) === String(parent)).flatMap(c => [{ ...c, depth }, ...descendants(categories, c.id, depth + 1, visited)]);
}
export function categoryNavHtml(categories, selected) {
  const visible = visibleCategories(categories);
  return `<nav class="store-category-nav" aria-label="Danh mục thời trang nam">${mainCategories.map(main => {
    const root = visible.find(c => c.parent_id == null && c.slug === main.slug);
    const branch = root ? descendants(visible, root.id) : [];
    const active = root && categoryPath(visible, selected?.id).some(c => c.id === root.id);
    return `<details class="category-menu ${active ? 'selected' : ''}"><summary>${main.name}<span aria-hidden="true">⌄</span></summary><div class="category-dropdown"><a class="category-all" href="${categoryHref(main)}">Tất cả ${main.name.toLocaleLowerCase('vi')}</a>${branch.length ? branch.map(c => `<a href="${categoryHref(c)}" style="--category-depth:${c.depth}" ${String(c.id) === String(selected?.id) ? 'aria-current="page"' : ''}>${esc(c.name)}</a>`).join('') : '<span class="category-no-children">Chưa có danh mục con.</span>'}</div></details>`;
  }).join('')}</nav>`;
}
export function categoryFiltersHtml(categories, selected) {
  const visible = visibleCategories(categories);
  const roots = mainCategories.map(main => visible.find(c => c.parent_id == null && c.slug === main.slug)).filter(Boolean);
  const parent = selected && (visible.some(c => String(c.parent_id) === String(selected.id)) ? selected.id : selected.parent_id);
  const children = selected && parent != null ? visible.filter(c => String(c.parent_id) === String(parent)) : [];
  return `<div class="category-primary-links"><a href="#/store" class="${!selected ? 'active' : ''}">Tất cả</a>${roots.map(c => `<a href="${categoryHref(c)}" class="${categoryPath(visible, selected?.id).some(p => p.id === c.id) ? 'active' : ''}">${esc(c.name)}</a>`).join('')}</div>${children.length ? `<div class="category-child-links" aria-label="Danh mục con">${children.map(c => `<a href="${categoryHref(c)}" class="${String(c.id) === String(selected?.id) ? 'active' : ''}">${esc(c.name)}</a>`).join('')}</div>` : ''}`;
}
export function categoryOptionsHtml(categories, selected, fallback = '') {
  const visible = visibleCategories(categories);
  const orderedRoots = visible.filter(c => c.parent_id == null).sort((a, b) => {
    const ai = mainCategories.findIndex(c => c.slug === a.slug), bi = mainCategories.findIndex(c => c.slug === b.slug);
    return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
  });
  const rows = orderedRoots.flatMap(c => [c, ...descendants(visible, c.id)]);
  if (selected && !rows.some(c => String(c.id) === String(selected))) rows.push({ id: selected, name: fallback || `#${selected} (đã ngừng dùng)` });
  return '<option value="" disabled>Chọn danh mục</option>' + rows.map(c => `<option value="${esc(c.id)}" ${String(c.id) === String(selected) ? 'selected' : ''}>${esc(categoryPath(visible, c.id).map(p => p.name).join(' → ') || c.name)}</option>`).join('');
}
export function categoryFormHtml(categories, selectedParent, returnToProduct = true) {
  const path = categoryPath(categories, selectedParent);
  const parent = path[0]?.id || categories.find(c => c.slug === 'ao' && c.parent_id == null)?.id;
  return `<form id="product-category-form" data-return-product="${returnToProduct}"><label>Thuộc danh mục cha<select name="parent_id" required>${categoryOptionsHtml(categories, parent)}</select></label><label>Tên danh mục con<input name="name" maxlength="150" placeholder="Ví dụ: Áo sơ mi, Áo khoác, Hoodie…" required></label><label>Đường dẫn<input name="slug" maxlength="170" data-auto="true" required></label><p class="ad-form-note">Sau khi tạo, danh mục con có liên kết riêng trong menu cửa hàng. Chọn đúng danh mục cha để đặt vào Áo, Quần hoặc Suit.</p><p class="form-error" role="alert"></p><div class="inline-actions"><button type="submit" class="ad-btn ad-btn-primary">${returnToProduct ? 'Tạo và chọn cho sản phẩm' : 'Tạo danh mục'}</button><button type="button" class="ad-btn" data-action="${returnToProduct ? 'back-product-editor' : 'close'}">Hủy</button></div></form>`;
}
