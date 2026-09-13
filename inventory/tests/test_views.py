from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="Password123!",
        )
        self.login_url = reverse("login")

    def test_login_page_loads(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_successful_login_redirect(self):
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "password": "Password123!"},
            follow=True,
        )
        self.assertTrue(response.context["user"].is_authenticated)
