"""
services/tracking.py - Servicio de tracking GPS
Lógica de negocio para gestión de ubicaciones
"""

from datetime import datetime
from database import get_tracking_collection


class TrackingService:
    """Servicio para gestión de tracking GPS"""
    
    @staticmethod
    def registrar(orden_id: int, latitud: float, longitud: float, 
                  timestamp: datetime = None, velocidad_kmh: float = None,
                  dispositivo_id: str = None) -> str:
        """Registra una ubicación GPS para una orden."""
        tracking_collection = get_tracking_collection()
        
        documento = {
            "orden_id": orden_id,
            "ubicacion": {
                "type": "Point",
                "coordinates": [longitud, latitud]  # GeoJSON: [lng, lat]
            },
            "timestamp": timestamp or datetime.utcnow(),
            "activo": True,
            "velocidad_kmh": velocidad_kmh,
            "metadata": {"dispositivo_id": dispositivo_id}
        }
        
        result = tracking_collection.insert_one(documento)
        return str(result.inserted_id)
    
    @staticmethod
    def obtener_ultima_ubicacion(orden_id: int) -> dict:
        """Obtiene la última ubicación registrada de una orden."""
        tracking_collection = get_tracking_collection()
        
        doc = tracking_collection.find_one(
            {"orden_id": orden_id},
            sort=[("timestamp", -1)]
        )
        
        if not doc:
            return None
        
        coords = doc.get("ubicacion", {}).get("coordinates", [])
        return {
            "latitud": coords[1] if len(coords) > 1 else None,
            "longitud": coords[0] if len(coords) > 0 else None,
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "activo": doc.get("activo"),
            "velocidad_kmh": doc.get("velocidad_kmh")
        }
    
    @staticmethod
    def obtener_historial(orden_id: int, limite: int = 50) -> list:
        """Obtiene historial de ubicaciones de una orden."""
        tracking_collection = get_tracking_collection()
        
        registros = list(tracking_collection.find(
            {"orden_id": orden_id},
            sort=[("timestamp", -1)]
        ).limit(limite))
        
        return [{
            "latitud": doc.get("ubicacion", {}).get("coordinates", [None, None])[1],
            "longitud": doc.get("ubicacion", {}).get("coordinates", [None])[0],
            "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None,
            "velocidad_kmh": doc.get("velocidad_kmh"),
            "activo": doc.get("activo")
        } for doc in registros]
    
    @staticmethod
    def obtener_estadisticas(orden_id: int) -> dict:
        """Calcula estadísticas de la ruta."""
        tracking_collection = get_tracking_collection()
        
        registros = list(tracking_collection.find(
            {"orden_id": orden_id},
            sort=[("timestamp", 1)]
        ))
        
        if not registros:
            return {"total_puntos": 0, "mensaje": "No hay datos de tracking"}
        
        velocidades = [r.get("velocidad_kmh") for r in registros if r.get("velocidad_kmh") is not None]
        timestamps = [r.get("timestamp") for r in registros if r.get("timestamp")]
        
        coords_inicio = registros[0].get("ubicacion", {}).get("coordinates", [])
        coords_fin = registros[-1].get("ubicacion", {}).get("coordinates", [])
        
        tiempo_transito = str(timestamps[-1] - timestamps[0]) if len(timestamps) >= 2 else None
        
        return {
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
    
    @staticmethod
    def eliminar(orden_id: int) -> int:
        """Elimina todos los registros de tracking de una orden."""
        tracking_collection = get_tracking_collection()
        result = tracking_collection.delete_many({"orden_id": orden_id})
        return result.deleted_count
