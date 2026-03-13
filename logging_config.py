import logging
import sys
from loguru import logger
from config import LOG_DIR


def _get_port() -> str:
    """Extract --port value from the CLI args uvicorn was started with."""
    args = sys.argv
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--port="):
            return arg.split("=", 1)[1]
    return "8000"  # uvicorn default


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
    port = _get_port()
    logger.add(
        LOG_DIR / f"app_port_{port}.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        level="DEBUG",
        enqueue=True,  # non-blocking, safe for async code
    )
