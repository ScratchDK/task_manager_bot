from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings


# Устанавливаем переменную окружения для настроек (не обязательно, но для ясности)
os.environ.setdefault("FASTAPI_SETTINGS_MODULE", "app.core.config")

# Создаем экземпляр Celery
celery_app = Celery(
    "task_manager_bot",
    broker=settings.CELERY_BROKER_URL,  # Указываем брокер
    backend=settings.CELERY_RESULT_BACKEND,  # Указываем бэкенд
)

# Загружаем настройки из объекта конфигурации
celery_app.config_from_object("app.core.config", namespace="CELERY")

# Автоматически находим задачи в файлах tasks.py
celery_app.autodiscover_tasks(["app"], related_name="celery_tasks")

# 🔥 Настройка периодических задач (Celery Beat)
celery_app.conf.beat_schedule = {
    "check-deadlines-every-hour": {
        "task": "app.celery_tasks.check_deadlines",
        "schedule": crontab(minute=0, hour="*"),  # Каждый час
    },
    "check-inactive-assignees-every-hour": {  # ← Новая задача
        "task": "app.celery_tasks.check_inactive_assignees",
        "schedule": crontab(minute=0, hour="*"),  # Каждый час
    },
    "check-upcoming-deadlines-every-15-minutes": {
        "task": "app.celery_tasks.check_upcoming_deadlines",
        "schedule": crontab(minute="*/15"),
    },
}

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True


# celery -A config purge    Очистить очередь
# celery -A config.celery worker --pool=solo -l INFO
# celery -A config.celery beat -l INFO
