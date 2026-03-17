from bs4 import BeautifulSoup
from datetime import datetime
import re
from collections import defaultdict
from .models import Teacher, Subject, Lesson  # Django модели
from .scheduling import extract_grade, infer_shift_by_grade

SUBJECT_REPLACEMENTS = {
    '{subjectname}': '{subjectname}',  # шаблонная заглушка в HTML

    'Алгебра': 'Алгебра',
    'Английский ...': 'Английский язык',
    'Биология': 'Биология',
    'Вероятн. и ...': 'ВиС',
    'География': 'География',
    'Геометрия': 'Геометрия',
    'ИЗО': 'ИЗО',
    'Информатика': 'Информатика',
    'История': 'История',
    'Литература': 'Литература',
    'Литературно...': 'Литературное чтение',
    'Мат.практ.': 'Математический практикум',
    'МатКонс': 'Консультация по математике',
    'МатемГрамот...': 'Математическая грамотность',
    'Математика': 'Математика',
    'Музыка': 'Музыка',
    'ОБиЗР': 'Основы безопасности и защиты Родины',
    'ОРКСЭ': 'Основы религиозных культур и светской этики',
    'Обраб. инфо...': 'Обр.инф.',
    'Обществозна...': 'Обществознание',
    'Окр. мир': 'Окружающий мир',
    'ПрВО': 'ПрВО',      # если нужно — впишешь расшифровку
    'Право': 'Право',
    'РЗПТБ': 'РЗПТБ',    # если нужно — впишешь расшифровку
    'РЗПТХ': 'РЗПТХ',    # если нужно — впишешь расшифровку
    'РМГ': 'РМГ',        # если нужно — впишешь расшифровку
    'Развитие ре...': 'Развитие речи',
    'Разговоры о...': 'РоВ',
    'Реш. сл. з....': 'РСЗ',
    'Русский язы...': 'Русский язык',
    'СВОиП': 'СВОиП',    # если нужно — впишешь расшифровку
    'Слож. вопр....': 'СВРЯ',
    'Т. р. с КИМ...': 'Т. р. с КИМ',
    'Труд': 'Труд',
    'Физика': 'Физика',
    'Физкультура': 'Физкультура',
    'Фин.грамотн...': 'ФинГрам',
    'Химия': 'Химия',
    'Химия вокру...': 'Химия вокруг',
    'ЧитатГрамот...': 'Читательская Грамотность',
    'Экономика': 'Экономика',
}

def normalize_class(raw):
    raw = raw.replace('\xa0', ' ').strip()
    raw = re.sub(r'\(.*?\)', '', raw)  # удаляет всё в скобках
    raw = raw.replace(')', '').replace('(', '')  # на случай одиночных скобок
    return raw.replace(' ', '')  # убираем пробелы


def extract_class_number(raw):
    match = re.search(r'(\d{1,2})', raw)
    return match.group(1) if match else ''

def replace_subject(name):
    name = (name or '').strip()
    # 1) точное совпадение
    if name in SUBJECT_REPLACEMENTS:
        return SUBJECT_REPLACEMENTS[name]
    # 2) совпадение по началу (для обрезанных названий с "...")
    for pattern, replacement in SUBJECT_REPLACEMENTS.items():
        if pattern and name.startswith(pattern):
            return replacement
    return name

