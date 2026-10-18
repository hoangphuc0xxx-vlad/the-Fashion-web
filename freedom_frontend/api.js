// Deployment configuration only. Browser storage cannot enable demo mode or change API origin.
const apiBase = globalThis.FREEDOM_CONFIG?.apiBase || 'http://127.0.0.1:8000';
const parsed = new URL(apiBase, globalThis.location?.href || 'http://localhost:5173/');
if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash) throw new Error('FREEDOM_API_BASE không hợp lệ');
export const config = Object.freeze({ mode: 'api', base: parsed.href.replace(/\/+$/, '') });
export function imageUrl(value) {
  if (!value) return '';
  try {
    const url = new URL(String(value).startsWith('/media/products/') ? config.base + value : value, globalThis.location.href);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export async function api(route, { method = 'GET', body, form, timeout = 12000 } = {}) {
  const headers = {};
  const token = sessionStorage.getItem('freedom-token');
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch(config.base + route, { method, headers, body: form || (body ? JSON.stringify(body) : undefined), signal: AbortSignal.timeout(timeout) });
  } catch { throw new ApiError('Không kết nối được cửa hàng. Vui lòng thử lại sau.', 0); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && route !== '/auth/token') {
      sessionStorage.removeItem('freedom-token');
      globalThis.dispatchEvent?.(new Event('freedom:session-expired'));
    }
    if (res.status === 403) globalThis.dispatchEvent?.(new Event('freedom:access-denied'));
    const detail = Array.isArray(data.detail) ? data.detail.map(x => `${x.loc?.slice(1).join('.')}: ${x.msg}`).join('; ') : data.detail;
    throw new ApiError(detail || (res.status === 403 ? 'Tài khoản chưa có quyền truy cập mục này.' : `Yêu cầu thất bại (${res.status}).`), res.status);
  }
  return data;
}
