"""Upload real image bytes into an isolated DB and temporary media directory."""
from io import BytesIO
import pytest
from PIL import Image
from sqlalchemy import insert
from app import media, security
from app.config import settings
from app.main import app
from test_product_crud import product_db, payload


def image_bytes(fmt='PNG', size=(40, 60)):
    output=BytesIO()
    Image.new('RGB',size,'navy').save(output,format=fmt)
    return output.getvalue()


@pytest.fixture
def image_product(client,product_db,tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'media_root',tmp_path)
    result=client.post('/staff/catalog/products',json=payload(status='active'))
    assert result.status_code==201,result.text
    pid=result.json()['id']
    engine,t,_=product_db
    with engine.begin() as db:db.execute(insert(t['product_variants']),{'product_id':pid,'sku':'IMAGE-M','price':549000})
    return pid,tmp_path


@pytest.mark.parametrize('fmt,mime',[('JPEG','image/jpeg'),('PNG','image/png'),('WEBP','image/webp')])
def test_upload_preview_public_listing_and_replace(client,product_db,image_product,fmt,mime):
    pid,directory=image_product
    path=f'/staff/catalog/products/{pid}/primary-image'
    upload=client.post(path,files={'file':('../../unsafe.html',image_bytes(fmt),mime)})
    assert upload.status_code==201,upload.text
    first=upload.json()
    assert first['is_primary'] is True and first['alt_text']=='Sơ mi Linen'
    assert first['image_url'].startswith('/media/products/')
    assert first['image_url'].endswith('.webp')
    # Images are public, independently of the authentication used for uploads.
    public=client.get(first['image_url'])
    assert public.status_code==200 and public.headers['content-type']=='image/webp'
    with Image.open(BytesIO(public.content)) as image:
        assert image.format=='WEBP' and image.size==(40,60)
    replaced=client.post(path,files={'file':('new.png',image_bytes(), 'image/png')})
    assert replaced.status_code==201
    for endpoint in ('/catalog/products','/staff/catalog/products',f'/staff/catalog/products/{pid}',f'/catalog/products/{pid}'):
        data=client.get(endpoint).json()
        product=data[0] if isinstance(data,list) else data
        images=product['product_images']
        assert sum(bool(i['is_primary']) for i in images)==1
        assert next(i for i in images if i['is_primary'])['id']==replaced.json()['id']
    assert len(list(directory.rglob('*.webp')))==2


def test_invalid_upload_does_not_replace_existing_image(client,product_db,image_product,monkeypatch):
    pid,directory=image_product
    path=f'/staff/catalog/products/{pid}/primary-image'
    good=client.post(path,files={'file':('ok.png',image_bytes(),'image/png')}).json()
    for name,data,mime,status in [
        ('bad.svg',b'<svg/>','image/svg+xml',422),
        ('fake.jpg',b'<script>alert(1)</script>','image/jpeg',422),
        ('empty.png',b'','image/png',422),
        ('large.png',b'x'*(5*1024*1024+1),'image/png',413),
    ]:
        assert client.post(path,files={'file':(name,data,mime)}).status_code==status
    monkeypatch.setattr(media,'MAX_IMAGE_PIXELS',100)
    assert client.post(path,files={'file':('pixels.png',image_bytes(),'image/png')}).status_code==422
    detail=client.get(f'/staff/catalog/products/{pid}').json()
    assert len(detail['product_images'])==1 and detail['product_images'][0]['id']==good['id']
    assert len(list(directory.rglob('*.webp')))==1
    assert client.get('/media/products/not-a-file.webp').status_code==404


@pytest.mark.parametrize('role',['customer','staff','guest'])
def test_upload_requires_catalog_permission(client,product_db,image_product,role):
    pid,directory=image_product
    if role=='guest':app.dependency_overrides.pop(security.current)
    else:product_db[2].update(role=role,role_id=2)
    assert client.post(f'/staff/catalog/products/{pid}/primary-image',files={'file':('ok.png',image_bytes(),'image/png')}).status_code==(401 if role=='guest' else 403)
    assert list(directory.rglob('*.webp'))==[]


def test_authorized_staff_can_upload_and_unknown_product_creates_no_file(client,product_db,image_product):
    pid,directory=image_product
    engine,t,user=product_db
    user.update(role='staff',role_id=2)
    with engine.begin() as db:db.execute(insert(t['role_permissions']),{'role_id':2,'permission_id':1})
    assert client.post('/staff/catalog/products/99999/primary-image',files={'file':('ok.png',image_bytes(),'image/png')}).status_code==404
    assert list(directory.rglob('*.webp'))==[]
    assert client.post(f'/staff/catalog/products/{pid}/primary-image',files={'file':('ok.png',image_bytes(),'image/png')}).status_code==201


def test_upload_multiple_images_and_invalid_batch_rolls_back(client,product_db,image_product):
    pid,directory=image_product
    path=f'/staff/catalog/products/{pid}/images'
    files=[('files',(f'{i}.png',image_bytes(),'image/png')) for i in range(3)]
    result=client.post(path,files=files)
    assert result.status_code==201,result.text
    rows=result.json()
    assert len(rows)==3 and [row['sort_order'] for row in rows]==[0,1,2]
    assert [row['is_primary'] for row in rows]==[True,False,False]
    assert len({row['image_url'] for row in rows})==3
    assert len(client.get('/catalog/products').json()[0]['product_images'])==3
    for row in rows:assert client.get(row['image_url']).status_code==200
    broken=client.post(path,files=[files[0],('files',('fake.jpg',b'not an image','image/jpeg'))])
    assert broken.status_code==422
    assert len(list(directory.rglob('*.webp')))==3
    detail=client.get(f'/staff/catalog/products/{pid}').json()
    assert len(detail['product_images'])==3
    assert next(i for i in detail['product_images'] if i['is_primary'])['id']==rows[0]['id']
    assert client.post(path,files=files*3).status_code==422
    assert len(list(directory.rglob('*.webp')))==3
    added=client.post(path,files=files[:2])
    assert added.status_code==201
    all_images=client.get('/catalog/products').json()[0]['product_images']
    assert [image['id'] for image in all_images[:2]]==[image['id'] for image in added.json()]
    assert len(all_images)==5 and sum(bool(image['is_primary']) for image in all_images)==1


@pytest.mark.parametrize('role',['customer','staff','guest'])
def test_multiple_upload_requires_permission(client,product_db,image_product,role):
    pid,directory=image_product
    if role=='guest':app.dependency_overrides.pop(security.current)
    else:product_db[2].update(role=role,role_id=2)
    assert client.post(f'/staff/catalog/products/{pid}/images',files=[('files',('ok.png',image_bytes(),'image/png'))]).status_code==(401 if role=='guest' else 403)
    assert list(directory.rglob('*.webp'))==[]
