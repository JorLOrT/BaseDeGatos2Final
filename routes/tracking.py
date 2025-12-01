"""
routes/tracking.py - Endpoints de tracking GPS
"""

from fastapi import APIRouter, HTTPException, Query
from models import TrackingCreate, TrackingResponse
from services import TrackingService, OrdenesService

router = APIRouter(prefix="/tracking", tags=["Tracking"])


@router.post("/{orden_id}", response_model=TrackingResponse)
def registrar_tracking(orden_id: int, tracking: TrackingCreate):
    """
    Registra coordenadas GPS para una orden.
    
    Almacena en MongoDB con formato GeoJSON para búsquedas geoespaciales.
    """
    # Verificar que la orden existe
    orden = OrdenesService.verificar_existe(orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    
    try:
        tracking_id = TrackingService.registrar(
            orden_id,
            tracking.latitud,
            tracking.longitud,
            tracking.timestamp,
            tracking.velocidad_kmh,
            tracking.dispositivo_id
        )
        
        return TrackingResponse(
            tracking_id=tracking_id,
            orden_id=orden_id,
            mensaje="Ubicación registrada"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error MongoDB: {str(e)}")


@router.get("/{orden_id}/historial")
def obtener_historial_tracking(
    orden_id: int,
    limite: int = Query(50, ge=1, le=500)
):
    """Obtiene el historial completo de ubicaciones de una orden"""
    orden = OrdenesService.verificar_existe(orden_id, "id, descripcion, estado")
    if not orden:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    
    historial = TrackingService.obtener_historial(orden_id, limite)
    
    return {
        "orden_id": orden_id,
        "descripcion": orden[1],
        "estado": orden[2],
        "total_registros": len(historial),
        "historial": historial
    }


@router.get("/{orden_id}/estadisticas")
def obtener_estadisticas_tracking(orden_id: int):
    """Calcula estadísticas de la ruta: velocidad promedio, tiempo en tránsito, etc."""
    orden = OrdenesService.verificar_existe(orden_id, "id, descripcion, estado")
    if not orden:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    
    stats = TrackingService.obtener_estadisticas(orden_id)
    
    return {
        "orden_id": orden_id,
        "descripcion": orden[1],
        "estado": orden[2],
        **stats
    }


@router.delete("/{orden_id}")
def eliminar_tracking(orden_id: int):
    """Elimina todos los registros de tracking de una orden"""
    deleted_count = TrackingService.eliminar(orden_id)
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No hay tracking para orden {orden_id}")
    
    return {"mensaje": "Tracking eliminado", "orden_id": orden_id, "registros_eliminados": deleted_count}
