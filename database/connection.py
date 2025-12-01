"""
database/connection.py - Conexiones a PostgreSQL y MongoDB
"""

import os
import psycopg2
from pymongo import MongoClient


# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# Detectar si estamos en Docker (si POSTGRES_HOST está configurado, usamos puerto 5432)
# En local usamos 5433 para evitar conflicto con PostgreSQL instalado
_default_pg_port = "5432" if os.getenv("POSTGRES_HOST") else "5433"

POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", _default_pg_port),
    "database": os.getenv("POSTGRES_DB", "logistics_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres123")
}

MONGO_CONFIG = {
    "host": os.getenv("MONGO_HOST", "localhost"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "database": os.getenv("MONGO_DB", "logistics_db")
}


# ==============================================================================
# POSTGRESQL
# ==============================================================================

def get_postgres_connection():
    """Establece conexión con PostgreSQL usando psycopg2."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database=POSTGRES_CONFIG["database"],
            user=POSTGRES_CONFIG["user"],
            password=POSTGRES_CONFIG["password"]
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error conectando a PostgreSQL: {e}")
        raise


# ==============================================================================
# MONGODB
# ==============================================================================

def get_mongo_client():
    """Establece conexión con MongoDB usando PyMongo."""
    try:
        client = MongoClient(
            host=MONGO_CONFIG["host"],
            port=MONGO_CONFIG["port"]
        )
        return client
    except Exception as e:
        print(f"Error conectando a MongoDB: {e}")
        raise


def get_mongo_database():
    """Obtiene la base de datos MongoDB."""
    client = get_mongo_client()
    return client[MONGO_CONFIG["database"]]


def get_tracking_collection():
    """Obtiene la colección 'tracking' de MongoDB."""
    db = get_mongo_database()
    return db["tracking"]


# ==============================================================================
# TEST DE CONEXIONES
# ==============================================================================

def test_connections():
    """Prueba las conexiones a ambas bases de datos."""
    print("Probando conexión a PostgreSQL...")
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ PostgreSQL conectado: {version[0][:50]}...")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"✗ Error PostgreSQL: {e}")
    
    print("\nProbando conexión a MongoDB...")
    try:
        client = get_mongo_client()
        db = get_mongo_database()
        server_info = client.server_info()
        print(f"✓ MongoDB conectado: versión {server_info['version']}")
        client.close()
    except Exception as e:
        print(f"✗ Error MongoDB: {e}")


if __name__ == "__main__":
    test_connections()
