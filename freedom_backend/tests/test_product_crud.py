"""Product CRUD contracts using an isolated database, never the live store."""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey, JSON, insert, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app import db as database, security
from app.routers import catalog


@pytest.fixture
def product_db(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    m=MetaData()
    Table('categories',m,Column('id',Integer,primary_key=True),Column('name',String),Column('slug',String,unique=True),Column('parent_id',Integer),Column('is_active',Boolean,default=True))
    Table('brands',m,Column('id',Integer,primary_key=True),Column('name',String),Column('slug',String),Column('is_active',Boolean,default=True))
    Table('products',m,Column('id',Integer,primary_key=True),Column('category_id',Integer,ForeignKey('categories.id'),nullable=False),Column('brand_id',Integer,ForeignKey('brands.id')),
          Column('name',String,nullable=False),Column('slug',String,unique=True,nullable=False),Column('description',Text),Column('material',String),Column('base_price',Numeric(15,2)),
          Column('status',String,default='draft'),Column('created_by',Integer),Column('created_at',DateTime,default=lambda:datetime.now(timezone.utc)),Column('updated_at',DateTime,default=lambda:datetime.now(timezone.utc)))
    Table('product_variants',m,Column('id',Integer,primary_key=True),Column('product_id',Integer,ForeignKey('products.id')),Column('sku',String),Column('is_active',Boolean,default=True),
          Column('price',Numeric(15,2)),Column('stock_quantity',Integer,default=5),Column('reserved_quantity',Integer,default=0),Column('size_id',Integer),Column('color_id',Integer))
    Table('product_images',m,Column('id',Integer,primary_key=True),Column('product_id',Integer,ForeignKey('products.id')),Column('image_url',String),
          Column('variant_id',Integer),Column('alt_text',String),Column('sort_order',Integer,default=0),Column('is_primary',Boolean,default=False))
    Table('order_items',m,Column('id',Integer,primary_key=True),Column('variant_id',Integer,ForeignKey('product_variants.id')))
    Table('reviews',m,Column('id',Integer,primary_key=True),Column('product_id',Integer),Column('status',String))
    Table('review_images',m,Column('id',Integer,primary_key=True),Column('review_id',Integer))
    Table('audit_logs',m,Column('id',Integer,primary_key=True),Column('user_id',Integer),Column('action',String),Column('entity_type',String),Column('entity_id',Integer),Column('details',JSON))
    Table('permissions',m,Column('id',Integer,primary_key=True),Column('code',String))
    Table('role_permissions',m,Column('role_id',Integer),Column('permission_id',Integer))
    m.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(m.tables['categories']),[{'id':1,'name':'Áo','slug':'ao'},{'id':2,'name':'Quần','slug':'quan'}])
        conn.execute(insert(m.tables['brands']),{'id':1,'name':'Freedom','slug':'freedom'})
        conn.execute(insert(m.tables['permissions']),{'id':1,'code':'catalog.manage'})
    user={'id':1,'role_id':1,'role':'admin','status':'active'}
    monkeypatch.setattr(database,'table',lambda name:m.tables[name])
    monkeypatch.setattr(catalog,'table',lambda name:m.tables[name])
    monkeypatch.setattr(security,'table',lambda name:m.tables[name])
    def test_session():
        with Session(engine) as db,db.begin():yield db
    app.dependency_overrides[database.session]=test_session
    app.dependency_overrides[security.current]=lambda:user
    yield engine,m.tables,user
    app.dependency_overrides.pop(database.session,None)
    app.dependency_overrides.pop(security.current,None)
    engine.dispose()


def payload(**values):
    return dict(dict(category_id=1,brand_id=1,name='Sơ mi Linen',slug='so-mi-linen',base_price='549000.50',material='Linen',description='Mô tả đầy đủ',status='draft'),**values)


