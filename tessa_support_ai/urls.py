from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("dashboard.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("tickets.api_urls")),
    path("tickets/", include("tickets.urls")),
]
