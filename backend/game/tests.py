import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from rooms.models import Room, RoomPlayer

from .models import GameMatch


class GameApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.host = User.objects.create_user(username='host', password='StrongPass!2026', nickname='Host')
        self.room = Room.objects.create(name='Test table', owner=self.host, max_players=8)
        RoomPlayer.objects.create(room=self.room, user=self.host)
        self.players = [self.host]
        for index in range(3):
            user = User.objects.create_user(username=f'player{index}', password='StrongPass!2026', nickname=f'Player {index}')
            self.players.append(user)
            RoomPlayer.objects.create(room=self.room, user=user)
        self.client.force_login(self.host)

    def test_start_assigns_one_role_per_player(self):
        response = self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 201)
        match = GameMatch.objects.get(room=self.room)
        self.assertEqual(match.participants.count(), 4)
        self.assertEqual(match.participants.filter(role='mafia').count(), 1)
        self.assertEqual(match.participants.filter(role='doctor').count(), 1)
        self.assertEqual(match.participants.filter(role='detective').count(), 1)
        self.assertEqual(match.participants.filter(role='citizen').count(), 1)

    def test_non_owner_cannot_start_match(self):
        self.client.force_login(self.players[1])
        response = self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(GameMatch.objects.filter(room=self.room).exists())

    def test_start_requires_four_players(self):
        RoomPlayer.objects.filter(room=self.room).exclude(user=self.host).delete()
        response = self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_game_state_only_exposes_callers_role(self):
        self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        response = self.client.get(reverse('game_state', kwargs={'code': self.room.code}))
        self.assertEqual(response.status_code, 200)
        participants = response.json()['game']['participants']
        self.assertTrue(all('role' not in participant for participant in participants))
        self.assertIn(response.json()['game']['my_role'], ['mafia', 'doctor', 'detective', 'citizen'])

    def test_action_is_rejected_for_user_without_membership(self):
        outsider = get_user_model().objects.create_user(username='outsider', password='StrongPass!2026')
        self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        self.client.force_login(outsider)
        response = self.client.post(
            reverse('game_action', kwargs={'code': self.room.code}),
            data=json.dumps({'target_user_id': self.host.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_all_night_roles_actions_advance_to_day(self):
        self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        match = GameMatch.objects.get(room=self.room)
        citizen = match.participants.get(role='citizen')
        target_id = citizen.room_player.user_id
        for role in ('mafia', 'doctor', 'detective'):
            participant = match.participants.get(role=role)
            self.client.force_login(participant.room_player.user)
            response = self.client.post(
                reverse('game_action', kwargs={'code': self.room.code}),
                data=json.dumps({'target_user_id': target_id}),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200, response.content)
        match.refresh_from_db()
        self.assertEqual(match.phase, 'day')

    def test_day_vote_finishes_match_when_mafia_is_eliminated(self):
        self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        match = GameMatch.objects.get(room=self.room)
        citizen = match.participants.get(role='citizen')
        for role in ('mafia', 'doctor', 'detective'):
            participant = match.participants.get(role=role)
            self.client.force_login(participant.room_player.user)
            response = self.client.post(
                reverse('game_action', kwargs={'code': self.room.code}),
                data=json.dumps({'target_user_id': citizen.room_player.user_id}),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
        mafia = match.participants.get(role='mafia')
        for participant in match.participants.filter(is_alive=True):
            self.client.force_login(participant.room_player.user)
            target = citizen if participant.role == 'mafia' else mafia
            response = self.client.post(
                reverse('game_action', kwargs={'code': self.room.code}),
                data=json.dumps({'target_user_id': target.room_player.user_id}),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
        match.refresh_from_db()
        self.assertEqual(match.phase, 'finished')
        self.assertEqual(match.winner, 'town')

    @override_settings(GAME_NIGHT_SECONDS=0)
    def test_expired_night_advances_when_state_is_requested(self):
        self.client.post(reverse('game_start', kwargs={'code': self.room.code}), data='{}', content_type='application/json')
        response = self.client.get(reverse('game_state', kwargs={'code': self.room.code}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['game']['phase'], 'day')
