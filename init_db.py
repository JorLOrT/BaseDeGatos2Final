"""
init_db.py - Script de inicialización de bases de datos
Crea tablas en PostgreSQL e índices geoespaciales en MongoDB
"""

import psycopg2
from pymongo import MongoClient, GEOSPHERE
from db import (
    get_postgres_connection, 
    get_mongo_database,
    POSTGRES_CONFIG,
    MONGO_CONFIG
)


# ==================== SCRIPT SQL PARA POSTGRESQL ====================
# Modelado de datos para las tablas clientes y ordenes

SQL_CREATE_TABLES = """
-- Tabla de clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de órdenes
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

-- Índice para búsquedas por estado
CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado);

-- Índice para búsquedas por cliente
CREATE INDEX IF NOT EXISTS idx_ordenes_cliente ON ordenes(cliente_id);
"""


# ==================== ESTRUCTURA JSON PARA MONGODB (TRACKING) ====================
"""
Estructura del documento JSON para la colección 'tracking':

{
    "_id": ObjectId,                    # ID único generado por MongoDB
    "orden_id": int,                    # Referencia al ID de la orden en PostgreSQL
    "ubicacion": {
        "type": "Point",                # Tipo GeoJSON
        "coordinates": [longitud, latitud]  # Coordenadas [lng, lat]
    },
    "timestamp": ISODate,               # Momento del registro
    "activo": bool,                     # Flag de sincronización con PostgreSQL
    "velocidad_kmh": float,             # Velocidad del vehículo (opcional)
    "rumbo": float,                     # Dirección en grados (opcional)
    "metadata": {
        "dispositivo_id": string,       # ID del dispositivo GPS
        "precision_metros": float       # Precisión del GPS
    }
}
"""


def init_postgres():
    """
    Inicializa las tablas en PostgreSQL.
    """
    print("=" * 50)
    print("Inicializando PostgreSQL...")
    print("=" * 50)
    
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Ejecutar script de creación de tablas
        cursor.execute(SQL_CREATE_TABLES)
        conn.commit()
        
        print("✓ Tablas 'clientes' y 'ordenes' creadas correctamente")
        
        # Verificar tablas creadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE';
        """)
        tables = cursor.fetchall()
        print(f"  Tablas existentes: {[t[0] for t in tables]}")
        
        cursor.close()
        
    except psycopg2.Error as e:
        print(f"✗ Error en PostgreSQL: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def init_mongodb():
    """
    Inicializa la colección 'tracking' y crea el índice geoespacial 2dsphere.
    """
    print("\n" + "=" * 50)
    print("Inicializando MongoDB...")
    print("=" * 50)
    
    try:
        db = get_mongo_database()
        
        # Crear colección tracking si no existe
        if "tracking" not in db.list_collection_names():
            db.create_collection("tracking")
            print("✓ Colección 'tracking' creada")
        else:
            print("✓ Colección 'tracking' ya existe")
        
        tracking_collection = db["tracking"]
        
        # Crear índice geoespacial 2dsphere en el campo 'ubicacion'
        # Este índice permite búsquedas eficientes de ubicación
        index_name = tracking_collection.create_index(
            [("ubicacion", GEOSPHERE)],
            name="ubicacion_2dsphere"
        )
        print(f"✓ Índice geoespacial 2dsphere creado: {index_name}")
        
        # Crear índice compuesto para búsquedas por orden_id y timestamp
        tracking_collection.create_index(
            [("orden_id", 1), ("timestamp", -1)],
            name="orden_timestamp_idx"
        )
        print("✓ Índice compuesto orden_id + timestamp creado")
        
        # Crear índice para filtrar por estado activo
        tracking_collection.create_index(
            [("activo", 1)],
            name="activo_idx"
        )
        print("✓ Índice de campo 'activo' creado")
        
        # Listar todos los índices
        indices = list(tracking_collection.list_indexes())
        print(f"\n  Índices en 'tracking': {[idx['name'] for idx in indices]}")
        
    except Exception as e:
        print(f"✗ Error en MongoDB: {e}")
        raise


def insert_sample_data():
    """
    Inserta datos de ejemplo para pruebas.
    """
    print("\n" + "=" * 50)
    print("Insertando datos de ejemplo...")
    print("=" * 50)
    
    # Datos de ejemplo para PostgreSQL
    conn = get_postgres_connection()
    cursor = conn.cursor()
    
    try:
        # Insertar cliente de ejemplo
        cursor.execute("""
            INSERT INTO clientes (nombre, email, telefono, direccion)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id;
        """, ("Juan Pérez", "juan.perez@email.com", "+57 300 123 4567", "Calle 123 #45-67, Bogotá"))
        
        result = cursor.fetchone()
        if result:
            cliente_id = result[0]
            print(f"✓ Cliente de ejemplo creado con ID: {cliente_id}")
            
            # Insertar orden de ejemplo
            cursor.execute("""
                INSERT INTO ordenes (cliente_id, descripcion, estado, direccion_origen, direccion_destino)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (cliente_id, "Paquete electrónico", "En Tránsito", 
                  "Bodega Central, Bogotá", "Calle 123 #45-67, Medellín"))
            
            orden_id = cursor.fetchone()[0]
            print(f"✓ Orden de ejemplo creada con ID: {orden_id}")
            
            conn.commit()
            
            # Insertar tracking de ejemplo en MongoDB
            db = get_mongo_database()
            tracking = db["tracking"]
            
            from datetime import datetime
            doc = {
                "orden_id": orden_id,
                "ubicacion": {
                    "type": "Point",
                    "coordinates": [-74.0721, 4.7110]  # Bogotá [lng, lat]
                },
                "timestamp": datetime.utcnow(),
                "activo": True,
                "velocidad_kmh": 60.5,
                "rumbo": 45.0,
                "metadata": {
                    "dispositivo_id": "GPS-001",
                    "precision_metros": 5.0
                }
            }
            result = tracking.insert_one(doc)
            print(f"✓ Documento de tracking insertado: {result.inserted_id}")
        else:
            print("  Cliente de ejemplo ya existe")
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Error insertando datos de ejemplo: {e}")
    finally:
        cursor.close()
        conn.close()


def main():
    """
    Función principal de inicialización.
    """
    print("\n" + "=" * 60)
    print("   INICIALIZACIÓN DE BASES DE DATOS - HybridLogisticsHub")
    print("=" * 60 + "\n")
    
    try:
        init_postgres()
        init_mongodb()
        
        # Preguntar si insertar datos de ejemplo
        respuesta = input("\n¿Desea insertar datos de ejemplo? (s/n): ").strip().lower()
        if respuesta == 's':
            insert_sample_data()
        
        print("\n" + "=" * 60)
        print("   ✓ INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error durante la inicialización: {e}")
        raise


if __name__ == "__main__":
    main()
