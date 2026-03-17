
from rest_framework import serializers
from .models import Teacher, Subject, Lesson, Replacement
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import LessonSerializer

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['teacher_id', 'full_name', 'specialization']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name']

class LessonSerializer(serializers.ModelSerializer):
    subject = serializers.StringRelatedField()
    teacher = serializers.StringRelatedField()

    class Meta:
        model = Lesson
        fields = '__all__'




@api_view(['GET'])
def get_lesson_details(request, lesson_id, day):
    try:
        lesson = Lesson.objects.get(id=lesson_id, day_of_week=day)
        serializer = LessonSerializer(lesson)
        return Response(serializer.data)
    except Lesson.DoesNotExist:
        return Response({"error": "Урок не найден"}, status=404)

class ReplacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Replacement
        fields = '__all__'
