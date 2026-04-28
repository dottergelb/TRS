from __future__ import annotations

import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .forms import LoginForm, RegisterForm, UserUpdateForm
from .models import CustomUser


def _can_manage_users(user) -> bool:
    return bool(
        user.is_authenticated
        and not getattr(user, "is_guest", False)
        and (
            user.is_superuser
            or getattr(user, "is_admin", False)
            or getattr(user, "can_users", False)
        )
    )


@login_required
@user_passes_test(_can_manage_users)
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("accounts:user_list")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})


@login_required
def user_list_view(request):
    if not _can_manage_users(request.user):
        return HttpResponse("Forbidden", status=403)
    users = CustomUser.objects.all().order_by("username")
    return render(request, "users_list.html", {"users": users})


@login_required
@require_POST
def export_teacher_credentials_view(request):
    if not _can_manage_users(request.user):
        return HttpResponse("Forbidden", status=403)

    users = list(CustomUser.objects.filter(is_teacher=True).order_by("full_name", "username"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="teacher_accounts_{ts}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["full_name", "username"])
    for user in users:
        writer.writerow([user.full_name or "", user.username or ""])
    return response


@login_required
def user_edit_view(request, user_id):
    if not _can_manage_users(request.user):
        return HttpResponse("Forbidden", status=403)

    user_obj = get_object_or_404(CustomUser, id=user_id)
    if getattr(user_obj, "is_admin", False) and not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403)
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user_obj, actor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Пользователь успешно обновлен")
            return redirect("accounts:user_list")
    else:
        form = UserUpdateForm(instance=user_obj, actor=request.user)

    return render(request, "user_edit.html", {"form": form, "user_obj": user_obj})


@login_required
@require_POST
def user_delete_view(request, user_id):
    if not _can_manage_users(request.user):
        return HttpResponse("Forbidden", status=403)

    user_obj = get_object_or_404(CustomUser, id=user_id)
    if getattr(user_obj, "is_admin", False) and not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403)
    if request.user == user_obj:
        messages.error(request, "Нельзя удалить текущего пользователя")
        return redirect("accounts:user_list")

    user_obj.delete()
    messages.success(request, "Пользователь удален")
    return redirect("accounts:user_list")


@ratelimit(key="ip", rate="20/m", block=True, method="POST")
def login_view(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("replacements:main-menu")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")
