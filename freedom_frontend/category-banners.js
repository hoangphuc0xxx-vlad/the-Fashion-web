import { categoryPath, categoryHref } from './categories.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const categoryBanners = Object.freeze({
  ao: {
    image: 'assets/category-ao-v1.png',
    eyebrow: 'THE EVERYDAY TOPS',
    description: 'Từ sơ mi chỉn chu đến những lớp áo thoải mái — lựa chọn phù hợp cho mỗi ngày.',
    alt: 'Phong cách áo nam Freedom với sơ mi Oxford xanh nhạt',
  },
  quan: {
    image: 'assets/category-quan-v1.png',
    eyebrow: 'A BETTER EVERYDAY FIT',
    description: 'Phom dáng gọn gàng, dễ phối cùng những món đồ bạn yêu thích.',
    alt: 'Quần chino màu olive cùng giày trắng trong bộ sưu tập Freedom',
  },
  suit: {
    image: 'assets/category-suit-v1.png',
    eyebrow: 'EFFORTLESSLY REFINED',
    description: 'Đường nét tinh tế cho những khoảnh khắc cần sự chỉn chu.',
    alt: 'Phong cách suit nam màu charcoal cùng sơ mi sáng màu',
  },
});

export function categoryBannerHtml(categories, selected) {
  if (!selected) return '';
  const root = categoryPath(categories, selected.id)[0];
  if (!root || !Object.hasOwn(categoryBanners, root.slug)) return '';
  const banner = categoryBanners[root.slug];
  return `<section class="category-hero category-hero-${root.slug}" aria-labelledby="category-hero-title">
    <div class="category-hero-copy"><span class="store-eyebrow">FREEDOM / ${esc(banner.eyebrow)}</span>
      <h1 id="category-hero-title">${esc(selected.name)}</h1><p>${esc(banner.description)}</p>
      <a class="store-primary" href="${categoryHref(selected)}" data-scroll="collection">Khám phá bộ sưu tập <span aria-hidden="true">→</span></a>
    </div><div class="category-hero-media"><img src="${banner.image}" alt="${esc(banner.alt)}" width="1536" height="1024" loading="eager" fetchpriority="high" decoding="async"></div>
  </section>`;
}
