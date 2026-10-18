"""Create the three requested store roots without moving existing categories."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .db import engine, table

MAIN_CATEGORIES=(('Áo','ao'),('Quần','quan'),('Suit','suit'))


def main():
    c=table('categories')
    with Session(engine) as db,db.begin():
        for name,slug in MAIN_CATEGORIES:
            db.execute(insert(c).values(name=name,slug=slug,parent_id=None,is_active=True).on_conflict_do_nothing(index_elements=['slug']))
            row=db.execute(select(c).where(c.c.slug==slug)).mappings().one()
            if row['parent_id'] is not None or not row['is_active']:
                raise SystemExit(f'Category {slug} already exists as a child or inactive category; no changes committed.')
    print('Store roots ready: ao, quan, suit. Existing categories were preserved.')


if __name__=='__main__':main()
