from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete, func
from .. import schemas as s
from ..config import settings
from ..db import session, table, one, add, audit
from ..security import current, require, owned

router=APIRouter(tags=['Tuấn Anh • giỏ hàng, đơn hàng, thanh toán'])

@router.get('/catalog/checkout-config')
def checkout_config():
    return {'shipping_fee':settings.shipping_fee,'store_address':settings.store_address,'timezone':'Asia/Ho_Chi_Minh'}


def check_product_visible(db,product):
    from .catalog import category_tree
    visible=category_tree(table('categories'))
    if product['status']!='active' or db.scalar(select(visible.c.id).where(visible.c.id==product['category_id'])) is None:
        raise HTTPException(409,'Sản phẩm hoặc danh mục đã ngừng bán')

def cart_for(db,uid):
    one(db,'users',uid,lock=True)
    t=table('carts');row=db.execute(select(t).where(t.c.user_id==uid).with_for_update()).mappings().first()
    return dict(row) if row else add(db,'carts',{'user_id':uid})

@router.get('/me/cart')
def cart(user=Depends(current),db=Depends(session)):
    c=cart_for(db,user['id']);t,v,p,sz,col=table('cart_items'),table('product_variants'),table('products'),table('sizes'),table('colors')
    rows=[dict(row) for row in db.execute(select(t,p.c.name.label('product_name'),p.c.id.label('product_id'),p.c.status.label('product_status'),v.c.price,v.c.stock_quantity,v.c.reserved_quantity,v.c.is_active,sz.c.name.label('size_name'),col.c.name.label('color_name')).join(v,t.c.variant_id==v.c.id).join(p,v.c.product_id==p.c.id).join(sz,v.c.size_id==sz.c.id).join(col,v.c.color_id==col.c.id).where(t.c.cart_id==c['id']).order_by(t.c.variant_id)).mappings()]
    from .catalog import with_product_images
    products=with_product_images(db,[{'id':pid} for pid in {row['product_id'] for row in rows}])
    images={p['id']:p['product_images'] for p in products}
    for row in rows:row['product_images']=images[row['product_id']]
    from .catalog import category_tree
    visible=category_tree(table('categories'))
    active_ids=set(db.scalars(select(p.c.id).where(p.c.category_id.in_(select(visible.c.id)))).all())
    for row in rows:
        if row['product_id'] not in active_ids:row['product_status']='archived'
    return rows

@router.put('/me/cart/items')
def cart_item(body:s.CartItem,user=Depends(current),db=Depends(session)):
    c=cart_for(db,user['id']);v=one(db,'product_variants',body.variant_id,lock=True)
    if body.quantity and (not v['is_active'] or body.quantity>v['stock_quantity']-v['reserved_quantity']):
        raise HTTPException(409,'SKU ngừng bán hoặc không đủ tồn khả dụng')
    if body.quantity:check_product_visible(db,one(db,'products',v['product_id']))
    t=table('cart_items');where=(t.c.cart_id==c['id']) & (t.c.variant_id==body.variant_id)
    old=db.execute(select(t).where(where)).mappings().first()
    if body.quantity==0:db.execute(delete(t).where(where));return {'detail':'Đã xóa'}
    if old:return db.execute(update(t).where(where).values(quantity=body.quantity).returning(t)).mappings().one()
    return add(db,'cart_items',dict(cart_id=c['id'],variant_id=body.variant_id,quantity=body.quantity))

def coupon_discount(coupon,subtotal,now):
    if not coupon['is_active'] or not coupon['starts_at']<=now<coupon['expires_at']:
        raise HTTPException(400,'Voucher không còn hiệu lực')
    if coupon['usage_limit'] is not None and coupon['used_count']>=coupon['usage_limit']:
        raise HTTPException(409,'Voucher hết lượt')
    if subtotal<coupon['min_order_value']:raise HTTPException(400,'Chưa đạt giá trị đơn tối thiểu')
    if coupon['discount_type']=='percent':
        discount=subtotal*coupon['discount_value']/100
    elif coupon['discount_type']=='fixed':discount=coupon['discount_value']
    else:raise HTTPException(400,'Loại voucher không hỗ trợ')
    if coupon['max_discount'] is not None:discount=min(discount,coupon['max_discount'])
    return min(subtotal,max(Decimal('0'),discount)).quantize(Decimal('.01'))

