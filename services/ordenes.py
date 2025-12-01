"""
services/ordenes.py - Servicio de órdenes
Lógica de negocio para gestión de órdenes
"""

from datetime import datetime
import psycopg2
from database import get_postgres_connection, get_tracking_collection


# Constantes
ESTADOS_ORDEN_VALIDOS = ["Pendiente", "En Proceso", "En Tránsito", "Entregado", "Cancelado"]

CAMPOS_ORDEN_PERMITIDOS = {
    "id", "cliente_id", "descripcion", "estado",
    "direccion_origen", "direccion_destino",
    "fecha_creacion", "fecha_actualizacion"
}


class OrdenesService:
    """Servicio para gestión de órdenes"""
    
    @staticmethod
    def validar_campos(campos: str) -> str:
        """Valida campos contra whitelist (prevención SQL injection)"""
        campos_solicitados = [c.strip() for c in campos.split(",")]
        for campo in campos_solicitados:
            if campo not in CAMPOS_ORDEN_PERMITIDOS:
                raise ValueError(f"Campo no permitido: {campo}")
        return ", ".join(campos_solicitados)
    
    @staticmethod
    def verificar_existe(orden_id: int, campos: str = "id, descripcion, estado") -> tuple:
        """Verifica si una orden existe y retorna sus datos."""
        campos_seguros = OrdenesService.validar_campos(campos)
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {campos_seguros} FROM ordenes WHERE id = %s;", (orden_id,))
        orden = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not orden:
            return None
        return orden
    
    @staticmethod
    def crear(cliente_id: int, descripcion: str, direccion_origen: str, direccion_destino: str, conn=None) -> int:
        """Crea una orden (dentro de una transacción existente)."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ordenes (cliente_id, descripcion, estado, direccion_origen, direccion_destino)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (cliente_id, descripcion, "Pendiente", direccion_origen, direccion_destino))
        orden_id = cursor.fetchone()[0]
        return orden_id
    
    @staticmethod
    def listar(estado: str = None, limite: int = 10) -> list:
        """Lista órdenes con filtro opcional por estado."""
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
        conn.close()
        
        return [{
            "id": row[0],
            "descripcion": row[1],
            "estado": row[2],
            "direccion_destino": row[3],
            "fecha_creacion": row[4].isoformat() if row[4] else None,
            "cliente_nombre": row[5]
        } for row in rows]
    
    @staticmethod
    def obtener_por_id(orden_id: int) -> dict:
        """Obtiene una orden por su ID."""
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.cliente_id, o.descripcion, o.estado, 
                   o.direccion_origen, o.direccion_destino,
                   o.fecha_creacion, o.fecha_actualizacion,
                   c.nombre as cliente_nombre
            FROM ordenes o
            JOIN clientes c ON o.cliente_id = c.id
            WHERE o.id = %s;
        """, (orden_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "cliente_id": row[1],
            "descripcion": row[2],
            "estado": row[3],
            "direccion_origen": row[4],
            "direccion_destino": row[5],
            "fecha_creacion": row[6].isoformat() if row[6] else None,
            "fecha_actualizacion": row[7].isoformat() if row[7] else None,
            "cliente_nombre": row[8]
        }
    
    @staticmethod
    def obtener_con_cliente(orden_id: int) -> dict:
        """Obtiene orden con datos del cliente."""
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, o.descripcion, o.estado, o.direccion_origen, o.direccion_destino,
                   o.fecha_creacion, o.fecha_actualizacion,
                   c.id, c.nombre, c.email
            FROM ordenes o
            JOIN clientes c ON o.cliente_id = c.id
            WHERE o.id = %s;
        """, (orden_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0], "descripcion": row[1], "estado": row[2],
            "direccion_origen": row[3], "direccion_destino": row[4],
            "fecha_creacion": row[5].isoformat() if row[5] else None,
            "fecha_actualizacion": row[6].isoformat() if row[6] else None,
            "cliente": {"id": row[7], "nombre": row[8], "email": row[9]}
        }
    
    @staticmethod
    def actualizar_estado(orden_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado de una orden."""
        if nuevo_estado not in ESTADOS_ORDEN_VALIDOS:
            raise ValueError(f"Estado inválido. Válidos: {ESTADOS_ORDEN_VALIDOS}")
        
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ordenes 
            SET estado = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id;
        """, (nuevo_estado, orden_id))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return result is not None
    
    @staticmethod
    def sincronizar_tracking_entregado(orden_id: int) -> dict:
        """Desactiva tracking en MongoDB cuando orden es entregada."""
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
            return {"error": str(e), "mensaje": "Error en sincronización"}
