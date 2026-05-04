from __future__ import annotations

import random
from pathlib import Path

from django.db import transaction
from django.db import connection

from accounts.models import School
from replacements.models import (
    Lesson,
    Replacement,
    SpecialReplacement,
    Subject,
    Teacher,
)


def _build_full_names(count: int) -> list[str]:
    last_names = [
        "Иванова", "Петрова", "Сидорова", "Кузнецова", "Смирнова", "Попова", "Васильева", "Новикова",
        "Морозова", "Волкова", "Лебедева", "Козлова", "Павлова", "Семенова", "Голубева", "Виноградова",
        "Беляева", "Тарасова", "Жукова", "Федорова", "Макарова", "Громова", "Егорова", "Королева",
        "Комарова", "Орлова", "Никитина", "Захарова", "Антонова", "Соколова", "Алексеева", "Медведева",
        "Романова", "Фролова", "Дмитриева", "Борисова", "Калинина", "Титова", "Филиппова", "Крылова",
        "Кириллова", "Чернова", "Рыбакова", "Гаврилова", "Миронова", "Нестерова", "Боброва", "Тихонова",
    ]
    first_names = [
        "Анна", "Елена", "Мария", "Ольга", "Наталья", "Татьяна", "Ирина", "Светлана", "Екатерина", "Юлия",
        "Людмила", "Нина", "Полина", "Вера", "Дарья", "Алина", "Лариса", "Галина", "Валентина", "Ксения",
        "Оксана", "Виктория", "Надежда", "Яна", "Зоя", "Диана", "Евгения", "Ангелина", "София", "Милана",
    ]
    patronymics = [
        "Ивановна", "Петровна", "Сергеевна", "Алексеевна", "Дмитриевна", "Андреевна", "Владимировна",
        "Николаевна", "Олеговна", "Юрьевна", "Геннадьевна", "Викторовна", "Васильевна", "Михайловна",
        "Павловна", "Анатольевна", "Степановна", "Игоревна", "Федоровна", "Константиновна",
    ]
    names: set[str] = set()
    while len(names) < count:
        names.add(
            f"{random.choice(last_names)} {random.choice(first_names)} {random.choice(patronymics)}"
        )
    return sorted(names)


def _export_xlsx(names: list[str], output_file: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Учителя"
    for i, full_name in enumerate(names, start=1):
        ws.cell(row=i, column=1, value=full_name)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_file)


def _reset_pk_sequence(table: str, pk_col: str) -> None:
    with connection.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, pk_col])
        seq_row = cur.fetchone()
        seq_name = seq_row[0] if seq_row else None
        if not seq_name:
            return
        cur.execute(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table}")
        max_id = cur.fetchone()[0] or 0
        cur.execute("SELECT setval(%s, %s, %s)", [seq_name, int(max_id), True])


@transaction.atomic
def run() -> None:
    random.seed()

    school_95 = School.objects.filter(name__icontains="№95").first()
    school_1001 = School.objects.filter(name__icontains="№1001").first()
    if not school_95 or not school_1001:
        raise RuntimeError("Не найдена школа №95 или №1001")

    teachers_95 = list(Teacher.all_objects.filter(school=school_95).order_by("id"))
    if not teachers_95:
        raise RuntimeError("В школе №95 нет учителей")
    target_count = len(teachers_95)

    # Clean school 1001 schedule-related data before reseed.
    Replacement.all_objects.filter(school=school_1001).delete()
    SpecialReplacement.all_objects.filter(school=school_1001).delete()
    Lesson.all_objects.filter(school=school_1001).delete()
    Teacher.all_objects.filter(school=school_1001).delete()
    Subject.all_objects.filter(school=school_1001).delete()
    _reset_pk_sequence("replacements_subject", "id_subject")
    _reset_pk_sequence("replacements_teacher", "teacher_id")
    _reset_pk_sequence("replacements_lesson", "lesson_id")

    # Clone subjects
    subj_map: dict[int, Subject] = {}
    for subj in Subject.all_objects.filter(school=school_95):
        new_subj = Subject.all_objects.create(
            school=school_1001,
            name=subj.name,
        )
        subj_map[subj.id_subject] = new_subj

    # Create random teachers and stable bijection 95 -> 1001
    new_names = _build_full_names(target_count)
    new_teachers: list[Teacher] = []
    for full_name in new_names:
        new_teachers.append(
            Teacher.all_objects.create(
                school=school_1001,
                full_name=full_name,
                specialization="",
                hours_per_week=0,
            )
        )
    teacher_map = {old.id: new_teachers[idx] for idx, old in enumerate(teachers_95)}

    # Clone lessons with teacher remap.
    lessons_95 = Lesson.all_objects.filter(school=school_95).select_related("teacher", "subject")
    created_lessons = 0
    for l in lessons_95:
        mapped_teacher = teacher_map.get(l.teacher_id)
        mapped_subject = subj_map.get(l.subject_id)
        if not mapped_teacher or not mapped_subject:
            continue
        Lesson.all_objects.create(
            school=school_1001,
            teacher=mapped_teacher,
            subject=mapped_subject,
            lesson_number=l.lesson_number,
            class_group=l.class_group,
            classroom=l.classroom,
            day_of_week=l.day_of_week,
            start_time=l.start_time,
            end_time=l.end_time,
            shift=l.shift,
            is_active=l.is_active,
        )
        created_lessons += 1

    # Derive specialization from created lessons.
    teacher_subject_ids: dict[int, set[str]] = {}
    for l in Lesson.all_objects.filter(school=school_1001).only("teacher_id", "subject_id"):
        teacher_subject_ids.setdefault(l.teacher_id, set()).add(str(l.subject_id))
    for t in new_teachers:
        ids = sorted(teacher_subject_ids.get(t.id, set()))
        t.specialization = ",".join(ids)
        t.save(update_fields=["specialization"])

    # Export xlsx with A1 column only.
    out_file = Path("/app/media/school_1001_teachers_A1.xlsx")
    _export_xlsx([t.full_name for t in new_teachers], out_file)

    print(f"OK: school95_teachers={target_count}, school1001_teachers={len(new_teachers)}, lessons={created_lessons}")
    print(f"XLSX: {out_file}")


run()
