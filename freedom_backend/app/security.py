from datetime import datetime, timedelta, timezone
import hashlib
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from .config import settings
from .db import session, table

passwords = PasswordHash.recommended()
oauth = OAuth2PasswordBearer(tokenUrl='/auth/token')
DUMMY_HASH = passwords.hash('dummy-not-a-real-account-password')

def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()

def token_for(user):
    now = datetime.now(timezone.utc)
    return jwt.encode(dict(sub=str(user['id']), iat=now.timestamp(), exp=(now + timedelta(minutes=settings.access_token_minutes)).timestamp(),
                           iss=settings.jwt_issuer, aud=settings.jwt_audience,
                           pv=fingerprint(user['password_hash']), typ='access'), settings.jwt_secret, algorithm='HS256')

def current(token: str = Depends(oauth), db=Depends(session)):
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'],
                            issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                            options={'require': ['sub','exp','iat','pv','typ']})
        if claims['typ'] != 'access':
            raise ValueError()
        uid = int(claims['sub'])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(401, 'Token không hợp lệ', headers={'WWW-Authenticate': 'Bearer'})
    u, r = table('users'), table('roles')
    user = db.execute(select(u, r.c.code.label('role')).join(r, u.c.role_id == r.c.id).where(u.c.id == uid)).mappings().first()
    if not user or user['status'] != 'active' or claims['pv'] != fingerprint(user['password_hash']):
        raise HTTPException(401, 'Tài khoản hoặc phiên không hợp lệ')
    a=table('audit_logs')
    revoked=db.scalar(select(a.c.created_at).where(a.c.user_id==uid,a.c.action=='logout_all').order_by(a.c.created_at.desc()).limit(1))
    if revoked and claims['iat'] <= revoked.timestamp():
        raise HTTPException(401, 'Phiên đã đăng xuất')
    return dict(user)

ADMIN_ONLY_PERMISSIONS = frozenset({'users.manage', 'payments.manage', 'reviews.moderate', 'audit.read'})


def effective_permissions(user, db):
    """Expose exactly the same grants that require() enforces, using current DB roles."""
    if user['role'] == 'admin':
        return ['*']
    if user['role'] != 'staff':
        return []
    p, rp = table('permissions'), table('role_permissions')
    return sorted(set(db.scalars(select(p.c.code).join(rp, rp.c.permission_id == p.c.id).where(
        rp.c.role_id == user['role_id'], p.c.code.not_in(ADMIN_ONLY_PERMISSIONS))).all()))


def require(permission):
    def check(user=Depends(current), db=Depends(session)):
        if user['role'] == 'admin':
            return user
        if user['role'] == 'staff' and permission not in ADMIN_ONLY_PERMISSIONS:
            p, rp = table('permissions'), table('role_permissions')
            if db.scalar(select(p.c.id).join(rp, rp.c.permission_id == p.c.id).where(
                    rp.c.role_id == user['role_id'], p.c.code == permission)):
                return user
        raise HTTPException(403, 'Không có quyền thực hiện')
    return check

def public_user(user):
    return {k:v for k,v in user.items() if k not in {'password_hash'}}

def owned(row, user):
    if row['user_id'] != user['id']:
        raise HTTPException(404, 'Không tìm thấy dữ liệu')
    return row
