import { mainCategories, categoryHref } from './categories.js';

const homeBanners = {
  ao: { description: 'Tự do trong từng lớp áo.', alt: 'Áo overshirt navy phối cùng áo thun trắng trong studio hiện đại' },
  quan: { description: 'Phom dáng cho mọi chuyển động.', alt: 'Quần âu beige phối áo đen và giày loafer trên phố' },
  suit: { description: 'Bản lĩnh trong từng đường nét.', alt: 'Quý ông diện suit xanh navy trước tòa nhà kính hiện đại' },
};

export function homeCategoryBannersHtml() {
  return `<section class="home-categories" aria-labelledby="home-categories-title">
    <div class="home-categories-heading"><span class="store-eyebrow">FREEDOM COLLECTIONS</span><h2 id="home-categories-title">Phong cách của riêng bạn.</h2><p>Ba lựa chọn. Muôn cách thể hiện bản lĩnh.</p></div>
    <div class="home-category-grid">${mainCategories.map(category => {
      const banner = homeBanners[category.slug];
      return `<a class="home-category-card" href="${categoryHref(category)}" aria-labelledby="home-category-${category.slug}">
        <img src="assets/home-category-${category.slug}-v1.png" alt="${banner.alt}" width="1024" height="1536" loading="lazy" decoding="async">
        <div class="home-category-copy"><h3 id="home-category-${category.slug}">${category.name}</h3><p>${banner.description}</p><span>Khám phá danh mục <span aria-hidden="true">↗</span></span></div>
      </a>`;
    }).join('')}</div>
  </section>`;
}

export function storeFooterHtml() {
  return `<footer class="store-footer">
    <div class="store-footer-main">
      <div class="store-footer-brand"><a class="store-logo" href="#/store" aria-label="Freedom — Trang chủ">freedom<sup>®</sup></a><p>Freedom — thương hiệu thời trang nam mạnh mẽ, mang đến sự tự do cho quý ông.</p></div>
      <div class="store-footer-contact"><h2>Thông tin cửa hàng</h2><address><p><strong>Trụ sở</strong><span>Số 69 phố Tràng Tiền, TP. Hà Nội</span></p><p><strong>Điện thoại</strong><a href="tel:0123699999">0123699999</a></p><p><strong>Email</strong><a href="mailto:freeshion69trangtien@gmail.com">freeshion69trangtien@gmail.com</a></p></address></div>
      <nav class="store-footer-categories" aria-label="Danh mục ở cuối trang"><h2>Bộ sưu tập</h2>${mainCategories.map(category => `<a href="${categoryHref(category)}">${category.name}</a>`).join('')}</nav>
    </div>
    <div class="store-footer-bottom"><span>© ${new Date().getFullYear()} Freedom</span><span>Tự do thể hiện. Mạnh mẽ là chính mình.</span></div>
  </footer>`;
}
