from __future__ import annotations

from rest_framework import serializers

from .models import Lesson, Replacement, Subject, Teacher


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ["id", "full_name", "specialization", "hours_per_week"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id_subject", "name"]


class LessonSerializer(serializers.ModelSerializer):
    subject = serializers.StringRelatedField()
    teacher = serializers.StringRelatedField()

    class Meta:
        model = Lesson
        fields = "__all__"


class ReplacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Replacement
        fields = "__all__"
