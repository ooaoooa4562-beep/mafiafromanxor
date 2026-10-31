from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from game.models import Game, PlayerRole
from .models import RoomPlayer


@database_sync_to_async
def chat_channel_for_user(room_code, user_id):
    member = RoomPlayer.objects.select_related("room", "user").filter(room__code=room_code, user_id=user_id).first()
    if not member:
        return None
    if member.room.status == "waiting":
        return ("lobby", member.user.nickname or member.user.username)
    game = Game.objects.filter(room=member.room).first()
    if not game or game.phase == "finished":
        return ("lobby", member.user.nickname or member.user.username)
    role = PlayerRole.objects.filter(game=game, player=member).first()
    if not role:
        return None
    if not role.is_alive:
        channel = "dead"
    elif game.phase == "night":
        channel = "mafia" if role.role == "mafia" else None
    else:
        channel = "town"
    return (channel, member.user.nickname or member.user.username) if channel else None


class RoomChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        access = await chat_channel_for_user(self.room_code, self.user.pk)
        if not access:
            await self.close(code=4403)
            return
        self.chat_channel, self.nickname = access
        self.group_name = f"chat_{self.room_code.hex}_{self.chat_channel}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        access = await chat_channel_for_user(self.room_code, self.user.pk)
        if not access or access[0] != self.chat_channel:
            await self.close(code=4409)
            return
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
        await self.send_json({"type": "message", "nickname": event["nickname"], "user_id": event["user_id"], "message": event["message"]})

    async def chat_phase_changed(self, event):
        await self.send_json({"type": "phase_changed"})
        await self.close(code=4409)
