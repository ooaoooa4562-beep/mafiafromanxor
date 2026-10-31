import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SessionAuthApiTests(TestCase):
    def test_register_creates_user_and_session(self):
        response = self.client.post(
            reverse('auth_register'),
            data=json.dumps({'username': 'new_player', 'password': 'StrongPass!2026', 'nickname': 'Anxor'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['user']['nickname'], 'Anxor')
        self.assertTrue(self.client.get(reverse('auth_me')).json()['authenticated'])
        self.assertTrue(get_user_model().objects.filter(username='new_player').exists())

    def test_duplicate_username_is_rejected(self):
        get_user_model().objects.create_user(username='taken', password='StrongPass!2026')
        response = self.client.post(
            reverse('auth_register'),
            data=json.dumps({'username': 'taken', 'password': 'StrongPass!2026'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)

    def test_login_and_logout(self):
        get_user_model().objects.create_user(username='player', password='StrongPass!2026')
        response = self.client.post(
            reverse('auth_login'),
            data=json.dumps({'username': 'player', 'password': 'StrongPass!2026'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get(reverse('auth_me')).json()['authenticated'])
        self.client.post(reverse('auth_logout'), data='{}', content_type='application/json')
        self.assertFalse(self.client.get(reverse('auth_me')).json()['authenticated'])

    def test_me_is_anonymous_without_login(self):
        response = self.client.get(reverse('auth_me'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['authenticated'])
