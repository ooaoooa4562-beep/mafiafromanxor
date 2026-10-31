from django.urls import path
from .consumers import RoomChatConsumer

websocket_urlpatterns = [
    path("ws/rooms/<uuid:room_code>/chat/", RoomChatConsumer.as_asgi()),
]
