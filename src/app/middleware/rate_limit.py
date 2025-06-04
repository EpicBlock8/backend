from collections import deque
from time import monotonic

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.shared import Config, Logger, load_config

logger = Logger(__name__).get_logger()
config: Config = load_config()
config_rate_limit = config.network.rate_limit


class RateLimit(BaseHTTPMiddleware):
    """Rate Limit middleware for FastApi endpoints
    Based loosely on sliding window rate limiting.
    Compares against IP and username.
    """

    def __init__(
        self,
        app,
        dispatch=None,
        timeout_period_s=config_rate_limit.timeout_period,
        max_per_second=config_rate_limit.requests_per_second,
    ):
        super().__init__(app, dispatch)

        # Params
        self.__max_per_second = max_per_second
        self.__timeout_period_s = timeout_period_s

        # Checks
        self.__bucket: dict[str, deque[float]] = {}
        self.__timeout_club: dict[str, float] = {}

        # Time
        self.__now = monotonic()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            assert request.client is not None

            # Skip rate limiting for OPTIONS requests (CORS preflight)
            if request.method == "OPTIONS":
                return await call_next(request)

            self.__now = monotonic()
            self.__check(request.client.host)

            return await call_next(request)
        except HTTPException as e:
            return Response(status_code=e.status_code)

    def __check(self, key: str):
        # record the connection timestamp
        # if property is in timeout; then reject
        # lazyily prune old records
        # after pruning, if records exceeds
        # `max_per_second` then reject

        self.__create_deque(key)
        self.__timeout_check(key)

        queue = self.__bucket[key]
        queue.append(self.__now)

        while self.__now - queue[0] > 1:
            queue.popleft()

        if len(queue) > self.__max_per_second:
            self.__timeout(key)
            raise HTTPException(status_code=429, detail="Too many requests.")

    def __create_deque(self, key: str):
        if key not in self.__bucket:
            self.__bucket[key] = deque()

    def __timeout_check(self, key: str):
        if key not in self.__timeout_club:
            return

        timeout_timestamp = self.__timeout_club[key]

        if self.__now - timeout_timestamp > self.__timeout_period_s:
            del self.__timeout_club[key]
        else:
            raise HTTPException(status_code=429, detail="Too many requests.")

    def __timeout(self, key: str):
        self.__timeout_club[key] = monotonic()
