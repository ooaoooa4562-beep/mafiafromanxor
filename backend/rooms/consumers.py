from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from rooms.models import Room


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.room_code = self.scope['url_route']['kwargs']['code']
        self.room_group = f'room_{self.room_code.hex}'
        if not await self.is_member(user.pk, self.room_code):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'room_code': str(self.room_code)})

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group'):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Game-changing commands go through CSRF-protected HTTP endpoints.
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})
        else:
            await self.send_json({'type': 'error', 'detail': 'Используй HTTP API для игровых действий.'})

    async def room_event(self, event):
        await self.send_json({'type': event.get('event', 'room.updated')})

    @database_sync_to_async
    def is_member(self, user_id, room_code):
        return Room.objects.filter(code=room_code, players__user_id=user_id).exists()
