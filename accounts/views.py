from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .forms import RegisterForm, LoginForm, UserUpdateForm
from .models import CustomUser
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib import messages

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, 'can_users', False))
def register_view(request):
    """
    Страница регистрации нового пользователя. Доступна только суперпользователю
    или пользователю с правом управления пользователями. После успешной
    регистрации администратор остаётся в своей учётной записи и
    возвращается на список пользователей.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:user_list')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required
def user_list_view(request):
    """
    Список всех пользователей с возможностью редактирования и удаления.
    Доступ разрешён только суперпользователю или пользователю с правом
    управления пользователями.
    """
    if not request.user.is_superuser and not getattr(request.user, 'can_users', False):
        return HttpResponse("Forbidden", status=403)
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'users_list.html', {'users': users})


@login_required
def user_edit_view(request, user_id):
    """
    Форма редактирования пользователя. Позволяет изменять ФИО, пароль и
    флажки доступа. Доступ разрешён только суперпользователю или
    пользователю с правом управления пользователями.
    """
    if not request.user.is_superuser and not getattr(request.user, 'can_users', False):
        return HttpResponse("Forbidden", status=403)
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь успешно обновлён')
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user_obj)
    return render(request, 'user_edit.html', {'form': form, 'user_obj': user_obj})


@login_required
def user_delete_view(request, user_id):
    """
    Удаляет пользователя. Нет подтверждения, так как действие вызывается
    ссылкой «Удалить». Доступ разрешён только суперпользователю или
    пользователю с правом управления пользователями.
    """
    if not request.user.is_superuser and not getattr(request.user, 'can_users', False):
        return HttpResponse("Forbidden", status=403)
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.user == user_obj:
        messages.error(request, 'Нельзя удалить текущего пользователя')
        return redirect('accounts:user_list')
    user_obj.delete()
    messages.success(request, 'Пользователь удалён')
    return redirect('accounts:user_list')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('replacements:main-menu')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
                                                                         
                                                              
    return redirect('accounts:login')
