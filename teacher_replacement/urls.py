from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from accounts.views import login_view
from replacements.views import class_schedule_view
from replacements.views import upload, clear_schedule, upload_schedule_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='root-login'),
    path('', include('accounts.urls')),  # теперь всё будет прямо в корне: /register/, /login/
    path('replacements/', include('replacements.urls')),
path('schedule/', class_schedule_view, name='class_schedule'),
path("upload/", upload, name="upload"),
path("upload/schedule/", upload_schedule_view, name="upload_schedule_view"),
    path("upload/clear/", clear_schedule, name="clear_schedule"),
]
