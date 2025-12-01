"""
database - Módulo de conexión a bases de datos
"""

from .connection import (
    get_postgres_connection,
    get_mongo_client,
    get_mongo_database,
    get_tracking_collection,
    POSTGRES_CONFIG,
    MONGO_CONFIG
)

from .init import init_databases, init_postgres, init_mongodb, SQL_CREATE_TABLES

__all__ = [
    "get_postgres_connection",
    "get_mongo_client", 
    "get_mongo_database",
    "get_tracking_collection",
    "POSTGRES_CONFIG",
    "MONGO_CONFIG",
    "init_databases",
    "init_postgres",
    "init_mongodb",
    "SQL_CREATE_TABLES"
]
