from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import Field, HttpUrl
from .schemas import Input

class ProductsInput(Input):
    category_id: Annotated[int, Field(gt=0)]
    brand_id: Annotated[int, Field(gt=0)] | None = None
    name: Annotated[str, Field(min_length=1,max_length=255)]
    slug: Annotated[str, Field(min_length=1,max_length=280)]
    description: Annotated[str, Field(min_length=1,max_length=50000)] | None = None
    material: Annotated[str, Field(min_length=1,max_length=150)] | None = None
    base_price: Annotated[Decimal, Field(ge=0,max_digits=15,decimal_places=2)]
    status: Literal['draft','active','archived'] = 'draft'

class ProductVariantsInput(Input):
    product_id: Annotated[int, Field(gt=0)]
    size_id: Annotated[int, Field(gt=0)]
    color_id: Annotated[int, Field(gt=0)]
    sku: Annotated[str, Field(min_length=1,max_length=80)]
    price: Annotated[Decimal, Field(ge=0,max_digits=15,decimal_places=2)]
    low_stock_threshold: Annotated[int, Field(ge=0)] = 5
    is_active: bool = True

class ProductImagesInput(Input):
    product_id: Annotated[int, Field(gt=0)]
    variant_id: Annotated[int, Field(gt=0)] | None = None
    image_url: HttpUrl
    alt_text: Annotated[str, Field(min_length=1,max_length=255)] | None = None
    sort_order: Annotated[int, Field(ge=0)] = 0
    is_primary: bool = False

class CategoriesInput(Input):
    parent_id: Annotated[int, Field(gt=0)] | None = None
    name: Annotated[str, Field(min_length=1,max_length=150)]
    slug: Annotated[str, Field(min_length=1,max_length=170)]
    is_active: bool = True

class BrandsInput(Input):
    name: Annotated[str, Field(min_length=1,max_length=150)]
    slug: Annotated[str, Field(min_length=1,max_length=170)]
    is_active: bool = True

class SizesInput(Input):
    name: Annotated[str, Field(min_length=1,max_length=30)]
    sort_order: Annotated[int, Field(ge=0)] = 0

class ColorsInput(Input):
    name: Annotated[str, Field(min_length=1,max_length=60)]
    hex_code: Annotated[str, Field(min_length=1,max_length=7)] | None = None

class CouponsInput(Input):
    code: Annotated[str, Field(min_length=1,max_length=60)]
    discount_type: Literal['percent','fixed']
    discount_value: Annotated[Decimal, Field(ge=0,max_digits=15,decimal_places=2)]
    min_order_value: Annotated[Decimal, Field(ge=0,max_digits=15,decimal_places=2)] = Decimal('0')
    max_discount: Annotated[Decimal, Field(ge=0,max_digits=15,decimal_places=2)] | None = None
    usage_limit: Annotated[int, Field(ge=0)] | None = None
    starts_at: datetime
    expires_at: datetime
    is_active: bool = True

class BannersInput(Input):
    title: Annotated[str, Field(min_length=1,max_length=255)] | None = None
    image_url: HttpUrl
    target_url: HttpUrl | None = None
    sort_order: Annotated[int, Field(ge=0)] = 0
    is_active: bool = True
    starts_at: datetime | None = None
    expires_at: datetime | None = None

class PostsInput(Input):
    title: Annotated[str, Field(min_length=1,max_length=255)]
    slug: Annotated[str, Field(min_length=1,max_length=280)]
    content: Annotated[str, Field(min_length=1,max_length=50000)]
    status: Literal['draft','published','archived'] = 'draft'
    published_at: datetime | None = None
