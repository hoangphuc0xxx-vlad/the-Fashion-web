import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from .config import settings
from .db import session
from .routers import auth, people, catalog, commerce, community
from . import media

app=FastAPI(title='Freedom – Backend thời trang nam',version='1.0.0',
    description='Phúc: auth/people; Dũng: catalog; Tuấn Anh: commerce; Khánh: community. Xem docs/PHAN_TICH.md về giới hạn.')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_credentials=False,
                   allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])
# Per-process guard for development; use a shared limiter at the reverse proxy in production.
_attempts=defaultdict(deque);_lock=Lock()
@app.middleware('http')
async def protect_auth(request:Request,call_next):
    if request.method=='POST' and request.url.path.startswith('/staff/catalog/products/') and request.url.path.endswith(('/primary-image','/images')):
        length=request.headers.get('content-length','')
        limit=42 if request.url.path.endswith('/images') else 6
        if length.isdecimal() and int(length)>limit*1024*1024:
            return JSONResponse(status_code=413,content={'detail':'Chọn tối đa 8 ảnh, mỗi ảnh tối đa 5 MB'})
    if request.method=='POST' and request.url.path in ('/auth/token','/auth/register','/auth/forgot-password','/auth/reset-password'):
        key=(request.client.host if request.client else 'unknown',request.url.path);now=monotonic()
        with _lock:
            for stale in [k for k,v in _attempts.items() if not v or v[-1]<now-60]:_attempts.pop(stale,None)
            queue=_attempts[key]
            while queue and queue[0]<now-60:queue.popleft()
            if len(queue)>=10:return JSONResponse(status_code=429,content={'detail':'Thử lại sau 60 giây'},headers={'Retry-After':'60'})
            queue.append(now)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(IntegrityError)
async def conflict(request,exc):
    return JSONResponse(status_code=409,content={'detail':'Trùng dữ liệu hoặc vi phạm liên kết database'})
@app.exception_handler(DataError)
async def invalid(request,exc):
    return JSONResponse(status_code=422,content={'detail':'Giá trị không hợp lệ cho schema database'})
@app.exception_handler(OperationalError)
async def unavailable(request,exc):
    logging.getLogger('freedom').error('Database operation unavailable (%s)',type(exc).__name__)
    return JSONResponse(status_code=503,content={'detail':'Database tạm thời không khả dụng'})

@app.get('/health',tags=['System'])
def health():return {'status':'ok'}
@app.get('/ready',tags=['System'])
def ready(db=Depends(session)):
    db.execute(text('SELECT 1'));return {'database':'ok'}

for router in (auth.router,people.router,catalog.router,commerce.router,community.router):app.include_router(router)
app.include_router(media.router)
