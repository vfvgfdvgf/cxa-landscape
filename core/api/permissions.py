from hmac import compare_digest

from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


class PublicReadOnlyPermission(BasePermission):
    """Allow reads and let unsupported writes reach DRF's correct 405 response.

    Any view that actually implements a write method is denied unless it replaces
    this permission explicitly (the submission views use HasFrontendSecret).
    """

    message = "الكتابة غير متاحة على هذا المسار."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        handler = getattr(view, request.method.lower(), None)
        return not callable(handler)


class HasFrontendSecret(BasePermission):
    message = "تعذر التحقق من مصدر الطلب."

    def has_permission(self, request, view):
        configured = settings.FRONTEND_API_SECRET
        supplied = request.headers.get("X-Frontend-Secret", "")
        return bool(configured and supplied and compare_digest(configured, supplied))
