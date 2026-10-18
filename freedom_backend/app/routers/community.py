from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete, func
from .. import schemas as s
from ..db import session, table, one, add, audit
from ..security import current, require, owned

router=APIRouter(tags=['Khánh • kho, yêu thích, đánh giá, đổi trả'])

@router.get('/me/wishlist')
def wishlist(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current),db=Depends(session)):
    w,p=table('wishlists'),table('products')
    return db.execute(select(p).join(w,w.c.product_id==p.c.id).where(w.c.user_id==user['id'],p.c.status=='active').order_by(p.c.id).limit(limit).offset(offset)).mappings().all()

@router.put('/me/wishlist/{pid}')
def wish(pid:int,user=Depends(current),db=Depends(session)):
    from sqlalchemy.dialects.postgresql import insert
    if one(db,'products',pid)['status']!='active':raise HTTPException(404,'Sản phẩm không đang bán')
    w=table('wishlists')
    db.execute(insert(w).values(user_id=user['id'],product_id=pid).on_conflict_do_nothing())
    return {'detail':'Đã lưu'}

@router.delete('/me/wishlist/{pid}',status_code=204)
def unwish(pid:int,user=Depends(current),db=Depends(session)):
    w=table('wishlists');db.execute(delete(w).where(w.c.user_id==user['id'],w.c.product_id==pid))

def purchased_item(db,item_id,user,lock=False):
    # All return/review creation for one order item is serialized.
    item=one(db,'order_items',item_id,lock=lock)
    order=owned(one(db,'orders',item['order_id']),user)
    if order['status']!='delivered':raise HTTPException(409,'Chỉ áp dụng khi đã giao hàng')
    return item

@router.post('/me/reviews',status_code=201)
def review(body:s.Review,user=Depends(current),db=Depends(session)):
    item=purchased_item(db,body.order_item_id,user,lock=True)
    v=one(db,'product_variants',item['variant_id'])
    row=add(db,'reviews',dict(user_id=user['id'],product_id=v['product_id'],order_item_id=item['id'],rating=body.rating,comment=body.comment))
    for url in body.images:add(db,'review_images',dict(review_id=row['id'],image_url=str(url)))
    return row

@router.post('/me/returns',status_code=201)
def request_return(body:s.Return,user=Depends(current),db=Depends(session)):
    item=purchased_item(db,body.order_item_id,user,lock=True)
    t=table('return_requests')
    used=db.scalar(select(func.coalesce(func.sum(t.c.quantity),0)).where(t.c.order_item_id==item['id'],t.c.status!='rejected'))
    if used+body.quantity>item['quantity']:raise HTTPException(409,'Số lượng trả vượt số lượng đã mua còn lại')
    return add(db,'return_requests',dict(**body.model_dump(),user_id=user['id']))

@router.get('/me/returns')
def returns(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current),db=Depends(session)):
    t=table('return_requests')
    return db.execute(select(t).where(t.c.user_id==user['id']).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.get('/staff/returns')
def staff_returns(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('returns.read')),db=Depends(session)):
    t=table('return_requests');return db.execute(select(t).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.patch('/staff/returns/{rid}')
def handle_return(rid:int,body:s.ReturnStatus,user=Depends(require('returns.read')),db=Depends(session)):
    row=one(db,'return_requests',rid,lock=True)
    if body.status in ('approved','rejected','refunded') and user['role']!='admin':raise HTTPException(403,'Chỉ Admin quyết định và đối soát hoàn tiền')
    transitions={'requested':{'received','rejected'},'received':{'approved','rejected'},'approved':{'refunded'}}
    if body.status not in transitions.get(row['status'],set()):raise HTTPException(409,'Trạng thái đổi trả không hợp lệ')
    values={'status':body.status,'handled_by':user['id']}
    if body.status=='refunded':
        if row['type']=='exchange':raise HTTPException(409,'Đổi hàng cần xác nhận SKU thay thế; chưa có trong schema')
        item=one(db,'order_items',row['order_item_id']);order=one(db,'orders',item['order_id'],lock=True)
        p=table('payments');payments=db.execute(select(p).where(p.c.order_id==order['id']).with_for_update()).mappings().all()
        if len(payments)!=1 or payments[0]['status'] not in ('paid','partially_refunded'):
            raise HTTPException(409,'Chưa có thanh toán đã thu hợp lệ')
        # Allocate order discount proportionally; shipping is not refunded by this policy.
        amount=(item['unit_price']*row['quantity']*(order['subtotal']-order['discount_amount'])/order['subtotal']).quantize(Decimal('.01')) if order['subtotal'] else Decimal(0)
        t=table('return_requests')
        oi=table('order_items')
        refunded=db.scalar(select(func.coalesce(func.sum(t.c.refund_amount),0)).select_from(t.join(oi,t.c.order_item_id==oi.c.id)).where(oi.c.order_id==order['id'],t.c.status=='refunded'))
        amount=min(amount,payments[0]['amount']-refunded)
        if amount<0:raise HTTPException(409,'Số tiền hoàn không hợp lệ')
        values['refund_amount']=amount
        db.execute(update(p).where(p.c.id==payments[0]['id']).values(status='refunded' if refunded+amount==payments[0]['amount'] else 'partially_refunded'))
        # This records reconciliation only; it does not initiate a bank transfer.
    t=table('return_requests')
    result=db.execute(update(t).where(t.c.id==rid).values(**values).returning(t)).mappings().one()
    audit(db,user['id'],'return_status','return_requests',rid,{'status':body.status})
    return result

@router.get('/staff/inventory')
def inventory(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('inventory.read')),db=Depends(session)):
    t,p,sz,col=table('product_variants'),table('products'),table('sizes'),table('colors')
    return db.execute(select(t,p.c.name.label('product_name'),sz.c.name.label('size_name'),col.c.name.label('color_name'),(t.c.stock_quantity-t.c.reserved_quantity).label('available_quantity')).join(p,t.c.product_id==p.c.id).join(sz,t.c.size_id==sz.c.id).join(col,t.c.color_id==col.c.id).order_by(t.c.id).limit(limit).offset(offset)).mappings().all()

