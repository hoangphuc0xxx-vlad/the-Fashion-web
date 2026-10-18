from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import jwt
import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.db import engine, table
from app.config import settings
from app.security import token_for
from app.schemas import Register
from app.routers.commerce import coupon_discount
from conftest import headers


def test_health_and_openapi(client):
    assert client.get('/health').json()=={'status':'ok'}
    schema=client.get('/openapi.json').json()
    assert '/auth/token' in schema['paths']
    assert schema['paths']['/staff/catalog/products']['post']['requestBody']['content']['application/json']['schema']['$ref'].endswith('ProductsInput')
    assert {'get','put','delete'} <= schema['paths']['/staff/catalog/products/{rid}'].keys()
    assert '/staff/catalog/products/{pid}' not in schema['paths']

def test_password_validation():
    with pytest.raises(ValueError):Register(full_name='X',email='x@example.com',password='short')
    with pytest.raises(ValueError):Register(full_name='X',email='x@example.com',password='long-password',role='admin')

def test_coupon():
    now=datetime.now(timezone.utc)
    c=dict(is_active=True,starts_at=now-timedelta(days=1),expires_at=now+timedelta(days=1),usage_limit=1,used_count=0,min_order_value=0,discount_type='percent',discount_value=Decimal(20),max_discount=Decimal(15000))
    assert coupon_discount(c,Decimal(100000),now)==Decimal(15000)
    c['used_count']=1
    with pytest.raises(Exception):coupon_discount(c,Decimal(100000),now)

def test_login_block_and_permissions(client,data):
    response=client.post('/auth/token',data={'username':'customer@example.com','password':'Strong-password-123'})
    assert response.status_code==200,response.text
    customer=headers(data['customer']);staff=headers(data['staff']);admin=headers(data['admin'])
    assert client.get('/admin/users',headers=customer).status_code==403
    assert client.post('/admin/users',headers=staff,json=dict(email='new@example.com',full_name='N',password='long-password-123',role='admin')).status_code==403
    assert 'password_hash' not in client.get('/auth/me',headers=customer).json()
    assert client.patch('/admin/users/'+str(data['customer']['id']),headers=admin,json={'status':'blocked'}).status_code==200
    assert client.get('/auth/me',headers=customer).status_code==401
    assert client.patch('/admin/users/'+str(data['admin']['id']),headers=admin,json={'status':'blocked'}).status_code==409

def test_address_ownership_default_and_support(client,data):
    h=headers(data['customer']);other=headers(data['other'])
    body=dict(recipient_name='Phúc',phone='0912345678',province='Hà Nội',street_address='10 A',is_default=True)
    a=client.post('/me/addresses',headers=h,json=body);assert a.status_code==201,a.text
    client.post('/me/addresses',headers=h,json={**body,'street_address':'20 B'})
    assert sum(x['is_default'] for x in client.get('/me/addresses',headers=h).json())==1
    assert client.put('/me/addresses/'+str(a.json()['id']),headers=other,json=body).status_code==404
    ticket=client.post('/support/tickets',headers=h,json={'subject':'Hỏi đơn','message':'Xin hỗ trợ'}).json()
    path=f"/support/tickets/{ticket['id']}/messages"
    assert client.get(path,headers=other).status_code==404
    assert client.post(path,headers=h,json={'content':'Cảm ơn'}).status_code==201
    assert client.post(f"/staff/support/tickets/{ticket['id']}/messages",headers=headers(data['staff']),json={'content':'Đã nhận'}).status_code==201

def prepare_checkout(client,user,vid,quantity=2):
    h=headers(user)
    a=client.post('/me/addresses',headers=h,json=dict(recipient_name='P',phone='0912345678',province='HN',street_address='1 A'))
    assert a.status_code==201,a.text
    c=client.put('/me/cart/items',headers=h,json=dict(variant_id=vid,quantity=quantity));assert c.status_code==200,c.text
    return h,dict(address_id=a.json()['id'],payment_method='cod')

def test_checkout_cancel_atomic(client,data):
    h,body=prepare_checkout(client,data['customer'],data['variant']['id'])
    order=client.post('/me/checkout',headers=h,json=body);assert order.status_code==201,order.text
    oid=order.json()['id'];assert Decimal(order.json()['total_amount'])==230000
    with Session(engine) as db:assert db.scalar(select(table('product_variants').c.stock_quantity))==3
    assert client.get(f'/me/orders/{oid}',headers=headers(data['other'])).status_code==404
    assert client.post(f'/me/orders/{oid}/cancel',headers=h).status_code==200
    assert client.post(f'/me/orders/{oid}/cancel',headers=h).status_code==409
    with Session(engine) as db:assert db.scalar(select(table('product_variants').c.stock_quantity))==5
    assert client.post('/me/checkout',headers=h,json=body).status_code==400

