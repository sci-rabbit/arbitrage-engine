import os

from celery import Celery

# Создаем экземпляр Celery приложения
celery_app = Celery(
    "aggregation_service",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6378/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6378/0"),
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Импортируем задачи, чтобы они зарегистрировались
# Это нужно для того, чтобы @shared_task зарегистрировал задачи в celery_app
# Устанавливаем default app для @shared_task
from celery import _state

from tasks import orderbooks  # noqa: F401, E402

_state.set_default_app(celery_app)

