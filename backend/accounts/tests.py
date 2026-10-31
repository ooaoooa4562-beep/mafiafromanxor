from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AccountApiTests(APITestCase):
    def test_csrf_endpoint_returns_token(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)

    def test_registration_creates_profile(self):
        response = self.client.post("/api/auth/register/", {
            "username": "newplayer", "nickname": "New Player", "password": "Very-Strong-Pass-982!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newplayer").exists())
        self.assertIn("id", response.data)

    def test_login_rejects_wrong_password(self):
        User.objects.create_user(username="player", password="Correct-Pass-123!")
        response = self.client.post("/api/auth/login/", {
            "username": "player", "password": "wrong-password",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
