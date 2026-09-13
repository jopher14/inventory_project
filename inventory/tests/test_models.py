from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import Asset

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user_with_role(self):
        user = User.objects.create_user(
            username="johndoe",
            email="john@example.com",
            password="Password123!",
            role="admin",
        )
        self.assertEqual(user.username, "johndoe")
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_active)


class AssetModelTest(TestCase):
    def test_asset_creation(self):
        asset = Asset.objects.create(
            unit_name="MacBook Pro 16",
            company_tag="TAG-001",
            serial_number="SN12345678",
            asset_type="laptop",
            status="available",
            date_purchased=date(2024, 1, 15),
        )
        self.assertEqual(str(asset), "TAG-001 - MacBook Pro 16")
        self.assertEqual(asset.company_tag, "TAG-001")
