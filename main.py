"""
main.py - API RESTful con FastAPI para HybridLogisticsHub
Sistema de logística con arquitectura de bases de datos híbrida
PostgreSQL (transaccional) + MongoDB (geoespacial/tracking)
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import psycopg2
from psycopg2 import sql

from db import (
    get_postgres_connection,
    get_tracking_collection,
    get_mongo_database
)

# ==================== CONFIGURACIÓN DE LA APP ====================

app = FastAPI(
    title="HybridLogisticsHub API",
    description="""
    API de logística con arquitectura híbrida:
    - PostgreSQL: Datos transaccionales (clientes, órdenes)
    - MongoDB: Datos geoespaciales y tracking en tiempo real
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==================== MODELOS PYDANTIC ====================

class ClienteCreate(BaseModel):
    """Modelo para crear un cliente"""
    nombre: str = Field(..., min_length=2, max_length=100, example="Juan Pérez")
    email: str = Field(..., example="juan.perez@email.com")
    telefono: Optional[str] = Field(None, example="+57 300 123 4567")
    direccion: Optional[str] = Field(None, example="Calle 123 #45-67, Bogotá")


class OrdenCreate(BaseModel):
    """Modelo para crear una orden con cliente asociado"""
    cliente: ClienteCreate
    descripcion: str = Field(..., example="Paquete electrónico")
    direccion_origen: str = Field(..., example="Bodega Central, Bogotá")
    direccion_destino: str = Field(..., example="Calle 80 #15-30, Medellín")


class OrdenResponse(BaseModel):
    """Respuesta al crear una orden"""
    orden_id: int
    cliente_id: int
    mensaje: str


class TrackingCreate(BaseModel):
    """Modelo para registrar ubicación GPS"""
    latitud: float = Field(..., ge=-90, le=90, example=4.7110)
    longitud: float = Field(..., ge=-180, le=180, example=-74.0721)
    timestamp: Optional[datetime] = Field(None, description="Timestamp UTC, se genera automáticamente si no se proporciona")
    velocidad_kmh: Optional[float] = Field(None, ge=0, example=60.5)
    dispositivo_id: Optional[str] = Field(None, example="GPS-001")


class TrackingResponse(BaseModel):
    """Respuesta al registrar tracking"""
    tracking_id: str
    orden_id: int
    mensaje: str


class UbicacionOrdenResponse(BaseModel):
    """Respuesta combinada de orden y ubicación (consulta federada)"""
    orden: dict
    ultima_ubicacion: Optional[dict]


class ActualizarEstadoRequest(BaseModel):
    """Modelo para actualizar estado de orden"""
    estado: str = Field(..., example="Entregado")


class BusquedaCercanaResponse(BaseModel):
    """Respuesta de búsqueda por proximidad"""
    ordenes_encontradas: int
    resultados: List[dict]


# ==================== FUNCIONES AUXILIARES ====================

def verificar_orden_existe(orden_id: int, campos: str = "id, descripcion, estado") -> tuple:
    """
    Verifica si una orden existe y retorna sus datos.
    Lanza HTTPException 404 si no existe.
    
    Args:
        orden_id: ID de la orden a verificar
        campos: Campos SQL a retornar (default: id, descripcion, estado)
    
    Returns:
        Tupla con los datos de la orden
    """
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {campos} FROM ordenes WHERE id = %s;", (orden_id,))
    orden = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not orden:
        raise HTTPException(
            status_code=404,
            detail=f"Orden con ID {orden_id} no encontrada"
        )
    
    return orden


def verificar_cliente_existe(cliente_id: int) -> tuple:
    """
    Verifica si un cliente existe y retorna sus datos.
    Lanza HTTPException 404 si no existe.
    """
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, email FROM clientes WHERE id = %s;", (cliente_id,))
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not cliente:
        raise HTTPException(
            status_code=404,
            detail=f"Cliente con ID {cliente_id} no encontrado"
        )
    
    return cliente


# ==================== ENDPOINTS ====================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz con información de la API"""
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


