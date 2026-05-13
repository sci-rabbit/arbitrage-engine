"""
Test configuration for update_orderbooks_service.

Settings are satisfied via env vars set here (before any module-level
`settings = Settings()` is triggered by an import).
A minimal Celery app is created so @shared_task tasks can bind to it.
"""
import os

os.environ.setdefault("KALSHI__ACCESS_KEY", "test_key")
os.environ.setdefault("KALSHI__PRIVATE_KEY_PATH", "test.pem")
os.environ.setdefault("PREDICT_FUN__API_KEY", "test_api_key")
os.environ.setdefault("DB__USER", "test")
os.environ.setdefault("DB__PASSWORD", "test")
os.environ.setdefault("DB__HOST", "localhost")
os.environ.setdefault("DB__PORT", "5432")
os.environ.setdefault("DB__NAME", "test")

from celery import Celery  # noqa: E402 — must come after env vars

celery_test_app = Celery("tests", broker="memory://localhost//")
celery_test_app.conf.update(task_always_eager=True, task_always_eager_propagates=True)
