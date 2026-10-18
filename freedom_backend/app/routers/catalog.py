from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import select, update, delete, exists, and_, or_, func
from .. import catalog_schemas as s
from ..db import session, table, one, add, audit
from ..security import require
from ..media import save_product_image

router=APIRouter(tags=['Dũng • danh mục, sản phẩm, nội dung, voucher'])


def with_product_images(db, rows):
    products=[dict(row) for row in rows]
    if not products:return products
    images=table('product_images')
    grouped={p['id']:[] for p in products}
    for image in db.execute(select(images).where(images.c.product_id.in_(grouped)).order_by(images.c.is_primary.desc(),images.c.sort_order,images.c.id)).mappings():
        grouped[image['product_id']].append(dict(image))
    for product in products:product['product_images']=grouped[product['id']]
    return products

def category_tree(category, root_id=None, name='visible_categories'):
    anchor=category.c.parent_id.is_(None) if root_id is None else category.c.id==root_id
    tree=select(category.c.id).where(anchor,category.c.is_active.is_(True)).cte(name,recursive=True)
    return tree.union_all(select(category.c.id).join(tree,category.c.parent_id==tree.c.id).where(category.c.is_active.is_(True)))


def product_sizes(db,pid,active_only=False):
    v,sz,col=table('product_variants'),table('sizes'),table('colors')
    query=select(v,sz.c.name.label('size_name'),col.c.name.label('color_name')).join(sz,v.c.size_id==sz.c.id).join(col,v.c.color_id==col.c.id).where(v.c.product_id==pid)
    if active_only:query=query.where(v.c.is_active.is_(True))
    return db.execute(query.order_by(sz.c.sort_order,sz.c.id,col.c.id)).mappings().all()


def save_product_sizes(db,pid,entries,user):
    if entries is None:return
    sizes,colors,variants=table('sizes'),table('colors'),table('product_variants')
    # Same lock order as checkout: variants by ID. The product lock is held by caller.
    old={v['id']:dict(v) for v in db.execute(select(variants).where(variants.c.product_id==pid).order_by(variants.c.id).with_for_update()).mappings()}
    seen=set()
    for entry in entries:
        size_name=entry['size_name'].strip().upper();color_name=entry['color_name'].strip()
        pair=(size_name,color_name.casefold())
        if pair in seen:raise HTTPException(422,'Size và màu bị trùng trong sản phẩm')
        seen.add(pair)
        size=db.execute(select(sizes).where(or_(sizes.c.name==size_name,func.lower(sizes.c.name)==size_name.lower()))).mappings().first()
        if not size:size=add(db,'sizes',{'name':size_name,'sort_order':0})
        color=db.execute(select(colors).where(or_(colors.c.name==color_name,func.lower(colors.c.name)==color_name.lower()))).mappings().first()
        if not color:color=add(db,'colors',{'name':color_name})
        rid=entry.get('id')
        previous=old.get(rid) if rid else next((v for v in old.values() if v['size_id']==size['id'] and v['color_id']==color['id']),None)
        if rid and not previous:raise HTTPException(422,'Size không thuộc sản phẩm này')
        if previous:
            if previous['size_id']!=size['id'] or previous['color_id']!=color['id']:raise HTTPException(409,'Không đổi định danh size/màu cũ; ngừng bán dòng cũ rồi thêm dòng mới')
            if entry.get('expected_stock') is not None and entry['expected_stock']!=previous['stock_quantity']:raise HTTPException(409,'Tồn kho vừa thay đổi do bán hàng. Mở lại sản phẩm trước khi sửa')
            if entry['stock_quantity']<previous['reserved_quantity']:raise HTTPException(409,'Tồn kho không được thấp hơn số lượng đang giữ')
        values=dict(price=entry['price'],stock_quantity=entry['stock_quantity'],is_active=entry['is_active'])
        if previous:
            row=db.execute(update(variants).where(variants.c.id==previous['id']).values(**values).returning(variants)).mappings().one()
        else:
            row=add(db,'product_variants',dict(product_id=pid,size_id=size['id'],color_id=color['id'],sku='FR-'+uuid4().hex,**values))
        change=entry['stock_quantity']-(previous['stock_quantity'] if previous else 0)
        if change and user.get('role')!='admin':require('inventory.manage')(user,db)
        if change:add(db,'inventory_movements',dict(variant_id=row['id'],movement_type='adjustment' if previous else 'import',quantity_change=change,reference_type='product',reference_id=pid,note='Cập nhật size và tồn kho từ form sản phẩm',created_by=user['id']))
        audit(db,user['id'],'save_size','product_variants',row['id'])


