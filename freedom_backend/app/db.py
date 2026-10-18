from functools import lru_cache
from threading import RLock
from sqlalchemy import MetaData, Table, create_engine, insert, select
from sqlalchemy.orm import Session
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
metadata = MetaData()
_reflect_lock = RLock()

@lru_cache
def table(name: str) -> Table:
    # Reflection reads the supplied schema; no create_all, ALTER or migration at startup.
    with _reflect_lock:
        if name in metadata.tables:
            return metadata.tables[name]
        return Table(name, metadata, autoload_with=engine)

def session():
    with Session(engine) as db:
        with db.begin():
            yield db

def one(db, name, row_id, lock=False):
    from fastapi import HTTPException
    t = table(name)
    query = select(t).where(t.c.id == row_id)
    if lock:
        query = query.with_for_update()
    row = db.execute(query).mappings().first()
    if row is None:
        raise HTTPException(404, 'Không tìm thấy dữ liệu')
    return dict(row)

def add(db, name, values):
    t = table(name)
    return dict(db.execute(insert(t).values(**values).returning(t)).mappings().one())

def audit(db, user_id, action, entity, entity_id=None, details=None):
    add(db, 'audit_logs', dict(user_id=user_id, action=action, entity_type=entity,
                             entity_id=entity_id, details=details))
