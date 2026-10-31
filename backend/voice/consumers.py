import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from game.models import Game, PlayerRole
from rooms.models import RoomPlayer


@database_sync_to_async
def voice_channel_for_user(room_code, user_id):
    member = RoomPlayer.objects.select_related("room").filter(room__code=room_code, user_id=user_id).first()
    if not member:
        return None
    room = member.room
    if room.status == "waiting":
        return "lobby"
    game = Game.objects.filter(room=room).first()
    if not game or game.phase == "finished":
        return "lobby"
    role = PlayerRole.objects.filter(game=game, player=member).first()
    if not role:
        return None
    if not role.is_alive:
        return "dead"
    if game.phase == "night":
        return "mafia" if role.role == "mafia" else None
    return "town"


class RoomVoiceSignalingConsumer(AsyncJsonWebsocketConsumer):
    """Role-aware WebRTC signaling. Audio itself travels peer-to-peer."""

    async def connect(self):
        self.user = self.scope.get("user")
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.voice_channel = await voice_channel_for_user(self.room_code, self.user.pk)
        if not self.voice_channel:
            await self.close(code=4403)
            return
        self.group_name = f"voice_{self.room_code.hex}_{self.voice_channel}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.joined_group = True
        await self.accept()
        await self.channel_layer.group_send(self.group_name, {
            "type": "voice.presence", "event": "peer_joined", "user_id": self.user.pk,
        })

    async def disconnect(self, close_code):
        if getattr(self, "joined_group", False):
            await self.channel_layer.group_send(self.group_name, {
                "type": "voice.presence", "event": "peer_left", "user_id": self.user.pk,
            })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if await voice_channel_for_user(self.room_code, self.user.pk) != self.voice_channel:
            await self.close(code=4409)
            return
        if not isinstance(content, dict):
            await self.close(code=4400)
            return
        message_type = content.get("type")
        target_user_id = content.get("target_user_id")
        payload = content.get("payload")
        if message_type not in ("offer", "answer", "candidate"):
            await self.send_json({"type": "error", "code": "invalid_signal_type"})
            return
        if type(target_user_id) is not int or target_user_id == self.user.pk:
            await self.send_json({"type": "error", "code": "invalid_target"})
            return
        if not isinstance(payload, dict) or len(json.dumps(payload)) > 48000:
            await self.send_json({"type": "error", "code": "invalid_payload"})
            return
        await self.channel_layer.group_send(self.group_name, {
            "type": "voice.signal", "signal_type": message_type,
            "sender_user_id": self.user.pk, "target_user_id": target_user_id,
            "payload": payload,
        })

    async def voice_signal(self, event):
        if event["target_user_id"] == self.user.pk:
            await self.send_json({"type": event["signal_type"], "sender_user_id": event["sender_user_id"], "payload": event["payload"]})

    async def voice_presence(self, event):
        if event["user_id"] != self.user.pk:
            await self.send_json({"type": event["event"], "user_id": event["user_id"]})

    async def voice_phase_changed(self, event):
        await self.send_json({"type": "phase_changed"})
        await self.close(code=4409)
