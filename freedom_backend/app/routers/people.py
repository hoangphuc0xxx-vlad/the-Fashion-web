from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete, func
from .. import schemas as s
from ..db import session, table, one, add, audit
from ..security import current, require, owned, public_user, passwords
from .auth import role_id

router=APIRouter(tags=['Phúc • tài khoản, địa chỉ, hỗ trợ'])

@router.put('/me/profile')
def profile(body:s.Profile,user=Depends(current),db=Depends(session)):
    u=table('users');values=body.model_dump(mode='json');values['updated_at']=datetime.now(timezone.utc)
    return public_user(db.execute(update(u).where(u.c.id==user['id']).values(**values).returning(u)).mappings().one())

@router.get('/me/addresses')
def addresses(user=Depends(current),db=Depends(session)):
    t=table('addresses')
    return db.execute(select(t).where(t.c.user_id==user['id']).order_by(t.c.id)).mappings().all()

def save_address(db,user,body,address_id=None):
    one(db,'users',user['id'],lock=True) # serializes default-address edits for this user
    t=table('addresses')
    if address_id: owned(one(db,'addresses',address_id),user)
    if body.is_default:
        db.execute(update(t).where(t.c.user_id==user['id']).values(is_default=False))
    values=body.model_dump();values['user_id']=user['id']
    if address_id:
        return db.execute(update(t).where(t.c.id==address_id).values(**values).returning(t)).mappings().one()
    return add(db,'addresses',values)

@router.post('/me/addresses',status_code=201)
def address_create(body:s.Address,user=Depends(current),db=Depends(session)):
    return save_address(db,user,body)

@router.put('/me/addresses/{address_id}')
def address_update(address_id:int,body:s.Address,user=Depends(current),db=Depends(session)):
    return save_address(db,user,body,address_id)

@router.delete('/me/addresses/{address_id}',status_code=204)
def address_delete(address_id:int,user=Depends(current),db=Depends(session)):
    one(db,'users',user['id'],lock=True)
    owned(one(db,'addresses',address_id),user)
    t=table('addresses');db.execute(delete(t).where(t.c.id==address_id))

@router.get('/admin/users')
def users(role:str|None=None,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),
          user=Depends(require('users.read')),db=Depends(session)):
    u,r=table('users'),table('roles');q=select(u,r.c.code.label('role')).join(r,u.c.role_id==r.c.id)
    if role:q=q.where(r.c.code==role)
    return [public_user(x) for x in db.execute(q.order_by(u.c.id).limit(limit).offset(offset)).mappings()]

@router.post('/admin/users',status_code=201)
def create_user(body:s.UserCreate,user=Depends(require('users.manage')),db=Depends(session)):
    new=add(db,'users',dict(full_name=body.full_name,email=str(body.email).lower(),
            password_hash=passwords.hash(body.password),role_id=role_id(db,body.role)))
    audit(db,user['id'],'create','users',new['id'],{'role':body.role})
    return public_user(new)

@router.patch('/admin/users/{uid}')
def edit_user(uid:int,body:s.UserUpdate,user=Depends(require('users.manage')),db=Depends(session)):
    # Lock roles first so concurrent demotions cannot remove every active admin.
    r=table('roles');db.execute(select(r).order_by(r.c.id).with_for_update()).all()
    target=one(db,'users',uid,lock=True);u=table('users');values=body.model_dump(exclude_unset=True)
    if any(v is None for v in values.values()):raise HTTPException(422,'Không chấp nhận null')
    if 'role' in values:values['role_id']=role_id(db,values.pop('role'))
    admin=role_id(db,'admin')
    if target['role_id']==admin and target['status']=='active' and (values.get('role_id',admin)!=admin or values.get('status','active')!='active'):
        count=db.scalar(select(func.count()).select_from(u).where(u.c.role_id==admin,u.c.status=='active'))
        if count<=1:raise HTTPException(409,'Phải giữ ít nhất một Admin hoạt động')
    values['updated_at']=datetime.now(timezone.utc)
    result=db.execute(update(u).where(u.c.id==uid).values(**values).returning(u)).mappings().one()
    audit(db,user['id'],'update','users',uid,body.model_dump(exclude_unset=True))
    return public_user(result)

@router.get('/admin/roles')
def roles(user=Depends(require('users.manage')),db=Depends(session)):
    return db.execute(select(table('roles'))).mappings().all()

@router.get('/admin/permissions')
def permissions(user=Depends(require('users.manage')),db=Depends(session)):
    return db.execute(select(table('permissions'))).mappings().all()

