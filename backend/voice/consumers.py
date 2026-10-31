import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from rooms.models import Room


@database_sync_to_async
def room_is_available(room_code):
    return Room.objects.filter(code=room_code).exclude(status="finished").exists()


class RoomVoiceSignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    Authenticated WebRTC signaling relay.

    Audio never passes through this consumer: browsers exchange audio peer-to-peer
    using WebRTC. This socket only forwards SDP/ICE signaling messages.
    """

    async def connect(self):
        self.user = self.scope.get("user")
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.group_name = f"voice_{self.room_code.hex}"

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        if not await room_is_available(self.room_code):
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(self.group_name, {
            "type": "voice.presence",
            "event": "peer_joined",
            "user_id": self.user.pk,
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and getattr(self, "user", None) and self.user.is_authenticated:
            await self.channel_layer.group_send(self.group_name, {
                "type": "voice.presence",
                "event": "peer_left",
                "user_id": self.user.pk,
            })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.close(code=4400)
            return

        message_type = content.get("type")
        target_user_id = content.get("target_user_id")
        payload = content.get("payload")

        if message_type not in ("offer", "answer", "candidate"):
            await self.send_json({"type": "error", "code": "invalid_signal_type"})
            return
        if not isinstance(target_user_id, int) or target_user_id == self.user.pk:
            await self.send_json({"type": "error", "code": "invalid_target"})
            return
        if not isinstance(payload, dict) or len(json.dumps(payload)) > 48_000:
            await self.send_json({"type": "error", "code": "invalid_payload"})
            return

        await self.channel_layer.group_send(self.group_name, {
            "type": "voice.signal",
            "signal_type": message_type,
            "sender_user_id": self.user.pk,
            "target_user_id": target_user_id,
            "payload": payload,
        })

    async def voice_signal(self, event):
        if event["target_user_id"] != self.user.pk:
            return
        await self.send_json({
            "type": event["signal_type"],
            "sender_user_id": event["sender_user_id"],
            "payload": event["payload"],
        })

    async def voice_presence(self, event):
        if event["user_id"] == self.user.pk:
            return
        await self.send_json({
            "type": event["event"],
            "user_id": event["user_id"],
        })
