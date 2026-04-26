from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from accounts.views import login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='root-login'),
    path('', include('accounts.urls')),
    path('comm/', include('communications.urls')),
    path('replacements/', include('replacements.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