@router.get('/staff/inventory/{vid}/movements')
def movements(vid:int,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('inventory.read')),db=Depends(session)):
    t=table('inventory_movements');return db.execute(select(t).where(t.c.variant_id==vid).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.post('/staff/inventory/{vid}/adjust')
def stock(vid:int,body:s.Stock,user=Depends(require('inventory.manage')),db=Depends(session)):
    v=one(db,'product_variants',vid,lock=True)
    if not body.quantity_change or v['stock_quantity']+body.quantity_change<v['reserved_quantity']:
        raise HTTPException(409,'Điều chỉnh làm tồn khả dụng âm hoặc không thay đổi')
    t=table('product_variants');db.execute(update(t).where(t.c.id==vid).values(stock_quantity=v['stock_quantity']+body.quantity_change))
    row=add(db,'inventory_movements',dict(variant_id=vid,movement_type='adjustment',quantity_change=body.quantity_change,note=body.note,created_by=user['id']))
    audit(db,user['id'],'stock','product_variants',vid,body.model_dump())
    return row

@router.get('/admin/dashboard')
def dashboard(start:datetime|None=None,end:datetime|None=None,user=Depends(require('dashboard.read')),db=Depends(session)):
    if (start and start.tzinfo is None) or (end and end.tzinfo is None):raise HTTPException(422,'Dùng thời gian kèm múi giờ')
    if start and end and start>=end:raise HTTPException(422,'Khoảng thời gian không hợp lệ')
    o,p,u,r,oi=table('orders'),table('payments'),table('users'),table('roles'),table('order_items')
    cond=[]
    if start:cond.append(o.c.placed_at>=start)
    if end:cond.append(o.c.placed_at<end)
    order_count=db.scalar(select(func.count()).select_from(o).where(*cond))
    revenue=db.scalar(select(func.coalesce(func.sum(o.c.total_amount),0)).where(*cond,o.c.status=='delivered'))
    customers=db.scalar(select(func.count()).select_from(u.join(r,u.c.role_id==r.c.id)).where(r.c.code=='customer'))
    top=db.execute(select(oi.c.product_name_snapshot,func.sum(oi.c.quantity).label('quantity')).join(o,o.c.id==oi.c.order_id).where(*cond,o.c.status=='delivered').group_by(oi.c.product_name_snapshot).order_by(func.sum(oi.c.quantity).desc()).limit(10)).mappings().all()
    return dict(orders=order_count,delivered_gross_revenue=revenue,customers_total=customers,top_products=top)

@router.get('/staff/customers/{uid}')
def customer_detail(uid:int,user=Depends(require('customers.read')),db=Depends(session)):
    from ..security import public_user
    target=one(db,'users',uid)
    if one(db,'roles',target['role_id'])['code']!='customer':raise HTTPException(404,'Không tìm thấy khách hàng')
    result=public_user(target)
    for name in ('addresses','orders'):
        t=table(name);result[name]=db.execute(select(t).where(t.c.user_id==uid).limit(100)).mappings().all()
    return result

@router.get('/staff/customers')
def customers(q:str=Query('',max_length=190),limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),
              user=Depends(require('customers.read')),db=Depends(session)):
    from ..security import public_user
    u,r=table('users'),table('roles')
    query=select(u).join(r,u.c.role_id==r.c.id).where(r.c.code=='customer')
    if q:
        pattern='%'+q.replace('%','\\%').replace('_','\\_')+'%'
        query=query.where(u.c.email.ilike(pattern,escape='\\')|u.c.full_name.ilike(pattern,escape='\\'))
    return [public_user(x) for x in db.execute(query.order_by(u.c.id).limit(limit).offset(offset)).mappings()]