# ==================== POST /ordenes ====================
@app.post("/ordenes", response_model=OrdenResponse, tags=["Órdenes"])
async def crear_orden(orden: OrdenCreate):
    """
    Crea una nueva orden con su cliente asociado.
    
    **Implementa transacciones ACID con psycopg2:**
    - Si el cliente ya existe (por email), se reutiliza
    - Si no existe, se crea uno nuevo
    - Si falla alguna operación, se hace rollback
    """
    conn = None
    cliente_existente = False
    try:
        conn = get_postgres_connection()
        # Desactivar autocommit para manejar transacción manualmente
        conn.autocommit = False
        cursor = conn.cursor()
        
        # PASO 1: Verificar si el cliente ya existe (por email)
        cursor.execute("""
            SELECT id, nombre FROM clientes WHERE email = %s;
        """, (orden.cliente.email,))
        
        cliente_row = cursor.fetchone()
        
        if cliente_row:
            # Cliente ya existe, reutilizarlo
            cliente_id = cliente_row[0]
            cliente_existente = True
        else:
            # Cliente no existe, crearlo
            cursor.execute("""
                INSERT INTO clientes (nombre, email, telefono, direccion)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (
                orden.cliente.nombre,
                orden.cliente.email,
                orden.cliente.telefono,
                orden.cliente.direccion
            ))
            cliente_id = cursor.fetchone()[0]
        
        # PASO 2: Insertar orden vinculada al cliente
        cursor.execute("""
            INSERT INTO ordenes (cliente_id, descripcion, estado, direccion_origen, direccion_destino)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            cliente_id,
            orden.descripcion,
            "Pendiente",  # Estado inicial
            orden.direccion_origen,
            orden.direccion_destino
        ))
        
        orden_id = cursor.fetchone()[0]
        
        # COMMIT: Operaciones exitosas
        conn.commit()
        
        mensaje = "Orden creada (cliente existente reutilizado)" if cliente_existente else "Orden y cliente creados exitosamente"
        
        return OrdenResponse(
            orden_id=orden_id,
            cliente_id=cliente_id,
            mensaje=mensaje
        )
        
    except psycopg2.IntegrityError as e:
        # ROLLBACK: Error de integridad (ej. email duplicado)
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad: {str(e)}"
        )
    except psycopg2.Error as e:
        # ROLLBACK: Cualquier error de base de datos
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error en la base de datos: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


# ==================== POST /tracking/{orden_id} ====================
@app.post("/tracking/{orden_id}", response_model=TrackingResponse, tags=["Tracking"])
async def registrar_tracking(orden_id: int, tracking: TrackingCreate):
    """
    Registra coordenadas GPS para una orden.
    
    Los datos se almacenan en MongoDB con formato GeoJSON
    para permitir búsquedas geoespaciales eficientes.
    """
    # Verificar que la orden existe
    verificar_orden_existe(orden_id)
    
    # Insertar documento de tracking en MongoDB
    try:
        tracking_collection = get_tracking_collection()
        
        # Estructura GeoJSON para el campo ubicacion
        documento = {
            "orden_id": orden_id,
            "ubicacion": {
                "type": "Point",
                "coordinates": [tracking.longitud, tracking.latitud]  # GeoJSON: [lng, lat]
            },
            "timestamp": tracking.timestamp or datetime.utcnow(),
            "activo": True,  # Flag de sincronización
            "velocidad_kmh": tracking.velocidad_kmh,
            "metadata": {
                "dispositivo_id": tracking.dispositivo_id,
                "precision_metros": None
            }
        }
        
        result = tracking_collection.insert_one(documento)
        
        return TrackingResponse(
            tracking_id=str(result.inserted_id),
            orden_id=orden_id,
            mensaje="Ubicación registrada exitosamente"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar tracking en MongoDB: {str(e)}"
        )


