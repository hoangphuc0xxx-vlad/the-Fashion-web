"""Apply explicit, transactional additive migrations to an existing store."""
from pathlib import Path
from sqlalchemy import text
from .db import engine


def main():
    migration = Path(__file__).resolve().parents[1] / 'database/migrations/002_checkout_pickup.sql'
    with engine.begin() as db:
        db.execute(text("SET LOCAL lock_timeout = '5s'"))
        db.execute(text('SELECT pg_advisory_xact_lock(20261018)'))
        db.exec_driver_sql(migration.read_text(encoding='utf-8'), execution_options={'no_parameters': True})
    print('Applied 002_checkout_pickup: existing data preserved.')


if __name__ == '__main__':
    main()
