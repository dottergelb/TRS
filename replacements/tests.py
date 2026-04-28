from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from replacements.models import Lesson, Subject, Teacher


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
        self.upload_user = CustomUser.objects.create_user(
            username="upload_user",
            password="testpass123",
            full_name="Загрузка",
            can_upload=True,
        )
        self.subject = Subject.objects.create(name="Математика")
        self.lesson = Lesson.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            lesson_number=1,
            class_group="5А",
            classroom="101",
            start_time="09:00",
            end_time="09:45",
            shift=1,
            day_of_week="пн",
            is_active=True,
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

    def test_delete_replacements_requires_post(self):
        self.client.login(username="calendar_user", password="testpass123")
        url = reverse("replacements:delete_replacements")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_check_replacements_invalid_date(self):
        self.client.login(username="calendar_user", password="testpass123")
        url = reverse("replacements:check_replacements")
        response = self.client.get(url, {"date": "2026/01/01"})
        self.assertEqual(response.status_code, 400)

    def test_update_lesson_teacher_invalid_teacher_id(self):
        self.client.login(username="upload_user", password="testpass123")
        url = reverse("replacements:lesson-teacher", args=[self.lesson.id])
        response = self.client.post(
            url,
            data=json.dumps({"teacher_id": "abc"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_save_replacements_invalid_json_returns_400(self):
        self.client.login(username="calendar_user", password="testpass123")
        url = reverse("replacements:save")
        response = self.client.post(
            url,
            data="{bad-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
