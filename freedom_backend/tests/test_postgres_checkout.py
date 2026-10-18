"""Run on a disposable PostgreSQL DB to exercise locks and real constraints."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import engine,table
from conftest import headers


def cart_and_body(client,data,user='customer',quantity=2):
    h=headers(data[user]);vid=data['variant']['id']
    assert client.put('/me/cart/items',headers=h,json={'variant_id':vid,'quantity':quantity}).status_code==200
    return h,dict(variant_ids=[vid],recipient_name='Người nhận kiểm thử',recipient_phone='0912345678',shipping_address='10 Tràng Tiền, Hà Nội',payment_method='cod',checkout_key=uuid4().hex)


def test_pg_delivery_real_constraints_and_failure(client,data):
    h,body=cart_and_body(client,data)
    response=client.post('/me/checkout',headers=h,json=body)
    assert response.status_code==201,response.text
    oid=response.json()['id'];admin=headers(data['admin'])
    assert client.post('/me/checkout',headers=h,json=body).json()['id']==oid
    assert client.get(f'/me/orders/{oid}',headers=headers(data['other'])).status_code==404
    for status in ['packing','shipping','failed']:
        result=client.patch(f'/staff/orders/{oid}/status',headers=admin,json={'status':status})
        assert result.status_code==200,result.text
    result=client.put(f'/staff/orders/{oid}/shipment',headers=admin,json={'carrier':'Thủ công','tracking_number':'PG-TEST-1'})
    assert result.status_code==200,result.text
    assert client.patch(f'/staff/orders/{oid}/status',headers=admin,json={'status':'cancelled'}).status_code==200
    with Session(engine) as db:
        assert db.scalar(select(table('product_variants').c.stock_quantity).where(table('product_variants').c.id==data['variant']['id']))==5


def test_pg_pickup_and_size_inventory(client,data):
    admin=headers(data['admin'])
    body=dict(category_id=data['product']['category_id'],name='Quần size test',slug='quan-size-test',base_price='500000',status='active',variants=[dict(size_name='L',color_name='Đen',price='500000',stock_quantity=12)])
    created=client.post('/staff/catalog/products',headers=admin,json=body)
    assert created.status_code==201,created.text
    detail=client.get('/staff/catalog/products/'+str(created.json()['id']),headers=admin).json()
    assert detail['product_variants'][0]['stock_quantity']==12
    inventory=client.get('/staff/inventory',headers=admin).json()
    assert any(item['product_id']==created.json()['id'] and item['size_name']=='L' and item['stock_quantity']==12 for item in inventory)
    h,checkout=cart_and_body(client,data)
    checkout.update(fulfillment_method='pickup',recipient_email='test@example.com',pickup_start=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),pickup_end=(datetime.now(timezone.utc)+timedelta(days=1,hours=1)).isoformat())
    response=client.post('/me/checkout',headers=h,json=checkout)
    assert response.status_code==201,response.text
    oid=response.json()['id'];assert float(response.json()['shipping_fee'])==0
    assert client.patch(f'/staff/orders/{oid}/status',headers=admin,json={'status':'packing'}).status_code==200
    assert client.patch(f'/staff/orders/{oid}/status',headers=admin,json={'status':'delivered'}).status_code==200


def test_pg_concurrent_idempotent_checkout_and_no_oversell(client,data):
    h,body=cart_and_body(client,data,quantity=4)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:client.post('/me/checkout',headers=h,json=body),range(2)))
    assert [response.status_code for response in results]==[201,201]
    assert results[0].json()['id']==results[1].json()['id']
    with Session(engine) as db:
        assert db.scalar(select(table('product_variants').c.stock_quantity).where(table('product_variants').c.id==data['variant']['id']))==1
    # A second customer cannot buy more than the remaining inventory.
    assert client.put('/me/cart/items',headers=headers(data['other']),json={'variant_id':data['variant']['id'],'quantity':2}).status_code==409