# ==================== GET /ordenes/{orden_id}/ubicacion ====================
@app.get("/ordenes/{orden_id}/ubicacion", response_model=UbicacionOrdenResponse, tags=["Consultas Federadas"])
async def obtener_ubicacion_orden(orden_id: int):
    """
    **Consulta Federada:** Obtiene información combinada de PostgreSQL y MongoDB.
    
    1. Busca detalles de la orden en PostgreSQL
    2. Busca la última ubicación conocida en MongoDB
    3. Retorna un objeto JSON combinado
    """
    # PASO 1: Obtener detalles de la orden desde PostgreSQL
    conn = None
    orden_data = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.descripcion, o.estado, o.direccion_origen, o.direccion_destino,
                   o.fecha_creacion, o.fecha_actualizacion,
                   c.id as cliente_id, c.nombre as cliente_nombre, c.email as cliente_email
            FROM ordenes o
            JOIN clientes c ON o.cliente_id = c.id
            WHERE o.id = %s;
        """, (orden_id,))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Orden con ID {orden_id} no encontrada"
            )
        
        orden_data = {
            "id": row[0],
            "descripcion": row[1],
            "estado": row[2],
            "direccion_origen": row[3],
            "direccion_destino": row[4],
            "fecha_creacion": row[5].isoformat() if row[5] else None,
            "fecha_actualizacion": row[6].isoformat() if row[6] else None,
            "cliente": {
                "id": row[7],
                "nombre": row[8],
                "email": row[9]
            }
        }
        
        cursor.close()
    finally:
        if conn:
            conn.close()
    
    # PASO 2: Obtener última ubicación desde MongoDB
    ultima_ubicacion = None
    try:
        tracking_collection = get_tracking_collection()
        
        # Buscar el documento más reciente para esta orden
        tracking_doc = tracking_collection.find_one(
            {"orden_id": orden_id},
            sort=[("timestamp", -1)]  # Ordenar por timestamp descendente
        )
        
        if tracking_doc:
            coords = tracking_doc.get("ubicacion", {}).get("coordinates", [])
            ultima_ubicacion = {
                "latitud": coords[1] if len(coords) > 1 else None,
                "longitud": coords[0] if len(coords) > 0 else None,
                "timestamp": tracking_doc.get("timestamp").isoformat() if tracking_doc.get("timestamp") else None,
                "activo": tracking_doc.get("activo"),
                "velocidad_kmh": tracking_doc.get("velocidad_kmh")
            }
            
    except Exception as e:
        # Si falla MongoDB, devolvemos la orden sin ubicación
        print(f"Advertencia: Error obteniendo tracking de MongoDB: {e}")
    
    # PASO 3: Retornar respuesta combinada
    return UbicacionOrdenResponse(
        orden=orden_data,
        ultima_ubicacion=ultima_ubicacion
    )


# ==================== GET /busqueda-cercana ====================
@app.get("/busqueda-cercana", response_model=BusquedaCercanaResponse, tags=["Búsqueda Geoespacial"])
async def busqueda_cercana(
    latitud: float = Query(..., ge=-90, le=90, description="Latitud del punto de búsqueda", example=4.7110),
    longitud: float = Query(..., ge=-180, le=180, description="Longitud del punto de búsqueda", example=-74.0721),
    radio_metros: float = Query(1000, gt=0, description="Radio de búsqueda en metros", example=5000)
):
    """
    Busca órdenes activas dentro de un radio específico.
    
    Utiliza el índice geoespacial 2dsphere de MongoDB para búsquedas eficientes.
    Solo retorna órdenes cuyo tracking está marcado como activo.
    """
    try:
        tracking_collection = get_tracking_collection()
        
        # Consulta geoespacial con $nearSphere
        # Busca documentos dentro del radio especificado
        query = {
            "activo": True,
            "ubicacion": {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitud, latitud]  # GeoJSON: [lng, lat]
                    },
                    "$maxDistance": radio_metros  # Distancia en metros
                }
            }
        }
        
        # Ejecutar consulta
        resultados_mongo = list(tracking_collection.find(query))
        
        # Obtener información adicional de PostgreSQL para cada orden
        ordenes_ids = list(set([doc["orden_id"] for doc in resultados_mongo]))
        
        ordenes_info = {}
        if ordenes_ids:
            conn = get_postgres_connection()
            cursor = conn.cursor()
            
            # Usar IN para obtener múltiples órdenes en una sola consulta
            cursor.execute("""
                SELECT id, descripcion, estado, direccion_destino
                FROM ordenes
                WHERE id = ANY(%s);
            """, (ordenes_ids,))
            
            for row in cursor.fetchall():
                ordenes_info[row[0]] = {
                    "descripcion": row[1],
                    "estado": row[2],
                    "direccion_destino": row[3]
                }
            
            cursor.close()
            conn.close()
        
        # Construir respuesta combinada
        resultados = []
        for doc in resultados_mongo:
            orden_id = doc["orden_id"]
            coords = doc.get("ubicacion", {}).get("coordinates", [])
            
            resultado = {
                "orden_id": orden_id,
                "ubicacion": {
                    "latitud": coords[1] if len(coords) > 1 else None,
                    "longitud": coords[0] if len(coords) > 0 else None
                },
                "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
                "velocidad_kmh": doc.get("velocidad_kmh"),
                "orden_info": ordenes_info.get(orden_id, {})
            }
            resultados.append(resultado)
        
        return BusquedaCercanaResponse(
            ordenes_encontradas=len(resultados),
            resultados=resultados
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda geoespacial: {str(e)}"
        )


# ==================== PUT /ordenes/{orden_id}/estado ====================
@app.put("/ordenes/{orden_id}/estado", tags=["Órdenes", "Sincronización"])
async def actualizar_estado_orden(orden_id: int, request: ActualizarEstadoRequest):
    """
    Actualiza el estado de una orden en PostgreSQL.
    
    **Sincronización:** Cuando el estado cambia a 'Entregado', 
    dispara un evento que actualiza el flag 'activo' a False 
    en todos los documentos de tracking asociados en MongoDB.
    """
    estados_validos = ["Pendiente", "En Proceso", "En Tránsito", "Entregado", "Cancelado"]
    
    if request.estado not in estados_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Estados válidos: {estados_validos}"
        )
    
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Actualizar estado en PostgreSQL
        cursor.execute("""
            UPDATE ordenes 
            SET estado = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, estado;
        """, (request.estado, orden_id))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Orden con ID {orden_id} no encontrada"
            )
        
        conn.commit()
        cursor.close()
        
        # EVENTO DE SINCRONIZACIÓN
        # Si el estado es "Entregado", actualizar MongoDB
        if request.estado == "Entregado":
            sync_result = sincronizar_tracking_entregado(orden_id)
            return {
                "mensaje": "Estado actualizado y tracking sincronizado",
                "orden_id": orden_id,
                "nuevo_estado": request.estado,
                "sincronizacion": sync_result
            }
        
        return {
            "mensaje": "Estado actualizado exitosamente",
            "orden_id": orden_id,
            "nuevo_estado": request.estado
        }
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar estado: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


# ==================== FUNCIÓN DE SINCRONIZACIÓN ====================

def sincronizar_tracking_entregado(orden_id: int) -> dict:
    """
    Evento de sincronización: Actualiza el flag 'activo' a False
    en MongoDB cuando una orden es marcada como 'Entregado' en PostgreSQL.
    
    Esta función simula un evento que mantiene la consistencia
    entre ambas bases de datos.
    """
    try:
        tracking_collection = get_tracking_collection()
        
        # Actualizar todos los documentos de tracking de esta orden
        result = tracking_collection.update_many(
            {"orden_id": orden_id},
            {
                "$set": {
                    "activo": False,
                    "fecha_sincronizacion": datetime.utcnow()
                }
            }
        )
        
        return {
            "documentos_actualizados": result.modified_count,
            "mensaje": f"Tracking desactivado para orden {orden_id}"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "mensaje": "Error en sincronización con MongoDB"
        }


# ==================== ENDPOINTS AUXILIARES ====================

@app.get("/ordenes", tags=["Órdenes"])
async def listar_ordenes(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    limite: int = Query(10, ge=1, le=100, description="Número máximo de resultados")
):
    """Lista todas las órdenes con filtro opcional por estado"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        if estado:
            cursor.execute("""
                SELECT o.id, o.descripcion, o.estado, o.direccion_destino, o.fecha_creacion,
                       c.nombre as cliente_nombre
                FROM ordenes o
                JOIN clientes c ON o.cliente_id = c.id
                WHERE o.estado = %s
                ORDER BY o.fecha_creacion DESC
                LIMIT %s;
            """, (estado, limite))
        else:
            cursor.execute("""
                SELECT o.id, o.descripcion, o.estado, o.direccion_destino, o.fecha_creacion,
                       c.nombre as cliente_nombre
                FROM ordenes o
                JOIN clientes c ON o.cliente_id = c.id
                ORDER BY o.fecha_creacion DESC
                LIMIT %s;
            """, (limite,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        ordenes = []
        for row in rows:
            ordenes.append({
                "id": row[0],
                "descripcion": row[1],
                "estado": row[2],
                "direccion_destino": row[3],
                "fecha_creacion": row[4].isoformat() if row[4] else None,
                "cliente_nombre": row[5]
            })
        
        return {"total": len(ordenes), "ordenes": ordenes}
        
    finally:
        if conn:
            conn.close()


# ==================== ENDPOINTS DE CLIENTES ====================

@app.get("/clientes", tags=["Clientes"])
async def listar_clientes(
    limite: int = Query(10, ge=1, le=100, description="Número máximo de resultados")
):
    """Lista todos los clientes registrados"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.nombre, c.email, c.telefono, c.direccion, c.fecha_registro,
                   COUNT(o.id) as total_ordenes
            FROM clientes c
            LEFT JOIN ordenes o ON c.id = o.cliente_id
            GROUP BY c.id
            ORDER BY c.fecha_registro DESC
            LIMIT %s;
        """, (limite,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        clientes = []
        for row in rows:
            clientes.append({
                "id": row[0],
                "nombre": row[1],
                "email": row[2],
                "telefono": row[3],
                "direccion": row[4],
                "fecha_registro": row[5].isoformat() if row[5] else None,
                "total_ordenes": row[6]
            })
        
        return {"total": len(clientes), "clientes": clientes}
        
    finally:
        if conn:
            conn.close()


@app.get("/clientes/{cliente_id}", tags=["Clientes"])
async def obtener_cliente(cliente_id: int):
    """Obtiene un cliente por su ID con sus órdenes asociadas"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Obtener cliente
        cursor.execute("""
            SELECT id, nombre, email, telefono, direccion, fecha_registro
            FROM clientes WHERE id = %s;
        """, (cliente_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Cliente con ID {cliente_id} no encontrado")
        
        cliente = {
            "id": row[0],
            "nombre": row[1],
            "email": row[2],
            "telefono": row[3],
            "direccion": row[4],
            "fecha_registro": row[5].isoformat() if row[5] else None
        }
        
        # Obtener órdenes del cliente
        cursor.execute("""
            SELECT id, descripcion, estado, direccion_destino, fecha_creacion
            FROM ordenes WHERE cliente_id = %s
            ORDER BY fecha_creacion DESC;
        """, (cliente_id,))
        
        ordenes = []
        for o in cursor.fetchall():
            ordenes.append({
                "id": o[0],
                "descripcion": o[1],
                "estado": o[2],
                "direccion_destino": o[3],
                "fecha_creacion": o[4].isoformat() if o[4] else None
            })
        
        cliente["ordenes"] = ordenes
        cursor.close()
        
        return cliente
        
    finally:
        if conn:
            conn.close()


# ==================== ENDPOINTS AVANZADOS DE TRACKING ====================

@app.get("/tracking/{orden_id}/historial", tags=["Tracking"])
async def obtener_historial_tracking(
    orden_id: int,
    limite: int = Query(50, ge=1, le=500, description="Número máximo de registros")
):
    """
    Obtiene el historial completo de ubicaciones de una orden.
    Útil para reconstruir la ruta del envío.
    """
    # Verificar que la orden existe y obtener datos
    orden = verificar_orden_existe(orden_id, "id, descripcion, estado")
    
    # Obtener historial de MongoDB
    tracking_collection = get_tracking_collection()
    
    registros = list(tracking_collection.find(
        {"orden_id": orden_id},
        sort=[("timestamp", -1)]
    ).limit(limite))
    
    historial = []
    for doc in registros:
        coords = doc.get("ubicacion", {}).get("coordinates", [])
        historial.append({
            "latitud": coords[1] if len(coords) > 1 else None,
            "longitud": coords[0] if len(coords) > 0 else None,
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "velocidad_kmh": doc.get("velocidad_kmh"),
            "activo": doc.get("activo")
        })
    
    return {
        "orden_id": orden_id,
        "descripcion": orden[1],
        "estado": orden[2],
        "total_registros": len(historial),
        "historial": historial
    }


@app.get("/tracking/{orden_id}/estadisticas", tags=["Tracking"])
async def obtener_estadisticas_tracking(orden_id: int):
    """
    Calcula estadísticas de la ruta: distancia recorrida, velocidad promedio, 
    tiempo en tránsito, etc.
    """
    # Verificar que la orden existe y obtener datos
    orden = verificar_orden_existe(orden_id, "id, descripcion, estado, fecha_creacion")
    
    # Obtener todos los registros de tracking
    tracking_collection = get_tracking_collection()
    
    registros = list(tracking_collection.find(
        {"orden_id": orden_id},
        sort=[("timestamp", 1)]  # Ordenar cronológicamente
    ))
    
    if not registros:
        return {
            "orden_id": orden_id,
            "mensaje": "No hay datos de tracking para esta orden",
            "total_puntos": 0
        }
    
    # Calcular estadísticas
    velocidades = [r.get("velocidad_kmh") for r in registros if r.get("velocidad_kmh") is not None]
    timestamps = [r.get("timestamp") for r in registros if r.get("timestamp")]
    
    primer_registro = registros[0]
    ultimo_registro = registros[-1]
    
    # Tiempo en tránsito
    tiempo_transito = None
    if len(timestamps) >= 2:
        delta = timestamps[-1] - timestamps[0]
        tiempo_transito = str(delta)
    
    # Coordenadas inicial y final
    coords_inicio = primer_registro.get("ubicacion", {}).get("coordinates", [])
    coords_fin = ultimo_registro.get("ubicacion", {}).get("coordinates", [])
    
    return {
        "orden_id": orden_id,
        "descripcion": orden[1],
        "estado": orden[2],
        "total_puntos_gps": len(registros),
        "estadisticas": {
            "velocidad_promedio_kmh": round(sum(velocidades) / len(velocidades), 2) if velocidades else None,
            "velocidad_maxima_kmh": max(velocidades) if velocidades else None,
            "velocidad_minima_kmh": min(velocidades) if velocidades else None,
            "tiempo_en_transito": tiempo_transito,
            "primer_registro": timestamps[0].isoformat() if timestamps else None,
            "ultimo_registro": timestamps[-1].isoformat() if timestamps else None
        },
        "ubicacion_inicial": {
            "latitud": coords_inicio[1] if len(coords_inicio) > 1 else None,
            "longitud": coords_inicio[0] if len(coords_inicio) > 0 else None
        },
        "ubicacion_actual": {
            "latitud": coords_fin[1] if len(coords_fin) > 1 else None,
            "longitud": coords_fin[0] if len(coords_fin) > 0 else None
        }
    }


@app.delete("/tracking/{orden_id}", tags=["Tracking"])
async def eliminar_tracking(orden_id: int):
    """Elimina todos los registros de tracking de una orden"""
    tracking_collection = get_tracking_collection()
    
    result = tracking_collection.delete_many({"orden_id": orden_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros de tracking para la orden {orden_id}")
    
    return {
        "mensaje": f"Tracking eliminado para orden {orden_id}",
        "registros_eliminados": result.deleted_count
    }


@app.get("/health", tags=["Sistema"])
async def health_check():
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


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
