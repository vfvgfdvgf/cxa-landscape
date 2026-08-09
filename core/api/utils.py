import logging
from functools import lru_cache
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework.views import exception_handler
from PIL import Image

from core.text_utils import fix_arabic_text


PUBLIC_SITE_URL = "https://getsiaq.online"
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1024)
def _static_image_info(relative_path):
    relative = str(relative_path or "").replace("\\", "/").lstrip("/")
    if not relative or ".." in Path(relative).parts:
        return None
    candidates = (settings.BASE_DIR / "imge" / relative, settings.BASE_DIR / "static" / relative)
    for candidate in candidates:
        try:
            if candidate.is_file():
                with Image.open(candidate) as opened:
                    return candidate, opened.width, opened.height
        except (OSError, ValueError):
            continue
    return None


def _responsive_variants(request, url):
    parsed = urlsplit(url)
    static_prefix = settings.STATIC_URL.rstrip("/") + "/"
    if not parsed.path.startswith(static_prefix):
        return []
    relative = parsed.path[len(static_prefix):]
    source = _static_image_info(relative)
    if not source:
        return []
    source_path, _width, _height = source
    # Variant filenames are produced by generate_responsive_images and encode
    # their target width in the filename. Existence checks are enough here;
    # reopening every WebP/AVIF during API serialization made image-heavy pages
    # pay dozens of unnecessary decoder/filesystem operations.
    variants = []
    for width in (320, 480, 768, 1200):
        webp = source_path.with_name(f"{source_path.stem}-w{width}.webp")
        avif = source_path.with_name(f"{source_path.stem}-w{width}.avif")
        webp_exists = webp.is_file()
        avif_exists = avif.is_file()
        if not webp_exists and not avif_exists:
            continue
        variant = {"width": width}
        if webp_exists:
            candidate_relative = Path(relative).with_name(webp.name).as_posix()
            variant["url"] = absolute_media_url(request, f"{settings.STATIC_URL}{candidate_relative}")
        if avif_exists:
            candidate_relative = Path(relative).with_name(avif.name).as_posix()
            variant["avif_url"] = absolute_media_url(request, f"{settings.STATIC_URL}{candidate_relative}")
        if not variant.get("url"):
            variant["url"] = variant["avif_url"]
        variants.append(variant)
    return variants


def _cloudinary_variant_url(url, width, image_format):
    """Build a delivery-only Cloudinary transformation URL without API calls."""
    parsed = urlsplit(str(url or ""))
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com" or "/image/upload/" not in parsed.path:
        return ""
    prefix, remainder = parsed.path.split("/image/upload/", 1)
    fmt = "avif" if image_format == "avif" else "webp"
    transform = f"f_{fmt},q_auto:eco,c_limit,w_{int(width)}"
    path = f"{prefix}/image/upload/{transform}/{remainder}"
    return parsed._replace(path=path).geturl()


def _cloudinary_variants(url):
    variants = []
    for width in (320, 480, 768, 1200):
        webp = _cloudinary_variant_url(url, width, "webp")
        avif = _cloudinary_variant_url(url, width, "avif")
        if webp:
            variants.append({"width": width, "url": webp, "avif_url": avif})
    return variants


def public_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    if response.status_code >= 500:
        logger.error("Unhandled public API error", exc_info=exc)
        response.data = {"detail": "الخدمة غير متاحة مؤقتًا. يرجى المحاولة بعد قليل."}
    return response


def clean_text(value):
    return fix_arabic_text(value or "")


def clean_meta_text(value):
    return " ".join(unescape(strip_tags(clean_text(value))).split())


def canonical_path(path):
    parsed = urlsplit(path or "/")
    normalized = parsed.path or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/" and not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def absolute_media_url(request, value):
    if not value:
        return ""
    if hasattr(value, "url"):
        try:
            value = value.url
        except (ValueError, OSError):
            return ""
    value = str(value)
    if value.startswith("http://"):
        return f"https://{value[7:]}"
    if value.startswith("https://"):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if not value.startswith("/"):
        value = f"/{value}"
    render_hostname = getattr(settings, "RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_hostname:
        return f"https://{render_hostname}{value}"
    public_base = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    if public_base:
        return f"{public_base}{value}"
    return request.build_absolute_uri(value) if request else value


def image_payload(request, value, alt=""):
    url = absolute_media_url(request, value)
    if not url:
        return None
    payload = {"url": url, "alt": clean_text(alt), "width": None, "height": None, "variants": []}
    if hasattr(value, "width"):
        try:
            payload["width"] = value.width
            payload["height"] = value.height
        except (AttributeError, FileNotFoundError, OSError, ValueError):
            pass
    parsed = urlsplit(url)
    static_prefix = settings.STATIC_URL.rstrip("/") + "/"
    if parsed.path.startswith(static_prefix):
        relative = parsed.path[len(static_prefix):]
        info = _static_image_info(relative)
        if info and payload["width"] is None:
            _path, payload["width"], payload["height"] = info
        payload["variants"] = _responsive_variants(request, url)
    elif parsed.netloc == "res.cloudinary.com":
        payload["variants"] = _cloudinary_variants(url)
    return payload


def seo_payload(
    obj=None,
    *,
    path="/",
    title="",
    description="",
    image="",
    og_type="website",
    schema=None,
    request=None,
    published_time=None,
    modified_time=None,
    robots="index, follow, max-image-preview:large",
):
    meta_title = clean_text(getattr(obj, "meta_title", "")) if obj else ""
    meta_description = clean_text(getattr(obj, "meta_description", "")) if obj else ""
    keywords = clean_text(getattr(obj, "meta_keywords", "")) if obj else ""
    updated = modified_time or getattr(obj, "updated_at", None)
    created = published_time or getattr(obj, "publish_at", None) or getattr(obj, "created_at", None)
    image_url = absolute_media_url(request, image)
    return {
        "title": clean_meta_text(meta_title or title),
        "description": clean_meta_text(meta_description or description),
        "keywords": clean_meta_text(keywords),
        "robots": robots,
        "canonical_path": canonical_path(path),
        "image": image_url,
        "og_type": og_type,
        "published_time": created.isoformat() if created else "",
        "modified_time": updated.isoformat() if updated else "",
        "schema": schema or {},
    }


def published_blog_filter():
    from django.db.models import Q

    return Q(status="published") & (Q(publish_at__lte=timezone.now()) | Q(publish_at__isnull=True))


def public_site_url():
    return getattr(settings, "FRONTEND_URL", PUBLIC_SITE_URL).rstrip("/") or PUBLIC_SITE_URL
