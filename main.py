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

from db import (
    get_postgres_connection,
    get_tracking_collection,
    get_mongo_database
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


# ==============================================================================
# CONSTANTES
# ==============================================================================

ESTADOS_ORDEN_VALIDOS = ["Pendiente", "En Proceso", "En Tránsito", "Entregado", "Cancelado"]

# Whitelist de campos para prevención de SQL injection
CAMPOS_ORDEN_PERMITIDOS = {
    "id", "cliente_id", "descripcion", "estado",
    "direccion_origen", "direccion_destino",
    "fecha_creacion", "fecha_actualizacion"
}


# ==============================================================================
# MODELOS PYDANTIC - REQUEST
# ==============================================================================

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


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================


def verificar_orden_existe(orden_id: int, campos: str = "id, descripcion, estado") -> tuple:
    """
    Verifica si una orden existe y retorna sus datos.
    Lanza HTTPException 404 si no existe.
    
    Args:
        orden_id: ID de la orden a verificar
        campos: Campos SQL a retornar (default: id, descripcion, estado)
               Solo se permiten campos de la whitelist CAMPOS_ORDEN_PERMITIDOS
    
    Returns:
        Tupla con los datos de la orden
    """
    # Validar campos contra whitelist para prevenir SQL injection
    campos_solicitados = [c.strip() for c in campos.split(",")]
    for campo in campos_solicitados:
        if campo not in CAMPOS_ORDEN_PERMITIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"Campo no permitido: {campo}"
            )
    
    # Construir query segura con campos validados
    campos_seguros = ", ".join(campos_solicitados)
    
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {campos_seguros} FROM ordenes WHERE id = %s;", (orden_id,))
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


def sincronizar_tracking_entregado(orden_id: int) -> dict:
    """
    Sincroniza MongoDB cuando una orden es marcada como 'Entregado'.
    Actualiza el flag 'activo' a False en todos los documentos de tracking.
    """
    try:
        tracking_collection = get_tracking_collection()
        result = tracking_collection.update_many(
            {"orden_id": orden_id},
            {"$set": {"activo": False, "fecha_sincronizacion": datetime.utcnow()}}
        )
        return {
            "documentos_actualizados": result.modified_count,
            "mensaje": f"Tracking desactivado para orden {orden_id}"
        }
    except Exception as e:
        return {"error": str(e), "mensaje": "Error en sincronización con MongoDB"}


# ==============================================================================
# ENDPOINTS - SISTEMA
# ==============================================================================

@app.get("/", tags=["Sistema"])
def root():
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


@app.get("/health", tags=["Sistema"])
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


# ==============================================================================
# ENDPOINTS - ÓRDENES
# ==============================================================================