@router.get('/catalog/products')
def products(q:str=Query('',max_length=200),category_id:int|None=None,brand_id:int|None=None,
             size_id:int|None=None,color_id:int|None=None,min_price:Decimal=Query(0,ge=0),max_price:Decimal|None=Query(None,ge=0),
             sort:str=Query('newest',pattern='^(newest|price_asc|price_desc)$'),
             limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),db=Depends(session)):
    p,v,c=table('products'),table('product_variants'),table('categories')
    visible=category_tree(c)
    query=select(p).where(p.c.status=='active',p.c.category_id.in_(select(visible.c.id)))
    if q:query=query.where(p.c.name.ilike('%'+q.replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    if category_id is not None:
        branch=category_tree(c,category_id,'selected_categories')
        query=query.where(p.c.category_id.in_(select(branch.c.id)))
    if brand_id:query=query.where(p.c.brand_id==brand_id)
    cond=[v.c.product_id==p.c.id,v.c.is_active.is_(True),v.c.price>=min_price]
    if max_price is not None:cond.append(v.c.price<=max_price)
    if size_id:cond.append(v.c.size_id==size_id)
    if color_id:cond.append(v.c.color_id==color_id)
    # Publication controls visibility. A new product can be displayed before its
    # size/color variants are configured; only explicit filters need a variant.
    if size_id or color_id:
        query=query.where(exists(select(v.c.id).where(*cond)))
    elif min_price>0 or max_price is not None:
        active_variant=exists(select(v.c.id).where(v.c.product_id==p.c.id,v.c.is_active.is_(True)))
        base_price=[p.c.base_price>=min_price]
        if max_price is not None:base_price.append(p.c.base_price<=max_price)
        query=query.where(or_(exists(select(v.c.id).where(*cond)),and_(~active_variant,*base_price)))
    order={'newest':p.c.id.desc(),'price_asc':p.c.base_price.asc(),'price_desc':p.c.base_price.desc()}[sort]
    return with_product_images(db,db.execute(query.order_by(order,p.c.id).limit(limit).offset(offset)).mappings().all())

@router.get('/catalog/products/{pid}')
def detail(pid:int,db=Depends(session)):
    row=one(db,'products',pid)
    if row['status']!='active':raise HTTPException(404,'Không tìm thấy sản phẩm')
    visible=category_tree(table('categories'))
    if db.scalar(select(visible.c.id).where(visible.c.id==row['category_id'])) is None:raise HTTPException(404,'Không tìm thấy sản phẩm')
    for name in ('product_variants','product_images'):
        t=table(name);q=select(t).where(t.c.product_id==pid)
        if name=='product_variants':q=q.where(t.c.is_active.is_(True))
        row[name]=db.execute(q.order_by(t.c.id)).mappings().all()
    row['product_variants']=product_sizes(db,pid,active_only=True)
    r=table('reviews');row['reviews']=db.execute(select(r).where(r.c.product_id==pid,r.c.status=='approved').order_by(r.c.id.desc()).limit(50)).mappings().all()
    ids=[x['id'] for x in row['reviews']];ri=table('review_images')
    row['review_images']=db.execute(select(ri).where(ri.c.review_id.in_(ids))).mappings().all() if ids else []
    return row

@router.get('/catalog/home')
def home(db=Depends(session)):
    now=datetime.now(timezone.utc);b,p=table('banners'),table('posts')
    return dict(banners=db.execute(select(b).where(b.c.is_active.is_(True),
        (b.c.starts_at.is_(None))|(b.c.starts_at<=now),(b.c.expires_at.is_(None))|(b.c.expires_at>now)).order_by(b.c.sort_order).limit(30)).mappings().all(),
        posts=db.execute(select(p).where(p.c.status=='published',p.c.published_at<=now).order_by(p.c.published_at.desc()).limit(10)).mappings().all())

@router.get('/catalog/lookups/{name}')
def lookup(name:str,db=Depends(session)):
    if name not in ('categories','brands','sizes','colors'):raise HTTPException(404,'Không tìm thấy')
    t=table(name);q=select(t)
    if name=='categories':
        visible=category_tree(t)
        return db.execute(q.where(t.c.id.in_(select(visible.c.id))).order_by(t.c.id)).mappings().all()
    if 'is_active' in t.c:q=q.where(t.c.is_active.is_(True))
    return db.execute(q.order_by(t.c.id).limit(500)).mappings().all()

@router.get('/staff/catalog/products/{rid}')
def staff_product_detail(rid:int,user=Depends(require('catalog.manage')),db=Depends(session)):
    # Management must also be able to read drafts and archived products.
    row=one(db,'products',rid)
    row['category']=one(db,'categories',row['category_id'])
    row['brand']=one(db,'brands',row['brand_id']) if row['brand_id'] else None
    for name in ('product_variants','product_images'):
        t=table(name)
        row[name]=db.execute(select(t).where(t.c.product_id==rid).order_by(t.c.id)).mappings().all()
    row['product_variants']=product_sizes(db,rid)
    return row


@router.post('/staff/catalog/products/{rid}/primary-image',status_code=201)
def upload_primary_image(rid:int,file:UploadFile,user=Depends(require('catalog.manage')),db=Depends(session)):
    # Lock the parent so concurrent uploads still leave exactly one primary image.
    product=one(db,'products',rid,lock=True)
    path,url=save_product_image(file)
    try:
        images=table('product_images')
        db.execute(update(images).where(images.c.product_id==rid).values(is_primary=False))
        row=add(db,'product_images',dict(product_id=rid,variant_id=None,image_url=url,alt_text=product['name'],sort_order=0,is_primary=True))
        audit(db,user['id'],'upload','product_images',row['id'])
        return row
    except Exception:
        path.unlink(missing_ok=True)
        raise


@router.post('/staff/catalog/products/{rid}/images',status_code=201)
def upload_product_images(rid:int,files:list[UploadFile],user=Depends(require('catalog.manage')),db=Depends(session)):
    if not 1<=len(files)<=8:raise HTTPException(422,'Chọn từ 1 đến 8 ảnh mỗi lần')
    product=one(db,'products',rid,lock=True)
    saved=[]
    try:
        # Validate the whole selection before changing DB image records.
        for file in files:saved.append(save_product_image(file))
        images=table('product_images')
        db.execute(update(images).where(images.c.product_id==rid).values(is_primary=False,sort_order=images.c.sort_order+len(saved)))
        rows=[]
        for index,(_,url) in enumerate(saved):
            row=add(db,'product_images',dict(product_id=rid,variant_id=None,image_url=url,alt_text=product['name'],sort_order=index,is_primary=index==0))
            audit(db,user['id'],'upload','product_images',row['id'])
            rows.append(row)
        return rows
    except Exception:
        for path,_ in saved:path.unlink(missing_ok=True)
        raise


def validate(db,name,values,rid=None):
    if name=='product_variants' and rid:
        old=one(db,name,rid)
        if any(values[k]!=old[k] for k in ('product_id','size_id','color_id','sku')):
            oi=table('order_items')
            if db.scalar(select(oi.c.id).where(oi.c.variant_id==rid).limit(1)):
                raise HTTPException(409,'SKU đã có đơn; tạo SKU mới thay vì đổi định danh')
    if name=='coupons':
        if values['starts_at'].tzinfo is None or values['expires_at'].tzinfo is None:raise HTTPException(422,'Voucher cần múi giờ')
        if values['expires_at']<=values['starts_at']:raise HTTPException(422,'Hạn dùng phải sau ngày bắt đầu')
        if values['discount_type']=='percent' and values['discount_value']>100:raise HTTPException(422,'Phần trăm tối đa 100')
    if name in ('banners','posts'):
        for col in ('starts_at','expires_at','published_at'):
            if values.get(col) is not None and values[col].tzinfo is None:raise HTTPException(422,'Thời gian cần múi giờ')
        if name=='banners' and values.get('starts_at') and values.get('expires_at') and values['starts_at']>=values['expires_at']:raise HTTPException(422,'Khoảng thời gian không hợp lệ')
    if name=='product_images' and values.get('variant_id'):
        if one(db,'product_variants',values['variant_id'])['product_id']!=values['product_id']:raise HTTPException(422,'Biến thể không thuộc sản phẩm')
    if name=='categories' and values.get('parent_id'):
        # Serialize category tree edits to prevent concurrent cycles.
        t=table('categories');db.execute(select(t.c.id).order_by(t.c.id).with_for_update()).all()
        seen={rid} if rid else set();parent=values['parent_id']
        while parent:
            if parent in seen:raise HTTPException(422,'Danh mục cha tạo vòng lặp')
            seen.add(parent);ancestor=one(db,'categories',parent)
            if not ancestor['is_active']:raise HTTPException(422,'Danh mục cha đã ngừng hoạt động')
            parent=ancestor['parent_id']

def mount(name,model,permission):
    def listing(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(require(permission)),db=Depends(session)):
        t=table(name);order=t.c.id.desc() if name=='products' else t.c.id
        rows=db.execute(select(t).order_by(order).limit(limit).offset(offset)).mappings().all()
        return with_product_images(db,rows) if name=='products' else rows
    def create(body:model,user=Depends(require(permission)),db=Depends(session)):
        values=body.model_dump();entries=values.pop('variants',None) if name=='products' else None
        validate(db,name,values)
        for k,v in list(values.items()):
            if hasattr(v,'unicode_string'):values[k]=str(v)
        if name=='products':values['created_by']=user['id']
        if name=='posts':values['author_id']=user['id']
        row=add(db,name,values)
        if name=='products':save_product_sizes(db,row['id'],entries,user)
        audit(db,user['id'],'create',name,row['id']);return row
    def replace(rid:int,body:model,user=Depends(require(permission)),db=Depends(session)):
        if name=='categories':
            t=table(name);db.execute(select(t.c.id).order_by(t.c.id).with_for_update()).all()
        one(db,name,rid,lock=True);values=body.model_dump();entries=values.pop('variants',None) if name=='products' else None
        validate(db,name,values,rid)
        for k,v in list(values.items()):
            if hasattr(v,'unicode_string'):values[k]=str(v)
        if name=='products':values['updated_at']=datetime.now(timezone.utc)
        t=table(name);row=db.execute(update(t).where(t.c.id==rid).values(**values).returning(t)).mappings().one()
        if name=='products':save_product_sizes(db,rid,entries,user)
        audit(db,user['id'],'update',name,rid);return row
    def remove(rid:int,user=Depends(require(permission)),db=Depends(session)):
        one(db,name,rid,lock=True);t=table(name)
        if 'is_active' in t.c:db.execute(update(t).where(t.c.id==rid).values(is_active=False))
        elif 'status' in t.c:
            values={'status':'archived'}
            if name=='products':values['updated_at']=datetime.now(timezone.utc)
            db.execute(update(t).where(t.c.id==rid).values(**values))
        elif name=='product_images':db.execute(delete(t).where(t.c.id==rid))
        else:raise HTTPException(409,'Bảng tra cứu được tham chiếu; không xóa qua API')
        audit(db,user['id'],'deactivate',name,rid)
    for method,path,fn in [('GET','',listing),('POST','',create),('PUT','/{rid}',replace),('DELETE','/{rid}',remove)]:
        router.add_api_route('/staff/catalog/'+name+path,fn,methods=[method],name=method+'_'+name,status_code=201 if method=='POST' else 204 if method=='DELETE' else 200)

for name in ['products','product_variants','product_images','categories','brands','sizes','colors','coupons','banners','posts']:
    mount(name,getattr(s,''.join(x.title() for x in name.split('_'))+'Input'),'coupons.manage' if name=='coupons' else 'content.manage' if name in ('banners','posts') else 'catalog.manage')
