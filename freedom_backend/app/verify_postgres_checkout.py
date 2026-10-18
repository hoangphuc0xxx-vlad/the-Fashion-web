"""Clone schema only into a new disposable DB, run checkout tests, clean it up."""
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
from sqlalchemy import create_engine,MetaData,text
from .db import engine


def main():
    source=engine.url
    target_name='freedom_checkout_'+uuid4().hex[:12]+'_test'
    if not re.fullmatch(r'freedom_checkout_[0-9a-f]{12}_test',target_name) or target_name==source.database:raise RuntimeError('Unsafe test database')
    admin=create_engine(source.set(database='postgres'),isolation_level='AUTOCOMMIT')
    created=False;test_engine=None
    try:
        with admin.connect() as db:db.exec_driver_sql('CREATE DATABASE "'+target_name+'"')
        created=True
        metadata=MetaData();metadata.reflect(bind=engine)
        test_engine=create_engine(source.set(database=target_name))
        metadata.create_all(test_engine)
        migration=Path(__file__).resolve().parents[1]/'database/migrations/002_checkout_pickup.sql'
        with test_engine.begin() as db:db.exec_driver_sql(migration.read_text(encoding='utf-8'),execution_options={'no_parameters':True})
        env={**os.environ,'DATABASE_URL':source.set(database=target_name).render_as_string(hide_password=False),'RUN_PG_TESTS':'1','JWT_SECRET':'checkout-test-'+uuid4().hex*2}
        print('Running isolated PostgreSQL checkout tests against schema-only clone.',flush=True)
        result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_postgres_checkout.py'],env=env,cwd=Path(__file__).resolve().parents[1])
        return result.returncode
    finally:
        if test_engine:test_engine.dispose()
        if created:
            with admin.connect() as db:
                db.execute(text('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()'),{'name':target_name})
                db.exec_driver_sql('DROP DATABASE "'+target_name+'"')
            print('Removed the disposable checkout test database.',flush=True)
        admin.dispose()


if __name__=='__main__':sys.exit(main())
