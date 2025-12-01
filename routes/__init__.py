"""
routes - Routers de FastAPI
"""

from .sistema import router as sistema_router
from .ordenes import router as ordenes_router
from .clientes import router as clientes_router
from .tracking import router as tracking_router
from .geoespacial import router as geoespacial_router

__all__ = [
    "sistema_router",
    "ordenes_router",
    "clientes_router",
    "tracking_router",
    "geoespacial_router"
]
