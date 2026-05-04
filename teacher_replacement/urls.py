from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from accounts.views import entry_view
from . import health
from replacements import views_schedule

urlpatterns = [
    path('admin/', admin.site.urls),
    path("health/live/", health.liveness, name="health-live"),
    path("health/ready/", health.readiness, name="health-ready"),
    path('', entry_view, name='root-entry'),
    path('schedule/', views_schedule.class_schedule_view, name='schedule-legacy'),
    path('upload/', views_schedule.upload, name='upload-legacy'),
    path('upload/schedule/', views_schedule.upload_schedule_view, name='upload-schedule-legacy'),
    path('', include('accounts.urls')),
    path('comm/', include('communications.urls')),
    path('replacements/', include('replacements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
