# from .machines import router as _machine_router
# from .metric_types import router as _metric_types_router
# from .metrics import router as _metric_router

# _routers = [_machine_router, _metric_types_router, _metric_router]
from .auth import router as auth_router
from .files import router as files_router
from .x3dh import router as x3dh_router

_routers = [auth_router, files_router, x3dh_router]

__all__ = ["get_routers"]


def get_routers():
    return _routers