@app.post("/ordenes", response_model=OrdenResponse, tags=["Órdenes"])
def crear_orden(orden: OrdenCreate):
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
        if conn:
            conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad: {str(e)}")
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.get("/ordenes", tags=["Órdenes"])
def listar_ordenes(
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
        
        ordenes = [{
            "id": row[0],
            "descripcion": row[1],
            "estado": row[2],
            "direccion_destino": row[3],
            "fecha_creacion": row[4].isoformat() if row[4] else None,
            "cliente_nombre": row[5]
        } for row in rows]
        
        return {"total": len(ordenes), "ordenes": ordenes}
        
    finally:
        if conn:
            conn.close()


@app.get("/ordenes/{orden_id}/ubicacion", response_model=UbicacionOrdenResponse, tags=["Órdenes"])
def obtener_ubicacion_orden(orden_id: int):
    """
    **Consulta Federada:** Combina datos de PostgreSQL y MongoDB.
    
    1. Obtiene detalles de la orden (PostgreSQL)
    2. Obtiene última ubicación (MongoDB)
    3. Retorna respuesta combinada
    """
    # Obtener orden de PostgreSQL
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
            raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
        
        orden_data = {
            "id": row[0], "descripcion": row[1], "estado": row[2],
            "direccion_origen": row[3], "direccion_destino": row[4],
            "fecha_creacion": row[5].isoformat() if row[5] else None,
            "fecha_actualizacion": row[6].isoformat() if row[6] else None,
            "cliente": {"id": row[7], "nombre": row[8], "email": row[9]}
        }
        cursor.close()
    finally:
        if conn:
            conn.close()
    
    # Obtener última ubicación de MongoDB
    ultima_ubicacion = None
    try:
        tracking_collection = get_tracking_collection()
        tracking_doc = tracking_collection.find_one(
            {"orden_id": orden_id},
            sort=[("timestamp", -1)]
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
        print(f"Error obteniendo tracking: {e}")
    
    return UbicacionOrdenResponse(orden=orden_data, ultima_ubicacion=ultima_ubicacion)


@app.put("/ordenes/{orden_id}/estado", tags=["Órdenes"])
def actualizar_estado_orden(orden_id: int, request: ActualizarEstadoRequest):
    """
    Actualiza el estado de una orden.
    
    **Sincronización:** Si el estado es 'Entregado', desactiva el tracking en MongoDB.
    """
    if request.estado not in ESTADOS_ORDEN_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {ESTADOS_ORDEN_VALIDOS}")
    
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ordenes 
            SET estado = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id;
        """, (request.estado, orden_id))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
        
        conn.commit()
        cursor.close()
        
        # Sincronización con MongoDB si es "Entregado"
        if request.estado == "Entregado":
            sync = sincronizar_tracking_entregado(orden_id)
            return {"mensaje": "Estado actualizado y tracking sincronizado", 
                    "orden_id": orden_id, "nuevo_estado": request.estado, "sincronizacion": sync}
        
        return {"mensaje": "Estado actualizado", "orden_id": orden_id, "nuevo_estado": request.estado}
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        if conn:
            conn.close()


# ==============================================================================
# ENDPOINTS - CLIENTES
# ==============================================================================

@app.get("/clientes", tags=["Clientes"])
def listar_clientes(
    limite: int = Query(10, ge=1, le=100, description="Número máximo de resultados")
):
    """Lista todos los clientes con conteo de órdenes"""
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
        
        clientes = [{
            "id": row[0], "nombre": row[1], "email": row[2],
            "telefono": row[3], "direccion": row[4],
            "fecha_registro": row[5].isoformat() if row[5] else None,
            "total_ordenes": row[6]
        } for row in rows]
        
        return {"total": len(clientes), "clientes": clientes}
        
    finally:
        if conn:
            conn.close()


@app.get("/clientes/{cliente_id}", tags=["Clientes"])
def obtener_cliente(cliente_id: int):
    """Obtiene un cliente con sus órdenes asociadas"""
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
            raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado")
        
        cliente = {
            "id": row[0], "nombre": row[1], "email": row[2],
            "telefono": row[3], "direccion": row[4],
            "fecha_registro": row[5].isoformat() if row[5] else None
        }
        
        # Obtener órdenes
        cursor.execute("""
            SELECT id, descripcion, estado, direccion_destino, fecha_creacion
            FROM ordenes WHERE cliente_id = %s
            ORDER BY fecha_creacion DESC;
        """, (cliente_id,))
        
        cliente["ordenes"] = [{
            "id": o[0], "descripcion": o[1], "estado": o[2],
            "direccion_destino": o[3],
            "fecha_creacion": o[4].isoformat() if o[4] else None
        } for o in cursor.fetchall()]
        
        cursor.close()
        return cliente
        
    finally:
        if conn:
            conn.close()


# ==============================================================================
# ENDPOINTS - TRACKING
# ==============================================================================

@app.post("/tracking/{orden_id}", response_model=TrackingResponse, tags=["Tracking"])
def registrar_tracking(orden_id: int, tracking: TrackingCreate):
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
            mensaje="Ubicación registrada"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error MongoDB: {str(e)}")


@app.get("/tracking/{orden_id}/historial", tags=["Tracking"])
def obtener_historial_tracking(
    orden_id: int,
    limite: int = Query(50, ge=1, le=500, description="Número máximo de registros")
):
    """Obtiene el historial completo de ubicaciones de una orden"""
    orden = verificar_orden_existe(orden_id, "id, descripcion, estado")
    
    tracking_collection = get_tracking_collection()
    registros = list(tracking_collection.find(
        {"orden_id": orden_id},
        sort=[("timestamp", -1)]
    ).limit(limite))
    
    historial = [{
        "latitud": doc.get("ubicacion", {}).get("coordinates", [None, None])[1],
        "longitud": doc.get("ubicacion", {}).get("coordinates", [None])[0],
        "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
        "velocidad_kmh": doc.get("velocidad_kmh"),
        "activo": doc.get("activo")
    } for doc in registros]
    
    return {
        "orden_id": orden_id,
        "descripcion": orden[1],
        "estado": orden[2],
        "total_registros": len(historial),
        "historial": historial
    }


@app.get("/tracking/{orden_id}/estadisticas", tags=["Tracking"])
def obtener_estadisticas_tracking(orden_id: int):
    """Calcula estadísticas de la ruta: velocidad promedio, tiempo en tránsito, etc."""
    orden = verificar_orden_existe(orden_id, "id, descripcion, estado")
    
    tracking_collection = get_tracking_collection()
    registros = list(tracking_collection.find(
        {"orden_id": orden_id},
        sort=[("timestamp", 1)]
    ))
    
    if not registros:
        return {"orden_id": orden_id, "mensaje": "No hay datos de tracking", "total_puntos": 0}
    
    velocidades = [r.get("velocidad_kmh") for r in registros if r.get("velocidad_kmh") is not None]
    timestamps = [r.get("timestamp") for r in registros if r.get("timestamp")]
    
    coords_inicio = registros[0].get("ubicacion", {}).get("coordinates", [])
    coords_fin = registros[-1].get("ubicacion", {}).get("coordinates", [])
    
    tiempo_transito = str(timestamps[-1] - timestamps[0]) if len(timestamps) >= 2 else None
    
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
def eliminar_tracking(orden_id: int):
    """Elimina todos los registros de tracking de una orden"""
    tracking_collection = get_tracking_collection()
    result = tracking_collection.delete_many({"orden_id": orden_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No hay tracking para orden {orden_id}")
    
    return {"mensaje": "Tracking eliminado", "orden_id": orden_id, "registros_eliminados": result.deleted_count}


# ==============================================================================
# ENDPOINTS - BÚSQUEDA GEOESPACIAL
# ==============================================================================

@app.get("/busqueda-cercana", response_model=BusquedaCercanaResponse, tags=["Geoespacial"])
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
        tracking_collection = get_tracking_collection()
        
        query = {
            "activo": True,
            "ubicacion": {
                "$nearSphere": {
                    "$geometry": {"type": "Point", "coordinates": [longitud, latitud]},
                    "$maxDistance": radio_metros
                }
            }
        }
        
        resultados_mongo = list(tracking_collection.find(query))
        ordenes_ids = list(set([doc["orden_id"] for doc in resultados_mongo]))
        
        # Obtener info de órdenes desde PostgreSQL
        ordenes_info = {}
        if ordenes_ids:
            conn = get_postgres_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, descripcion, estado, direccion_destino
                FROM ordenes WHERE id = ANY(%s);
            """, (ordenes_ids,))
            
            for row in cursor.fetchall():
                ordenes_info[row[0]] = {
                    "descripcion": row[1], "estado": row[2], "direccion_destino": row[3]
                }
            cursor.close()
            conn.close()
        
        resultados = [{
            "orden_id": doc["orden_id"],
            "ubicacion": {
                "latitud": doc.get("ubicacion", {}).get("coordinates", [None, None])[1],
                "longitud": doc.get("ubicacion", {}).get("coordinates", [None])[0]
            },
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "velocidad_kmh": doc.get("velocidad_kmh"),
            "orden_info": ordenes_info.get(doc["orden_id"], {})
        } for doc in resultados_mongo]
        
        return BusquedaCercanaResponse(ordenes_encontradas=len(resultados), resultados=resultados)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error geoespacial: {str(e)}")


# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
