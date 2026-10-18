"""Commerce contracts, isolated DB and actual FastAPI request validation."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import Table,Column,Integer,String,Text,DateTime,Numeric,ForeignKey,UniqueConstraint,CheckConstraint,insert,select,func,update
from app import db as database,security
from app.main import app
from app.routers import commerce,community
from test_product_crud import product_db,payload


@pytest.fixture
def store_db(product_db,monkeypatch):
    engine,t,user=product_db;m=t['products'].metadata
    Table('users',m,Column('id',Integer,primary_key=True),Column('full_name',String),Column('email',String))
    Table('carts',m,Column('id',Integer,primary_key=True),Column('user_id',Integer,unique=True))
    Table('cart_items',m,Column('id',Integer,primary_key=True),Column('cart_id',Integer),Column('variant_id',Integer),Column('quantity',Integer),UniqueConstraint('cart_id','variant_id'))
    Table('orders',m,Column('id',Integer,primary_key=True),Column('order_code',String,unique=True),Column('user_id',Integer),Column('coupon_id',Integer),Column('recipient_name',String),Column('recipient_phone',String),Column('shipping_address',Text),Column('recipient_email',String),Column('fulfillment_method',String,default='delivery'),Column('pickup_start',DateTime(timezone=True)),Column('pickup_end',DateTime(timezone=True)),Column('checkout_key',String),Column('subtotal',Numeric(15,2)),Column('shipping_fee',Numeric(15,2)),Column('discount_amount',Numeric(15,2)),Column('total_amount',Numeric(15,2)),Column('payment_method',String),Column('customer_note',Text),Column('confirmed_by',Integer),Column('placed_at',DateTime,default=lambda:datetime.now(timezone.utc)),Column('updated_at',DateTime),Column('status',String,default='pending'),UniqueConstraint('user_id','checkout_key'),CheckConstraint("status IN ('pending','packing','shipping','delivered','failed','cancelled','confirmed','preparing','shipped')"))
    # Replace the minimal history-only order_items table in product_db.
    m.remove(t['order_items'])
    Table('order_items',m,Column('id',Integer,primary_key=True),Column('order_id',Integer),Column('variant_id',Integer),Column('sku_snapshot',String),Column('product_name_snapshot',String),Column('size_snapshot',String),Column('color_snapshot',String),Column('unit_price',Numeric(15,2)),Column('quantity',Integer))
    Table('payments',m,Column('id',Integer,primary_key=True),Column('order_id',Integer),Column('provider',String),Column('amount',Numeric(15,2)),Column('status',String,default='pending'),Column('paid_at',DateTime),Column('provider_transaction_id',String),CheckConstraint("status IN ('pending','paid','failed','refunded')"))
    Table('shipments',m,Column('id',Integer,primary_key=True),Column('order_id',Integer),Column('carrier',String),Column('tracking_number',String),Column('status',String,default='preparing'),Column('shipped_at',DateTime),Column('delivered_at',DateTime),CheckConstraint("status IN ('preparing','picked_up','in_transit','delivered','failed','returned')"))
    Table('order_status_histories',m,Column('id',Integer,primary_key=True),Column('order_id',Integer),Column('old_status',String),Column('new_status',String),Column('changed_by',Integer),Column('created_at',DateTime,default=lambda:datetime.now(timezone.utc)))
    # Existing order_items is already present physically, recreate it inside test DB only.
    with engine.begin() as db:db.exec_driver_sql('DROP TABLE order_items')
    m.create_all(engine)
    with engine.begin() as db:db.execute(insert(m.tables['users']),[{'id':1,'full_name':'Admin'},{'id':2,'full_name':'Customer'},{'id':3,'full_name':'Other'}])
    monkeypatch.setattr(commerce,'table',lambda name:m.tables[name])
    monkeypatch.setattr(community,'table',lambda name:m.tables[name])
    return engine,m.tables,user


def create_sizes(client,store_db):
    response=client.post('/staff/catalog/products',json=payload(status='active',variants=[dict(size_name='M',color_name='Đen',price='500000',stock_quantity=10),dict(size_name='L',color_name='Đen',price='550000',stock_quantity=5)]))
    assert response.status_code==201,response.text
    detail=client.get('/staff/catalog/products/'+str(response.json()['id'])).json()
    assert [v['size_name'] for v in detail['product_variants']]==['M','L']
    inventory=client.get('/staff/inventory').json()
    assert sum(item['stock_quantity'] for item in inventory)==15
    assert inventory[0]['product_name']=='Sơ mi Linen' and inventory[0]['size_name']=='M'
    store_db[2].update(id=2,role='customer',role_id=2)
    for variant in detail['product_variants']:
        assert client.put('/me/cart/items',json={'variant_id':variant['id'],'quantity':2}).status_code==200
    return detail


def checkout_body(ids,**changes):
    return dict(variant_ids=ids,fulfillment_method='delivery',recipient_name='Khách hàng',recipient_phone='0912345678',shipping_address='Số 10 Tràng Tiền, Hà Nội',payment_method='cod',checkout_key=uuid4().hex,**changes)


def test_selected_checkout_and_idempotent_retry(client,store_db):
    product=create_sizes(client,store_db);ids=[v['id'] for v in product['product_variants']]
    cart=client.get('/me/cart').json()
    assert len(cart)==2 and cart[0]['product_name']=='Sơ mi Linen' and cart[0]['size_name']=='M'
    body=checkout_body(ids[:1])
    response=client.post('/me/checkout',json=body)
    assert response.status_code==201,response.text
    order=response.json();oid=order['id']
    assert order['recipient_name']=='Khách hàng' and order['shipping_address']==body['shipping_address']
    assert float(order['total_amount'])==1030000
    assert [item['variant_id'] for item in client.get('/me/cart').json()]==ids[1:]
    assert client.post('/me/checkout',json=body).json()['id']==oid
    engine,t,user=store_db
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(t['orders']))==1
        assert db.scalar(select(t['product_variants'].c.stock_quantity).where(t['product_variants'].c.id==ids[0]))==8
    user['id']=3
    assert client.get(f'/me/orders/{oid}').status_code==404
    assert client.post('/me/checkout',json=checkout_body(ids[1:])).status_code==400
    user.update(id=1,role='admin',role_id=1)
    detail=client.get(f'/staff/orders/{oid}').json()
    assert detail['recipient_phone']==body['recipient_phone'] and len(detail['order_items'])==1


def test_pickup_fields_dates_no_shipping_fee_and_statuses(client,store_db):
    product=create_sizes(client,store_db);ids=[v['id'] for v in product['product_variants']]
    body=checkout_body(ids);body.update(fulfillment_method='pickup',recipient_email='customer@example.com',pickup_start=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),pickup_end=(datetime.now(timezone.utc)+timedelta(days=1,hours=1)).isoformat())
    response=client.post('/me/checkout',json=body)
    assert response.status_code==201,response.text
    order=response.json();oid=order['id']
    assert float(order['shipping_fee'])==0 and order['recipient_email']=='customer@example.com'
    assert '69' in order['shipping_address'] and order['pickup_start']
    assert client.get('/me/cart').json()==[]
    store_db[2].update(id=1,role='admin',role_id=1)
    for status,code in [('packing',200),('shipping',409),('delivered',200),('failed',409)]:
        assert client.patch(f'/staff/orders/{oid}/status',json={'status':status}).status_code==code
    assert client.put(f'/staff/orders/{oid}/shipment',json={'carrier':'X','tracking_number':'X'}).status_code==409


def test_delivery_status_failure_retry_and_cancel_stock_once(client,store_db):
    product=create_sizes(client,store_db);vid=product['product_variants'][0]['id']
    order=client.post('/me/checkout',json=checkout_body([vid])).json();oid=order['id']
    assert client.patch(f'/staff/orders/{oid}/status',json={'status':'packing'}).status_code==403
    store_db[2].update(id=1,role='admin',role_id=1)
    assert client.patch(f'/staff/orders/{oid}/status',json={'status':'delivered'}).status_code==409
    for status in ['packing','shipping','failed','shipping','failed']:
        response=client.patch(f'/staff/orders/{oid}/status',json={'status':status})
        assert response.status_code==200,response.text
    assert client.put(f'/staff/orders/{oid}/shipment',json={'carrier':'Giao hàng thủ công','tracking_number':'TRACK-1'}).status_code==200
    assert client.patch(f'/staff/orders/{oid}/status',json={'status':'cancelled'}).status_code==200
    assert client.patch(f'/staff/orders/{oid}/status',json={'status':'cancelled'}).status_code==409
    with store_db[0].connect() as db:
        assert db.scalar(select(store_db[1]['product_variants'].c.stock_quantity).where(store_db[1]['product_variants'].c.id==vid))==10


def test_invalid_selection_or_stock_rolls_back_whole_checkout(client,store_db):
    product=create_sizes(client,store_db);ids=[v['id'] for v in product['product_variants']]
    for selected,status in [([],422),([ids[0],ids[0]],422),([ids[0],99999],409)]:
        assert client.post('/me/checkout',json=checkout_body(selected)).status_code==status
    with store_db[0].begin() as db:db.execute(update(store_db[1]['product_variants']).where(store_db[1]['product_variants'].c.id==ids[1]).values(stock_quantity=1))
    assert client.post('/me/checkout',json=checkout_body(ids)).status_code==409
    with store_db[0].connect() as db:
        assert db.scalar(select(func.count()).select_from(store_db[1]['orders']))==0
        assert db.scalar(select(store_db[1]['product_variants'].c.stock_quantity).where(store_db[1]['product_variants'].c.id==ids[0]))==10
    assert len(client.get('/me/cart').json())==2


def test_size_stock_edit_stale_inventory_and_preserve_old_sku(client,store_db):
    product=create_sizes(client,store_db)
    store_db[2].update(id=1,role='admin',role_id=1)
    first=product['product_variants'][0]
    values=dict(id=first['id'],size_name=first['size_name'],color_name=first['color_name'],price='520000',stock_quantity=12,expected_stock=first['stock_quantity'],is_active=True)
    response=client.put('/staff/catalog/products/'+str(product['id']),json=payload(status='active',variants=[values]))
    assert response.status_code==200,response.text
    assert client.put('/staff/catalog/products/'+str(product['id']),json=payload(status='active',variants=[values])).status_code==409
    values.update(expected_stock=12,size_name='XL')
    assert client.put('/staff/catalog/products/'+str(product['id']),json=payload(status='active',variants=[values])).status_code==409
    detail=client.get('/staff/catalog/products/'+str(product['id'])).json()
    assert len(detail['product_variants'])==2 and detail['product_variants'][0]['sku']==first['sku']


@pytest.mark.parametrize('change',[{'recipient_phone':'bad'},{'recipient_name':''},{'shipping_address':'X'},{'variant_ids':[]}])
def test_invalid_recipient_rejected(client,store_db,change):
    body=checkout_body([1]);body.update(change)
    assert client.post('/me/checkout',json=body).status_code==422


def test_checkout_rejects_changed_quantity_and_price(client,store_db):
    product=create_sizes(client,store_db);vid=product['product_variants'][0]['id']
    for extra in [{'expected_total':'1'},{'expected_quantities':{str(vid):1}}]:
        body=checkout_body([vid]);body.update(extra)
        assert client.post('/me/checkout',json=body).status_code==409
    assert len(client.get('/me/cart').json())==2


@pytest.mark.parametrize('invalid',[{'recipient_email':None},{'pickup_start':'2020-01-01T09:00:00+07:00','pickup_end':'2020-01-01T10:00:00+07:00'},{'pickup_start':'2030-01-01T10:00:00+07:00','pickup_end':'2030-01-01T09:00:00+07:00'}])
def test_pickup_validation(client,store_db,invalid):
    product=create_sizes(client,store_db);vid=product['product_variants'][0]['id']
    body=checkout_body([vid]);body.update(fulfillment_method='pickup',recipient_email='customer@example.com',pickup_start='2030-01-01T09:00:00+07:00',pickup_end='2030-01-01T10:00:00+07:00');body.update(invalid)
    assert client.post('/me/checkout',json=body).status_code==422
    assert len(client.get('/me/cart').json())==2
