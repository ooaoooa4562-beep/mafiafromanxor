from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/rooms/", include("rooms.urls")),
    path("api/game/", include("game.urls")),
]