def test_concurrent_checkout_no_oversell(client,data):
    h,b=prepare_checkout(client,data['customer'],data['variant']['id'],4)
    h2,b2=prepare_checkout(client,data['other'],data['variant']['id'],4)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(client.post,'/me/checkout',headers=hh,json=bb) for hh,bb in [(h,b),(h2,b2)]]
        codes=sorted(f.result().status_code for f in futures)
    assert codes==[201,409]
    with Session(engine) as db:
        assert db.scalar(select(table('product_variants').c.stock_quantity))==1
        assert len(db.execute(select(table('orders'))).all())==1

def test_logout_password_reset_and_review(client,data):
    h=headers(data['customer'])
    assert client.post('/auth/logout',headers=h).status_code==200
    assert client.get('/auth/me',headers=h).status_code==401
    login=client.post('/auth/token',data={'username':'customer@example.com','password':'Strong-password-123'})
    assert login.status_code==200,login.text
    h={'Authorization':'Bearer '+login.json()['access_token']}
    assert client.get('/auth/me',headers=h).status_code==200
    assert client.post('/auth/password',headers=h,json={'old_password':'Strong-password-123','new_password':'New-strong-password-123'}).status_code==200
    assert client.get('/auth/me',headers=h).status_code==401
    # Purchase proof required for reviews; another user's order item cannot be used.
    h,body=prepare_checkout(client,data['other'],data['variant']['id'],1)
    order=client.post('/me/checkout',headers=h,json=body).json()
    detail=client.get(f"/me/orders/{order['id']}",headers=h).json();item=detail['order_items'][0]
    assert Decimal(item['line_total'])==100000
    assert client.post('/me/reviews',headers=h,json={'order_item_id':item['id'],'rating':5}).status_code==409
    admin=headers(data['admin'])
    for status in ('confirmed','preparing','shipped','delivered'):
        response=client.patch(f"/staff/orders/{order['id']}/status",headers=admin,json={'status':status})
        assert response.status_code==200,response.text
    assert client.post('/me/reviews',headers=h,json={'order_item_id':item['id'],'rating':5}).status_code==201
    assert client.post('/me/reviews',headers=h,json={'order_item_id':item['id'],'rating':5}).status_code==409

def test_reset_token_single_use_and_email(client,data,monkeypatch):
    from app.routers import auth
    sent=[]
    class Mailbox:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def starttls(self):pass
        def login(self,*args):pass
        def send_message(self,message):sent.append(message)
    monkeypatch.setattr(auth.smtplib,'SMTP',Mailbox)
    result=client.post('/auth/forgot-password',json={'email':'customer@example.com'})
    assert result.status_code==202,result.text
    assert 'token' not in result.json()
    assert len(sent)==1
    from urllib.parse import urlparse,parse_qs
    raw=parse_qs(urlparse(sent[0].get_content().strip()).query)['token'][0]
    with Session(engine) as db:
        stored=db.scalar(select(table('password_reset_tokens').c.token_hash))
        assert stored!=raw
    h=headers(data['customer'])
    reset={'token':raw,'new_password':'new-reset-password-123'}
    assert client.post('/auth/reset-password',json=reset).status_code==200
    assert client.post('/auth/reset-password',json=reset).status_code==400
    assert client.get('/auth/me',headers=h).status_code==401
    assert client.post('/auth/token',data={'username':'customer@example.com','password':'new-reset-password-123'}).status_code==200
    assert client.post('/auth/forgot-password',json={'email':'absent@example.com'}).status_code==202
    assert len(sent)==1

