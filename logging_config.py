import logging
from loguru import logger
from config import LOG_DIR


class _InterceptHandler(logging.Handler):
    """Route standard-library logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Find the loguru level that matches the record's level name/number
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk the call stack to find the original log site outside this handler
        frame, depth = logging.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru as the single logging sink for the application."""
    # Replace every handler on the root logger (and key uvicorn loggers) with ours
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.DEBUG, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [_InterceptHandler()]
        log.propagate = False

    # Log to a rotating file outside the project dir so watchfiles doesn't pick it up
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "app.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        level="DEBUG",
        enqueue=True,  # non-blocking, safe for async code
    )
