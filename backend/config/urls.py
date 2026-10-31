from django.contrib import admin
from django.urls import include, path

from . import frontend
from voice.views import ice_servers

urlpatterns = [
    path('', frontend.lobby, name='lobby'),
    path('play/', frontend.play, name='play'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/rooms/', include('rooms.urls')),
    path('api/game/', include('game.urls')),
    path('api/friends/', include('friends.urls')),
    path('api/voice/ice-servers/', ice_servers, name='voice_ice_servers'),
]