def test_create_read_update_archive_restore_preserves_history(client,product_db):
    engine,t,_=product_db
    body=payload()
    created=client.post('/staff/catalog/products',json=body)
    assert created.status_code==201,created.text
    pid=created.json()['id'];path=f'/staff/catalog/products/{pid}'
    detail=client.get(path)
    assert detail.status_code==200
    assert detail.json()['category']['name']=='Áo'
    assert detail.json()['brand']['name']=='Freedom'
    assert detail.json()['description']==body['description']
    assert client.get(f'/catalog/products/{pid}').status_code==404
    changed={**body,'name':'Sơ mi mới','slug':'so-mi-moi','category_id':2,'brand_id':None,'material':None,'description':None,'base_price':'699000.75','status':'active'}
    updated=client.put(path,json=changed)
    assert updated.status_code==200,updated.text
    assert Decimal(updated.json()['base_price'])==Decimal('699000.75')
    assert updated.json()['brand_id'] is None
    with engine.begin() as conn:
        conn.execute(insert(t['product_variants']),{'id':1,'product_id':pid,'sku':'SM-M','price':699000,'size_id':1,'color_id':1})
        conn.execute(insert(t['product_images']),{'product_id':pid,'image_url':'https://example.com/shirt.jpg'})
        conn.execute(insert(t['order_items']),{'id':1,'variant_id':1})
    assert len(client.get('/catalog/products').json())==1
    assert len(client.get(path).json()['product_variants'])==1
    assert len(client.get(path).json()['product_images'])==1
    deleted=client.delete(path)
    assert deleted.status_code==204 and deleted.content==b''
    assert client.get(path).json()['status']=='archived'
    assert client.get(f'/catalog/products/{pid}').status_code==404
    assert client.get('/catalog/products').json()==[]
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(t['products']))==1
        assert conn.scalar(select(func.count()).select_from(t['product_variants']))==1
        assert conn.scalar(select(func.count()).select_from(t['order_items']))==1
        assert conn.scalar(select(func.count()).select_from(t['audit_logs']))==3
    assert client.put(path,json=changed).status_code==200
    assert client.get(f'/catalog/products/{pid}').status_code==200


def test_validation_duplicate_slug_and_not_found(client,product_db):
    assert client.post('/staff/catalog/products',json=payload()).status_code==201
    assert client.post('/staff/catalog/products',json=payload()).status_code==409
    assert client.post('/staff/catalog/products',json={**payload(),'base_price':-1}).status_code==422
    assert client.post('/staff/catalog/products',json={**payload(),'name':'   '}).status_code==422
    assert client.post('/staff/catalog/products',json={**payload(),'status':'unsupported'}).status_code==422
    for method in ('get','put','delete'):
        args={'json':payload()} if method=='put' else {}
        assert getattr(client,method)('/staff/catalog/products/999',**args).status_code==404


@pytest.mark.parametrize('role',['customer','staff'])
def test_unauthorized_roles_cannot_crud(client,product_db,role):
    product_db[2].update(role=role,role_id=2)
    for method,path in [('get','/staff/catalog/products'),('post','/staff/catalog/products'),('get','/staff/catalog/products/1'),('put','/staff/catalog/products/1'),('delete','/staff/catalog/products/1')]:
        args={'json':payload()} if method in ('post','put') else {}
        assert getattr(client,method)(path,**args).status_code==403


def test_staff_with_catalog_permission_can_crud(client,product_db):
    engine,t,user=product_db
    user.update(role='staff',role_id=2)
    with engine.begin() as conn:conn.execute(insert(t['role_permissions']),{'role_id':2,'permission_id':1})
    created=client.post('/staff/catalog/products',json=payload())
    assert created.status_code==201
    path='/staff/catalog/products/'+str(created.json()['id'])
    assert client.get(path).status_code==200
    assert client.put(path,json={**payload(),'name':'Đã sửa'}).status_code==200
    assert client.delete(path).status_code==204


def test_guest_cannot_read_private_product(client,product_db):
    app.dependency_overrides.pop(security.current)
    assert client.get('/staff/catalog/products/1').status_code==401


