import asyncio
import time
from collections import defaultdict

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from core.config import settings

_WINDOW_SECONDS = 60
_MAX_EVENTS_PER_TYPE = 50

_error_counter = defaultdict(int)
_window_started_at = time.time()


def before_send(event, hint):
    global _window_started_at

    now = time.time()
    if now - _window_started_at > _WINDOW_SECONDS:
        _window_started_at = now
        _error_counter.clear()

    exc_info = hint.get("exc_info")
    exc_type = exc_info[0] if exc_info else None

    if exc_type and issubclass(exc_type, asyncio.CancelledError):
        return None

    exc_name = exc_type.__name__ if exc_type else "unknown"
    _error_counter[exc_name] += 1

    if _error_counter[exc_name] > _MAX_EVENTS_PER_TYPE:
        return None

    return event


def setup_sentry() -> None:
    cfg = settings.sentry

    if not cfg.enabled or not cfg.dsn or cfg.environment == "local":
        return

    sentry_sdk.init(
        dsn=cfg.dsn,
        environment=cfg.environment,
        release=cfg.release or None,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
        sample_rate=cfg.sample_rate,
        traces_sample_rate=cfg.traces_sample_rate,
        profiles_sample_rate=0.0,
        send_default_pii=False,
        attach_stacktrace=True,
        max_breadcrumbs=50,
        shutdown_timeout=2,
        before_send=before_send,
    )

    sentry_sdk.set_tag("service", "arbitrage-engine")
