import { imageUrl } from './api.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const mounted = new Map();
export function productImages(product) {
  const seen = new Set();
  return [...(product.product_images || [])].sort((a, b) => Number(Boolean(b.is_primary)) - Number(Boolean(a.is_primary)) || (a.sort_order || 0) - (b.sort_order || 0) || a.id - b.id).flatMap(image => {
    const url = imageUrl(image.image_url);
    if (!url || seen.has(url)) return [];
    seen.add(url); return [{ ...image, url }];
  });
}

export function galleryHtml(product, { card = false } = {}) {
  const images = productImages(product);
  if (!images.length) return '';
  const slide = (image, index, clone = false) => `<div class="gallery-slide" aria-hidden="${clone || index !== 0}">${card ? `<button type="button" class="gallery-open" data-product="${esc(product.id)}" tabindex="${clone || index !== 0 ? '-1' : '0'}" aria-label="Xem ${esc(product.name)}">` : ''}<img src="${esc(image.url)}" alt="${clone ? '' : esc(image.alt_text || product.name)}" loading="${index === 0 && !card ? 'eager' : 'lazy'}" decoding="async">${card ? '</button>' : ''}</div>`;
  return `<div class="product-gallery ${card ? 'gallery-card' : 'gallery-detail'}" data-gallery-count="${images.length}" role="group" aria-roledescription="bộ ảnh" aria-label="Ảnh ${esc(product.name)}">
    <div class="gallery-viewport"><div class="gallery-track">${images.map((image, index) => slide(image, index)).join('')}${images.length > 1 ? slide(images[0], 0, true) : ''}</div></div>
    ${images.length > 1 ? `<div class="gallery-controls"><button type="button" data-gallery-step="-1" aria-label="Ảnh trước">‹</button><div class="gallery-dots">${images.map((_, index) => `<button type="button" data-gallery-index="${index}" aria-label="Xem ảnh ${index + 1} trên ${images.length}" aria-pressed="${index === 0}"></button>`).join('')}</div><button type="button" data-gallery-step="1" aria-label="Ảnh tiếp theo">›</button><button type="button" class="gallery-play" data-gallery-play aria-label="Tạm dừng chuyển ảnh" aria-pressed="false">Ⅱ</button></div>` : ''}
  </div>`;
}

export function attachGallery(element) {
  const count = Number(element.dataset.galleryCount);
  if (count < 2) return () => {};
  const track = element.querySelector('.gallery-track');
  const slides = [...track.children], dots = [...element.querySelectorAll('[data-gallery-index]')];
  const play = element.querySelector('[data-gallery-play]');
  const motion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  let index = 0, moving = false, hovered = false, focused = false, paused = false, visible = true, timer, fallback;
  const listeners = [];
  function listen(target, type, callback) { target.addEventListener(type, callback); listeners.push(() => target.removeEventListener(type, callback)); }
  function finish() {
    clearTimeout(fallback);
    if (index === count) { index = 0; track.style.transition = 'none'; track.style.transform = 'translateX(0%)'; }
    moving = false;
  }
  function go(next) {
    if (moving) return;
    index = next < 0 ? count - 1 : next > count ? 0 : next;
    track.style.transition = motion?.matches ? 'none' : 'transform 650ms cubic-bezier(.22,.61,.36,1)';
    track.style.transform = `translateX(-${index * 100}%)`;
    slides.forEach((slide, i) => {
      const active = i === index % count;
      slide.setAttribute('aria-hidden', String(!active));
      const button = slide.querySelector('button'); if (button) button.tabIndex = active ? 0 : -1;
    });
    dots.forEach((dot, i) => dot.setAttribute('aria-pressed', String(i === index % count)));
    moving = true;
    if (motion?.matches) finish(); else fallback = setTimeout(finish, 750);
  }
  function schedule() {
    clearInterval(timer);
    if (!paused && !hovered && !focused && visible && !document.hidden && !motion?.matches) timer = setInterval(() => go(index + 1), 3500);
    if (play) { play.textContent = paused ? '▶' : 'Ⅱ'; play.setAttribute('aria-label', paused ? 'Tiếp tục chuyển ảnh' : 'Tạm dừng chuyển ảnh'); play.setAttribute('aria-pressed', String(paused)); }
  }
  listen(track, 'transitionend', event => { if (event.target === track && event.propertyName === 'transform') finish(); });
  listen(element, 'mouseenter', () => { hovered = true; schedule(); });
  listen(element, 'mouseleave', () => { hovered = false; schedule(); });
  listen(element, 'focusin', () => { focused = true; schedule(); });
  listen(element, 'focusout', event => { focused = element.contains(event.relatedTarget); schedule(); });
  listen(element, 'click', event => {
    const control = event.target.closest('[data-gallery-index], [data-gallery-step], [data-gallery-play]');
    if (!control) return;
    event.preventDefault(); event.stopPropagation();
    if (control.hasAttribute('data-gallery-play')) paused = !paused;
    else go(control.dataset.galleryIndex !== undefined ? Number(control.dataset.galleryIndex) : index % count + Number(control.dataset.galleryStep));
    schedule();
  });
  listen(element, 'keydown', event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault(); go(index % count + (event.key === 'ArrowRight' ? 1 : -1)); schedule();
  });
  listen(document, 'visibilitychange', schedule);
  if (motion?.addEventListener) listen(motion, 'change', schedule);
  let observer;
  if (typeof IntersectionObserver !== 'undefined') {
    observer = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; schedule(); });
    observer.observe(element);
  }
  schedule();
  return () => { clearInterval(timer); clearTimeout(fallback); observer?.disconnect(); listeners.forEach(remove => remove()); };
}

export function destroyGalleries(root) {
  for (const [element, destroy] of mounted) {
    if (!element.isConnected || root === element || root?.contains(element)) { destroy(); mounted.delete(element); }
  }
}
export function mountGalleries(root = document) {
  destroyGalleries();
  root.querySelectorAll('[data-gallery-count]').forEach(element => {
    if (!mounted.has(element) && Number(element.dataset.galleryCount) > 1) mounted.set(element, attachGallery(element));
  });
}
