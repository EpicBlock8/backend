from .files import router as files_router
from .x3dh import router as x3dh_router
from .auth import router as auth_router

_routers = [auth_router, files_router, x3dh_router]

__all__ = ["get_routers"]


def get_routers():
    return _routers
