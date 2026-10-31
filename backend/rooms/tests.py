from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Room, RoomPlayer

User = get_user_model()


class RoomApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="safe-password-123")
        self.client.force_authenticate(self.owner)

    def test_create_room_adds_owner_as_member(self):
        response = self.client.post("/api/rooms/", {"name": "Тестовая игра", "max_players": 8, "is_private": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = Room.objects.get(code=response.data["code"])
        self.assertTrue(RoomPlayer.objects.filter(room=room, user=self.owner).exists())

    def test_room_size_is_limited(self):
        response = self.client.post("/api/rooms/", {"name": "Слишком большая", "max_players": 30, "is_private": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_join_and_ready(self):
        room = Room.objects.create(name="Открытая", owner=self.owner, max_players=6, is_private=False)
        other = User.objects.create_user(username="guest", password="safe-password-123")
        self.client.force_authenticate(other)
        joined = self.client.post(f"/api/rooms/{room.code}/join/")
        self.assertEqual(joined.status_code, status.HTTP_200_OK)
        ready = self.client.post(f"/api/rooms/{room.code}/ready/", {"is_ready": True}, format="json")
        self.assertEqual(ready.status_code, status.HTTP_200_OK)
        self.assertTrue(RoomPlayer.objects.get(room=room, user=other).is_ready)

    def test_private_room_is_not_listed(self):
        Room.objects.create(name="Secret", owner=self.owner, is_private=True)
        response = self.client.get("/api/rooms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
