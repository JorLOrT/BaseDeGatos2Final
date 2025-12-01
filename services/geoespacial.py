"""
services/geoespacial.py - Servicio de búsquedas geoespaciales
Lógica de negocio para consultas de proximidad
"""

from database import get_postgres_connection, get_tracking_collection


class GeoespacialService:
    """Servicio para búsquedas geoespaciales"""
    
    @staticmethod
    def buscar_cercanos(latitud: float, longitud: float, radio_metros: float) -> list:
        """
        Busca órdenes activas dentro de un radio específico.
        Utiliza el índice 2dsphere de MongoDB.
        """
        tracking_collection = get_tracking_collection()
        
        # Consulta geoespacial con $nearSphere
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
        
        # Construir respuesta
        return [{
            "orden_id": doc["orden_id"],
            "ubicacion": {
                "latitud": doc.get("ubicacion", {}).get("coordinates", [None, None])[1],
                "longitud": doc.get("ubicacion", {}).get("coordinates", [None])[0]
            },
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "velocidad_kmh": doc.get("velocidad_kmh"),
            "orden_info": ordenes_info.get(doc["orden_id"], {})
        } for doc in resultados_mongo]
