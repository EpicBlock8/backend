import logging
from contextlib import contextmanager

from fastapi import HTTPException

from app.shared import Logger, load_config

__all__ = ["server_error_handler"]

logger = Logger(__name__, level=logging.DEBUG).get_logger()

config = load_config()
endpoint = config.endpoint


@contextmanager
def server_error_handler(stacklevel=1):
    # Go 3 levels up to escape @contextmanager methods and current function
    stack_level = 2 + stacklevel
    kw = {"stacklevel": stack_level}
    try:
        yield

    except Exception as e:
        logger.error("Failed to process request: %s", e, **kw)
        raise HTTPException(status_code=500, detail=str(e)) from e
