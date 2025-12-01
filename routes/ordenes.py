"""
routes/ordenes.py - Endpoints de órdenes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import psycopg2

from models import OrdenCreate, OrdenResponse, UbicacionOrdenResponse, ActualizarEstadoRequest
from services import OrdenesService, ClientesService, TrackingService
from database import get_postgres_connection

router = APIRouter(prefix="/ordenes", tags=["Órdenes"])


@router.post("", response_model=OrdenResponse)
def crear_orden(orden: OrdenCreate):
    """
    Crea una nueva orden con cliente asociado.
    
    **Transacción ACID:**
    - Si el cliente ya existe (por email), se reutiliza
    - Si no existe, se crea uno nuevo
    - Si falla alguna operación, se hace rollback
    """
    conn = None
    cliente_existente = False
    
    try:
        conn = get_postgres_connection()
        conn.autocommit = False
        
        # Buscar cliente existente
        cliente_row = ClientesService.buscar_por_email(orden.cliente.email, conn)
        
        if cliente_row:
            cliente_id = cliente_row[0]
            cliente_existente = True
        else:
            cliente_id = ClientesService.crear(
                orden.cliente.nombre,
                orden.cliente.email,
                orden.cliente.telefono,
                orden.cliente.direccion,
                conn
            )
        
        # Crear orden
        orden_id = OrdenesService.crear(
            cliente_id,
            orden.descripcion,
            orden.direccion_origen,
            orden.direccion_destino,
            conn
        )
        
        conn.commit()
        
        mensaje = "Orden creada (cliente existente)" if cliente_existente else "Orden y cliente creados"
        return OrdenResponse(orden_id=orden_id, cliente_id=cliente_id, mensaje=mensaje)
        
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad: {str(e)}")
    except psycopg2.Error as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    finally:
        if conn: conn.close()


@router.get("")
def listar_ordenes(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    limite: int = Query(10, ge=1, le=100)
):
    """Lista todas las órdenes con filtro opcional por estado"""
    ordenes = OrdenesService.listar(estado, limite)
    return {"total": len(ordenes), "ordenes": ordenes}


@router.get("/{orden_id}")
def obtener_orden(orden_id: int):
    """Obtiene los detalles de una orden específica por ID"""
    orden = OrdenesService.obtener_por_id(orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    return orden


@router.get("/{orden_id}/ubicacion", response_model=UbicacionOrdenResponse)
def obtener_ubicacion_orden(orden_id: int):
    """
    **Consulta Federada:** Combina datos de PostgreSQL y MongoDB.
    
    1. Obtiene detalles de la orden (PostgreSQL)
    2. Obtiene última ubicación (MongoDB)
    """
    orden_data = OrdenesService.obtener_con_cliente(orden_id)
    if not orden_data:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    
    ultima_ubicacion = TrackingService.obtener_ultima_ubicacion(orden_id)
    
    return UbicacionOrdenResponse(orden=orden_data, ultima_ubicacion=ultima_ubicacion)


@router.put("/{orden_id}/estado")
def actualizar_estado_orden(orden_id: int, request: ActualizarEstadoRequest):
    """
    Actualiza el estado de una orden.
    
    **Sincronización:** Si el estado es 'Entregado', desactiva el tracking en MongoDB.
    """
    try:
        actualizado = OrdenesService.actualizar_estado(orden_id, request.estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not actualizado:
        raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
    
    # Sincronización con MongoDB si es "Entregado"
    if request.estado == "Entregado":
        sync = OrdenesService.sincronizar_tracking_entregado(orden_id)
        return {"mensaje": "Estado actualizado y tracking sincronizado", 
                "orden_id": orden_id, "nuevo_estado": request.estado, "sincronizacion": sync}
    
    return {"mensaje": "Estado actualizado", "orden_id": orden_id, "nuevo_estado": request.estado}
