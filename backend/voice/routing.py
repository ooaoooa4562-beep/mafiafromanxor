from django.urls import path
from .consumers import RoomVoiceSignalingConsumer

websocket_urlpatterns = [
    path("ws/rooms/<uuid:room_code>/voice/", RoomVoiceSignalingConsumer.as_asgi()),
]
