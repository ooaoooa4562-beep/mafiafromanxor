from django.contrib import admin
from django.urls import include, path

from . import frontend
from .realtime_views import (
    connection_token, subscription_token, send_room_message,
    voice_join, voice_leave, voice_signal,
)
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
    path('api/realtime/connection-token/', connection_token, name='realtime_connection_token'),
    path('api/realtime/subscription-token/', subscription_token, name='realtime_subscription_token'),
    path('api/realtime/rooms/<uuid:code>/messages/', send_room_message, name='realtime_room_message'),
    path('api/realtime/rooms/<uuid:code>/voice/join/', voice_join, name='realtime_voice_join'),
    path('api/realtime/rooms/<uuid:code>/voice/leave/', voice_leave, name='realtime_voice_leave'),
    path('api/realtime/rooms/<uuid:code>/voice/signal/', voice_signal, name='realtime_voice_signal'),
]
