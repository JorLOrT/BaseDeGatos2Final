"""
database/init.py - Inicialización de bases de datos
"""

from pymongo import GEOSPHERE
from .connection import get_postgres_connection, get_mongo_database


SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ordenes (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    descripcion TEXT NOT NULL,
    estado VARCHAR(50) DEFAULT 'Pendiente',
    direccion_origen TEXT NOT NULL,
    direccion_destino TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT estado_valido CHECK (estado IN ('Pendiente', 'En Proceso', 'En Tránsito', 'Entregado', 'Cancelado'))
);

CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);
CREATE INDEX IF NOT EXISTS idx_ordenes_cliente ON ordenes(cliente_id);
"""


def init_postgres():
    """Inicializa las tablas en PostgreSQL."""
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(SQL_CREATE_TABLES)
    conn.commit()
    cursor.close()
    conn.close()


def init_mongodb():
    """Inicializa la colección 'tracking' y crea índices."""
    db = get_mongo_database()
    
    if "tracking" not in db.list_collection_names():
        db.create_collection("tracking")
    
    tracking = db["tracking"]
    tracking.create_index([("ubicacion", GEOSPHERE)], name="ubicacion_2dsphere")
    tracking.create_index([("orden_id", 1), ("timestamp", -1)], name="orden_timestamp_idx")
    tracking.create_index([("activo", 1)], name="activo_idx")


def init_databases():
    """Inicializa ambas bases de datos."""
    init_postgres()
    init_mongodb()
