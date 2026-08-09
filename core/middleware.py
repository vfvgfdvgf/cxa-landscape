import re
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect


def is_safe_local_redirect(target):
    return bool(target and target.startswith("/") and not target.startswith("//") and "://" not in target)


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdMiddleware:
    """Attach a traceable request ID while rejecting unbounded client values."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "").strip()
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else uuid4().hex
        request.request_id = request_id
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware:
    """Add a conservative CSP and modern browser security headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        backend_host = request.get_host().split(":", 1)[0].lower()
        if (
            request.path.startswith(("/api/", "/admin/"))
            or backend_host == "nakheel-najd.onrender.com"
            or backend_host == getattr(settings, "RENDER_EXTERNAL_HOSTNAME", "").lower()
        ):
            response.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        # Public media is embedded by the separately hosted Next.js frontend.
        # Static project imagery also lives under /static/, so it must not be
        # restricted to the onrender.com site by CORP.
        if request.path.startswith(("/static/", "/media/", "/media-db/")):
            response.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        else:
            response.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "base-uri 'self'",
                    "form-action 'self' https://wa.me https://api.whatsapp.com",
                    "frame-ancestors 'none'",
                    "object-src 'none'",
                    "img-src 'self' data: blob: https:",
                    "font-src 'self' data:",
                    "style-src 'self' 'unsafe-inline'",
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                    "connect-src 'self' https:",
                    "upgrade-insecure-requests" if not settings.DEBUG else "block-all-mixed-content",
                ]
            ),
        )
        return response


class LegacyRedirectMiddleware:
    HEALTH_PATHS = frozenset({"/health/", "/ready/", "/api/v1/health/", "/api/v1/ready/"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Operational probes must never depend on redirect lookup or its cache.
        if request.path_info in self.HEALTH_PATHS:
            return self.get_response(request)

        from .models import LegacyRedirect

        path = request.path
        normalized = path.rstrip("/") or "/"
        candidates = {path, normalized, f"{normalized}/"}
        cache_key = f"legacy_redirect:{path}"
        try:
            cached_redirect = cache.get(cache_key)
        except Exception:
            cached_redirect = None

        if cached_redirect is None:
            try:
                redirect = (
                    LegacyRedirect.objects.filter(is_active=True, old_path__in=candidates)
                    .order_by("-is_permanent", "-updated_at")
                    .only("target_path", "is_permanent")
                    .first()
                )
                cached_redirect = (redirect.target_path, redirect.is_permanent) if redirect else False
            except (OperationalError, ProgrammingError):
                cached_redirect = False
            try:
                cache.set(cache_key, cached_redirect, 300)
            except Exception:
                # Redirect lookup remains correct without the optional cache.
                pass

        if cached_redirect:
            target_path, is_permanent = cached_redirect
            if is_safe_local_redirect(target_path) and target_path != path:
                response_class = HttpResponsePermanentRedirect if is_permanent else HttpResponseRedirect
                return response_class(target_path)
        return self.get_response(request)
