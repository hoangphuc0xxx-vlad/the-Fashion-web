"""Real auth dependencies against isolated in-memory tables; never touch the user's DB."""
import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, insert, delete, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException
from app.main import app
from app.db import session
from app import security


@pytest.fixture
def access_db(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    meta = MetaData()
    tables = {
        'roles': Table('roles', meta, Column('id', Integer, primary_key=True), Column('code', String)),
        'users': Table('users', meta, Column('id', Integer, primary_key=True), Column('role_id', Integer),
                       Column('status', String), Column('password_hash', String), Column('full_name', String), Column('email', String)),
        'permissions': Table('permissions', meta, Column('id', Integer, primary_key=True), Column('code', String)),
        'role_permissions': Table('role_permissions', meta, Column('role_id', Integer), Column('permission_id', Integer)),
        'audit_logs': Table('audit_logs', meta, Column('id', Integer, primary_key=True), Column('user_id', Integer),
                            Column('action', String), Column('created_at', DateTime(timezone=True))),
    }
    meta.create_all(engine)
    users = {role: dict(id=i, role_id=i, status='active', password_hash='test-hash', full_name=role, email=role+'@example.com')
             for i, role in enumerate(('customer', 'staff', 'admin', 'unknown'), 1)}
    with engine.begin() as db:
        db.execute(insert(tables['roles']), [dict(id=u['id'], code=role) for role, u in users.items()])
        db.execute(insert(tables['users']), list(users.values()))
        db.execute(insert(tables['permissions']), [dict(id=1, code='orders.manage'), dict(id=2, code='inventory.read'), dict(id=3, code='users.manage')])
        # A mistakenly granted admin-only permission must still be denied for staff.
        db.execute(insert(tables['role_permissions']), [dict(role_id=2, permission_id=i) for i in (1, 2, 3)])
    monkeypatch.setattr(security, 'table', lambda name: tables[name])
    def test_session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[session] = test_session
    yield engine, tables, users
    app.dependency_overrides.pop(session, None)
    engine.dispose()


def auth(user):
    return {'Authorization': 'Bearer ' + security.token_for(user)}


@pytest.mark.parametrize('path', ['/auth/me', '/admin/users', '/admin/dashboard', '/staff/orders', '/staff/inventory'])
def test_guest_cannot_access_private_api(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize('role,grants', [('customer', []), ('staff', ['inventory.read', 'orders.manage']), ('admin', ['*']), ('unknown', [])])
def test_me_exposes_db_role_and_effective_grants(client, access_db, role, grants):
    _, _, users = access_db
    result = client.get('/auth/me', headers=auth(users[role]))
    assert result.status_code == 200
    assert result.json()['role'] == role
    assert result.json()['permissions'] == grants
    assert 'password_hash' not in result.json()


@pytest.mark.parametrize('path', ['/admin/users', '/admin/dashboard', '/admin/roles', '/admin/audit-logs', '/admin/reviews', '/staff/orders', '/staff/inventory', '/staff/customers', '/staff/catalog/products', '/staff/returns', '/staff/support/tickets'])
def test_customer_direct_api_requests_are_forbidden(client, access_db, path):
    assert client.get(path, headers=auth(access_db[2]['customer'])).status_code == 403


def test_permissions_and_role_changes_take_effect_without_relogin(client, access_db):
    engine, tables, users = access_db
    headers = auth(users['staff'])
    with Session(engine) as db:
        staff = {**users['staff'], 'role': 'staff'}
        assert security.require('orders.manage')(staff, db)['id'] == staff['id']
        with pytest.raises(HTTPException) as denied:
            security.require('users.manage')(staff, db)
        assert denied.value.status_code == 403
    with engine.begin() as db:
        db.execute(delete(tables['role_permissions']).where(tables['role_permissions'].c.role_id == 2))
    assert client.get('/auth/me', headers=headers).json()['permissions'] == []
    assert client.get('/staff/orders', headers=headers).status_code == 403
    with engine.begin() as db:
        db.execute(update(tables['users']).where(tables['users'].c.id == 2).values(role_id=1))
    assert client.get('/auth/me', headers=headers).json()['role'] == 'customer'
    assert client.get('/admin/dashboard', headers=headers).status_code == 403
    with engine.begin() as db:
        db.execute(update(tables['users']).where(tables['users'].c.id == 2).values(status='blocked'))
    assert client.get('/auth/me', headers=headers).status_code == 401
