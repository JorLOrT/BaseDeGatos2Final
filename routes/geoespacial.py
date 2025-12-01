"""
routes/geoespacial.py - Endpoints de búsquedas geoespaciales
"""

from fastapi import APIRouter, HTTPException, Query
from models import BusquedaCercanaResponse
from services import GeoespacialService

router = APIRouter(tags=["Geoespacial"])


@router.get("/busqueda-cercana", response_model=BusquedaCercanaResponse)
def busqueda_cercana(
    latitud: float = Query(..., ge=-90, le=90, example=4.7110),
    longitud: float = Query(..., ge=-180, le=180, example=-74.0721),
    radio_metros: float = Query(1000, gt=0, example=5000)
):
    """
    Busca órdenes activas dentro de un radio específico.
    
    Utiliza el índice geoespacial 2dsphere de MongoDB.
    """
    try:
        resultados = GeoespacialService.buscar_cercanos(latitud, longitud, radio_metros)
        return BusquedaCercanaResponse(ordenes_encontradas=len(resultados), resultados=resultados)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error geoespacial: {str(e)}")
