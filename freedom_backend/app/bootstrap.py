"""Explicit, idempotent reference-data bootstrap. Never changes the schema."""
import argparse
from getpass import getpass
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .db import engine, table, add
from .security import passwords

PERMISSIONS=['users.read','users.manage','audit.read','support.manage','reviews.read','reviews.moderate',
             'catalog.manage','content.manage','coupons.manage','inventory.read','inventory.manage',
             'orders.manage','payments.manage','returns.read','customers.read','dashboard.read']
STAFF=['support.manage','reviews.read','inventory.read','orders.manage','returns.read','customers.read']

def seed(db):
    r,p,rp=table('roles'),table('permissions'),table('role_permissions')
    staff_created=False
    for code,name in [('admin','Admin'),('staff','Nhân viên'),('customer','Khách hàng')]:
        created=db.scalar(insert(r).values(code=code,name=name).on_conflict_do_nothing(index_elements=['code']).returning(r.c.id))
        if code=='staff' and created is not None:staff_created=True
    for code in PERMISSIONS:db.execute(insert(p).values(code=code,description=code).on_conflict_do_nothing(index_elements=['code']))
    staff=db.scalar(select(r.c.id).where(r.c.code=='staff'))
    # Never restore permissions after an Admin deliberately removed every grant.
    if staff_created:
        for pid in db.scalars(select(p.c.id).where(p.c.code.in_(STAFF))):
            db.execute(insert(rp).values(role_id=staff,permission_id=pid).on_conflict_do_nothing())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--admin-email');args=parser.parse_args()
    with Session(engine) as db,db.begin():
        seed(db)
        if args.admin_email:
            from pydantic import TypeAdapter, EmailStr
            email=str(TypeAdapter(EmailStr).validate_python(args.admin_email)).lower()
            u,r=table('users'),table('roles')
            if db.scalar(select(u.c.id).where(u.c.email==email)):
                raise SystemExit('Email đã tồn tại; không tự nâng quyền tài khoản cũ')
            password=getpass('Mật khẩu Admin (ít nhất 12 ký tự): ')
            if len(password)<12 or len(password)>128:raise SystemExit('Mật khẩu cần 12–128 ký tự')
            add(db,'users',dict(email=email,full_name='Administrator',password_hash=passwords.hash(password),role_id=db.scalar(select(r.c.id).where(r.c.code=='admin'))))
    print('Đã khởi tạo roles/permissions và Admin nếu được yêu cầu')

if __name__=='__main__':main()
