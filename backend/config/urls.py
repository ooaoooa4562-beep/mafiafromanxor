from django.contrib import admin
from django.urls import include, path

from . import frontend

urlpatterns = [
    path('', frontend.lobby, name='lobby'),
    path('play/', frontend.play, name='play'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/rooms/', include('rooms.urls')),
    path('api/game/', include('game.urls')),
    path('api/friends/', include('friends.urls')),
]