def parse_schedule_file(html_content, shifts):
    """Парсит HTML, сохранённый со страницы расписания Дневник.ру (schedulesSchool).

    В «полной» сохранённой странице учителя и сетка уроков лежат в *разных* таблицах:
    - div.lefttable  — список учителей
    - div.contenttable — строки с ячейками уроков
    Старый парсер ожидал, что учитель и уроки находятся в одном <tr>, поэтому часто
    возвращал пустой результат.
    """

    soup = BeautifulSoup(html_content, 'html.parser')
    result = []

    day_map = {0: 'пн', 1: 'вт', 2: 'ср', 3: 'чт', 4: 'пт', 5: 'сб', 6: 'вс'}

    # ✅ Основной (правильный для «Save as Webpage» из Дневник.ру) вариант
    teacher_cells = soup.select("div.lefttable td.rowitem.border.left")
    content_rows = soup.select("div.contenttable table tr")

    if teacher_cells and content_rows and len(teacher_cells) == len(content_rows):
        for teacher_cell, row in zip(teacher_cells, content_rows):
            teacher_name = teacher_cell.get_text(" ", strip=True)

            # иногда попадаются строки вроде "Вакансия"
            if not teacher_name or teacher_name.lower().startswith("вакан"):
                continue

            cells = row.select("td.cell.content")
            for cell in cells:
                date_raw = cell.get("data-date")
                lnum = cell.get("data-lessonnumber")
                if not date_raw or not lnum:
                    continue
                if not lnum.lstrip('-').isdigit() or int(lnum) < 0:
                    continue

                lesson_num = int(lnum)
                date_obj = datetime.strptime(date_raw, "%Y%m%d")
                day_short = day_map[date_obj.weekday()]

                lessons = cell.select(".lessonitems .lessonitem")
                for lesson in lessons:
                    title_el = lesson.select_one(".lessontitle a")
                    class_el = lesson.select_one("a.orange")
                    if not title_el or not class_el:
                        continue

                    subject_name = replace_subject(title_el.get_text(strip=True))
                    raw_class = class_el.get_text(strip=True)
                    full_class = normalize_class(raw_class)
                    class_num = extract_class_number(raw_class)
                    room_el = lesson.select_one(".gray2")
                    room = room_el.get_text(strip=True) if room_el else ""

                    # Определяем смену по правилу школы (1–4: 1 смена; 6–8: 2 смена; 5/9/10/11: 1 смена)
                    grade = extract_grade(raw_class)
                    preferred_shift = infer_shift_by_grade(grade)

                    # Сначала пытаемся найти звонок именно для нужной смены (если смена определилась),
                    # иначе — любой подходящий (как раньше).
                    if preferred_shift in (1, 2):
                        matched_shift = next(
                            (
                                s for s in shifts
                                if s['lesson_number'] == lesson_num
                                and extract_grade(s['class_group']) == grade
                                and int(s.get('shift') or 0) == int(preferred_shift)
                            ),
                            None,
                        )
                    else:
                        matched_shift = None

                    if not matched_shift:
                        matched_shift = next(
                            (
                                s for s in shifts
                                if s['lesson_number'] == lesson_num
                                and extract_class_number(s['class_group']) == class_num
                            ),
                            None,
                        )

                    # если не настроено расписание звонков (ClassSchedule) —
                    # лучше не "молчать", а пропустить запись
                    if not matched_shift:
                        continue

                    result.append({
                        "class_group": full_class,
                        "subject": subject_name,
                        "teacher": teacher_name,
                        "lesson_number": lesson_num,
                        "start_time": matched_shift['start_time'],
                        "end_time": matched_shift['end_time'],
                        "shift": matched_shift['shift'],
                        "day_of_week": day_short,
                        "room": room
                    })

        return result

    # 🔁 Фолбэк: если HTML другого формата (всё лежит в одном <tr>)
    for row in soup.select("tr"):
        teacher_tag = row.select_one("td.rowitem a.teacher")
        if not teacher_tag:
            continue
        teacher_name = teacher_tag.get_text(strip=True)
        if not teacher_name or teacher_name.lower().startswith("вакан"):
            continue

        cells = row.select("td.cell.content")
        for cell in cells:
            date_raw = cell.get("data-date")
            lnum = cell.get("data-lessonnumber")
            if not date_raw or not lnum or not lnum.isdigit():
                continue

            lesson_num = int(lnum)
            date_obj = datetime.strptime(date_raw, "%Y%m%d")
            day_short = day_map[date_obj.weekday()]

            lessons = cell.select(".lessonitems .lessonitem")
            for lesson in lessons:
                title_el = lesson.select_one(".lessontitle a")
                class_el = lesson.select_one("a.orange")
                if not title_el or not class_el:
                    continue
                subject_name = replace_subject(title_el.get_text(strip=True))
                raw_class = class_el.get_text(strip=True)
                full_class = normalize_class(raw_class)
                class_num = extract_class_number(raw_class)
                room_el = lesson.select_one(".gray2")
                room = room_el.get_text(strip=True) if room_el else ""

                grade = extract_grade(raw_class)
                preferred_shift = infer_shift_by_grade(grade)

                if preferred_shift in (1, 2):
                    matched_shift = next(
                        (
                            s for s in shifts
                            if s['lesson_number'] == lesson_num
                            and extract_grade(s['class_group']) == grade
                            and int(s.get('shift') or 0) == int(preferred_shift)
                        ),
                        None,
                    )
                else:
                    matched_shift = None

                if not matched_shift:
                    matched_shift = next(
                        (
                            s for s in shifts
                            if s['lesson_number'] == lesson_num
                            and extract_class_number(s['class_group']) == class_num
                        ),
                        None,
                    )
                if matched_shift:
                    result.append({
                        "class_group": full_class,
                        "subject": subject_name,
                        "teacher": teacher_name,
                        "lesson_number": lesson_num,
                        "start_time": matched_shift['start_time'],
                        "end_time": matched_shift['end_time'],
                        "shift": matched_shift['shift'],
                        "day_of_week": day_short,
                        "room": room
                    })

    return result

def save_lessons_to_db(data):
    """Save parsed lessons as the *active* schedule.

    Important: we DO NOT delete or mutate old lessons, because they may be linked
    to already-saved replacements (Replacement -> Lesson FK with CASCADE).
    Instead, upload() deactivates the previous active schedule (Lesson.is_active=False),
    and here we create (or reactivate) lessons as is_active=True.
    """
    # Precompute subjects per teacher to keep Teacher.specialization fresh
    subjects_by_teacher = defaultdict(set)
    for item in data:
        subjects_by_teacher[item['teacher']].add(item['subject'])

    for item in data:
        subject_obj, _ = Subject.objects.get_or_create(name=item['subject'])
        teacher_obj, _ = Teacher.objects.get_or_create(full_name=item['teacher'])

        # Update specialization for this teacher (based on current upload data)
        subject_ids = Subject.objects.filter(
            name__in=subjects_by_teacher.get(item['teacher'], set())
        ).values_list('id_subject', flat=True)

        teacher_obj.specialization = ','.join(str(sid) for sid in sorted(subject_ids))
        teacher_obj.save(update_fields=['specialization'])

        # Try to reactivate an *exact* matching lesson (to avoid duplicates on re-upload),
        # but never update times/shift on existing rows.
        existing = Lesson.objects.filter(
            teacher=teacher_obj,
            subject=subject_obj,
            class_group=item['class_group'],
            lesson_number=item['lesson_number'],
            day_of_week=item['day_of_week'],
            start_time=item['start_time'],
            end_time=item['end_time'],
            shift=item['shift'],
            classroom=item.get('room') or '---',
        ).first()

        if existing:
            if not getattr(existing, 'is_active', True):
                existing.is_active = True
                existing.save(update_fields=['is_active'])
        else:
            Lesson.objects.create(
                teacher=teacher_obj,
                subject=subject_obj,
                class_group=item['class_group'],
                lesson_number=item['lesson_number'],
                shift=item['shift'],
                day_of_week=item['day_of_week'],
                start_time=item['start_time'],
                end_time=item['end_time'],
                classroom=item.get('room') or '---',
                is_active=True,
            )
