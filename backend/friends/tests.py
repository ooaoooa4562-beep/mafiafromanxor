import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Friendship


class FriendsApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user(username='alice', password='StrongPass!2026')
        self.bob = User.objects.create_user(username='bob', password='StrongPass!2026')
        self.client.force_login(self.alice)

    def test_send_and_accept_friend_request(self):
        response = self.client.post(reverse('friend_request'), data=json.dumps({'username': 'bob'}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        request_id = response.json()['request_id']
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse('friend_respond', kwargs={'request_id': request_id}),
            data=json.dumps({'decision': 'accept'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Friendship.objects.get(pk=request_id).status, 'accepted')

    def test_cannot_send_request_to_self(self):
        response = self.client.post(reverse('friend_request'), data=json.dumps({'username': 'alice'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_only_recipient_can_accept_request(self):
        friendship = Friendship.objects.create(sender=self.alice, receiver=self.bob)
        response = self.client.post(
            reverse('friend_respond', kwargs={'request_id': friendship.pk}),
            data=json.dumps({'decision': 'accept'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_blocked_user_cannot_send_friend_request_back(self):
        self.client.post(reverse('friend_block', kwargs={'user_id': self.bob.pk}), data='{}', content_type='application/json')
        self.client.force_login(self.bob)
        response = self.client.post(reverse('friend_request'), data=json.dumps({'username': 'alice'}), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_send_request_accepts_game_nickname_case_insensitively(self):
        self.bob.nickname = 'NightWolf'
        self.bob.save(update_fields=['nickname'])
        response = self.client.post(
            reverse('friend_request'),
            data=json.dumps({'username': 'nightwolf'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['username'], 'bob')

    def test_login_match_takes_precedence_over_another_users_nickname(self):
        User = get_user_model()
        User.objects.create_user(username='nightwolf', password='StrongPass!2026', nickname='Other')
        self.bob.nickname = 'NightWolf'
        self.bob.save(update_fields=['nickname'])
        response = self.client.post(
            reverse('friend_request'),
            data=json.dumps({'username': 'nightwolf'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['user']['username'], 'nightwolf')

    def test_duplicate_game_nickname_returns_clear_ambiguity_error(self):
        User = get_user_model()
        self.bob.nickname = 'NightWolf'
        self.bob.save(update_fields=['nickname'])
        User.objects.create_user(username='charlie', password='StrongPass!2026', nickname='NightWolf')
        response = self.client.post(
            reverse('friend_request'),
            data=json.dumps({'username': 'NightWolf'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'nickname_ambiguous')
