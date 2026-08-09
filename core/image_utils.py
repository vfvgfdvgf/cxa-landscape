from io import BytesIO
from pathlib import Path, PurePosixPath
import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 40_000_000
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

RESPONSIVE_VARIANT_RE = re.compile(r"-w(?:320|480|768|1200)\.(?:webp|avif)$", re.IGNORECASE)


def is_responsive_variant_name(name):
    return bool(RESPONSIVE_VARIANT_RE.search(PurePosixPath(str(name or "")).name))


def _target_name(original_name, extension):
    original = PurePosixPath(str(original_name or "image").replace("\\", "/"))
    parent = "" if str(original.parent) == "." else str(original.parent)
    filename = f"{original.stem or 'image'}.{extension}"
    return f"{parent}/{filename}" if parent else filename


def optimize_uploaded_image(image_field, quality=82, max_size=(1600, 1600)):
    """Optimize an uncommitted upload without writing a second copy to storage.

    Transparency is preserved as PNG, animated GIFs are kept intact, EXIF orientation
    is applied, and decompression-bomb sized inputs are rejected.
    """
    if (
        not image_field
        or getattr(image_field, "_cxa_optimized", False)
        or getattr(image_field, "_committed", False)
    ):
        return

    upload = getattr(image_field, "file", image_field)
    size = getattr(upload, "size", 0) or 0
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError("حجم الصورة أكبر من الحد المسموح (15 ميجابايت).")

    try:
        upload.seek(0)
        image = Image.open(upload)
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValidationError("أبعاد الصورة كبيرة جدًا. الحد الأقصى 40 مليون بكسل.")
        if getattr(image, "is_animated", False):
            upload.seek(0)
            return
        image = ImageOps.exif_transpose(image)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    except ValidationError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("ملف الصورة غير صالح أو تالف.") from exc

    has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
    if has_alpha:
        if image.mode not in {"RGBA", "LA"}:
            image = image.convert("RGBA")
        extension, image_format = "png", "PNG"
        save_kwargs = {"optimize": True, "compress_level": 8}
    else:
        if image.mode != "RGB":
            image = image.convert("RGB")
        extension, image_format = "jpg", "JPEG"
        save_kwargs = {"quality": quality, "optimize": True, "progressive": True}

    buffer = BytesIO()
    image.save(buffer, format=image_format, **save_kwargs)
    new_name = _target_name(getattr(image_field, "name", "image"), extension)
    image_field.name = new_name
    image_field.file = ContentFile(buffer.getvalue(), name=Path(new_name).name)
    image_field._committed = False
    image_field._cxa_optimized = True
