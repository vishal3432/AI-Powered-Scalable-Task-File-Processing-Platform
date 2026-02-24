"""
URL Configuration - Django Auth Engine
All routes prefixed with /auth/ via Nginx
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("apps.users.urls")),
    path("auth/files/", include("apps.files.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
