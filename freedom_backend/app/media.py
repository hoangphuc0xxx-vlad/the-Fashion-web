"""Validated product uploads; file names never come from the client."""
from io import BytesIO
import re
from uuid import uuid4
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from .config import settings

router = APIRouter(tags=['Product media'])
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000


def save_product_image(file: UploadFile):
    if file.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
        raise HTTPException(422, 'Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP')
    raw = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(413, 'Ảnh tối đa 5 MB')
    try:
        with Image.open(BytesIO(raw), formats=['JPEG', 'PNG', 'WEBP']) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise HTTPException(422, 'Ảnh tối đa 24 triệu điểm ảnh')
            if getattr(source, 'is_animated', False):
                raise HTTPException(422, 'Vui lòng chọn ảnh tĩnh')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGBA' if 'A' in source.getbands() or 'transparency' in source.info else 'RGB')
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format='WEBP', quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, 'File không phải ảnh hợp lệ hoặc ảnh đã bị hỏng') from exc
    directory = settings.media_root / 'products'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (uuid4().hex + '.webp')
    try:
        path.write_bytes(output.getvalue())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path, '/media/products/' + path.name


@router.get('/media/products/{filename}')
def product_image(filename: str):
    if not re.fullmatch(r'[0-9a-f]{32}\.webp', filename):
        raise HTTPException(404, 'Không tìm thấy ảnh')
    path = settings.media_root / 'products' / filename
    if not path.is_file():
        raise HTTPException(404, 'Không tìm thấy ảnh')
    return FileResponse(path, media_type='image/webp')
