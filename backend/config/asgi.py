"""ASGI entry point for HTTP and authenticated room WebSockets."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from rooms.routing import websocket_urlpatterns as room_websocket_urls
from voice.routing import websocket_urlpatterns as voice_websocket_urls

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(room_websocket_urls + voice_websocket_urls))
    ),
})
