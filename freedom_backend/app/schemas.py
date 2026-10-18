from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints, model_validator

Text = Annotated[str, Field(min_length=1, max_length=150)]
Password = Annotated[str, StringConstraints(strip_whitespace=False), Field(min_length=12, max_length=128)]
Positive = Annotated[int, Field(gt=0)]
Money = Annotated[Decimal, Field(ge=0, max_digits=15, decimal_places=2)]
class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class Register(Input):
    full_name: Text
    email: EmailStr
    password: Password
class Profile(Input):
    full_name: Text
    phone: Annotated[str, Field(min_length=8,max_length=20)] | None = None
    avatar_url: HttpUrl | None = None
class ChangePassword(Input):
    old_password: str
    new_password: Password
class Forgot(Input):
    email: EmailStr
class Reset(Input):
    token: Annotated[str,Field(min_length=20,max_length=200)]
    new_password: Password
class Address(Input):
    recipient_name: Text
    phone: Annotated[str,Field(min_length=8,max_length=20)]
    province: Annotated[str,Field(min_length=1,max_length=100)]
    district: Annotated[str,Field(max_length=100)] | None = None
    ward: Annotated[str,Field(max_length=100)] | None = None
    street_address: Annotated[str,Field(min_length=1,max_length=255)]
    is_default: bool = False
class UserCreate(Register):
    role: Literal['admin','staff','customer'] = 'staff'
class UserUpdate(Input):
    role: Literal['admin','staff','customer'] | None = None
    status: Literal['active','blocked'] | None = None
    full_name: Text | None = None
class RolePermissions(Input):
    codes: list[Annotated[str,Field(min_length=1,max_length=100)]] = Field(max_length=100)
class ReviewModeration(Input):
    status: Literal['approved','hidden','pending']
class Ticket(Input):
    subject: Annotated[str,Field(min_length=1,max_length=255)]
    message: Annotated[str,Field(min_length=1,max_length=10000)]
    order_id: Positive | None = None
class Message(Input):
    content: Annotated[str,Field(min_length=1,max_length=10000)]
class TicketUpdate(Input):
    status: Literal['open','in_progress','closed']
    assigned_to: Positive | None = None
class CartItem(Input):
    variant_id: Positive
    quantity: Annotated[int,Field(ge=0,le=999)]
class Checkout(Input):
    address_id: Positive | None = None
    variant_ids: list[Positive] | None = Field(default=None,min_length=1,max_length=100)
    fulfillment_method: Literal['delivery','pickup'] = 'delivery'
    recipient_name: Text | None = None
    recipient_phone: Annotated[str,Field(pattern=r'^\+?[0-9][0-9 ()-]{7,19}$')] | None = None
    shipping_address: Annotated[str,Field(min_length=5,max_length=1000)] | None = None
    recipient_email: EmailStr | None = None
    pickup_start: datetime | None = None
    pickup_end: datetime | None = None
    checkout_key: Annotated[str,Field(min_length=16,max_length=64,pattern=r'^[a-zA-Z0-9-]+$')]
    expected_total: Money | None = None
    expected_quantities: dict[Positive,Annotated[int,Field(gt=0,le=999)]] | None = Field(default=None,max_length=100)
    coupon_code: Annotated[str,Field(max_length=60)] | None = None
    payment_method: Literal['cod','bank_transfer']
    customer_note: Annotated[str,Field(max_length=2000)] | None = None
    @model_validator(mode='after')
    def validate_checkout(self):
        if self.variant_ids and len(set(self.variant_ids))!=len(self.variant_ids):raise ValueError('Sản phẩm được chọn bị trùng')
        if not self.address_id or self.fulfillment_method=='pickup':
            if not self.recipient_name or not self.recipient_phone:raise ValueError('Nhập tên và số điện thoại người nhận')
        if self.fulfillment_method=='delivery':
            if not self.address_id and not self.shipping_address:raise ValueError('Nhập địa chỉ nhận hàng')
            if self.pickup_start or self.pickup_end:raise ValueError('Đơn giao hàng không có lịch lấy tại cửa hàng')
        else:
            if not self.recipient_email or not self.pickup_start or not self.pickup_end:raise ValueError('Nhập email và khoảng thời gian đến lấy')
            if not self.pickup_start.tzinfo or not self.pickup_end.tzinfo:raise ValueError('Lịch lấy hàng cần múi giờ')
            duration=(self.pickup_end-self.pickup_start).total_seconds()
            if not 900<=duration<=8*3600:raise ValueError('Khoảng lấy hàng từ 15 phút đến 8 giờ')
            if self.payment_method!='cod':raise ValueError('Đặt trước thanh toán khi lấy hàng')
        return self
class OrderStatus(Input):
    status: Literal['confirmed','packing','shipping','preparing','shipped','delivered','failed','cancelled']
class Stock(Input):
    quantity_change: Annotated[int,Field(ge=-1000000,le=1000000)]
    note: Annotated[str,Field(min_length=1,max_length=500)]
class Review(Input):
    order_item_id: Positive
    rating: Annotated[int,Field(ge=1,le=5)]
    comment: Annotated[str,Field(max_length=5000)] | None = None
    images: list[HttpUrl] = Field(default_factory=list,max_length=5)
class Return(Input):
    order_item_id: Positive
    quantity: Positive
    reason: Annotated[str,Field(min_length=1,max_length=5000)]
    type: Literal['return','exchange','refund']
class ReturnStatus(Input):
    status: Literal['received','approved','rejected','refunded']
class PaymentConfirm(Input):
    transaction_id: Annotated[str,Field(min_length=1,max_length=150)]
class Shipment(Input):
    carrier: Annotated[str,Field(min_length=1,max_length=100)]
    tracking_number: Annotated[str,Field(min_length=1,max_length=120)]
