from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from inventory.forms import CustomAuthenticationForm, CustomUserCreationForm

User = get_user_model()


class CustomUserCreationFormTest(TestCase):
    def test_passwords_mismatch(self):
        form_data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "IT",  # Updated to match valid choices uppercase
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_successful_user_creation(self):
        form_data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "IT",  # Updated to match valid choices uppercase
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        form = CustomUserCreationForm(data=form_data)

        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "newuser")
        self.assertTrue(user.check_password("Password123!"))


class CustomAuthenticationFormTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.active_user = User.objects.create_user(username="activeuser", password="Password123!", is_active=True)
        self.disabled_user = User.objects.create_user(username="disableduser", password="Password123!", is_active=False)

    def test_disabled_account_validation(self):
        request = self.factory.get("/")
        form_data = {"username": "disableduser", "password": "Password123!"}
        form = CustomAuthenticationForm(request=request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Your account has been disabled.", str(form.non_field_errors()))

    def test_valid_login(self):
        request = self.factory.get("/")
        form_data = {"username": "activeuser", "password": "Password123!"}
        form = CustomAuthenticationForm(request=request, data=form_data)
        self.assertTrue(form.is_valid())
