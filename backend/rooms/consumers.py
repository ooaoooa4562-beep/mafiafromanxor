from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .models import RoomPlayer


@database_sync_to_async
def is_room_member(room_code, user_id):
    return RoomPlayer.objects.filter(room__code=room_code, user_id=user_id, room__status__in=("waiting", "playing")).select_related("user").first()


class RoomChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.group_name = f"chat_{self.room_code.hex}"
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.membership = await is_room_member(self.room_code, self.user.pk)
        if not self.membership:
            await self.close(code=4403)
            return
        self.nickname = self.membership.user.nickname or self.membership.user.username
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if getattr(self, "membership", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        message = content.get("message", "") if isinstance(content, dict) else ""
        if not isinstance(message, str):
            await self.send_json({"type": "error", "detail": "Некорректное сообщение."})
            return
        message = message.strip()
        if not message:
            return
        if len(message) > 500:
            await self.send_json({"type": "error", "detail": "Сообщение слишком длинное (максимум 500 символов)."})
            return
        await self.channel_layer.group_send(self.group_name, {
            "type": "chat.message", "nickname": self.nickname,
            "user_id": self.user.pk, "message": message,
        })

    async def chat_message(self, event):
        await self.send_json({
            "type": "message", "nickname": event["nickname"],
            "user_id": event["user_id"], "message": event["message"],
        })