def test_catalog_moderation_payment_returns(client,data):
    admin=headers(data['admin']);staff=headers(data['staff'])
    # Staff defaults do not allow product mutation or payment reconciliation.
    assert client.post('/staff/catalog/brands',headers=staff,json={'name':'X','slug':'x'}).status_code==403
    brand=client.post('/staff/catalog/brands',headers=admin,json={'name':'Brand','slug':'brand'})
    assert brand.status_code==201,brand.text
    assert client.delete('/staff/catalog/brands/'+str(brand.json()['id']),headers=admin).status_code==204
    assert all(x['slug']!='brand' for x in client.get('/catalog/lookups/brands').json())
    h,body=prepare_checkout(client,data['customer'],data['variant']['id'],2)
    order=client.post('/me/checkout',headers=h,json=body).json();oid=order['id']
    for status in ('confirmed','preparing','shipped','delivered'):
        assert client.patch(f'/staff/orders/{oid}/status',headers=admin,json={'status':status}).status_code==200
    pay=f'/admin/orders/{oid}/confirm-payment'
    assert client.post(pay,headers=staff,json={'transaction_id':'COD-1'}).status_code==403
    assert client.post(pay,headers=admin,json={'transaction_id':'COD-1'}).status_code==200
    assert client.post(pay,headers=admin,json={'transaction_id':'COD-1'}).status_code==200
    detail=client.get(f'/me/orders/{oid}',headers=h).json();item=detail['order_items'][0]
    review=client.post('/me/reviews',headers=h,json={'order_item_id':item['id'],'rating':4,'images':['https://example.com/review.jpg']})
    assert review.status_code==201,review.text
    path=f"/admin/reviews/{review.json()['id']}"
    assert client.patch(path,headers=staff,json={'status':'approved'}).status_code==403
    assert client.patch(path,headers=admin,json={'status':'approved'}).status_code==200
    assert len(client.get(path,headers=admin).json()['images'])==1
    customer_rows=client.get('/staff/customers',headers=staff,params={'q':'customer@'}).json()
    assert len(customer_rows)==1 and 'password_hash' not in customer_rows[0]
    assert len(client.get(f"/catalog/products/{data['product']['id']}").json()['reviews'])==1
    ret=client.post('/me/returns',headers=h,json={'order_item_id':item['id'],'quantity':1,'reason':'Lỗi may','type':'refund'})
    assert ret.status_code==201,ret.text
    assert client.post('/me/returns',headers=h,json={'order_item_id':item['id'],'quantity':2,'reason':'Lỗi','type':'refund'}).status_code==409
    path=f"/staff/returns/{ret.json()['id']}"
    assert client.patch(path,headers=staff,json={'status':'approved'}).status_code==403
    assert client.patch(path,headers=staff,json={'status':'received'}).status_code==200
    assert client.patch(path,headers=admin,json={'status':'approved'}).status_code==200
    refund=client.patch(path,headers=admin,json={'status':'refunded'})
    assert refund.status_code==200,refund.text
    assert Decimal(refund.json()['refund_amount'])==100000
    assert client.patch(path,headers=admin,json={'status':'refunded'}).status_code==409

def test_coupon_checkout_rollback_and_admin_permissions(client,data):
    admin=headers(data['admin']);h,body=prepare_checkout(client,data['customer'],data['variant']['id'],2)
    failed=client.post('/me/checkout',headers=h,json={**body,'coupon_code':'MISSING'})
    assert failed.status_code==400,failed.text
    with Session(engine) as db:
        assert db.scalar(select(table('product_variants').c.stock_quantity))==5
        assert len(db.execute(select(table('orders'))).all())==0
    assert len(client.get('/me/cart',headers=h).json())==1
    now=datetime.now(timezone.utc)
    coupon=client.post('/staff/catalog/coupons',headers=admin,json=dict(code='SALE10',discount_type='percent',discount_value='10',starts_at=(now-timedelta(days=1)).isoformat(),expires_at=(now+timedelta(days=1)).isoformat(),usage_limit=1))
    assert coupon.status_code==201,coupon.text
    order=client.post('/me/checkout',headers=h,json={**body,'coupon_code':'SALE10'})
    assert order.status_code==201,order.text
    assert Decimal(order.json()['discount_amount'])==20000
    assert Decimal(order.json()['total_amount'])==210000
    with Session(engine) as db:
        assert db.scalar(select(table('coupons').c.used_count))==1
    rid=data['staff']['role_id']
    assert client.put(f'/admin/roles/{rid}/permissions',headers=admin,json={'codes':['users.manage']}).status_code==400
    assert client.put(f'/admin/roles/{rid}/permissions',headers=admin,json={'codes':[]}).status_code==200
    from app.bootstrap import seed
    with Session(engine) as db,db.begin():seed(db)
    assert client.get('/staff/orders',headers=headers(data['staff'])).status_code==403
