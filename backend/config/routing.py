from django.urls import re_path

from rooms.consumers import RoomConsumer

websocket_urlpatterns = [
    re_path(r'^ws/rooms/(?P<code>[0-9a-fA-F-]{36})/$', RoomConsumer.as_asgi()),
]
