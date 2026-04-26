from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from replacements.models import Teacher


class ReplacementsSecurityTests(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(full_name="Тест Учитель", specialization="")
        self.user = CustomUser.objects.create_user(
            username="user_no_calendar",
            password="testpass123",
            full_name="Пользователь",
            is_guest=False,
            is_teacher=False,
        )
        self.calendar_user = CustomUser.objects.create_user(
            username="calendar_user",
            password="testpass123",
            full_name="Календарный",
            can_calendar=True,
        )

    def test_teacher_details_requires_login(self):
        url = reverse("replacements:teacher-details", args=[self.teacher.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_teacher_details_forbidden_without_calendar_access(self):
        self.client.login(username="user_no_calendar", password="testpass123")
        url = reverse("replacements:teacher-details", args=[self.teacher.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_teacher_details_allowed_with_calendar_access(self):
        self.client.login(username="calendar_user", password="testpass123")
        url = reverse("replacements:teacher-details", args=[self.teacher.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.json())
