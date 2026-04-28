from __future__ import annotations

from django.db import DatabaseError
from django.http import Http404

from .gsheets_adapter import (
    _gs_active_lessons_rows,
    _gs_is_teacher_replacement,
    _gs_lesson_map,
    _gs_next_id,
    _gs_parse_time,
    _gs_shift_boundary,
    _gs_store,
    _gs_subject_id_by_name,
    _gs_subject_map,
    _gs_teacher_map,
    _gs_time_str,
)
from .permissions_parsing import (
    FIRST_SHIFT_GRADES_SECONDARY,
    SECOND_SHIFT_GRADES,
    BooleanField,
    Case,
    ClassSchedule,
    Count,
    HttpResponse,
    JsonResponse,
    Lesson,
    Q,
    Replacement,
    SpecialReplacement,
    Teacher,
    Value,
    When,
    _active_lessons,
    _can_calendar_read,
    _deny_guest_write_json,
    _effective_shift_for_class,
    _effective_times_for_lesson,
    _is_guest_user,
    _is_vacancy_teacher_name,
    _name_matches_term_ci,
    _teacher_replacements,
    _use_gsheets_backend,
    as_bool,
    as_int,
    datetime,
    day_short_from_date,
    extract_grade,
    get_object_or_404,
    get_subject_id,
    infer_shift_by_grade,
    json,
    log_activity,
    logger,
    login_required,
    overlaps,
    require_GET,
    timedelta,
    transaction,
)

