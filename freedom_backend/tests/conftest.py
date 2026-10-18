"""Integration tests require an EMPTY disposable PostgreSQL DB; never use production."""
import os
os.environ.setdefault('JWT_SECRET','test-only-'+'x'*64)
os.environ.setdefault('DATABASE_URL','postgresql+psycopg://unused@localhost/unused')
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from app.db import engine, table, add
from app.bootstrap import seed
from app.security import passwords, token_for
from app.main import app

@pytest.fixture(scope='session')
def client():
    return TestClient(app)

@pytest.fixture
def data():
    if os.getenv('RUN_PG_TESTS')!='1':pytest.skip('Set RUN_PG_TESTS=1 and DATABASE_URL to a disposable PostgreSQL database')
    # Safety gate: DB must explicitly use a test name; schema must be loaded separately.
    if not engine.url.database or not engine.url.database.endswith('_test'):
        raise RuntimeError('Integration test database name must end with _test')
    with Session(engine) as db,db.begin():
        names=db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars().all()
        for name in names:
            if not name.replace('_','').isalnum():raise RuntimeError('Unsafe table name')
        for name in names:table(name)
        db.execute(text('TRUNCATE '+', '.join('"'+n+'"' for n in names)+' RESTART IDENTITY CASCADE'))
        seed(db);r=table('roles')
        result={}
        for code in ('admin','staff','customer'):
            uid=db.scalar(select(r.c.id).where(r.c.code==code))
            result[code]=add(db,'users',dict(role_id=uid,full_name=code,email=code+'@example.com',password_hash=passwords.hash('Strong-password-123')))
        result['other']=add(db,'users',dict(role_id=result['customer']['role_id'],full_name='Other',email='other@example.com',password_hash=passwords.hash('Strong-password-123')))
        category=add(db,'categories',dict(name='Áo',slug='ao'))
        size=add(db,'sizes',dict(name='M'));color=add(db,'colors',dict(name='Đen'))
        product=add(db,'products',dict(category_id=category['id'],name='Áo sơ mi',slug='ao-so-mi',base_price=100000,status='active'))
        variant=add(db,'product_variants',dict(product_id=product['id'],size_id=size['id'],color_id=color['id'],sku='AO-M-DEN',price=100000,stock_quantity=5))
        result.update(product=product,variant=variant)
    return result

def headers(user):return {'Authorization':'Bearer '+token_for(user)}