@router.post('/me/checkout',status_code=201)
def checkout(body:s.Checkout,user=Depends(current),db=Depends(session)):
    c=cart_for(db,user['id']);orders=table('orders')
    previous=db.execute(select(orders).where(orders.c.user_id==user['id'],orders.c.checkout_key==body.checkout_key)).mappings().first()
    if previous:return dict(previous)
    now=datetime.now(timezone.utc)
    if body.fulfillment_method=='pickup' and body.pickup_start<=now:raise HTTPException(422,'Chọn lịch lấy hàng trong tương lai')
    ci=table('cart_items');query=select(ci).where(ci.c.cart_id==c['id'])
    if body.variant_ids is not None:query=query.where(ci.c.variant_id.in_(body.variant_ids))
    items=db.execute(query.order_by(ci.c.variant_id).with_for_update()).mappings().all()
    if not items:raise HTTPException(400,'Giỏ hàng rỗng')
    if body.variant_ids is not None and len(items)!=len(body.variant_ids):raise HTTPException(409,'Có sản phẩm đã thay đổi hoặc không thuộc giỏ hàng của bạn')
    if body.expected_quantities is not None and {i['variant_id']:i['quantity'] for i in items}!=body.expected_quantities:raise HTTPException(409,'Số lượng trong giỏ vừa thay đổi. Quay lại giỏ để kiểm tra trước khi đặt')
    subtotal=Decimal(0);snapshots=[];variants=table('product_variants')
    for item in items:
        v=one(db,'product_variants',item['variant_id'],lock=True);p=one(db,'products',v['product_id'])
        check_product_visible(db,p)
        if not v['is_active'] or p['status']!='active' or item['quantity']<=0 or v['price']<0 or v['stock_quantity']-v['reserved_quantity']<item['quantity']:
            raise HTTPException(409,'Sản phẩm hết hàng hoặc ngừng bán')
        size=one(db,'sizes',v['size_id']);color=one(db,'colors',v['color_id'])
        subtotal+=v['price']*item['quantity']
        snapshots.append(dict(variant_id=v['id'],sku_snapshot=v['sku'],product_name_snapshot=p['name'],
            size_snapshot=size['name'],color_snapshot=color['name'],unit_price=v['price'],quantity=item['quantity']))
    discount=Decimal(0);coupon=None;now=datetime.now(timezone.utc)
    if body.coupon_code:
        t=table('coupons');coupon=db.execute(select(t).where(t.c.code==body.coupon_code).with_for_update()).mappings().first()
        if not coupon:raise HTTPException(400,'Voucher không tồn tại')
        discount=coupon_discount(coupon,subtotal,now)
        db.execute(update(t).where(t.c.id==coupon['id']).values(used_count=t.c.used_count+1))
    if body.fulfillment_method=='pickup':
        name,phone,address_text=body.recipient_name,body.recipient_phone,settings.store_address
    elif body.address_id:
        address=owned(one(db,'addresses',body.address_id),user)
        name,phone=address['recipient_name'],address['phone']
        address_text=', '.join(str(address[x]) for x in ('street_address','ward','district','province') if address[x])
    else:name,phone,address_text=body.recipient_name,body.recipient_phone,body.shipping_address
    shipping_fee=Decimal(0) if body.fulfillment_method=='pickup' else settings.shipping_fee
    if body.expected_total is not None and subtotal+shipping_fee-discount!=body.expected_total:raise HTTPException(409,'Giá sản phẩm hoặc phí giao hàng vừa thay đổi. Quay lại giỏ để kiểm tra trước khi đặt')
    order=add(db,'orders',dict(order_code='FR-'+uuid4().hex,user_id=user['id'],coupon_id=coupon['id'] if coupon else None,
        recipient_name=name,recipient_phone=phone,shipping_address=address_text,recipient_email=str(body.recipient_email) if body.recipient_email else None,
        fulfillment_method=body.fulfillment_method,pickup_start=body.pickup_start,pickup_end=body.pickup_end,checkout_key=body.checkout_key,
        subtotal=subtotal,shipping_fee=shipping_fee,discount_amount=discount,total_amount=subtotal+shipping_fee-discount,
        payment_method=body.payment_method,customer_note=body.customer_note))
    for snapshot in snapshots:
        add(db,'order_items',dict(order_id=order['id'],**snapshot))
        # Stock is deducted immediately; reserved_quantity is respected but unchanged.
        db.execute(update(variants).where(variants.c.id==snapshot['variant_id']).values(stock_quantity=variants.c.stock_quantity-snapshot['quantity']))
        add(db,'inventory_movements',dict(variant_id=snapshot['variant_id'],movement_type='sale',quantity_change=-snapshot['quantity'],
            reference_type='order',reference_id=order['id'],created_by=user['id']))
    add(db,'payments',dict(order_id=order['id'],provider=body.payment_method,amount=order['total_amount']))
    add(db,'order_status_histories',dict(order_id=order['id'],new_status='pending',changed_by=user['id']))
    db.execute(delete(ci).where(ci.c.cart_id==c['id'],ci.c.variant_id.in_([item['variant_id'] for item in items])))
    audit(db,user['id'],'checkout','orders',order['id'])
    return order