@login_required
def save_replacements_service(request):
    guest_forbidden = _deny_guest_write_json(request)
    if guest_forbidden:
        return guest_forbidden

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('replacements', [])
            special_items = data.get('special_replacements', None)
            special_date = data.get('special_replacements_date')
            if not isinstance(items, list):
                return JsonResponse({"error": "replacements должен быть списком"}, status=400)
            if special_items is not None and not isinstance(special_items, list):
                return JsonResponse({"error": "special_replacements должен быть списком"}, status=400)

            if _use_gsheets_backend():
                store = _gs_store()
                all_lessons = store.get_table_dicts("replacements_lesson")
                lessons = [l for l in all_lessons if as_bool(l.get("is_active"))]
                lesson_map = {as_int(l.get("lesson_id")): l for l in lessons if as_int(l.get("lesson_id")) is not None}
                teachers = store.get_table_dicts("replacements_teacher")
                teacher_map = {as_int(t.get("teacher_id")): str(t.get("full_name") or "") for t in teachers if as_int(t.get("teacher_id")) is not None}
                replacement_rows = store.get_table_dicts("replacements_replacement")
                special_rows = store.get_table_dicts("replacements_special_replacement")
                schedule_rows = store.get_table_dicts("replacements_class_schedule")

                replacement_ids = []
                for i in items:
                    try:
                        if i.get('teacher_id'):
                            replacement_ids.append(int(i.get('teacher_id')))
                    except (TypeError, ValueError):
                        pass
                replacement_ids = list(set(replacement_ids))

                grade_map_all_payload: dict[int, set[int]] = {}
                for l in lessons:
                    tid = as_int(l.get("teacher_id"))
                    if tid not in replacement_ids:
                        continue
                    g = extract_grade(str(l.get("class_group") or ""))
                    if g is None:
                        continue
                    grade_map_all_payload.setdefault(tid, set()).add(g)

                def teacher_level_payload(t_id: int) -> str:
                    grades = grade_map_all_payload.get(t_id) or set()
                    if not grades:
                        return "none"
                    if max(grades) <= 4:
                        return "1-4"
                    if min(grades) >= 5:
                        return "5-11"
                    return "1-11"

                shift1_max_end = None
                shift2_min_start = None
                for row in schedule_rows:
                    sh = as_int(row.get("shift"))
                    st = _gs_parse_time(row.get("start_time"))
                    en = _gs_parse_time(row.get("end_time"))
                    if sh == 1 and en:
                        shift1_max_end = en if shift1_max_end is None or en > shift1_max_end else shift1_max_end
                    if sh == 2 and st:
                        shift2_min_start = st if shift2_min_start is None or st < shift2_min_start else shift2_min_start
                boundary = shift2_min_start
                if shift1_max_end and shift2_min_start:
                    try:
                        dt1 = datetime.combine(datetime.today().date(), shift1_max_end)
                        dt2 = datetime.combine(datetime.today().date(), shift2_min_start)
                        boundary = (dt1 + (dt2 - dt1) / 2).time() if dt2 > dt1 else shift2_min_start
                    except (TypeError, ValueError):
                        boundary = shift2_min_start

                shift_presence_cache: dict[tuple[int, str, int], bool] = {}

                def teacher_has_lessons_in_shift(t_id: int, day_of_week: str, target_shift: int) -> bool:
                    key = (t_id, day_of_week, int(target_shift))
                    if key in shift_presence_cache:
                        return shift_presence_cache[key]
                    has = False
                    for l in lessons:
                        if as_int(l.get("teacher_id")) != t_id:
                            continue
                        if str(l.get("day_of_week") or "") != str(day_of_week):
                            continue
                        sh = _effective_shift_for_class(str(l.get("class_group") or ""), as_int(l.get("shift")))
                        st = _gs_parse_time(l.get("start_time"))
                        if sh not in (1, 2):
                            try:
                                if shift2_min_start and boundary and st and st >= boundary:
                                    sh = 2
                                else:
                                    sh = 1
                            except TypeError:
                                sh = 1
                        if int(sh) == int(target_shift):
                            has = True
                            break
                    shift_presence_cache[key] = has
                    return has

                replace_all = bool(data.get('replace_all'))
                vacancy_cache: dict[int, bool] = {}

                def _replacement_is_vacancy(teacher_id: int) -> bool:
                    if teacher_id in vacancy_cache:
                        return vacancy_cache[teacher_id]
                    name = teacher_map.get(teacher_id) or ""
                    val = _is_vacancy_teacher_name(name)
                    vacancy_cache[teacher_id] = val
                    return val

                payload_busy = {}
                payload_busy_rooms: dict[str, list[tuple]] = {}

                if replace_all:
                    date_set = sorted({i.get('date') for i in items if i.get('date')})
                    if special_date:
                        date_set.append(special_date)
                    replacement_rows = [
                        r for r in replacement_rows
                        if str(r.get("date") or "") not in date_set
                    ]
                    special_rows = [
                        r for r in special_rows
                        if str(r.get("date") or "") not in date_set
                    ]
                special_rows_changed = bool(replace_all)

                for item in items:
                    if 'lesson_id' not in item:
                        return JsonResponse({"error": "Поле lesson_id обязательно"}, status=400)

                    lid = as_int(item.get('lesson_id'))
                    date_str = item.get('date')
                    original_id = as_int(item.get('original_id'))
                    replacement_id = as_int(item.get('teacher_id'))
                    confirmed = bool(item.get('confirmed'))
                    production_necessity = bool(item.get('production_necessity'))
                    ignore_in_reports = bool(item.get('ignore_in_reports'))

                    if not (lid and date_str and original_id and replacement_id):
                        return JsonResponse({"error": "Некорректные данные замены"}, status=400)

                    lesson = lesson_map.get(lid)
                    if not lesson:
                        return JsonResponse({"error": f"Урок с ID {lid} не найден"}, status=404)

                    try:
                        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        return JsonResponse({"error": f"Некорректная дата: {date_str}"}, status=400)

                    replacement_room = (item.get('classroom') or item.get('room') or '').strip() or None
                    if _replacement_is_vacancy(replacement_id):
                        return JsonResponse({"error": "Учитель «Вакансия» не может быть назначен замещающим."}, status=400)
                    if replacement_id == original_id:
                        return JsonResponse({"error": "Нельзя поставить учителя на замещение самого себя."}, status=400)

                    lesson_grade = extract_grade(str(lesson.get("class_group") or ""))
                    lvl = teacher_level_payload(replacement_id)
                    cross_level = False
                    if lesson_grade is not None:
                        if lesson_grade <= 4 and lvl == "5-11":
                            cross_level = True
                        if lesson_grade >= 5 and lvl == "1-4":
                            cross_level = True
                    if cross_level and not confirmed:
                        return JsonResponse({"error": "Требуется подтверждение: учитель другой ступени."}, status=400)

                    lesson_start = _gs_parse_time(lesson.get("start_time"))
                    lesson_end = _gs_parse_time(lesson.get("end_time"))
                    if not lesson_start or not lesson_end:
                        return JsonResponse({"error": "Урок имеет некорректное время"}, status=400)

                    target_shift = _effective_shift_for_class(str(lesson.get("class_group") or ""), as_int(lesson.get("shift")))
                    if target_shift not in (1, 2):
                        try:
                            if shift2_min_start and boundary and lesson_start >= boundary:
                                target_shift = 2
                            else:
                                target_shift = 1
                        except TypeError:
                            target_shift = 1
                    if not teacher_has_lessons_in_shift(replacement_id, str(lesson.get("day_of_week") or ""), int(target_shift)):
                        if not confirmed:
                            return JsonResponse({"error": "Требуется подтверждение: в этот день у выбранного учителя нет уроков в эту смену."}, status=400)

                    for l in lessons:
                        if as_int(l.get("teacher_id")) != replacement_id:
                            continue
                        if str(l.get("day_of_week") or "") != str(lesson.get("day_of_week") or ""):
                            continue
                        if str(l.get("class_group") or "") == str(lesson.get("class_group") or "") and as_int(l.get("lesson_number")) == as_int(lesson.get("lesson_number")):
                            continue
                        s = _gs_parse_time(l.get("start_time"))
                        e = _gs_parse_time(l.get("end_time"))
                        if s and e and overlaps(lesson_start, lesson_end, s, e):
                            if not confirmed:
                                return JsonResponse({"error": "Требуется подтверждение: выбранный учитель занят уроком."}, status=400)
                            break

                    for r in replacement_rows:
                        if not _gs_is_teacher_replacement(r):
                            continue
                        if str(r.get("date") or "") != selected_date.strftime("%Y-%m-%d"):
                            continue
                        if as_int(r.get("replacement_teacher_id")) != replacement_id:
                            continue
                        if as_int(r.get("lesson_id")) == lid:
                            continue
                        l2 = lesson_map.get(as_int(r.get("lesson_id")))
                        if not l2:
                            continue
                        s2 = _gs_parse_time(l2.get("start_time"))
                        e2 = _gs_parse_time(l2.get("end_time"))
                        if not s2 or not e2:
                            continue
                        if overlaps(lesson_start, lesson_end, s2, e2):
                            if (str(l2.get("class_group") or "") == str(lesson.get("class_group") or "") and as_int(l2.get("lesson_number")) == as_int(lesson.get("lesson_number"))):
                                continue
                            if not confirmed:
                                return JsonResponse({"error": "Требуется подтверждение: выбранный учитель уже назначен на замещение."}, status=400)

                    busy_list = payload_busy.setdefault(replacement_id, [])
                    for (s, e, cls, num, other_lid, other_confirmed) in busy_list:
                        if overlaps(lesson_start, lesson_end, s, e):
                            if (cls == str(lesson.get("class_group") or "") and num == as_int(lesson.get("lesson_number"))):
                                continue
                            if not (confirmed and other_confirmed):
                                return JsonResponse({"error": "Требуется подтверждение: пересечение по времени в выбранных заменах."}, status=400)
                    busy_list.append((lesson_start, lesson_end, str(lesson.get("class_group") or ""), as_int(lesson.get("lesson_number")), lid, confirmed))

                    if replacement_room:
                        for l in lessons:
                            if str(l.get("classroom") or "") != replacement_room:
                                continue
                            if str(l.get("day_of_week") or "") != str(lesson.get("day_of_week") or ""):
                                continue
                            if as_int(l.get("lesson_id")) == lid:
                                continue
                            s = _gs_parse_time(l.get("start_time"))
                            e = _gs_parse_time(l.get("end_time"))
                            if s and e and overlaps(lesson_start, lesson_end, s, e) and not confirmed:
                                return JsonResponse({"error": "Требуется подтверждение: выбранный кабинет занят уроком."}, status=400)

                        for r in replacement_rows:
                            if str(r.get("date") or "") != selected_date.strftime("%Y-%m-%d"):
                                continue
                            if str(r.get("replacement_classroom") or "") != replacement_room:
                                continue
                            if as_int(r.get("lesson_id")) == lid:
                                continue
                            l2 = lesson_map.get(as_int(r.get("lesson_id")))
                            if not l2:
                                continue
                            s2 = _gs_parse_time(l2.get("start_time"))
                            e2 = _gs_parse_time(l2.get("end_time"))
                            if s2 and e2 and overlaps(lesson_start, lesson_end, s2, e2) and not confirmed:
                                return JsonResponse({"error": "Требуется подтверждение: выбранный кабинет уже назначен на замещение."}, status=400)

                        busy_rooms = payload_busy_rooms.setdefault(replacement_room, [])
                        for (s, e, cls, num, other_lid, other_confirmed) in busy_rooms:
                            if overlaps(lesson_start, lesson_end, s, e):
                                if (cls == str(lesson.get("class_group") or "") and num == as_int(lesson.get("lesson_number"))):
                                    continue
                                if not (confirmed and other_confirmed):
                                    return JsonResponse({"error": "Требуется подтверждение: пересечение по времени по кабинетам."}, status=400)
                        busy_rooms.append((lesson_start, lesson_end, str(lesson.get("class_group") or ""), as_int(lesson.get("lesson_number")), lid, confirmed))

                    existing_idx = None
                    for idx, r in enumerate(replacement_rows):
                        if as_int(r.get("lesson_id")) == lid and str(r.get("date") or "") == selected_date.strftime("%Y-%m-%d"):
                            existing_idx = idx
                            break

                    if existing_idx is not None:
                        row = replacement_rows[existing_idx]
                    else:
                        row = {"id": _gs_next_id(replacement_rows, "id")}
                    row["date"] = selected_date.strftime("%Y-%m-%d")
                    row["lesson_id"] = lid
                    row["original_teacher_id"] = original_id
                    row["replacement_teacher_id"] = replacement_id
                    row["confirmed"] = 1 if confirmed else 0
                    row["production_necessity"] = 1 if production_necessity else 0
                    row["ignore_in_reports"] = 1 if ignore_in_reports else 0
                    if ('classroom' in item or 'room' in item):
                        row["replacement_classroom"] = replacement_room or ""
                    elif existing_idx is None:
                        row["replacement_classroom"] = ""
                    if existing_idx is None:
                        replacement_rows.append(row)
                    else:
                        replacement_rows[existing_idx] = row

                if special_items is not None:
                    if not special_date:
                        return JsonResponse({"error": "special_replacements_date обязателен"}, status=400)
                    try:
                        special_dt = datetime.strptime(special_date, "%Y-%m-%d").date()
                    except ValueError:
                        return JsonResponse({"error": "Некорректная дата special_replacements_date"}, status=400)

                    special_rows = [r for r in special_rows if str(r.get("date") or "") != special_dt.strftime("%Y-%m-%d")]
                    special_rows_changed = True
                    for item in special_items:
                        class_group = (item.get("class_group") or "").strip()
                        subject_name = (item.get("subject_name") or "").strip()
                        replacement_id = as_int(item.get("teacher_id"))
                        lesson_id = as_int(item.get("lesson_id"))
                        original_teacher_id = as_int(item.get("original_teacher_id"))

                        if not (class_group and subject_name and replacement_id):
                            return JsonResponse({"error": "Некорректные данные отдельной замены"}, status=400)
                        if _replacement_is_vacancy(replacement_id):
                            return JsonResponse({"error": "Учитель «Вакансия» не может быть назначен замещающим."}, status=400)
                        row = {"id": _gs_next_id(special_rows, "id"), "date": special_dt.strftime("%Y-%m-%d")}
                        if lesson_id:
                            lesson_obj = lesson_map.get(lesson_id)
                            if not lesson_obj:
                                return JsonResponse({"error": "Урок для отдельной замены не найден"}, status=404)
                            subj_name = subject_name
                            sid = as_int(lesson_obj.get("subject_id_subject"))
                            if sid is not None:
                                subj_name = _gs_subject_map().get(sid) or subj_name
                            row.update({
                                "lesson_id": lesson_id,
                                "class_group": lesson_obj.get("class_group") or "",
                                "subject_name": subj_name,
                                "lesson_number": as_int(lesson_obj.get("lesson_number")),
                                "start_time": _gs_time_str(_gs_parse_time(lesson_obj.get("start_time"))),
                                "end_time": _gs_time_str(_gs_parse_time(lesson_obj.get("end_time"))),
                                "classroom": lesson_obj.get("classroom") or "",
                                "replacement_teacher_id": replacement_id,
                                "original_teacher_id": original_teacher_id or as_int(lesson_obj.get("teacher_id")),
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            })
                        else:
                            lesson_number = as_int(item.get("lesson_number"))
                            start_raw = (item.get("start") or "").strip()
                            end_raw = (item.get("end") or "").strip()
                            classroom = (item.get("classroom") or "").strip()
                            if lesson_number is None:
                                return JsonResponse({"error": "Для ручного урока укажите номер урока"}, status=400)
                            start_t = _gs_parse_time(start_raw) if start_raw else None
                            end_t = _gs_parse_time(end_raw) if end_raw else None
                            if bool(start_t) ^ bool(end_t):
                                return JsonResponse({"error": "Для ручного урока укажите и начало, и конец"}, status=400)
                            if not start_t and not end_t:
                                shift = _effective_shift_for_class(class_group, None)
                                start_t, end_t = _effective_times_for_lesson(class_group, lesson_number, shift, None, None)
                            if not start_t or not end_t:
                                return JsonResponse({"error": "Не удалось определить время по номеру урока и смене."}, status=400)
                            if start_t >= end_t:
                                return JsonResponse({"error": "Время окончания должно быть позже начала"}, status=400)
                            row.update({
                                "lesson_id": "",
                                "class_group": class_group,
                                "subject_name": subject_name,
                                "lesson_number": lesson_number,
                                "start_time": _gs_time_str(start_t),
                                "end_time": _gs_time_str(end_t),
                                "classroom": classroom or "",
                                "replacement_teacher_id": replacement_id,
                                "original_teacher_id": original_teacher_id or "",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            })
                        special_rows.append(row)

                store.replace_table_dicts("replacements_replacement", replacement_rows)
                if special_rows_changed:
                    store.replace_table_dicts("replacements_special_replacement", special_rows)
                log_activity(request, "replacements_save", {
                    "items": len(items),
                    "dates": sorted({i.get("date") for i in items if i.get("date")}),
                    "replace_all": replace_all,
                    "backend": "gsheets",
                })
                return JsonResponse({"status": "success"})

                                                
            lesson_ids = [i.get('lesson_id') for i in items if i.get('lesson_id')]
            lessons = Lesson.objects.select_related('teacher').filter(id__in=lesson_ids)
            lesson_map = {l.id: l for l in lessons}

                                                                                        
            replacement_ids = []
            for i in items:
                try:
                    if i.get('teacher_id'):
                        replacement_ids.append(int(i.get('teacher_id')))
                except (TypeError, ValueError):
                    pass
            replacement_ids = list(set(replacement_ids))

            grade_map_all_payload: dict[int, set[int]] = {}
            for t_id, cls in _active_lessons().filter(teacher_id__in=replacement_ids).values_list("teacher_id", "class_group"):
                g = extract_grade(cls)
                if g is None:
                    continue
                grade_map_all_payload.setdefault(t_id, set()).add(g)

            def teacher_level_payload(t_id: int) -> str:
                grades = grade_map_all_payload.get(t_id) or set()
                if not grades:
                    return "none"
                if max(grades) <= 4:
                    return "1-4"
                if min(grades) >= 5:
                    return "5-11"
                return "1-11"

                                                                          
            from django.db.models import Max, Min
            shift1_max_end = ClassSchedule.objects.filter(shift=1).aggregate(mx=Max("end_time"))["mx"]
            shift2_min_start = ClassSchedule.objects.filter(shift=2).aggregate(mn=Min("start_time"))["mn"]
            boundary = None
            if shift2_min_start and shift1_max_end:
                try:
                    dt1 = datetime.combine(datetime.today().date(), shift1_max_end)
                    dt2 = datetime.combine(datetime.today().date(), shift2_min_start)
                    boundary = (dt1 + (dt2 - dt1) / 2).time() if dt2 > dt1 else shift2_min_start
                except (TypeError, ValueError):
                    boundary = shift2_min_start
            elif shift2_min_start:
                boundary = shift2_min_start

            shift_presence_cache: dict[tuple[int, str, int], bool] = {}

            def teacher_has_lessons_in_shift(t_id: int, day_of_week: str, target_shift: int) -> bool:
                key = (t_id, day_of_week, int(target_shift))
                if key in shift_presence_cache:
                    return shift_presence_cache[key]
                has = False
                for cls, st, sh_stored in _active_lessons().filter(teacher_id=t_id, day_of_week=day_of_week).values_list('class_group', 'start_time', 'shift'):
                    sh = _effective_shift_for_class(cls, sh_stored)
                    if sh not in (1, 2):
                        try:
                            if shift2_min_start and boundary and st >= boundary:
                                sh = 2
                            else:
                                sh = 1
                        except TypeError:
                            sh = 1
                    if int(sh) == int(target_shift):
                        has = True
                        break
                shift_presence_cache[key] = has
                return has

            replace_all = bool(data.get('replace_all'))
            vacancy_cache: dict[int, bool] = {}

            def _replacement_is_vacancy(teacher_id: int) -> bool:
                if teacher_id in vacancy_cache:
                    return vacancy_cache[teacher_id]
                name = Teacher.objects.filter(id=teacher_id).values_list("full_name", flat=True).first()
                val = _is_vacancy_teacher_name(name)
                vacancy_cache[teacher_id] = val
                return val

                                                                 
                                                                                              
                                                     
                                                
            payload_busy = {}                                                                
                                                                                                                  
            payload_busy_rooms: dict[str, list[tuple]] = {}                                                          

            with transaction.atomic():
                                                                                   
                                                                                     
                if replace_all:
                    date_set = sorted({i.get('date') for i in items if i.get('date')})
                    if special_date:
                        date_set.append(special_date)
                    for dstr in date_set:
                        try:
                            d = datetime.strptime(dstr, "%Y-%m-%d").date()
                            Replacement.objects.filter(date=d).delete()
                            SpecialReplacement.objects.filter(date=d).delete()
                        except ValueError:
                            continue

                for item in items:
                    if 'lesson_id' not in item:
                        logger.error(f"Отсутствует lesson_id в элементе: {item}")
                        return JsonResponse({"error": "Поле lesson_id обязательно"}, status=400)

                    lid = item.get('lesson_id')
                    date_str = item.get('date')
                    original_id = item.get('original_id')
                    replacement_id = item.get('teacher_id')

                    confirmed = bool(item.get('confirmed'))
                    production_necessity = bool(item.get('production_necessity'))
                    ignore_in_reports = bool(item.get('ignore_in_reports'))

                    if not (lid and date_str and original_id and replacement_id):
                        return JsonResponse({"error": "Некорректные данные замены"}, status=400)

                    lesson = lesson_map.get(int(lid))
                    if not lesson:
                        return JsonResponse({"error": f"Урок с ID {lid} не найден"}, status=404)

                    try:
                        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        return JsonResponse({"error": f"Некорректная дата: {date_str}"}, status=400)

                    replacement_id = int(replacement_id)
                    original_id = int(original_id)

                                                                                            
                    replacement_room = (item.get('classroom') or item.get('room') or '').strip() or None

                    if _replacement_is_vacancy(replacement_id):
                        return JsonResponse({
                            "error": "Учитель «Вакансия» не может быть назначен замещающим."
                        }, status=400)

                    if replacement_id == original_id:
                        return JsonResponse({
                            "error": "Нельзя поставить учителя на замещение самого себя."
                        }, status=400)
                                                                                             
                    lesson_grade = extract_grade(lesson.class_group)
                    lvl = teacher_level_payload(replacement_id)
                    cross_level = False
                    if lesson_grade is not None:
                        if lesson_grade <= 4 and lvl == "5-11":
                            cross_level = True
                        if lesson_grade >= 5 and lvl == "1-4":
                            cross_level = True
                    if cross_level and not confirmed:
                        return JsonResponse({
                            "error": "Требуется подтверждение: учитель другой ступени."
                        }, status=400)

                                                                                                                
                    target_shift = _effective_shift_for_class(lesson.class_group, getattr(lesson, 'shift', None))
                    if target_shift not in (1, 2):
                        try:
                            if shift2_min_start and boundary and lesson.start_time >= boundary:
                                target_shift = 2
                            else:
                                target_shift = 1
                        except TypeError:
                            target_shift = 1
                    if not teacher_has_lessons_in_shift(replacement_id, lesson.day_of_week, int(target_shift)):
                        if not confirmed:
                            return JsonResponse({
                                "error": "Требуется подтверждение: в этот день у выбранного учителя нет уроков в эту смену."
                            }, status=400)


                                                                                                       
                    scheduled_conflict = _active_lessons().filter(
                        teacher_id=replacement_id,
                        day_of_week=lesson.day_of_week,
                        start_time__lt=lesson.end_time,
                        end_time__gt=lesson.start_time,
                    ).exclude(
                        class_group=lesson.class_group,
                        lesson_number=lesson.lesson_number,
                        day_of_week=lesson.day_of_week,
                    )
                    if scheduled_conflict.exists():
                        c = scheduled_conflict.first()
                        if not confirmed:
                            return JsonResponse({
                                "error": (
                                    "Требуется подтверждение: выбранный учитель занят уроком "
                                    f"({c.start_time.strftime('%H:%M')}-{c.end_time.strftime('%H:%M')}, {c.class_group})."
                                )
                            }, status=400)

                                                                              
                    existing_repls = _teacher_replacements().filter(
                        date=selected_date,
                        replacement_teacher_id=replacement_id,
                    ).exclude(lesson_id=lesson.id).select_related('lesson')

                    for r in existing_repls:
                        l2 = r.lesson
                        if not l2:
                            continue
                        if overlaps(lesson.start_time, lesson.end_time, l2.start_time, l2.end_time):
                                                                                  
                            if (l2.class_group == lesson.class_group and l2.lesson_number == lesson.lesson_number):
                                continue
                            if not confirmed:
                                return JsonResponse({
                                    "error": (
                                        "Требуется подтверждение: выбранный учитель уже назначен на замещение "
                                        f"({l2.start_time.strftime('%H:%M')}-{l2.end_time.strftime('%H:%M')}, {l2.class_group})."
                                    )
                                }, status=400)

                                                          
                    busy_list = payload_busy.setdefault(replacement_id, [])
                    for (s, e, cls, num, other_lid, other_confirmed) in busy_list:
                        if overlaps(lesson.start_time, lesson.end_time, s, e):
                            if (cls == lesson.class_group and num == lesson.lesson_number):
                                continue
                            if not (confirmed and other_confirmed):
                                return JsonResponse({
                                    "error": (
                                        "Требуется подтверждение: пересечение по времени в выбранных заменах "
                                        f"({s.strftime('%H:%M')}-{e.strftime('%H:%M')}, {cls})."
                                    )
                                }, status=400)
                    busy_list.append((lesson.start_time, lesson.end_time, lesson.class_group, lesson.lesson_number, lesson.id, confirmed))

                                                                                          
                    if replacement_room:
                                                                                              
                        room_sched_conflict = _active_lessons().filter(
                            classroom=replacement_room,
                            day_of_week=lesson.day_of_week,
                            start_time__lt=lesson.end_time,
                            end_time__gt=lesson.start_time,
                        ).exclude(id=lesson.id)
                        if room_sched_conflict.exists() and not confirmed:
                            c = room_sched_conflict.first()
                            return JsonResponse({
                                "error": (
                                    "Требуется подтверждение: выбранный кабинет занят уроком "
                                    f"({c.start_time.strftime('%H:%M')}-{c.end_time.strftime('%H:%M')}, {c.class_group})."
                                )
                            }, status=400)

                                                                                                           
                        existing_room_repls = Replacement.objects.filter(
                            date=selected_date,
                            replacement_classroom=replacement_room,
                        ).exclude(lesson_id=lesson.id).select_related('lesson')
                        for r in existing_room_repls:
                            l2 = r.lesson
                            if not l2:
                                continue
                            if overlaps(lesson.start_time, lesson.end_time, l2.start_time, l2.end_time):
                                                                                                                   
                                if not confirmed:
                                    return JsonResponse({
                                        "error": (
                                            "Требуется подтверждение: выбранный кабинет уже назначен на замещение "
                                            f"({l2.start_time.strftime('%H:%M')}-{l2.end_time.strftime('%H:%M')}, {l2.class_group})."
                                        )
                                    }, status=400)

                                                                                
                        busy_rooms = payload_busy_rooms.setdefault(replacement_room, [])
                        for (s, e, cls, num, other_lid, other_confirmed) in busy_rooms:
                            if overlaps(lesson.start_time, lesson.end_time, s, e):
                                                                                                            
                                if (cls == lesson.class_group and num == lesson.lesson_number):
                                    continue
                                if not (confirmed and other_confirmed):
                                    return JsonResponse({
                                        "error": (
                                            "Требуется подтверждение: пересечение по времени по кабинетам "
                                            f"({s.strftime('%H:%M')}-{e.strftime('%H:%M')}, {cls})."
                                        )
                                    }, status=400)
                        busy_rooms.append((lesson.start_time, lesson.end_time, lesson.class_group, lesson.lesson_number, lesson.id, confirmed))

                                       
                    defaults = {
                        'original_teacher_id': original_id,
                        'replacement_teacher_id': replacement_id,
                        'confirmed': confirmed,
                        'production_necessity': production_necessity,
                        'ignore_in_reports': ignore_in_reports,
                    }
                                                                                                               
                                                                                                                        
                    if ('classroom' in item or 'room' in item):
                        defaults['replacement_classroom'] = replacement_room
                    Replacement.objects.update_or_create(
                        lesson_id=lesson.id,
                        date=selected_date,
                        defaults=defaults
                    )

                                                            
                if special_items is not None:
                    if not special_date:
                        return JsonResponse({"error": "special_replacements_date обязателен"}, status=400)
                    try:
                        special_dt = datetime.strptime(special_date, "%Y-%m-%d").date()
                    except ValueError:
                        return JsonResponse({"error": "Некорректная дата special_replacements_date"}, status=400)

                    SpecialReplacement.objects.filter(date=special_dt).delete()
                    for item in special_items:
                        class_group = (item.get("class_group") or "").strip()
                        subject_name = (item.get("subject_name") or "").strip()
                        replacement_id = item.get("teacher_id")
                        lesson_id = item.get("lesson_id")
                        original_id = item.get("original_teacher_id")

                        if not (class_group and subject_name and replacement_id):
                            return JsonResponse({"error": "Некорректные данные отдельной замены"}, status=400)
                        replacement_id = int(replacement_id)
                        original_teacher_id = None
                        if original_id not in (None, "", 0, "0"):
                            try:
                                original_teacher_id = int(original_id)
                            except (TypeError, ValueError):
                                return JsonResponse({"error": "Некорректный original_teacher_id"}, status=400)
                            if not Teacher.objects.filter(id=original_teacher_id).exists():
                                return JsonResponse({"error": "Исходный учитель не найден"}, status=404)
                        if _replacement_is_vacancy(replacement_id):
                            return JsonResponse({"error": "Учитель «Вакансия» не может быть назначен замещающим."}, status=400)
                        if lesson_id:
                            lesson_obj = Lesson.objects.filter(id=lesson_id, is_active=True).first()
                            if not lesson_obj:
                                return JsonResponse({"error": "Урок для отдельной замены не найден"}, status=404)
                            SpecialReplacement.objects.create(
                                date=special_dt,
                                lesson=lesson_obj,
                                class_group=lesson_obj.class_group,
                                subject_name=lesson_obj.subject.name if lesson_obj.subject else subject_name,
                                lesson_number=lesson_obj.lesson_number,
                                start_time=lesson_obj.start_time,
                                end_time=lesson_obj.end_time,
                                classroom=lesson_obj.classroom,
                                replacement_teacher_id=replacement_id,
                                original_teacher_id=original_teacher_id or (lesson_obj.teacher_id if lesson_obj.teacher_id else None),
                            )
                        else:
                            lesson_number_raw = item.get("lesson_number")
                            start_raw = (item.get("start") or "").strip()
                            end_raw = (item.get("end") or "").strip()
                            classroom = (item.get("classroom") or "").strip()
                            if lesson_number_raw in (None, "", 0, "0"):
                                return JsonResponse({"error": "Для ручного урока укажите номер урока"}, status=400)
                            try:
                                lesson_number = int(lesson_number_raw)
                            except (TypeError, ValueError):
                                return JsonResponse({"error": "Некорректный номер урока"}, status=400)

                            start_t = None
                            end_t = None
                            if start_raw:
                                try:
                                    start_t = datetime.strptime(start_raw, "%H:%M").time()
                                except ValueError:
                                    return JsonResponse({"error": "Некорректное время начала (HH:MM)"}, status=400)
                            if end_raw:
                                try:
                                    end_t = datetime.strptime(end_raw, "%H:%M").time()
                                except ValueError:
                                    return JsonResponse({"error": "Некорректное время окончания (HH:MM)"}, status=400)
                            if bool(start_t) ^ bool(end_t):
                                return JsonResponse({"error": "Для ручного урока укажите и начало, и конец"}, status=400)
                            if not start_t and not end_t:
                                shift = _effective_shift_for_class(class_group, None)
                                start_t, end_t = _effective_times_for_lesson(
                                    class_group=class_group,
                                    lesson_number=lesson_number,
                                    shift=shift,
                                    fallback_start=None,
                                    fallback_end=None,
                                )
                                if not (start_t and end_t):
                                    return JsonResponse({
                                        "error": "Не удалось определить время по номеру урока и смене. Проверьте расписание звонков."
                                    }, status=400)
                            if start_t and end_t and start_t >= end_t:
                                return JsonResponse({"error": "Время окончания должно быть позже начала"}, status=400)

                            SpecialReplacement.objects.create(
                                date=special_dt,
                                lesson=None,
                                class_group=class_group,
                                subject_name=subject_name,
                                lesson_number=lesson_number,
                                start_time=start_t,
                                end_time=end_t,
                                classroom=classroom or None,
                                replacement_teacher_id=replacement_id,
                                original_teacher_id=original_teacher_id,
                            )

            log_activity(request, "replacements_save", {
                "items": len(items),
                "dates": sorted({i.get("date") for i in items if i.get("date")}),
                "replace_all": replace_all,
            })
            return JsonResponse({"status": "success"})

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка формата JSON: {str(e)}")
            return JsonResponse({"error": "Некорректный JSON"}, status=400)
        except DatabaseError as e:
            logger.error(f"Ошибка БД в save_replacements: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Внутренняя ошибка"}, status=500)

    return JsonResponse({"error": "Метод не разрешен"}, status=405)



