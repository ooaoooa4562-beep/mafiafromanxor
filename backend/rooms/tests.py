import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Room, RoomPlayer


class RoomApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='host', password='test-pass-123')
        self.client.force_login(self.user)

    def test_create_room_adds_owner_as_first_player(self):
        response = self.client.post(
            reverse('rooms_collection'),
            data=json.dumps({'name': 'Ночной город', 'max_players': 8, 'is_private': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get()
        self.assertEqual(room.owner, self.user)
        self.assertEqual(RoomPlayer.objects.filter(room=room, user=self.user).count(), 1)
        self.assertEqual(response.json()['room']['players_count'], 1)

    def test_public_list_hides_private_rooms(self):
        Room.objects.create(name='Private', owner=self.user, is_private=True)
        Room.objects.create(name='Public', owner=self.user, is_private=False)
        response = self.client.get(reverse('rooms_collection'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['name'] for item in response.json()['rooms']], ['Public'])

    def test_join_room_adds_player_once(self):
        room = Room.objects.create(name='Open table', owner=self.user, is_private=False)
        guest = get_user_model().objects.create_user(username='guest', password='test-pass-123')
        self.client.force_login(guest)
        url = reverse('join_room', kwargs={'code': room.code})
        self.assertEqual(self.client.post(url, data='{}', content_type='application/json').status_code, 200)
        self.assertEqual(self.client.post(url, data='{}', content_type='application/json').status_code, 200)
        self.assertEqual(RoomPlayer.objects.filter(room=room, user=guest).count(), 1)

    def test_player_switching_rooms_releases_previous_seat(self):
        first = Room.objects.create(name='First', owner=self.user, is_private=False)
        second = Room.objects.create(name='Second', owner=self.user, is_private=False)
        RoomPlayer.objects.create(room=first, user=self.user)
        guest = get_user_model().objects.create_user(username='guest', password='test-pass-123')
        self.client.force_login(guest)
        RoomPlayer.objects.create(room=first, user=guest)
        response = self.client.post(reverse('join_room', kwargs={'code': second.code}), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoomPlayer.objects.filter(room=first, user=guest).exists())
        self.assertTrue(RoomPlayer.objects.filter(room=second, user=guest).exists())
        self.assertEqual(first.players.count(), 1)

    def test_leave_room_removes_player_and_updates_count(self):
        room = Room.objects.create(name='Leave test', owner=self.user, is_private=False)
        RoomPlayer.objects.create(room=room, user=self.user)
        guest = get_user_model().objects.create_user(username='guest', password='test-pass-123')
        RoomPlayer.objects.create(room=room, user=guest)
        response = self.client.post(reverse('leave_room', kwargs={'code': room.code}), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoomPlayer.objects.filter(room=room, user=self.user).exists())
        self.assertEqual(response.json()['players_count'], 1)

    def test_full_room_rejects_new_player(self):
        room = Room.objects.create(name='Small table', owner=self.user, max_players=4)
        RoomPlayer.objects.create(room=room, user=self.user)
        for index in range(3):
            player = get_user_model().objects.create_user(username=f'p{index}', password='test-pass-123')
            RoomPlayer.objects.create(room=room, user=player)
        guest = get_user_model().objects.create_user(username='late_guest', password='test-pass-123')
        self.client.force_login(guest)
        response = self.client.post(
            reverse('join_room', kwargs={'code': room.code}),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(RoomPlayer.objects.filter(room=room, user=guest).exists())

    def test_room_api_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('rooms_collection'))
        self.assertEqual(response.status_code, 401)


from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from rooms.models import RoomMessage


@override_settings(
    CENTRIFUGO_TOKEN_SECRET="test-centrifugo-secret",
    CENTRIFUGO_PUBLIC_URL="wss://centrifugo.example.test/connection/websocket",
)
class RealtimeApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.host = User.objects.create_user(username="realtime_host", password="StrongPass!2026")
        self.guest = User.objects.create_user(username="realtime_guest", password="StrongPass!2026")
        self.outsider = User.objects.create_user(username="realtime_outsider", password="StrongPass!2026")
        self.room = Room.objects.create(name="Realtime room", owner=self.host, max_players=8)
        RoomPlayer.objects.create(room=self.room, user=self.host)
        RoomPlayer.objects.create(room=self.room, user=self.guest)
        self.client.force_login(self.host)

    def test_connection_token_contains_user_and_public_endpoint(self):
        response = self.client.get(reverse("realtime_connection_token"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "wss://centrifugo.example.test/connection/websocket")
        claims = jwt.decode(response.json()["token"], "test-centrifugo-secret", algorithms=["HS256"])
        self.assertEqual(claims["sub"], str(self.host.pk))

    def test_subscription_token_only_allows_room_members(self):
        channel = f"$room-{self.room.code}-chat"
        response = self.client.get(reverse("realtime_subscription_token"), {"channel": channel})
        self.assertEqual(response.status_code, 200)
        claims = jwt.decode(response.json()["token"], "test-centrifugo-secret", algorithms=["HS256"])
        self.assertEqual(claims["channel"], channel)

        self.client.force_login(self.outsider)
        denied = self.client.get(reverse("realtime_subscription_token"), {"channel": channel})
        self.assertEqual(denied.status_code, 403)

    @patch("config.realtime_views.publish")
    def test_chat_message_is_saved_and_published(self, publish_mock):
        response = self.client.post(
            reverse("realtime_room_message", kwargs={"code": self.room.code}),
            data=json.dumps({"message": "Hello from realtime"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RoomMessage.objects.filter(room=self.room, user=self.host).count(), 1)
        self.assertEqual(response.json()["message"]["content"], "Hello from realtime")
        publish_mock.assert_called_once()
        self.assertEqual(publish_mock.call_args.args[0], f"$room-{self.room.code}-chat")

    @patch("config.realtime_views.publish")
    def test_voice_join_and_signal_are_validated_and_published(self, publish_mock):
        joined = self.client.post(reverse("realtime_voice_join", kwargs={"code": self.room.code}), data="{}", content_type="application/json")
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.json()["channel"], "lobby")

        signal = self.client.post(
            reverse("realtime_voice_signal", kwargs={"code": self.room.code}),
            data=json.dumps({"signal_type": "offer", "payload": {"to": self.guest.pk, "description": {"type": "offer", "sdp": "test"}}}),
            content_type="application/json",
        )
        self.assertEqual(signal.status_code, 200)
        self.assertEqual(publish_mock.call_count, 2)

    def test_chat_history_is_hidden_from_non_members(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("realtime_room_chat_history", kwargs={"code": self.room.code}))
        self.assertEqual(response.status_code, 404)
