from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from PIL import Image

register = template.Library()
RESPONSIVE_WIDTHS = (480, 768, 1200)


def _local_path(url):
    if not url or "://" in url or url.startswith("data:"):
        return None
    if url.startswith(settings.MEDIA_URL):
        return settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):].lstrip("/")
    if url.startswith(settings.STATIC_URL):
        relative = url[len(settings.STATIC_URL):].lstrip("/")
        found = finders.find(relative)
        return Path(found) if found else None
    return None


@lru_cache(maxsize=1024)
def _dimensions(url):
    path = _local_path(url)
    if not path or not path.exists():
        return None
    try:
        with Image.open(path) as image:
            return image.width, image.height
    except Exception:
        return None


def _responsive_url(url, width):
    path = Path(url)
    return str(path.with_name(f"{path.stem}-w{width}.webp")).replace("\\", "/")


@register.simple_tag
def image_srcset(url):
    """Return only real, distinct responsive files generated for local images."""
    candidates = []
    for width in RESPONSIVE_WIDTHS:
        candidate = _responsive_url(url, width)
        dimensions = _dimensions(candidate)
        if dimensions and dimensions[0] == width:
            candidates.append(f"{candidate} {width}w")
    return ", ".join(candidates) if len(candidates) >= 2 else ""


@register.simple_tag
def image_dimensions(url):
    dimensions = _dimensions(url)
    if not dimensions:
        return ""
    return f'width="{dimensions[0]}" height="{dimensions[1]}"'