@router.get('/me/orders')
def my_orders(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current),db=Depends(session)):
    t=table('orders')
    return db.execute(select(t).where(t.c.user_id==user['id']).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

def order_detail(db,order):
    result=dict(order)
    for name in ('order_items','payments','shipments','order_status_histories'):
        t=table(name);result[name]=db.execute(select(t).where(t.c.order_id==order['id']).order_by(t.c.id)).mappings().all()
    return result

@router.get('/me/orders/{oid}')
def my_order(oid:int,user=Depends(current),db=Depends(session)):
    return order_detail(db,owned(one(db,'orders',oid),user))

TRANSITIONS={'pending':{'packing','cancelled'},'confirmed':{'packing','cancelled'},'packing':{'shipping','cancelled'},'shipping':{'delivered','failed'},'failed':{'shipping','cancelled'}}
STATUS_ALIASES={'confirmed':'packing','preparing':'packing','shipped':'shipping'}

def transition(db,order,new,user):
    new=STATUS_ALIASES.get(new,new)
    old=STATUS_ALIASES.get(order['status'],order['status'])
    allowed=TRANSITIONS.get(old,set())
    if order.get('fulfillment_method')=='pickup':
        allowed={'packing','cancelled'} if order['status']=='pending' else {'delivered','cancelled'} if old=='packing' else set()
    if new not in allowed:raise HTTPException(409,'Chuyển trạng thái không hợp lệ')
    if new=='cancelled':
        p=table('payments')
        if db.scalar(select(p.c.id).where(p.c.order_id==order['id'],p.c.status=='paid')):
            raise HTTPException(409,'Đơn đã thanh toán cần quy trình hoàn tiền riêng')
        oi=table('order_items');v=table('product_variants')
        for item in db.execute(select(oi).where(oi.c.order_id==order['id']).order_by(oi.c.variant_id)).mappings():
            one(db,'product_variants',item['variant_id'],lock=True)
            db.execute(update(v).where(v.c.id==item['variant_id']).values(stock_quantity=v.c.stock_quantity+item['quantity']))
            add(db,'inventory_movements',dict(variant_id=item['variant_id'],movement_type='return',quantity_change=item['quantity'],reference_type='order',reference_id=order['id'],created_by=user['id']))
        db.execute(update(p).where(p.c.order_id==order['id'],p.c.status=='pending').values(status='failed'))
    shipment_table=table('shipments')
    if new in ('shipping','delivered','failed','cancelled'):
        shipment_values={'status':{'shipping':'in_transit','delivered':'delivered','failed':'failed','cancelled':'returned'}[new]}
        if new=='shipping':shipment_values['shipped_at']=datetime.now(timezone.utc)
        if new=='delivered':shipment_values['delivered_at']=datetime.now(timezone.utc)
        db.execute(update(shipment_table).where(shipment_table.c.order_id==order['id']).values(**shipment_values))
    t=table('orders');values=dict(status=new,updated_at=datetime.now(timezone.utc))
    if new=='packing':values['confirmed_by']=user['id']
    db.execute(update(t).where(t.c.id==order['id']).values(**values))
    add(db,'order_status_histories',dict(order_id=order['id'],old_status=order['status'],new_status=new,changed_by=user['id']))
    audit(db,user['id'],'status','orders',order['id'],{'from':order['status'],'to':new})
    return one(db,'orders',order['id'])

@router.post('/me/orders/{oid}/cancel')
def cancel(oid:int,user=Depends(current),db=Depends(session)):
    order=owned(one(db,'orders',oid,lock=True),user)
    if order['status']!='pending':raise HTTPException(409,'Chỉ hủy được đơn chưa xác nhận; liên hệ cửa hàng để được hỗ trợ')
    return transition(db,order,'cancelled',user)

@router.get('/staff/orders')
def all_orders(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('orders.manage')),db=Depends(session)):
    t=table('orders');return db.execute(select(t).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.get('/staff/orders/{oid}')
def staff_order(oid:int,user=Depends(require('orders.manage')),db=Depends(session)):
    return order_detail(db,one(db,'orders',oid))

@router.patch('/staff/orders/{oid}/status')
def status(oid:int,body:s.OrderStatus,user=Depends(require('orders.manage')),db=Depends(session)):
    return transition(db,one(db,'orders',oid,lock=True),body.status,user)

@router.post('/admin/orders/{oid}/confirm-payment')
def confirm_payment(oid:int,body:s.PaymentConfirm,user=Depends(require('payments.manage')),db=Depends(session)):
    order=one(db,'orders',oid,lock=True)
    if order['status']=='cancelled':raise HTTPException(409,'Đơn đã hủy')
    if order['payment_method']=='cod' and order['status']!='delivered':raise HTTPException(409,'COD chỉ đối soát sau giao hàng')
    t=table('payments');rows=db.execute(select(t).where(t.c.order_id==oid).with_for_update()).mappings().all()
    if len(rows)!=1:raise HTTPException(409,'Cần đối soát thủ công: số bản ghi thanh toán khác 1')
    payment=rows[0]
    if payment['status']=='paid':
        if payment['provider_transaction_id']==body.transaction_id:return payment
        raise HTTPException(409,'Đơn đã được đối soát')
    if payment['status']!='pending':raise HTTPException(409,'Thanh toán không chờ xử lý')
    row=db.execute(update(t).where(t.c.id==payment['id']).values(status='paid',paid_at=datetime.now(timezone.utc),provider_transaction_id=body.transaction_id).returning(t)).mappings().one()
    audit(db,user['id'],'confirm_payment','payments',payment['id'])
    return row

@router.put('/staff/orders/{oid}/shipment')
def shipment(oid:int,body:s.Shipment,user=Depends(require('orders.manage')),db=Depends(session)):
    order=one(db,'orders',oid,lock=True)
    if order.get('fulfillment_method')=='pickup':raise HTTPException(409,'Đơn lấy tại cửa hàng không cần vận đơn')
    if order['status'] in ('pending','cancelled'):raise HTTPException(409,'Đơn chưa sẵn sàng giao')
    t=table('shipments');rows=db.execute(select(t).where(t.c.order_id==oid)).mappings().all()
    if len(rows)>1:raise HTTPException(409,'Có nhiều vận đơn, cần đối soát')
    values=dict(**body.model_dump(),order_id=oid,status={'shipping':'in_transit','shipped':'in_transit','delivered':'delivered','failed':'failed'}.get(order['status'],'preparing'))
    if order['status'] in ('shipping','shipped'):values['shipped_at']=datetime.now(timezone.utc)
    if order['status']=='delivered':values['delivered_at']=datetime.now(timezone.utc)
    audit(db,user['id'],'shipment','orders',oid)
    if rows:return db.execute(update(t).where(t.c.id==rows[0]['id']).values(**values).returning(t)).mappings().one()
    return add(db,'shipments',values)
