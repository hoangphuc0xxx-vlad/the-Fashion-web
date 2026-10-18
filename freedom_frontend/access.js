// UI policy mirrors backend dependencies. The backend remains authoritative.
export const routePermissions = Object.freeze({
  dashboard: 'dashboard.read', orders: 'orders.manage', shipping: 'orders.manage',
  products: 'catalog.manage', categories: 'catalog.manage', brands: 'catalog.manage',
  inventory: 'inventory.read', customers: 'customers.read', coupons: 'coupons.manage',
  reviews: 'reviews.read', banners: 'content.manage', posts: 'content.manage',
  returns: 'returns.read', support: 'support.manage', users: 'users.read', audit: 'audit.read',
  settings: 'admin.only',
});
const adminOnly = new Set(['users.manage', 'payments.manage', 'reviews.moderate', 'audit.read', 'admin.only']);
export const isOperator = user => user?.status === 'active' && ['admin', 'staff'].includes(user.role);
export function can(user, permission) {
  if (!isOperator(user)) return false;
  if (user.role === 'admin') return true;
  return !adminOnly.has(permission) && Array.isArray(user.permissions) && user.permissions.includes(permission);
}
export const canVisit = (user, route) => Boolean(routePermissions[route]) && can(user, routePermissions[route]);
export const firstAdminRoute = user => Object.keys(routePermissions).find(route => canVisit(user, route));
