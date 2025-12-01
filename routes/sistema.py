"""
routes/sistema.py - Endpoints del sistema
"""

from fastapi import APIRouter
from database import get_postgres_connection, get_mongo_database

router = APIRouter(prefix="", tags=["Sistema"])


@router.get("/")
def root():
    """Información general de la API y endpoints disponibles"""
    return {
        "nombre": "HybridLogisticsHub API",
        "version": "1.0.0",
        "endpoints": {
            "ordenes": {
                "crear": "POST /ordenes",
                "listar": "GET /ordenes",
                "ubicacion": "GET /ordenes/{orden_id}/ubicacion",
                "actualizar_estado": "PUT /ordenes/{orden_id}/estado"
            },
            "clientes": {
                "listar": "GET /clientes",
                "detalle": "GET /clientes/{cliente_id}"
            },
            "tracking": {
                "registrar": "POST /tracking/{orden_id}",
                "historial": "GET /tracking/{orden_id}/historial",
                "estadisticas": "GET /tracking/{orden_id}/estadisticas",
                "eliminar": "DELETE /tracking/{orden_id}"
            },
            "geoespacial": {
                "busqueda_cercana": "GET /busqueda-cercana"
            },
            "sistema": {
                "health": "GET /health",
                "documentacion": "GET /docs"
            }
        }
    }


@router.get("/health")
def health_check():
    """Verifica el estado de las conexiones a las bases de datos"""
    status = {"api": "ok", "postgresql": "error", "mongodb": "error"}
    
    # Verificar PostgreSQL
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.close()
        conn.close()
        status["postgresql"] = "ok"
    except Exception as e:
        status["postgresql_error"] = str(e)
    
    # Verificar MongoDB
    try:
        db = get_mongo_database()
        db.command("ping")
        status["mongodb"] = "ok"
    except Exception as e:
        status["mongodb_error"] = str(e)
    
    return status
