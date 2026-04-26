from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class AccountsSecurityTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="admin_user",
            password="testpass123",
            full_name="Админ",
            can_users=True,
        )
        self.target = CustomUser.objects.create_user(
            username="target_user",
            password="testpass123",
            full_name="Цель",
        )

    def test_logout_requires_post(self):
        url = reverse("accounts:logout")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_user_delete_requires_post(self):
        self.client.login(username="admin_user", password="testpass123")
        url = reverse("accounts:user_delete", args=[self.target.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_user_delete_post_deletes_user(self):
        self.client.login(username="admin_user", password="testpass123")
        url = reverse("accounts:user_delete", args=[self.target.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(id=self.target.id).exists())
