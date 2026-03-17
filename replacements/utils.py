from .models import Lesson, Teacher
from datetime import time
from django.db import connection



def get_subject_id(subject_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id_subject FROM replacements_subject WHERE name = %s",
            [subject_name]
        )
        row = cursor.fetchone()
        return row[0] if row else None
