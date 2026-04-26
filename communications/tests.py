from __future__ import annotations

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import ChatMessage


class CommunicationsAccessTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="admin_user",
            password="testpass123",
            full_name="Администратор",
            is_admin=True,
        )
        self.teacher = CustomUser.objects.create_user(
            username="teacher_user",
            password="testpass123",
            full_name="Учитель",
            is_teacher=True,
        )
        self.guest = CustomUser.objects.create_user(
            username="guest_user",
            password="testpass123",
            full_name="Гость",
            is_guest=True,
        )

    def test_guest_cannot_open_chats(self):
        self.client.login(username="guest_user", password="testpass123")
        response = self.client.get(reverse("communications:chats"))
        self.assertEqual(response.status_code, 403)

    def test_notifications_preview_is_admin_only(self):
        self.client.login(username="teacher_user", password="testpass123")
        url = reverse("communications:notifications_preview_api")
        response = self.client.get(url, {"date": date.today().isoformat()})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_preview_notifications(self):
        self.client.login(username="admin_user", password="testpass123")
        url = reverse("communications:notifications_preview_api")
        response = self.client.get(url, {"date": date.today().isoformat()})
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertIn("teachers", payload)
        self.assertIn("teachers_count", payload)

    def test_read_all_marks_messages_as_read(self):
        ChatMessage.objects.create(
            sender=self.teacher,
            recipient=self.admin,
            text="test-1",
            message_type=ChatMessage.TYPE_USER,
        )
        ChatMessage.objects.create(
            sender=self.teacher,
            recipient=self.admin,
            text="test-2",
            message_type=ChatMessage.TYPE_USER,
        )
        self.client.login(username="admin_user", password="testpass123")
        url = reverse("communications:chats_read_all_api")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["updated"], 2)
        self.assertEqual(payload["unread_total"], 0)

    def test_chats_state_api_invalid_thread_limit(self):
        self.client.login(username="admin_user", password="testpass123")
        url = reverse("communications:chats_state_api")
        response = self.client.get(url, {"thread_limit": "abc"})
        self.assertEqual(response.status_code, 400)
