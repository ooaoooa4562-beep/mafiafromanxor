from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from rooms.models import Room, RoomPlayer
from .models import Game, PlayerRole

User = get_user_model()


class GameApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="host", password="Test-Password-982!")
        self.room = Room.objects.create(name="Night game", owner=self.owner, max_players=6, is_private=False)
        self.members = [RoomPlayer.objects.create(room=self.room, user=self.owner, is_ready=True)]
        for index in range(3):
            user = User.objects.create_user(username=f"player{index}", password="Test-Password-982!")
            self.members.append(RoomPlayer.objects.create(room=self.room, user=user, is_ready=True))
        self.client.force_authenticate(self.owner)

    def test_owner_can_start_and_only_sees_own_role(self):
        response = self.client.post(f"/api/game/{self.room.code}/start/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["my_role"])
        self.assertTrue(all("role" not in player for player in response.data["players"]))
        self.assertEqual(PlayerRole.objects.filter(game__room=self.room).count(), 4)

    def test_non_owner_cannot_start(self):
        self.client.force_authenticate(self.members[1].user)
        response = self.client.post(f"/api/game/{self.room.code}/start/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_player_can_submit_only_role_action(self):
        game = Game.objects.create(room=self.room, phase="night", phase_ends_at=timezone.now() + timedelta(seconds=60))
        roles = ["mafia", "detective", "civilian", "civilian"]
        role_rows = [PlayerRole.objects.create(game=game, player=member, role=role) for member, role in zip(self.members, roles)]
        response = self.client.post(f"/api/game/{self.room.code}/action/", {"action": "kill", "target_user_id": self.members[2].user_id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invalid = self.client.post(f"/api/game/{self.room.code}/action/", {"action": "heal", "target_user_id": self.members[2].user_id}, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_advance_is_blocked_before_timer(self):
        game = Game.objects.create(room=self.room, phase="night", phase_ends_at=timezone.now() + timedelta(minutes=2))
        response = self.client.post(f"/api/game/{self.room.code}/advance/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
