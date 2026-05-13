import asyncio

import sentry_sdk
import structlog

logger = structlog.getLogger(__name__)


def setup_asyncio_exception_handler():
    loop = asyncio.get_event_loop()

    def handler(loop, context):
        exc = context.get("exception")
        if exc:
            sentry_sdk.capture_exception(exc)
            logger.error("Asyncio unhandled exception", exc_info=exc)
        else:
            sentry_sdk.capture_message(str(context))
            logger.error("Asyncio error", extra=context)

    loop.set_exception_handler(handler)
