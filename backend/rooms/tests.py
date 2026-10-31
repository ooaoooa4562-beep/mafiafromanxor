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


    def test_joining_another_room_moves_player_out_of_previous_waiting_room(self):
        first = Room.objects.create(name='First', owner=self.user, is_private=False)
        RoomPlayer.objects.create(room=first, user=self.user)
        second = Room.objects.create(name='Second', owner=self.user, is_private=False)
        response = self.client.post(
            reverse('join_room', kwargs={'code': second.code}),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoomPlayer.objects.filter(room=first, user=self.user).exists())
        self.assertTrue(RoomPlayer.objects.filter(room=second, user=self.user).exists())
        self.assertEqual(RoomPlayer.objects.filter(user=self.user).count(), 1)

    def test_leave_room_removes_membership_and_updates_count(self):
        room = Room.objects.create(name='Leave me', owner=self.user, is_private=False)
        RoomPlayer.objects.create(room=room, user=self.user)
        response = self.client.post(
            reverse('leave_room', kwargs={'code': room.code}),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoomPlayer.objects.filter(room=room, user=self.user).exists())
        self.assertFalse(Room.objects.filter(pk=room.pk).exists())

    def test_cannot_join_second_room_while_current_room_is_playing(self):
        current = Room.objects.create(name='Playing', owner=self.user, status='playing')
        RoomPlayer.objects.create(room=current, user=self.user)
        target = Room.objects.create(name='Waiting', owner=self.user, is_private=False)
        response = self.client.post(
            reverse('join_room', kwargs={'code': target.code}),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertTrue(RoomPlayer.objects.filter(room=current, user=self.user).exists())
        self.assertFalse(RoomPlayer.objects.filter(room=target, user=self.user).exists())
