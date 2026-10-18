from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import secrets
import smtplib
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from .. import schemas as s
from ..config import settings
from ..db import session, table, add, audit, one
from ..security import passwords, token_for, current, public_user, fingerprint, DUMMY_HASH, effective_permissions

router = APIRouter(prefix='/auth',tags=['Phúc • xác thực'])

def role_id(db, code):
    t=table('roles')
    rid=db.scalar(select(t.c.id).where(t.c.code==code))
    if rid is None:
        raise HTTPException(503,'Chạy python -m app.bootstrap trước')
    return rid

@router.post('/register',status_code=201)
def register(body:s.Register,db=Depends(session)):
    user=add(db,'users',dict(full_name=body.full_name,email=str(body.email).lower(),
        role_id=role_id(db,'customer'),password_hash=passwords.hash(body.password)))
    audit(db,user['id'],'register','users',user['id'])
    return public_user(user)

@router.post('/token')
def login(form:OAuth2PasswordRequestForm=Depends(),db=Depends(session)):
    t=table('users')
    user=db.execute(select(t).where(t.c.email==form.username.strip().lower())).mappings().first()
    try:
        valid=passwords.verify(form.password,user['password_hash'] if user else DUMMY_HASH)
    except Exception:
        valid=False
    if not user or not valid or user['status']!='active':
        raise HTTPException(401,'Email hoặc mật khẩu không đúng')
    audit(db,user['id'],'login','users',user['id'])
    return dict(access_token=token_for(user),token_type='bearer',expires_in=settings.access_token_minutes*60)

@router.get('/me')
def me(user=Depends(current), db=Depends(session)):
    return {**public_user(user), 'permissions': effective_permissions(user, db)}

@router.post('/logout')
def logout(user=Depends(current),db=Depends(session)):
    # Existing audit table doubles as a persistent per-user revocation marker.
    # updated_at is not used: profile edits must not invalidate tokens accidentally.
    audit(db,user['id'],'logout_all','users',user['id'])
    return {'detail':'Đã đăng xuất tất cả token cấp trước thời điểm này'}

@router.post('/password')
def change_password(body:s.ChangePassword,user=Depends(current),db=Depends(session)):
    row=one(db,'users',user['id'],lock=True)
    if not passwords.verify(body.old_password,row['password_hash']):
        raise HTTPException(400,'Mật khẩu hiện tại không đúng')
    db.execute(update(table('users')).where(table('users').c.id==user['id']).values(
        password_hash=passwords.hash(body.new_password),updated_at=datetime.now(timezone.utc)))
    audit(db,user['id'],'change_password','users',user['id'])
    return {'detail':'Đã đổi mật khẩu; đăng nhập lại'}

@router.post('/forgot-password',status_code=202)
def forgot(body:s.Forgot,db=Depends(session)):
    t=table('users')
    user=db.execute(select(t).where(t.c.email==str(body.email).lower(),t.c.status=='active')).mappings().first()
    try:
        # Connect for every request so SMTP outages do not disclose account existence.
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:
            if settings.smtp_starttls: smtp.starttls()
            if settings.smtp_username: smtp.login(settings.smtp_username,settings.smtp_password)
            if user:
                raw=secrets.token_urlsafe(48)
                add(db,'password_reset_tokens',dict(user_id=user['id'],token_hash=fingerprint(raw),
                    expires_at=datetime.now(timezone.utc)+timedelta(minutes=20)))
                msg=EmailMessage();msg['Subject']='Đặt lại mật khẩu Freedom';msg['From']=settings.mail_from;msg['To']=user['email']
                msg.set_content(settings.frontend_reset_url+'?'+urlencode({'token':raw}))
                smtp.send_message(msg)
    except (OSError,smtplib.SMTPException):
        raise HTTPException(503,'Dịch vụ email tạm thời không khả dụng')
    return {'detail':'Nếu email hợp lệ, hướng dẫn đặt lại mật khẩu sẽ được gửi'}

@router.post('/reset-password')
def reset(body:s.Reset,db=Depends(session)):
    t=table('password_reset_tokens');now=datetime.now(timezone.utc)
    row=db.execute(select(t).where(t.c.token_hash==fingerprint(body.token))).mappings().first()
    if not row:raise HTTPException(400,'Liên kết hết hạn hoặc đã dùng')
    one(db,'users',row['user_id'],lock=True)
    row=db.execute(select(t).where(t.c.id==row['id']).with_for_update()).mappings().one()
    if row['used_at'] or row['expires_at']<=now:
        raise HTTPException(400,'Liên kết hết hạn hoặc đã dùng')
    u=table('users')
    db.execute(update(u).where(u.c.id==row['user_id']).values(password_hash=passwords.hash(body.new_password),updated_at=now))
    db.execute(update(t).where(t.c.user_id==row['user_id'],t.c.used_at.is_(None)).values(used_at=now))
    audit(db,row['user_id'],'reset_password','users',row['user_id'])
    return {'detail':'Đã đặt lại mật khẩu'}
