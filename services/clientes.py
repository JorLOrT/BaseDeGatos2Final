"""
services/clientes.py - Servicio de clientes
Lógica de negocio para gestión de clientes
"""

from database import get_postgres_connection


class ClientesService:
    """Servicio para gestión de clientes"""
    
    @staticmethod
    def verificar_existe(cliente_id: int) -> tuple:
        """Verifica si un cliente existe."""
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email FROM clientes WHERE id = %s;", (cliente_id,))
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        return cliente
    
    @staticmethod
    def buscar_por_email(email: str, conn=None) -> tuple:
        """Busca cliente por email."""
        close_conn = False
        if conn is None:
            conn = get_postgres_connection()
            close_conn = True
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM clientes WHERE email = %s;", (email,))
        result = cursor.fetchone()
        cursor.close()
        
        if close_conn:
            conn.close()
        
        return result
    
    @staticmethod
    def crear(nombre: str, email: str, telefono: str = None, direccion: str = None, conn=None) -> int:
        """Crea un nuevo cliente."""
        close_conn = False
        if conn is None:
            conn = get_postgres_connection()
            close_conn = True
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nombre, email, telefono, direccion)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (nombre, email, telefono, direccion))
        cliente_id = cursor.fetchone()[0]
        cursor.close()
        
        if close_conn:
            conn.commit()
            conn.close()
        
        return cliente_id
    
    @staticmethod
    def listar(limite: int = 10) -> list:
        """Lista clientes con conteo de órdenes."""
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
        conn.close()
        
        return [{
            "id": row[0], "nombre": row[1], "email": row[2],
            "telefono": row[3], "direccion": row[4],
            "fecha_registro": row[5].isoformat() if row[5] else None,
            "total_ordenes": row[6]
        } for row in rows]
    
    @staticmethod
    def obtener_con_ordenes(cliente_id: int) -> dict:
        """Obtiene cliente con sus órdenes."""
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Obtener cliente
        cursor.execute("""
            SELECT id, nombre, email, telefono, direccion, fecha_registro
            FROM clientes WHERE id = %s;
        """, (cliente_id,))
        
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return None
        
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
        conn.close()
        
        return cliente
