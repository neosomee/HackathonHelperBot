from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("miniapp/", TemplateView.as_view(template_name="index.html"), name="miniapp"),
    path(
        "miniapp/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "mini_app"},
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/", include("hackathon.urls")),
]