@login_required
@require_GET
def get_suggestions_service(request):
    if not _can_calendar_read(request.user):
        return HttpResponse("Forbidden", status=403)
    try:
        lesson_id = request.GET.get("lesson_id")
        day = request.GET.get("day")
        subject = request.GET.get("subject")
        date_str = request.GET.get("date")

        if not all([lesson_id, day, subject, date_str]):
            return JsonResponse({"error": "Недостаточно данных"}, status=400)

        if _use_gsheets_backend():
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day = day_short_from_date(selected_date)
            start_of_week = selected_date - timedelta(days=selected_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            active_lessons = _gs_active_lessons_rows()
            lessons_by_id = {as_int(l.get("lesson_id")): l for l in active_lessons if as_int(l.get("lesson_id")) is not None}
            lesson = lessons_by_id.get(as_int(lesson_id))
            if not lesson:
                return JsonResponse({"error": "Урок не найден"}, status=404)

            subject_id = _gs_subject_id_by_name(subject)
            if not subject_id:
                return JsonResponse({"error": "Предмет не найден"}, status=400)

            teacher_rows = _gs_store().get_table_dicts("replacements_teacher")
            teacher_by_id = {as_int(t.get("teacher_id")): t for t in teacher_rows if as_int(t.get("teacher_id")) is not None}
            original_teacher_id = as_int(lesson.get("teacher_id"))
            lesson_start = _gs_parse_time(lesson.get("start_time"))
            lesson_end = _gs_parse_time(lesson.get("end_time"))
            if not lesson_start or not lesson_end:
                return JsonResponse({"error": "Некорректное время урока"}, status=400)

            lesson_grade = extract_grade(str(lesson.get("class_group") or ""))

            def _is_parallel(item):
                return (
                    str(item.get("class_group") or "") == str(lesson.get("class_group") or "")
                    and as_int(item.get("lesson_number")) == as_int(lesson.get("lesson_number"))
                )

            specialized_ids = set()
            for t in teacher_rows:
                tid = as_int(t.get("teacher_id"))
                if tid is None or tid == original_teacher_id:
                    continue
                if _is_vacancy_teacher_name(str(t.get("full_name") or "")):
                    continue
                spec = str(t.get("specialization") or "")
                spec_ids = {s.strip() for s in spec.split(",") if s.strip()}
                if str(subject_id) in spec_ids:
                    specialized_ids.add(tid)

            replacement_rows = _gs_store().get_table_dicts("replacements_replacement")
            absent_teacher_ids = {
                as_int(r.get("original_teacher_id"))
                for r in replacement_rows
                if _gs_is_teacher_replacement(r) and str(r.get("date") or "") == selected_date.strftime("%Y-%m-%d")
            }
            absent_teacher_ids = {tid for tid in absent_teacher_ids if tid is not None}

            free_teacher_ids = []
            for t in teacher_rows:
                tid = as_int(t.get("teacher_id"))
                if tid is None or tid == original_teacher_id:
                    continue
                if _is_vacancy_teacher_name(str(t.get("full_name") or "")):
                    continue
                busy = False
                for l in active_lessons:
                    if as_int(l.get("teacher_id")) != tid:
                        continue
                    if str(l.get("day_of_week") or "") != str(day):
                        continue
                    s = _gs_parse_time(l.get("start_time"))
                    e = _gs_parse_time(l.get("end_time"))
                    if not s or not e:
                        continue
                    if overlaps(lesson_start, lesson_end, s, e) and not _is_parallel(l):
                        busy = True
                        break
                if not busy:
                    free_teacher_ids.append(tid)

            candidate_ids = sorted(set(free_teacher_ids) - absent_teacher_ids)

            grade_map: dict[int, set[int]] = {}
            for l in active_lessons:
                tid = as_int(l.get("teacher_id"))
                if tid not in candidate_ids:
                    continue
                g = extract_grade(str(l.get("class_group") or ""))
                if g is None:
                    continue
                grade_map.setdefault(tid, set()).add(g)

            def teacher_level(t_id: int) -> str:
                grades = grade_map.get(t_id) or set()
                if not grades:
                    return "none"
                if max(grades) <= 4:
                    return "1-4"
                if min(grades) >= 5:
                    return "5-11"
                return "1-11"

            def teacher_base_shifts(t_id: int) -> set[int]:
                grades = grade_map.get(t_id) or set()
                sec = {g for g in grades if g is not None and g >= 5}
                if not sec:
                    return {1}
                if sec.issubset(SECOND_SHIFT_GRADES):
                    return {2}
                if sec.issubset(FIRST_SHIFT_GRADES_SECONDARY):
                    return {1}
                return {1, 2}

            _, shift2_min_start, boundary = _gs_shift_boundary(selected_date)

            def infer_shift_by_time(t):
                if not shift2_min_start:
                    return 1
                if boundary and t >= boundary:
                    return 2
                return 1

            target_shift = _effective_shift_for_class(str(lesson.get("class_group") or ""), as_int(lesson.get("shift")))
            if target_shift is None:
                target_shift = int(infer_shift_by_time(lesson_start))

            day_shift_map: dict[int, set[int]] = {}
            for l in active_lessons:
                tid = as_int(l.get("teacher_id"))
                if tid not in candidate_ids:
                    continue
                if str(l.get("day_of_week") or "") != str(day):
                    continue
                g = extract_grade(str(l.get("class_group") or ""))
                sh = infer_shift_by_grade(g)
                if sh is None:
                    st = _gs_parse_time(l.get("start_time"))
                    sh = int(infer_shift_by_time(st)) if st else 1
                day_shift_map.setdefault(tid, set()).add(int(sh))

            repl_time_map: dict[int, list[tuple]] = {}
            for r in replacement_rows:
                if not _gs_is_teacher_replacement(r):
                    continue
                if str(r.get("date") or "") != selected_date.strftime("%Y-%m-%d"):
                    continue
                tid = as_int(r.get("replacement_teacher_id"))
                if tid not in candidate_ids:
                    continue
                l2 = lessons_by_id.get(as_int(r.get("lesson_id")))
                if not l2:
                    continue
                s2 = _gs_parse_time(l2.get("start_time"))
                e2 = _gs_parse_time(l2.get("end_time"))
                if not s2 or not e2:
                    continue
                repl_time_map.setdefault(tid, []).append((s2, e2, str(l2.get("class_group") or ""), as_int(l2.get("lesson_number"))))

            base_hours_map: dict[int, int] = {}
            for l in active_lessons:
                tid = as_int(l.get("teacher_id"))
                if tid in candidate_ids:
                    base_hours_map[tid] = base_hours_map.get(tid, 0) + 1

            week_repl_hours_map: dict[int, int] = {}
            for r in replacement_rows:
                if not _gs_is_teacher_replacement(r):
                    continue
                tid = as_int(r.get("replacement_teacher_id"))
                if tid not in candidate_ids:
                    continue
                d_raw = str(r.get("date") or "")
                try:
                    d = datetime.strptime(d_raw, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if start_of_week <= d <= end_of_week:
                    week_repl_hours_map[tid] = week_repl_hours_map.get(tid, 0) + 1

            suggestions = []
            for tid in candidate_ids:
                t = teacher_by_id.get(tid) or {}
                name = str(t.get("full_name") or "")
                level = teacher_level(tid)
                grade_ok = True
                if lesson_grade is not None:
                    if lesson_grade <= 4 and level == "5-11":
                        grade_ok = False
                    if lesson_grade >= 5 and level == "1-4":
                        grade_ok = False

                teacher_day_shifts = day_shift_map.get(tid) or set()
                teacher_shifts = teacher_day_shifts or teacher_base_shifts(tid)
                shift_ok = int(target_shift) in set(teacher_shifts)
                no_lessons_shift = int(target_shift) not in set(teacher_day_shifts) if teacher_day_shifts else True

                conflict = False
                for (s, e, cls, num) in repl_time_map.get(tid, []):
                    if overlaps(lesson_start, lesson_end, s, e):
                        if not (cls == str(lesson.get("class_group") or "") and num == as_int(lesson.get("lesson_number"))):
                            conflict = True
                            break

                auto_allowed = bool(grade_ok and shift_ok and not conflict and not no_lessons_shift)
                base_hours = base_hours_map.get(tid, 0)
                replacement_hours = week_repl_hours_map.get(tid, 0)
                compatibility = "Специализация" if tid in specialized_ids else "Свободен"

                suggestions.append({
                    "id": tid,
                    "name": name,
                    "status": "Урок" if conflict else "Свободен",
                    "compatibility": compatibility,
                    "hours": base_hours + replacement_hours,
                    "auto_allowed": auto_allowed,
                    "grade_profile": level,
                    "grade_ok": grade_ok,
                    "shift_ok": shift_ok,
                    "no_lessons_shift": no_lessons_shift,
                    "conflict": conflict,
                    "teacher_shifts": sorted(list(teacher_shifts)) if teacher_shifts else [],
                    "teacher_day_shifts": sorted(list(teacher_day_shifts)) if teacher_day_shifts else [],
                })

            compatibility_order = {"Вторая группа": 0, "Специализация": 1, "Свободен": 2}
            suggestions.sort(
                key=lambda s: (
                    compatibility_order.get(s["compatibility"], 99),
                    0 if s.get("auto_allowed") else 1,
                    str(s.get("name") or "").casefold(),
                )
            )
            return JsonResponse({"suggestions": suggestions})

        lesson = get_object_or_404(Lesson, id=lesson_id)
        original_teacher = lesson.teacher
        subject_id = get_subject_id(subject)

        if not subject_id:
            return JsonResponse({"error": "Предмет не найден"}, status=400)

                                                                   
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        day = day_short_from_date(selected_date)
        start_of_week = selected_date - timedelta(days=selected_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        lesson_grade = extract_grade(lesson.class_group)

                                  
        specialized_teachers = Teacher.objects.filter(
            Q(specialization__contains=f",{subject_id},") |
            Q(specialization__startswith=f"{subject_id},") |
            Q(specialization__endswith=f",{subject_id}") |
            Q(specialization=subject_id)
        ).exclude(id=original_teacher.id).exclude(
            Q(full_name__contains="Вакан")
            | Q(full_name__contains="вакан")
            | Q(full_name__icontains="vakans")
        )

                                                                                 
        free_teachers = Teacher.objects.exclude(
            Q(lesson__is_active=True)
            & Q(lesson__day_of_week=day)
            & Q(lesson__start_time__lt=lesson.end_time)
            & Q(lesson__end_time__gt=lesson.start_time)
        ).exclude(id=original_teacher.id).exclude(
            Q(full_name__contains="Вакан")
            | Q(full_name__contains="вакан")
            | Q(full_name__icontains="vakans")
        ).distinct()

                                             
        absent_teacher_ids = _teacher_replacements().filter(
            date=selected_date
        ).values_list('original_teacher_id', flat=True)

                         
        candidate_ids = list(
            free_teachers.exclude(id__in=absent_teacher_ids).values_list("id", flat=True)
        )

        candidate_ids = list(set(candidate_ids))

                                                               
        replacements = Teacher.objects.filter(id__in=candidate_ids).annotate(
            is_specialized=Case(
                When(id__in=specialized_teachers.values_list('id', flat=True), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

                                                         
        grade_map: dict[int, set[int]] = {}
        for t_id, cls in _active_lessons().filter(teacher_id__in=candidate_ids).values_list("teacher_id", "class_group"):
            g = extract_grade(cls)
            if g is None:
                continue
            grade_map.setdefault(t_id, set()).add(g)

        def teacher_level(t_id: int) -> str:
            grades = grade_map.get(t_id) or set()
            if not grades:
                return "none"
            if max(grades) <= 4:
                return "1-4"
            if min(grades) >= 5:
                return "5-11"
            return "1-11"

                                                                                    
                     
                             
                                
                                                                                
                                                                                                         
                                                                                                               
        from django.db.models import Max, Min

                                                                                                  
        shift1_max_end = ClassSchedule.objects.filter(shift=1).aggregate(mx=Max("end_time"))["mx"]
        shift2_min_start = ClassSchedule.objects.filter(shift=2).aggregate(mn=Min("start_time"))["mn"]

        boundary = None
        if shift2_min_start and shift1_max_end:
            try:
                dt1 = datetime.combine(selected_date, shift1_max_end)
                dt2 = datetime.combine(selected_date, shift2_min_start)
                boundary = (dt1 + (dt2 - dt1) / 2).time() if dt2 > dt1 else shift2_min_start
            except (TypeError, ValueError):
                boundary = shift2_min_start
        elif shift2_min_start:
            boundary = shift2_min_start

        def infer_shift_by_time(t):
            if not shift2_min_start:
                return 1
            if boundary and t >= boundary:
                return 2
            return 1

                                                     
        target_shift = infer_shift_by_grade(lesson_grade)
        if target_shift is None:
            target_shift = int(infer_shift_by_time(lesson.start_time))

                                                                                    
                                                 
        def teacher_base_shifts(t_id: int) -> set[int]:
            grades = grade_map.get(t_id) or set()
            sec = {g for g in grades if g is not None and g >= 5}
            if not sec:
                                        
                return {1}
            if sec.issubset(SECOND_SHIFT_GRADES):
                return {2}
            if sec.issubset(FIRST_SHIFT_GRADES_SECONDARY):
                return {1}
                                                       
            return {1, 2}

                                                                                                 
        day_shift_map: dict[int, set[int]] = {}
        for t_id, cls, st in _active_lessons().filter(
            teacher_id__in=candidate_ids,
            day_of_week=day
        ).values_list("teacher_id", "class_group", "start_time"):
            g = extract_grade(cls)
            sh = infer_shift_by_grade(g)
            if sh is None:
                sh = int(infer_shift_by_time(st))
            day_shift_map.setdefault(t_id, set()).add(int(sh))

                                                              
        repl_time_map: dict[int, list[tuple]] = {}
        existing_repls = (
            _teacher_replacements().filter(date=selected_date, replacement_teacher_id__in=candidate_ids)
            .select_related("lesson")
        )
        for r in existing_repls:
            if not r.lesson:
                continue
            repl_time_map.setdefault(r.replacement_teacher_id, []).append(
                (r.lesson.start_time, r.lesson.end_time, r.lesson.class_group, r.lesson.lesson_number)
            )

                                                 
        base_hours_map = dict(
            _active_lessons().filter(teacher_id__in=candidate_ids)
            .values("teacher_id")
            .annotate(c=Count("id"))
            .values_list("teacher_id", "c")
        )
        week_repl_hours_map = dict(
            _teacher_replacements().filter(replacement_teacher_id__in=candidate_ids, date__range=(start_of_week, end_of_week))
            .values("replacement_teacher_id")
            .annotate(c=Count("id"))
            .values_list("replacement_teacher_id", "c")
        )

                            
        suggestions = []

                                     
        parallel_lessons = _active_lessons().filter(
            class_group=lesson.class_group,
            lesson_number=lesson.lesson_number,
            day_of_week=lesson.day_of_week
        ).exclude(teacher=original_teacher)

        if parallel_lessons.exists():
            parallel_teacher = parallel_lessons.first().teacher
            if parallel_teacher and not _is_vacancy_teacher_name(parallel_teacher.full_name):
                base_hours = _active_lessons().filter(teacher=parallel_teacher).count()
                replacement_hours = _teacher_replacements().filter(
                    replacement_teacher=parallel_teacher,
                    date__range=(start_of_week, end_of_week)
                ).count()

                                                                                                              
                conflict = False
                for r in _teacher_replacements().filter(
                    date=selected_date,
                    replacement_teacher=parallel_teacher,
                ).exclude(lesson_id=lesson.id).select_related('lesson'):
                    l2 = r.lesson
                    if not l2:
                        continue
                    if overlaps(lesson.start_time, lesson.end_time, l2.start_time, l2.end_time):
                        if not (l2.class_group == lesson.class_group and l2.lesson_number == lesson.lesson_number):
                            conflict = True
                            break

                suggestions.append({
                    "id": parallel_teacher.id,
                    "name": parallel_teacher.full_name,
                    "status": "Урок",
                    "compatibility": "Вторая группа",
                    "hours": base_hours + replacement_hours,
                    "auto_allowed": True,
                    "grade_ok": True,
                    "shift_ok": True,                                          
                    "no_lessons_shift": False,
                    "conflict": conflict,
                })

                               
        for t in replacements:
            if any(s["id"] == t.id for s in suggestions):
                continue                                    

            level = teacher_level(t.id)
            lesson_is_primary = lesson_grade is not None and lesson_grade <= 4
            grade_ok = False
            if lesson_grade is not None:
                if lesson_is_primary:
                    grade_ok = level in ("1-4", "1-11")
                else:
                    grade_ok = level in ("5-11", "1-11")

            teacher_day_shifts = day_shift_map.get(t.id, set())
            teacher_shifts = teacher_day_shifts if teacher_day_shifts else teacher_base_shifts(t.id)
            shift_ok = bool(teacher_shifts) and (int(target_shift) in set(map(int, teacher_shifts)))

                                                                                              
                                                            
            no_lessons_shift = int(target_shift) not in set(map(int, teacher_day_shifts or []))

                                                             
            conflict = False
            for (s, e, cls, num) in repl_time_map.get(t.id, []):
                if overlaps(lesson.start_time, lesson.end_time, s, e):
                                                                                 
                    if not (cls == lesson.class_group and num == lesson.lesson_number):
                        conflict = True
                        break

            auto_allowed = bool(grade_ok and shift_ok and not conflict and not no_lessons_shift)

            base_hours = base_hours_map.get(t.id, 0)
            replacement_hours = week_repl_hours_map.get(t.id, 0)

            compatibility = "Специализация" if t.is_specialized else "Свободен"

            suggestions.append({
                "id": t.id,
                "name": t.full_name,
                                                                                                                        
                "status": "Урок" if conflict else "Свободен",
                "compatibility": compatibility,
                "hours": base_hours + replacement_hours,
                "auto_allowed": auto_allowed,
                "grade_profile": level,
                "grade_ok": grade_ok,
                "shift_ok": shift_ok,
                "no_lessons_shift": no_lessons_shift,
                "conflict": conflict,
                "teacher_shifts": sorted(list(teacher_shifts)) if teacher_shifts else [],
                "teacher_day_shifts": sorted(list(teacher_day_shifts)) if teacher_day_shifts else [],
            })

                                    
        compatibility_order = {"Вторая группа": 0, "Специализация": 1, "Свободен": 2}
                                                                                           
        suggestions.sort(
            key=lambda s: (
                compatibility_order.get(s["compatibility"], 99),
                0 if s.get("auto_allowed") else 1,
                str(s.get("name") or "").casefold(),
            )
        )

        return JsonResponse({"suggestions": suggestions})

    except Http404:
        return JsonResponse({"error": "Урок не найден"}, status=404)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Некорректные параметры запроса"}, status=400)
    except DatabaseError as e:
        logger.error(f"Ошибка БД в get_suggestions: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Внутренняя ошибка"}, status=500)



@login_required
def get_saved_replacements_service(request):
    if not (request.user.is_superuser or _is_guest_user(request.user) or getattr(request.user, 'can_calendar', False)):
        return HttpResponse("Forbidden", status=403)

    date = request.GET.get('date')
    if not date:
        return JsonResponse({"error": "Параметр date обязателен"}, status=400)

    if _use_gsheets_backend():
        teacher_map = _gs_teacher_map()
        lesson_map = _gs_lesson_map()

        replacements_data = []
        for repl in _gs_store().get_table_dicts("replacements_replacement"):
            if str(repl.get("date") or "") != date:
                continue
            if not _gs_is_teacher_replacement(repl):
                continue
            lesson_id = as_int(repl.get("lesson_id"))
            original_id = as_int(repl.get("original_teacher_id"))
            replacement_id = as_int(repl.get("replacement_teacher_id"))
            if lesson_id is None or original_id is None or replacement_id is None:
                continue
            if lesson_id not in lesson_map:
                continue
            if original_id not in teacher_map or replacement_id not in teacher_map:
                continue
            replacements_data.append({
                "lesson_id": lesson_id,
                "original_id": original_id,
                "teacher_id": replacement_id,
                "date": date,
                "confirmed": as_bool(repl.get("confirmed")),
                "classroom": (repl.get("replacement_classroom") or None),
                "production_necessity": as_bool(repl.get("production_necessity")),
                "ignore_in_reports": as_bool(repl.get("ignore_in_reports")),
            })

        special_data = []
        for sr in _gs_store().get_table_dicts("replacements_special_replacement"):
            if str(sr.get("date") or "") != date:
                continue
            repl_tid = as_int(sr.get("replacement_teacher_id"))
            orig_tid = as_int(sr.get("original_teacher_id"))
            special_data.append({
                "id": as_int(sr.get("id")),
                "date": date,
                "class_group": str(sr.get("class_group") or ""),
                "subject_name": str(sr.get("subject_name") or ""),
                "lesson_id": as_int(sr.get("lesson_id")),
                "lesson_number": as_int(sr.get("lesson_number")),
                "start": str(sr.get("start_time") or ""),
                "end": str(sr.get("end_time") or ""),
                "classroom": str(sr.get("classroom") or ""),
                "teacher_id": repl_tid,
                "teacher_name": teacher_map.get(repl_tid, "") if repl_tid is not None else "",
                "original_teacher_id": orig_tid,
                "original_teacher_name": teacher_map.get(orig_tid, "") if orig_tid is not None else "",
            })
        return JsonResponse({"replacements": replacements_data, "special_replacements": special_data})

    replacements = _teacher_replacements().filter(date=date).select_related(
        'original_teacher',
        'replacement_teacher',
        'lesson'
    )

    replacements_data = []
    for repl in replacements:
        if not (repl.lesson and repl.original_teacher and repl.replacement_teacher):
                                                                         
            continue
        replacements_data.append({
            "lesson_id": repl.lesson.id,
            "original_id": repl.original_teacher.id,
            "teacher_id": repl.replacement_teacher.id,
            "date": repl.date.strftime("%Y-%m-%d"),
            "confirmed": bool(getattr(repl, 'confirmed', False)),
                                                          
            "classroom": getattr(repl, 'replacement_classroom', None),
            "production_necessity": bool(getattr(repl, "production_necessity", False)),
            "ignore_in_reports": bool(getattr(repl, "ignore_in_reports", False)),
        })

    special_repls = SpecialReplacement.objects.filter(date=date).select_related("replacement_teacher", "original_teacher")
    special_data = [
        {
            "id": sr.id,
            "date": sr.date.strftime("%Y-%m-%d"),
            "class_group": sr.class_group,
            "subject_name": sr.subject_name,
            "lesson_id": sr.lesson_id,
            "lesson_number": sr.lesson_number,
            "start": sr.start_time.strftime("%H:%M") if sr.start_time else "",
            "end": sr.end_time.strftime("%H:%M") if sr.end_time else "",
            "classroom": sr.classroom or "",
            "teacher_id": sr.replacement_teacher.id if sr.replacement_teacher else None,
            "teacher_name": sr.replacement_teacher.full_name if sr.replacement_teacher else "",
            "original_teacher_id": sr.original_teacher.id if sr.original_teacher else None,
            "original_teacher_name": sr.original_teacher.full_name if sr.original_teacher else "",
        }
        for sr in special_repls
    ]

    return JsonResponse({"replacements": replacements_data, "special_replacements": special_data})


from django.db.models import Min



