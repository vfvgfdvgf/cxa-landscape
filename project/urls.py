from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView

from core import views as core_views
from core.admin_site import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    path("api/v1/", include("core.api.urls")),
    path(
        "media/library-images/library-images/<path:path>",
        RedirectView.as_view(url="/media/library-images/%(path)s", permanent=True),
    ),
    path("", include("core.urls")),
]

handler404 = core_views.custom_404

if settings.DEBUG or settings.DJANGO_SERVE_MEDIA_FILES:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
