from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, StringConstraints

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
    address_id: Positive
    coupon_code: Annotated[str,Field(max_length=60)] | None = None
    payment_method: Literal['cod','bank_transfer']
    customer_note: Annotated[str,Field(max_length=2000)] | None = None
class OrderStatus(Input):
    status: Literal['confirmed','preparing','shipped','delivered','cancelled']
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
