import os
from django.core.wsgi import get_wsgi_application

# Убедитесь, что имя модуля совпадает с вашим проектом
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teacher_replacement.settings')
application = get_wsgi_application()