"""
models/schemas.py - Modelos Pydantic para validación de datos
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==============================================================================
# MODELOS DE CLIENTES
# ==============================================================================

class ClienteCreate(BaseModel):
    """Datos para crear un cliente"""
    nombre: str = Field(..., min_length=2, max_length=100, example="Juan Pérez")
    email: str = Field(..., example="juan.perez@email.com")
    telefono: Optional[str] = Field(None, example="+57 300 123 4567")
    direccion: Optional[str] = Field(None, example="Calle 123 #45-67, Bogotá")


# ==============================================================================
# MODELOS DE ÓRDENES
# ==============================================================================

class OrdenCreate(BaseModel):
    """Datos para crear una orden con cliente"""
    cliente: ClienteCreate
    descripcion: str = Field(..., example="Paquete electrónico")
    direccion_origen: str = Field(..., example="Bodega Central, Bogotá")
    direccion_destino: str = Field(..., example="Calle 80 #15-30, Medellín")


class OrdenResponse(BaseModel):
    """Respuesta al crear una orden"""
    orden_id: int
    cliente_id: int
    mensaje: str


class ActualizarEstadoRequest(BaseModel):
    """Datos para actualizar estado de orden"""
    estado: str = Field(..., example="Entregado")


# ==============================================================================
# MODELOS DE TRACKING
# ==============================================================================

class TrackingCreate(BaseModel):
    """Datos para registrar ubicación GPS"""
    latitud: float = Field(..., ge=-90, le=90, example=4.7110)
    longitud: float = Field(..., ge=-180, le=180, example=-74.0721)
    timestamp: Optional[datetime] = Field(None)
    velocidad_kmh: Optional[float] = Field(None, ge=0, example=60.5)
    dispositivo_id: Optional[str] = Field(None, example="GPS-001")


class TrackingResponse(BaseModel):
    """Respuesta al registrar tracking"""
    tracking_id: str
    orden_id: int
    mensaje: str


# ==============================================================================
# MODELOS DE CONSULTAS FEDERADAS
# ==============================================================================

class UbicacionOrdenResponse(BaseModel):
    """Respuesta de consulta federada (orden + ubicación)"""
    orden: dict
    ultima_ubicacion: Optional[dict]


class BusquedaCercanaResponse(BaseModel):
    """Respuesta de búsqueda geoespacial"""
    ordenes_encontradas: int
    resultados: List[dict]
