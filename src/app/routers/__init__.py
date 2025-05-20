# from .machines import router as _machine_router
# from .metric_types import router as _metric_types_router
# from .metrics import router as _metric_router

# _routers = [_machine_router, _metric_types_router, _metric_router]

_routers = []

__all__ = ["get_routers"]


def get_routers():
    return _routers
