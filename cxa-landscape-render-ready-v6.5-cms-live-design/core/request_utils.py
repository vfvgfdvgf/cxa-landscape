"""Small request-security helpers with no third-party middleware dependency."""

import hashlib
import re
from functools import wraps
from urllib.parse import urlsplit

from django.core.cache import cache
from django.http import JsonResponse

PHONE_RE = re.compile(r"^[+0-9()\-\s]{6,20}$")


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def request_fingerprint(request, scope="request"):
    raw = "|".join(
        [
            scope,
            client_ip(request),
            request.META.get("HTTP_USER_AGENT", "")[:220],
        ]
    )
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


def rate_limit(scope, limit=10, window=60):
    """Process-local cache-backed fixed-window limiter."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            bucket = int(__import__("time").time() // window)
            key = f"ratelimit:{scope}:{request_fingerprint(request, scope)}:{bucket}"
            added = cache.add(key, 1, timeout=window + 2)
            if not added:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window + 2)
                    count = 1
                if count > limit:
                    response = JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
                    response["Retry-After"] = str(window)
                    return response
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def valid_phone(value):
    value = (value or "").strip()
    if not PHONE_RE.fullmatch(value):
        return False
    digits = "".join(character for character in value if character.isdigit())
    return 8 <= len(digits) <= 15


def safe_page_url(value, allowed_hosts=()):
    value = (value or "").strip()[:1000]
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc and allowed_hosts and parsed.hostname not in set(allowed_hosts):
        return ""
    return value
