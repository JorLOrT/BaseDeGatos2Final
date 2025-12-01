"""
main.py - API RESTful con FastAPI para HybridLogisticsHub
Sistema de logística con arquitectura de bases de datos híbrida
PostgreSQL (transaccional) + MongoDB (geoespacial/tracking)
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    sistema_router,
    ordenes_router,
    clientes_router,
    tracking_router,
    geoespacial_router
)


# ==============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ==============================================================================

app = FastAPI(
    title="HybridLogisticsHub API",
    description="""
    API de logística con arquitectura híbrida:
    - **PostgreSQL**: Datos transaccionales (clientes, órdenes)
    - **MongoDB**: Datos geoespaciales y tracking en tiempo real
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS para permitir acceso desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos (visualizador de tracking)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==============================================================================
# REGISTRO DE ROUTERS
# ==============================================================================

app.include_router(sistema_router)
app.include_router(ordenes_router)
app.include_router(clientes_router)
app.include_router(tracking_router)
app.include_router(geoespacial_router)


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