@router.put('/admin/roles/{rid}/permissions')
def set_permissions(rid:int,body:s.RolePermissions,user=Depends(require('users.manage')),db=Depends(session)):
    role=one(db,'roles',rid,lock=True)
    if role['code']!='staff':raise HTTPException(400,'Chỉ cấu hình quyền vai trò staff; Admin toàn quyền, khách hàng chỉ dữ liệu của mình')
    if 'users.manage' in body.codes:raise HTTPException(400,'Không cấp quyền quản trị tài khoản cho staff')
    p,rp=table('permissions'),table('role_permissions')
    ids=db.scalars(select(p.c.id).where(p.c.code.in_(body.codes))).all()
    if len(ids)!=len(set(body.codes)):raise HTTPException(422,'Mã quyền không tồn tại')
    db.execute(delete(rp).where(rp.c.role_id==rid))
    for pid in ids:db.execute(rp.insert().values(role_id=rid,permission_id=pid))
    audit(db,user['id'],'permissions','roles',rid,{'codes':body.codes})
    return {'codes':body.codes}

@router.get('/admin/audit-logs')
def logs(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('audit.read')),db=Depends(session)):
    t=table('audit_logs')
    return db.execute(select(t).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.post('/support/tickets',status_code=201)
def ticket_create(body:s.Ticket,user=Depends(current),db=Depends(session)):
    if body.order_id:owned(one(db,'orders',body.order_id),user)
    return add(db,'support_tickets',dict(**body.model_dump(),user_id=user['id']))

@router.get('/support/tickets')
def my_tickets(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current),db=Depends(session)):
    t=table('support_tickets')
    return db.execute(select(t).where(t.c.user_id==user['id']).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.get('/support/tickets/{tid}/messages')
def messages(tid:int,user=Depends(current),db=Depends(session)):
    owned(one(db,'support_tickets',tid),user)
    t=table('support_messages')
    return db.execute(select(t).where(t.c.ticket_id==tid).order_by(t.c.id).limit(200)).mappings().all()

@router.post('/support/tickets/{tid}/messages',status_code=201)
def message_create(tid:int,body:s.Message,user=Depends(current),db=Depends(session)):
    ticket=owned(one(db,'support_tickets',tid,lock=True),user)
    if ticket['status']=='closed':raise HTTPException(409,'Yêu cầu đã đóng')
    return add(db,'support_messages',dict(ticket_id=tid,sender_id=user['id'],content=body.content))

@router.get('/staff/support/tickets')
def staff_tickets(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('support.manage')),db=Depends(session)):
    t=table('support_tickets')
    return db.execute(select(t).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.get('/staff/support/tickets/{tid}/messages')
def staff_messages(tid:int,user=Depends(require('support.manage')),db=Depends(session)):
    one(db,'support_tickets',tid);t=table('support_messages')
    return db.execute(select(t).where(t.c.ticket_id==tid).order_by(t.c.id).limit(200)).mappings().all()

@router.post('/staff/support/tickets/{tid}/messages',status_code=201)
def staff_reply(tid:int,body:s.Message,user=Depends(require('support.manage')),db=Depends(session)):
    ticket=one(db,'support_tickets',tid,lock=True)
    if ticket['status']=='closed':raise HTTPException(409,'Yêu cầu đã đóng')
    result=add(db,'support_messages',dict(ticket_id=tid,sender_id=user['id'],content=body.content))
    audit(db,user['id'],'reply','support_tickets',tid)
    return result

@router.patch('/staff/support/tickets/{tid}')
def staff_ticket(tid:int,body:s.TicketUpdate,user=Depends(require('support.manage')),db=Depends(session)):
    one(db,'support_tickets',tid,lock=True)
    if body.assigned_to:
        assignee=one(db,'users',body.assigned_to)
        if assignee['status']!='active' or one(db,'roles',assignee['role_id'])['code'] not in ('admin','staff'):
            raise HTTPException(422,'Người nhận phải là nhân viên hoạt động')
    t=table('support_tickets')
    result=db.execute(update(t).where(t.c.id==tid).values(**body.model_dump()).returning(t)).mappings().one()
    audit(db,user['id'],'update','support_tickets',tid)
    return result

@router.get('/admin/reviews')
def reviews(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require('reviews.read')),db=Depends(session)):
    t=table('reviews')
    return db.execute(select(t).order_by(t.c.id.desc()).limit(limit).offset(offset)).mappings().all()

@router.patch('/admin/reviews/{rid}')
def moderate(rid:int,body:s.ReviewModeration,user=Depends(require('reviews.moderate')),db=Depends(session)):
    one(db,'reviews',rid,lock=True);t=table('reviews')
    row=db.execute(update(t).where(t.c.id==rid).values(status=body.status).returning(t)).mappings().one()
    audit(db,user['id'],'moderate','reviews',rid,{'status':body.status})
    return row

@router.post('/staff/reviews/{rid}/flag')
def flag_review(rid:int,body:s.Message,user=Depends(require('reviews.read')),db=Depends(session)):
    one(db,'reviews',rid)
    audit(db,user['id'],'flag_review','reviews',rid,{'reason':body.content})
    return {'detail':'Đã ghi nhận cho Admin kiểm tra trong audit logs'}

@router.get('/admin/reviews/{rid}')
def review_detail(rid:int,user=Depends(require('reviews.read')),db=Depends(session)):
    row=one(db,'reviews',rid);t=table('review_images')
    row['images']=db.execute(select(t).where(t.c.review_id==rid).order_by(t.c.id)).mappings().all()
    return row
