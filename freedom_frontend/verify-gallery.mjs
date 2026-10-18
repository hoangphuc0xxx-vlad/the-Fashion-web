// Exercise autoplay and lifecycle with a controlled DOM and clock.
import assert from 'node:assert/strict';
import { galleryHtml, productImages, attachGallery } from './gallery.js';

globalThis.location ??= { href: 'http://localhost:5173/' };
const product = { id: 7, name: 'Áo linen', base_price: 549000, product_images: [
  { id: 1, image_url: 'https://example.com/back.jpg', is_primary: false, sort_order: 1 },
  { id: 2, image_url: 'https://example.com/front.jpg', is_primary: true, sort_order: 0 },
  { id: 3, image_url: 'javascript:alert(1)', is_primary: false },
] };
assert.equal(productImages(product)[0].url, 'https://example.com/front.jpg');
const html = galleryHtml(product, { card: true });
assert.match(html, /data-gallery-count="2"/);
assert.equal((html.match(/class="gallery-slide"/g) || []).length, 3); // Seamless end clone.
assert.doesNotMatch(html, /javascript:|549000|product-meta/); // Price stays outside the track.
assert.equal(galleryHtml({ product_images: [] }), '');
assert.doesNotMatch(galleryHtml({ ...product, product_images: [product.product_images[0]] }), /gallery-controls/);

const saved = Object.fromEntries(['window', 'document', 'setInterval', 'clearInterval', 'setTimeout', 'clearTimeout'].map(key => [key, globalThis[key]]));
const emitter = extra => ({
  events: new Map(), ...extra,
  addEventListener(type, fn) { this.events.set(type, fn); },
  removeEventListener(type) { this.events.delete(type); },
  emit(type, event = {}) { this.events.get(type)?.(event); },
});
const intervals = new Map(), timeouts = new Map(); let nextTimer = 1;
globalThis.setInterval = fn => { const id = nextTimer++; intervals.set(id, fn); return id; };
globalThis.clearInterval = id => intervals.delete(id);
globalThis.setTimeout = fn => { const id = nextTimer++; timeouts.set(id, fn); return id; };
globalThis.clearTimeout = id => timeouts.delete(id);
const motion = emitter({ matches: false });
globalThis.window = { matchMedia: () => motion };
globalThis.document = emitter({ hidden: false });
const attr = () => ({ attrs: {}, setAttribute(key, value) { this.attrs[key] = value; } });
const slides = Array.from({ length: 4 }, () => ({ ...attr(), button: {}, querySelector() { return this.button; } }));
const track = emitter({ style: {}, children: slides });
const dots = Array.from({ length: 3 }, attr), play = attr();
const element = emitter({ dataset: { galleryCount: '3' }, contains: () => false,
  querySelector: key => key === '.gallery-track' ? track : play,
  querySelectorAll: () => dots,
});
try {
  const destroy = attachGallery(element);
  const tick = () => [...intervals.values()][0]?.();
  const finish = () => track.emit('transitionend', { target: track, propertyName: 'transform' });
  assert.equal(intervals.size, 1);
  tick(); assert.equal(track.style.transform, 'translateX(-100%)'); assert.equal(dots[1].attrs['aria-pressed'], 'true');
  finish(); tick(); assert.equal(track.style.transform, 'translateX(-200%)');
  finish(); tick(); assert.equal(track.style.transform, 'translateX(-300%)');
  finish(); assert.equal(track.style.transform, 'translateX(0%)');
  element.emit('mouseenter'); assert.equal(intervals.size, 0);
  element.emit('mouseleave'); assert.equal(intervals.size, 1);
  document.hidden = true; document.emit('visibilitychange'); assert.equal(intervals.size, 0);
  document.hidden = false; document.emit('visibilitychange'); assert.equal(intervals.size, 1);
  element.emit('focusin'); assert.equal(intervals.size, 0);
  element.emit('focusout', { relatedTarget: null }); assert.equal(intervals.size, 1);
  const click = control => element.emit('click', { target: { closest: () => control }, preventDefault() {}, stopPropagation() {} });
  click({ hasAttribute: () => true }); assert.equal(intervals.size, 0);
  click({ hasAttribute: () => true }); assert.equal(intervals.size, 1);
  motion.matches = true; motion.emit('change'); assert.equal(intervals.size, 0);
  click({ hasAttribute: () => false, dataset: { galleryIndex: '2' } });
  assert.equal(track.style.transform, 'translateX(-200%)'); assert.equal(track.style.transition, 'none');
  destroy(); assert.equal(intervals.size, 0); assert.equal(timeouts.size, 0); assert.equal(element.events.size, 0);
  attachGallery({ dataset: { galleryCount: '1' } })(); assert.equal(intervals.size, 0);
} finally {
  Object.entries(saved).forEach(([key, value]) => { globalThis[key] = value; });
}
console.log('PASS: gallery autoplay moves right to left, seamless wrap, pause/resume, reduced motion, single image and cleanup.');
