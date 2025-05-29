from collections import deque
from time import monotonic
from typing import TypeVar

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.models.requests import SignedPayload
from app.shared import Logger

logger = Logger(__name__).get_logger()

T = TypeVar("T")


class RateLimit(BaseHTTPMiddleware):
    """Rate Limit middleware for FastApi endpoints
    Based loosely on sliding window rate limiting.
    Compares against IP and username.
    """

    def __init__(self, app, dispatch=None, max_per_second=15, timeout_period_s=60):
        super().__init__(app, dispatch)

        # Params
        self.__max_per_second = max_per_second
        self.__timeout_period_s = timeout_period_s

        self.__func = None

        # Checks
        self.__ip: dict[str, deque[float]] = {}
        self.__user: dict[str, deque[float]] = {}
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

            self.__now = monotonic()
            self.__check_ip(request.client.host)
            self.__check_user(
                SignedPayload.model_validate(await request.json()).username
            )

            return await call_next(request)
        except HTTPException as e:
            return Response(status_code=e.status_code)

    def __check_ip(self, ip: str):
        self.__check(self.__ip, ip)

    def __check_user(self, user: str):
        self.__check(self.__user, user)

    def __check(self, bucket: dict, key: str):
        # record the connection timestamp
        # if property is in timeout; then reject
        # lazyily prune old records
        # after pruning, if records exceeds
        # `max_per_second` then reject

        self.__create_deque(bucket, key)
        self.__timeout_check(key)

        queue = bucket[key]
        queue.append(self.__now)

        while self.__now - queue[0] > 1:
            queue.popleft()

        if len(queue) > self.__max_per_second:
            self.__timeout(key)
            raise HTTPException(status_code=429, detail="Too many requests.")

    @staticmethod
    def __create_deque(bucket: dict, key: str):
        if key not in bucket:
            bucket[key] = deque()

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
