from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from uuid import UUID

from game.models import GameMatch, GameParticipant
from rooms.models import Room


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_id = user.pk
        self.room_code = UUID(self.scope['url_route']['kwargs']['code'])
        self.room_group = f'room_{self.room_code.hex}'
        self.voice_group = None
        if not await self.is_member(user.pk, self.room_code):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'room_code': str(self.room_code)})

    async def disconnect(self, close_code):
        if getattr(self, 'voice_group', None):
            await self.channel_layer.group_send(
                self.voice_group,
                {'type': 'voice.presence', 'user_id': self.user_id, 'state': 'left'},
            )
            await self.channel_layer.group_discard(self.voice_group, self.channel_name)
        if hasattr(self, 'room_group'):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        if message_type == 'ping':
            await self.send_json({'type': 'pong'})
            return
        if message_type == 'voice.join':
            channel = await self.allowed_voice_channel(self.user_id, self.room_code)
            if channel is None:
                await self.send_json({'type': 'voice.denied', 'detail': 'Голосовой канал недоступен на этой фазе игры.'})
                return
            next_group = f'voice_{self.room_code.hex}_{channel}'
            if self.voice_group and self.voice_group != next_group:
                await self.channel_layer.group_discard(self.voice_group, self.channel_name)
            self.voice_group = next_group
            await self.channel_layer.group_add(self.voice_group, self.channel_name)
            await self.send_json({'type': 'voice.joined', 'channel': channel})
            await self.channel_layer.group_send(
                self.voice_group,
                {'type': 'voice.presence', 'user_id': self.user_id, 'state': 'joined'},
            )
            return
        if message_type == 'voice.leave':
            if self.voice_group:
                await self.channel_layer.group_send(
                    self.voice_group,
                    {'type': 'voice.presence', 'user_id': self.user_id, 'state': 'left'},
                )
                await self.channel_layer.group_discard(self.voice_group, self.channel_name)
                self.voice_group = None
            await self.send_json({'type': 'voice.left'})
            return
        if message_type == 'voice.signal':
            if not self.voice_group:
                await self.send_json({'type': 'voice.denied', 'detail': 'Сначала войди в голосовой канал.'})
                return
            signal_type = content.get('signal_type')
            payload = content.get('payload')
            if signal_type not in ('offer', 'answer', 'ice') or not isinstance(payload, dict) or len(str(payload)) > 12000:
                await self.send_json({'type': 'error', 'detail': 'Некорректный сигнал WebRTC.'})
                return
            await self.channel_layer.group_send(
                self.voice_group,
                {
                    'type': 'voice.signal',
                    'sender_channel': self.channel_name,
                    'sender_id': self.user_id,
                    'signal_type': signal_type,
                    'payload': payload,
                },
            )
            return
        await self.send_json({'type': 'error', 'detail': 'Неизвестное событие.'})

    async def room_event(self, event):
        # Re-check channel access on every game transition; clients must re-join voice.
        await self.send_json({'type': event.get('event', 'room.updated')})
        if self.voice_group:
            allowed = await self.allowed_voice_channel(self.user_id, self.room_code)
            expected = f'voice_{self.room_code.hex}_{allowed}' if allowed else None
            if expected != self.voice_group:
                old_group = self.voice_group
                self.voice_group = None
                await self.channel_layer.group_send(old_group, {'type': 'voice.presence', 'user_id': self.user_id, 'state': 'left'})
                await self.channel_layer.group_discard(old_group, self.channel_name)
                await self.send_json({'type': 'voice.rejoin_required'})

    async def voice_signal(self, event):
        if event.get('sender_channel') != self.channel_name:
            await self.send_json({
                'type': 'voice.signal',
                'from_user_id': event.get('sender_id'),
                'signal_type': event.get('signal_type'),
                'payload': event.get('payload'),
            })

    async def voice_presence(self, event):
        if event.get('user_id') != self.user_id:
            await self.send_json({'type': 'voice.presence', 'user_id': event.get('user_id'), 'state': event.get('state')})

    @database_sync_to_async
    def is_member(self, user_id, room_code):
        return Room.objects.filter(code=room_code, players__user_id=user_id).exists()

    @database_sync_to_async
    def allowed_voice_channel(self, user_id, room_code):
        room = Room.objects.filter(code=room_code, players__user_id=user_id).first()
        if room is None:
            return None
        match = GameMatch.objects.filter(room=room).first()
        if match is None:
            return 'lobby'
        participant = GameParticipant.objects.filter(match=match, room_player__user_id=user_id).first()
        if participant is None:
            return None
        if match.phase == 'finished':
            return 'finished'
        if not participant.is_alive:
            return 'dead'
        if match.phase == 'day':
            return 'living'
        if participant.role == 'mafia':
            return 'mafia'
        return None