def test_parent_category_includes_children_and_grandchildren(client,product_db):
    engine,t,_=product_db
    def child(name,slug,parent):
        result=client.post('/staff/catalog/categories',json={'name':name,'slug':slug,'parent_id':parent,'is_active':True})
        assert result.status_code==201,result.text
        return result.json()['id']
    suit=child('Suit','suit',None)
    shirt=child('Áo sơ mi','ao-so-mi',1)
    jacket=child('Áo khoác','ao-khoac',1)
    linen=child('Sơ mi Linen','so-mi-linen',shirt)
    ids={}
    for index,(name,cat) in enumerate([('Ao',1),('Shirt',shirt),('Jacket',jacket),('Linen',linen),('Pants',2),('Suit',suit)],1):
        product=client.post('/staff/catalog/products',json=payload(name=name,slug=name.lower(),category_id=cat,status='active'))
        assert product.status_code==201,product.text
        ids[name]=product.json()['id']
        with engine.begin() as db:db.execute(insert(t['product_variants']),{'product_id':ids[name],'sku':name,'price':549000})
    assert {p['name'] for p in client.get('/catalog/products?category_id=1').json()}=={'Ao','Shirt','Jacket','Linen'}
    assert {p['name'] for p in client.get(f'/catalog/products?category_id={shirt}').json()}=={'Shirt','Linen'}
    assert {p['name'] for p in client.get('/catalog/products?category_id=2').json()}=={'Pants'}
    assert {p['name'] for p in client.get(f'/catalog/products?category_id={suit}').json()}=={'Suit'}
    assert client.get('/catalog/products?category_id=999999').json()==[]
    # Hiding a parent also hides every descendant and their public product pages.
    assert client.delete('/staff/catalog/categories/1').status_code==204
    assert {c['id'] for c in client.get('/catalog/lookups/categories').json()}=={2,suit}
    assert {p['name'] for p in client.get('/catalog/products').json()}=={'Pants','Suit'}
    assert client.get(f'/catalog/products?category_id={shirt}').json()==[]
    assert client.get(f"/catalog/products/{ids['Shirt']}").status_code==404
    assert client.get(f"/catalog/products/{ids['Pants']}").status_code==200
    assert client.post('/staff/catalog/categories',json={'name':'Hoodie','slug':'hoodie','parent_id':shirt}).status_code==422
    # Restoring the root restores valid descendants without changing their links.
    assert client.put('/staff/catalog/categories/1',json={'name':'Áo','slug':'ao','parent_id':None,'is_active':True}).status_code==200
    assert len(client.get('/catalog/products?category_id=1').json())==4
    assert client.put('/staff/catalog/categories/1',json={'name':'Áo','slug':'ao','parent_id':linen,'is_active':True}).status_code==422


def test_category_filter_is_applied_before_pagination(client,product_db):
    engine,t,_=product_db
    with engine.begin() as db:
        db.execute(insert(t['products']),[{'id':i,'category_id':1 if i==1 else 2,'name':f'Product {i}','slug':f'product-{i}','status':'active','base_price':100000} for i in range(1,103)])
        db.execute(insert(t['product_variants']),[{'product_id':i,'sku':f'SKU-{i}','price':100000} for i in range(1,103)])
    assert len(client.get('/catalog/products?limit=100').json())==100
    assert [p['id'] for p in client.get('/catalog/products?category_id=1&limit=100').json()]==[1]


def test_published_product_is_visible_without_variants(client,product_db):
    engine,t,_=product_db
    draft=client.post('/staff/catalog/products',json=payload()).json()
    pid=draft['id']
    assert client.get('/catalog/products').json()==[]
    assert client.put(f'/staff/catalog/products/{pid}',json=payload(status='active')).status_code==200
    for query in ('','?category_id=1','?q=Linen','?min_price=500000&max_price=600000'):
        assert [p['id'] for p in client.get('/catalog/products'+query).json()]==[pid]
    assert client.get(f'/catalog/products/{pid}').json()['product_variants']==[]
    assert client.get('/catalog/products?size_id=1').json()==[]
    assert client.get('/catalog/products?color_id=1').json()==[]
    assert client.get('/catalog/products?max_price=100000').json()==[]
    with engine.begin() as db:db.execute(insert(t['product_variants']),{'product_id':pid,'sku':'SM-M','price':700000,'size_id':1,'color_id':1})
    assert len(client.get('/catalog/products?size_id=1').json())==1
    assert client.get('/catalog/products?size_id=2').json()==[]
    assert client.get('/catalog/products?max_price=600000').json()==[]
    assert len(client.get('/catalog/products?min_price=650000&max_price=750000').json())==1
    assert client.delete(f'/staff/catalog/products/{pid}').status_code==204
    assert client.get('/catalog/products').json()==[]
