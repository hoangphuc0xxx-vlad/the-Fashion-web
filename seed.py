"""Nạp dữ liệu mẫu cho Freedom qua API (có kiểm tra hợp lệ của backend).

Cách chạy (server uvicorn phải đang chạy ở cổng 8000):
    python seed.py

Có thể chạy lại nhiều lần: mục nào đã có thì bỏ qua, không tạo trùng.
Sửa các danh sách trong phần "DỮ LIỆU" bên dưới cho khớp giao diện của bạn.
"""
import sys
from getpass import getpass

import httpx

API = "http://127.0.0.1:8000"
ADMIN_EMAIL = "admin@freedom.com"

# ===================== DỮ LIỆU (sửa cho khớp giao diện) =====================
CATEGORIES = [  # (tên, slug)  - khớp 4 danh mục trên index.html
    ("Áo sơ mi", "ao-so-mi"),
    ("Áo polo", "ao-polo"),
    ("Quần dài", "quan-dai"),
    ("Áo khoác", "ao-khoac"),
]
BRAND = ("Freedom", "freedom")
SIZES = ["S", "M", "L", "XL"]
COLORS = [("Be", "#E5E0D8"), ("Đen", "#1A1A1A"), ("Xanh nhạt", "#C2D4E0"),
          ("Xanh sage", "#949F8E"), ("Trắng", "#FFFFFF")]

# (tên PHẢI giống hệt tên trên index.html, slug, slug danh mục, giá VND, chất liệu, mô tả, màu)
PRODUCTS = [
    ("Utility Jacket", "utility-jacket", "ao-khoac", 899000, "Cotton canvas",
     "Áo khoác utility phong cách tối giản.", ["Be", "Đen", "Xanh sage"]),
    ("Sơ mi Linen Essential", "so-mi-linen-essential", "ao-so-mi", 549000, "Linen",
     "Sơ mi linen thoáng mát.", ["Be", "Đen", "Xanh nhạt"]),
    ("Polo Cotton Signature", "polo-cotton-signature", "ao-polo", 399000, "Cotton",
     "Áo polo cotton cổ dệt.", ["Xanh sage", "Đen", "Trắng"]),
    ("Sơ mi Oxford Relaxed", "so-mi-oxford-relaxed", "ao-so-mi", 599000, "Oxford cotton",
     "Sơ mi Oxford dáng relaxed.", ["Xanh nhạt", "Trắng", "Đen"]),
    ("Quần Chino Daily", "quan-chino-daily", "quan-dai", 649000, "Chino",
     "Quần chino mặc hằng ngày.", ["Be", "Đen", "Xanh sage"]),
]
STOCK_PER_VARIANT = 50

COUPONS = [  # (mã, loại, giá trị, đơn tối thiểu)
    ("FREEDOM10", "percent", 10, 300000),
    ("GIAM50K", "fixed", 50000, 500000),
]
# ============================================================================


def die(msg):
    print("LỖI:", msg)
    sys.exit(1)


def check(r, what):
    if r.status_code >= 400:
        die(f"{what}: HTTP {r.status_code} - {r.text[:300]}")
    return r


def main():
    password = getpass(f"Mật khẩu Admin của {ADMIN_EMAIL}: ")
    c = httpx.Client(base_url=API, timeout=30)

    r = c.post("/auth/token", data={"username": ADMIN_EMAIL, "password": password})
    if r.status_code != 200:
        die("Đăng nhập thất bại (sai mật khẩu, hoặc server chưa chạy ở cổng 8000)")
    c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
    print("Đăng nhập OK")

    def existing(name, key):
        """Trả về {giá trị key: id} của những dòng đã có."""
        out, offset = {}, 0
        while True:
            rows = check(c.get(f"/staff/catalog/{name}", params={"limit": 100, "offset": offset}),
                         f"đọc {name}").json()
            for row in rows:
                out[row[key]] = row["id"]
            if len(rows) < 100:
                return out
            offset += 100

    def ensure(name, key, body):
        have = existing(name, key)
        if body[key] in have:
            return have[body[key]]
        row = check(c.post(f"/staff/catalog/{name}", json=body), f"tạo {name} {body[key]}").json()
        print(f"  + {name}: {body[key]}")
        return row["id"]

    print("Danh mục / thương hiệu / size / màu")
    cat_id = {slug: ensure("categories", "slug", {"name": n, "slug": slug}) for n, slug in CATEGORIES}
    brand_id = ensure("brands", "slug", {"name": BRAND[0], "slug": BRAND[1]})
    size_id = {n: ensure("sizes", "name", {"name": n, "sort_order": i}) for i, n in enumerate(SIZES)}
    color_id = {n: ensure("colors", "name", {"name": n, "hex_code": hx}) for n, hx in COLORS}

    print("Sản phẩm / biến thể / tồn kho")
    for name, slug, cat, price, material, desc, colors in PRODUCTS:
        pid = ensure("products", "slug", {
            "category_id": cat_id[cat], "brand_id": brand_id, "name": name, "slug": slug,
            "description": desc, "material": material, "base_price": price, "status": "active"})
        have_skus = existing("product_variants", "sku")
        for s in SIZES:
            for col in colors:
                sku = f"{slug}-{s}-{col}".upper().replace(" ", "")
                sku = sku.encode("ascii", "ignore").decode() or f"{slug}-{s}".upper()
                if sku in have_skus:
                    continue
                v = check(c.post("/staff/catalog/product_variants", json={
                    "product_id": pid, "size_id": size_id[s], "color_id": color_id[col],
                    "sku": sku, "price": price}), f"tạo biến thể {sku}").json()
                check(c.post(f"/staff/inventory/{v['id']}/adjust",
                             json={"quantity_change": STOCK_PER_VARIANT, "note": "Nhập tồn ban đầu (seed)"}),
                      f"nhập tồn {sku}")
                print(f"  + {sku}")

    print("Voucher")
    for code, kind, value, min_order in COUPONS:
        ensure("coupons", "code", {
            "code": code, "discount_type": kind, "discount_value": value,
            "min_order_value": min_order,
            "starts_at": "2026-01-01T00:00:00+07:00", "expires_at": "2027-12-31T23:59:59+07:00"})

    print("\nXong! Thử: http://127.0.0.1:8000/catalog/products")


if __name__ == "__main__":
    main()
