# 📘 Memoria Técnica Descriptiva - HybridLogisticsHub

## Sistema de Gestión Logística con Arquitectura Híbrida PostgreSQL + MongoDB

---

## 📑 Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Arquitectura General](#2-arquitectura-general)
3. [Tecnologías Utilizadas](#3-tecnologías-utilizadas)
4. [Modelado de Datos](#4-modelado-de-datos)
5. [Modelado de Procesos](#5-modelado-de-procesos)
6. [API REST - Endpoints](#6-api-rest---endpoints)
7. [Validaciones y Reglas de Negocio](#7-validaciones-y-reglas-de-negocio)
8. [Seguridad](#8-seguridad)
9. [Instalación y Despliegue](#9-instalación-y-despliegue)
10. [Conclusiones](#10-conclusiones)

---

## 1. Introducción

### 1.1 Objetivo del Sistema

**HybridLogisticsHub** es un sistema de gestión logística diseñado para demostrar la implementación de una **arquitectura de bases de datos híbrida**, combinando:

- **PostgreSQL**: Base de datos relacional para datos transaccionales
- **MongoDB**: Base de datos NoSQL para datos geoespaciales y tracking en tiempo real

### 1.2 Contexto del Proyecto

Este proyecto fue desarrollado como parte del curso de **Sistemas de Bases de Datos II** de la Universidad de La Salle, con el objetivo de:

1. Implementar una arquitectura de múltiples bases de datos
2. Aplicar consultas geoespaciales con MongoDB
3. Desarrollar una API REST con FastAPI
4. Crear una interfaz visual de tracking en tiempo real

### 1.3 Alcance

El sistema abarca:
- ✅ Gestión de clientes y órdenes (CRUD completo)
- ✅ Tracking de ubicación en tiempo real
- ✅ Consultas geoespaciales (búsqueda por cercanía y zona)
- ✅ Visualización interactiva con mapas
- ✅ Simulación de entregas con rutas reales

---

## 2. Arquitectura General

### 2.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE (Frontend)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    tracking_visual.html                              │   │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │   │
│   │  │   Leaflet.js │    │  JavaScript  │    │  OpenRouteService    │   │   │
│   │  │   (Mapas)    │    │  (Lógica)    │    │  (Rutas externas)    │   │   │
│   │  └──────────────┘    └──────────────┘    └──────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│                           HTTP/REST (JSON)                                   │
│                                    │                                         │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────────┐
│                              SERVIDOR (Backend)                              │
├────────────────────────────────────┼─────────────────────────────────────────┤
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         FastAPI (main.py)                            │   │
│   │                    CORS Middleware + Static Files                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│          ┌─────────────────────────┼─────────────────────────┐               │
│          ▼                         ▼                         ▼               │
│   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│   │   routes/   │          │  services/  │          │   models/   │         │
│   │  Endpoints  │◄────────►│   Lógica    │◄────────►│  Schemas    │         │
│   │   (API)     │          │  Negocio    │          │  Pydantic   │         │
│   └─────────────┘          └─────────────┘          └─────────────┘         │
│          │                         │                                         │
│          └─────────────────────────┼─────────────────────────────────────────┤
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      database/connection.py                          │   │
│   │              Gestión de conexiones y pool de conexiones              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                     │                                   │                    │
└─────────────────────┼───────────────────────────────────┼────────────────────┘
                      │                                   │
                      ▼                                   ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
│          PostgreSQL 18              │  │            MongoDB 8                 │
│         (Docker: 5433)              │  │         (Docker: 27017)              │
├─────────────────────────────────────┤  ├─────────────────────────────────────┤
│                                     │  │                                     │
│  ┌─────────────┐  ┌─────────────┐   │  │  ┌─────────────────────────────┐   │
│  │  clientes   │  │   ordenes   │   │  │  │   tracking (collection)    │   │
│  │  (tabla)    │──│   (tabla)   │   │  │  │   - GeoJSON ubicaciones    │   │
│  └─────────────┘  └─────────────┘   │  │  │   - Índice 2dsphere        │   │
│                                     │  │  └─────────────────────────────┘   │
│  Datos transaccionales:             │  │                                     │
│  - Información de clientes          │  │  Datos geoespaciales:               │
│  - Órdenes y estados                │  │  - Ubicaciones GPS                  │
│  - Relaciones FK                    │  │  - Historial de movimientos         │
│  - Integridad referencial           │  │  - Consultas $near, $geoWithin      │
│                                     │  │                                     │
└─────────────────────────────────────┘  └─────────────────────────────────────┘
```

### 2.2 Patrón de Arquitectura

El sistema implementa una **arquitectura en capas**:

| Capa | Responsabilidad | Componentes |
|------|-----------------|-------------|
| **Presentación** | Interfaz de usuario | `tracking_visual.html`, Leaflet.js |
| **API** | Exposición de endpoints | `routes/*.py`, FastAPI |
| **Servicios** | Lógica de negocio | `services/*.py` |
| **Modelos** | Validación de datos | `models/schemas.py`, Pydantic |
| **Datos** | Persistencia | `database/connection.py`, PostgreSQL, MongoDB |

### 2.3 Justificación de la Arquitectura Híbrida

| Aspecto | PostgreSQL | MongoDB |
|---------|------------|---------|
| **Uso principal** | Datos transaccionales | Datos geoespaciales |
| **Tipo de datos** | Estructurados (clientes, órdenes) | Semi-estructurados (tracking) |
| **Consultas** | JOINs, transacciones ACID | Geoespaciales ($near, $geoWithin) |
| **Escalabilidad** | Vertical | Horizontal (sharding) |
| **Consistencia** | Fuerte | Eventual (configurable) |

---

## 3. Tecnologías Utilizadas

### 3.1 Backend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.10+ | Lenguaje principal |
| **FastAPI** | 0.100+ | Framework web asíncrono |
| **Uvicorn** | 0.22+ | Servidor ASGI |
| **psycopg2** | 2.9+ | Driver PostgreSQL |
| **PyMongo** | 4.6+ | Driver MongoDB |
| **Pydantic** | 2.0+ | Validación de datos |

### 3.2 Bases de Datos

| Tecnología | Versión | Puerto | Propósito |
|------------|---------|--------|-----------|
| **PostgreSQL** | 18-alpine | 5433 | Datos transaccionales |
| **MongoDB** | 8 | 27017 | Datos geoespaciales |

### 3.3 Frontend

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **HTML5/CSS3** | - | Estructura y estilos |
| **JavaScript ES6+** | - | Lógica del cliente |
| **Leaflet.js** | 1.9.4 | Mapas interactivos |
| **OpenStreetMap** | - | Tiles del mapa |
| **OpenRouteService** | API v2 | Cálculo de rutas |

### 3.4 Infraestructura

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Docker** | 20+ | Contenedores |
| **Docker Compose** | 2.0+ | Orquestación local |

### 3.5 Diagrama de Dependencias

```
requirements.txt
├── fastapi>=0.100.0
├── uvicorn[standard]>=0.22.0
├── psycopg2-binary>=2.9.0
├── pymongo>=4.6.0
├── pydantic>=2.0.0
└── python-multipart>=0.0.6
```

---

## 4. Modelado de Datos

### 4.1 Modelo Relacional (PostgreSQL)

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENTES                             │
├─────────────────────────────────────────────────────────────┤
│ PK  id              SERIAL                                   │
│     nombre          VARCHAR(100)    NOT NULL                 │
│     email           VARCHAR(100)    NOT NULL UNIQUE          │
│     telefono        VARCHAR(20)                              │
│     direccion       TEXT                                     │
│     fecha_registro  TIMESTAMP       DEFAULT NOW()            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          ORDENES                             │
├─────────────────────────────────────────────────────────────┤
│ PK  id                  SERIAL                               │
│ FK  cliente_id          INTEGER       REFERENCES clientes    │
│     descripcion         TEXT          NOT NULL               │
│     estado              VARCHAR(20)   DEFAULT 'Pendiente'    │
│     direccion_origen    TEXT          NOT NULL               │
│     direccion_destino   TEXT          NOT NULL               │
│     fecha_creacion      TIMESTAMP     DEFAULT NOW()          │
│     fecha_actualizacion TIMESTAMP     DEFAULT NOW()          │
└─────────────────────────────────────────────────────────────┘
```

#### Estados de Orden Válidos:
```python
ESTADOS_ORDEN_VALIDOS = [
    "Pendiente",    # Orden creada, esperando procesamiento
    "En Proceso",   # Orden siendo preparada
    "En Tránsito",  # Orden en camino
    "Entregado",    # Orden entregada exitosamente
    "Cancelado"     # Orden cancelada
]
```

### 4.2 Modelo de Documentos (MongoDB)

#### Colección: `tracking`

```json
{
  "_id": ObjectId("..."),
  "orden_id": 1,
  "ubicacion": {
    "type": "Point",
    "coordinates": [-71.537, -16.409]  // [longitud, latitud]
  },
  "timestamp": ISODate("2025-11-30T10:30:00Z"),
  "velocidad_kmh": 45.5,
  "dispositivo_id": "GPS-001",
  "metadata": {
    "bateria": 85,
    "precision_metros": 5
  }
}
```

#### Índice Geoespacial:
```javascript
db.tracking.createIndex({ "ubicacion": "2dsphere" })
```

### 4.3 Relación entre Bases de Datos

```
PostgreSQL                              MongoDB
┌──────────────┐                       ┌──────────────────────┐
│   ordenes    │                       │      tracking        │
│              │     orden_id          │                      │
│  id: 1  ─────┼──────────────────────►│  orden_id: 1         │
│  id: 2  ─────┼──────────────────────►│  orden_id: 2         │
│  id: 3  ─────┼──────────────────────►│  orden_id: 3         │
│              │                       │                      │
└──────────────┘                       └──────────────────────┘

La relación es por convención (orden_id), no por FK.
Las consultas federadas se realizan en la capa de servicios.
```

---

## 5. Modelado de Procesos

### 5.1 Flujo: Crear Orden

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Cliente │────►│  API    │────►│ Service │────►│ Validar │────►│PostgreSQL│
│ (POST)  │     │ /orden  │     │ crear() │     │ Pydantic│     │ INSERT   │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  Respuesta  │
                              │  orden_id   │
                              └─────────────┘
```

**Código relevante:**
```python
# routes/ordenes.py
@router.post("/ordenes")
async def crear_orden(orden: OrdenCreate):
    resultado = OrdenesService.crear_orden_completa(
        cliente=orden.cliente,
        descripcion=orden.descripcion,
        direccion_origen=orden.direccion_origen,
        direccion_destino=orden.direccion_destino
    )
    return resultado
```

### 5.2 Flujo: Registrar Tracking

```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   GPS   │────►│   API    │────►│ Service │────►│ Validar │────►│ MongoDB │
│ (POST)  │     │/tracking │     │ crear() │     │ coords  │     │ INSERT  │
└─────────┘     └──────────┘     └─────────┘     └─────────┘     └─────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
              ┌───────────┐   ┌───────────┐   ┌───────────┐
              │  Guardar  │   │ Actualizar│   │ Respuesta │
              │  GeoJSON  │   │  Estado   │   │ tracking  │
              └───────────┘   └───────────┘   └───────────┘
```

### 5.3 Flujo: Consulta Geoespacial (Órdenes Cercanas)

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────┐
│ Cliente │────►│     API      │────►│   MongoDB    │────►│ Filtrar │
│  (GET)  │     │ /geo/cercanas│     │   $near      │     │ Órdenes │
└─────────┘     └──────────────┘     └──────────────┘     └─────────┘
     │                                                          │
     │                                                          ▼
     │              ┌──────────────┐     ┌──────────────┐     ┌─────────┐
     └──────────────│   Respuesta  │◄────│  PostgreSQL  │◄────│ Obtener │
                    │  Combinada   │     │  Detalles    │     │ Datos   │
                    └──────────────┘     └──────────────┘     └─────────┘
```

**Consulta MongoDB:**
```python
tracking_collection.find({
    "ubicacion": {
        "$near": {
            "$geometry": {
                "type": "Point",
                "coordinates": [longitud, latitud]
            },
            "$maxDistance": radio_metros
        }
    }
})
```

### 5.4 Flujo: Simulación de Entrega (Frontend)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIMULACIÓN DE ENTREGA                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. Usuario selecciona orden
         │
         ▼
┌─────────────────┐
│ Obtener coords  │
│ origen/destino  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌────────────────────────┐
│ OpenRouteService│────►│ Calcular ruta real     │
│      API        │     │ (calles de la ciudad)  │
└─────────────────┘     └───────────┬────────────┘
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │ Dibujar polyline en    │
                        │ mapa (Leaflet)         │
                        └───────────┬────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Crear marcador  │      │ Iniciar loop de │      │ Actualizar UI   │
│ vehículo 🚚     │      │ animación       │      │ progreso/vel.   │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │ Interpolar posición │◄────┐
                        │ en la ruta          │     │
                        └────────┬────────────┘     │
                                 │                  │
                                 ▼                  │
                        ┌─────────────────────┐     │
                        │ ¿Llegó al destino?  │─No──┘
                        └────────┬────────────┘
                                 │ Sí
                                 ▼
                        ┌─────────────────────┐
                        │ PUT /ordenes/{id}/  │
                        │ estado = "Entregado"│
                        └─────────────────────┘
```

---

## 6. API REST - Endpoints

### 6.1 Resumen de Endpoints

| Método | Endpoint | Descripción | BD |
|--------|----------|-------------|-----|
| GET | `/` | Health check | - |
| GET | `/stats` | Estadísticas del sistema | PG + Mongo |
| GET | `/clientes` | Listar clientes | PostgreSQL |
| GET | `/clientes/{id}` | Obtener cliente | PostgreSQL |
| POST | `/clientes` | Crear cliente | PostgreSQL |
| PUT | `/clientes/{id}` | Actualizar cliente | PostgreSQL |
| DELETE | `/clientes/{id}` | Eliminar cliente | PostgreSQL |
| GET | `/ordenes` | Listar órdenes | PostgreSQL |
| GET | `/ordenes/{id}` | Obtener orden | PostgreSQL |
| POST | `/ordenes` | Crear orden | PostgreSQL |
| PUT | `/ordenes/{id}` | Actualizar orden | PostgreSQL |
| PUT | `/ordenes/{id}/estado` | Cambiar estado | PostgreSQL |
| DELETE | `/ordenes/{id}` | Eliminar orden | PostgreSQL |
| GET | `/tracking/{orden_id}` | Última ubicación | MongoDB |
| POST | `/tracking` | Registrar ubicación | MongoDB |
| GET | `/tracking/{orden_id}/historial` | Historial GPS | MongoDB |
| GET | `/geo/cercanas` | Órdenes cercanas | Mongo + PG |
| GET | `/geo/zona` | Órdenes en zona | Mongo + PG |

### 6.2 Ejemplos de Uso

#### Crear Orden Completa
```http
POST /ordenes
Content-Type: application/json

{
  "cliente": {
    "nombre": "Juan Pérez",
    "email": "juan@email.com",
    "telefono": "+51 999 888 777"
  },
  "descripcion": "Laptop Dell XPS 15",
  "direccion_origen": "Centro de Distribución, Arequipa",
  "direccion_destino": "Av. Ejercito 1200, Cayma, Arequipa"
}
```

**Respuesta:**
```json
{
  "orden_id": 101,
  "cliente_id": 51,
  "mensaje": "Orden creada exitosamente"
}
```

#### Buscar Órdenes Cercanas
```http
GET /geo/cercanas?lat=-16.409&lon=-71.537&radio=5000
```

**Respuesta:**
```json
{
  "ordenes_encontradas": 3,
  "resultados": [
    {
      "orden_id": 15,
      "descripcion": "Paquete electrónico",
      "distancia_metros": 450,
      "ultima_ubicacion": {
        "lat": -16.408,
        "lon": -71.536
      }
    }
  ]
}
```

---

## 7. Validaciones y Reglas de Negocio

### 7.1 Validaciones de Entrada (Pydantic)

```python
class ClienteCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: str = Field(...)  # Validación de formato email
    telefono: Optional[str] = Field(None)
    direccion: Optional[str] = Field(None)

class TrackingCreate(BaseModel):
    latitud: float = Field(..., ge=-90, le=90)    # Rango válido
    longitud: float = Field(..., ge=-180, le=180) # Rango válido
    velocidad_kmh: Optional[float] = Field(None, ge=0)
```

### 7.2 Prevención de SQL Injection

```python
# Whitelist de campos permitidos
CAMPOS_ORDEN_PERMITIDOS = {
    "id", "cliente_id", "descripcion", "estado",
    "direccion_origen", "direccion_destino",
    "fecha_creacion", "fecha_actualizacion"
}

@staticmethod
def validar_campos(campos: str) -> str:
    """Valida campos contra whitelist"""
    campos_solicitados = [c.strip() for c in campos.split(",")]
    for campo in campos_solicitados:
        if campo not in CAMPOS_ORDEN_PERMITIDOS:
            raise ValueError(f"Campo no permitido: {campo}")
    return ", ".join(campos_solicitados)
```

### 7.3 Transiciones de Estado

```python
# Estados válidos y sus transiciones permitidas
TRANSICIONES_ESTADO = {
    "Pendiente": ["En Proceso", "Cancelado"],
    "En Proceso": ["En Tránsito", "Cancelado"],
    "En Tránsito": ["Entregado", "Cancelado"],
    "Entregado": [],  # Estado final
    "Cancelado": []   # Estado final
}
```

### 7.4 Validaciones Geoespaciales

- Coordenadas dentro del rango válido (-90 a 90 latitud, -180 a 180 longitud)
- Radio de búsqueda máximo: 50,000 metros
- Formato GeoJSON estándar para ubicaciones

---

## 8. Seguridad

### 8.1 CORS (Cross-Origin Resource Sharing)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En producción: especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> ⚠️ **Nota**: En producción, configurar `allow_origins` con dominios específicos.

### 8.2 Credenciales de Base de Datos

Las credenciales se manejan mediante variables de entorno:

```python
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5433"),
    "database": os.getenv("POSTGRES_DB", "logistics_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres123")
}
```

### 8.3 Recomendaciones para Producción

| Aspecto | Implementación Recomendada |
|---------|---------------------------|
| Autenticación | JWT tokens con OAuth2 |
| Rate Limiting | 100 requests/minuto por IP |
| HTTPS | Certificado SSL/TLS |
| Logs | Auditoría de accesos |
| Secrets | Vault o AWS Secrets Manager |

---

## 9. Instalación y Despliegue

### 9.1 Requisitos del Sistema

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disco | 10 GB | 20 GB SSD |
| Docker | 20.10+ | Última versión |
| Python | 3.10 | 3.11+ |

### 9.2 Instalación Local (Desarrollo)

```bash
# 1. Clonar repositorio
git clone https://github.com/JorLOrT/BaseDeGatos2Final.git
cd HybridLogisticsHub

# 2. Iniciar bases de datos
docker-compose up -d

# 3. Crear entorno virtual (opcional pero recomendado)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Inicializar base de datos
python init_db.py

# 6. Iniciar servidor
python -m uvicorn main:app --reload --port 8000
```

### 9.3 Despliegue con Docker Compose

```yaml
# docker-compose.yml (producción)
services:
  postgres:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: logistics_db
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  mongodb:
    image: mongo:8
    environment:
      MONGO_INITDB_DATABASE: logistics_db
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      POSTGRES_HOST: postgres
      MONGO_HOST: mongodb
    depends_on:
      - postgres
      - mongodb
    restart: unless-stopped
```

### 9.4 Verificación de Instalación

```bash
# Verificar contenedores
docker ps

# Verificar conexión PostgreSQL
docker exec -it logistics_postgres psql -U postgres -d logistics_db -c "SELECT count(*) FROM ordenes;"

# Verificar conexión MongoDB
docker exec -it logistics_mongodb mongosh logistics_db --eval "db.tracking.countDocuments()"

# Verificar API
curl http://localhost:8000/
```

---

## 10. Conclusiones

### 10.1 Ventajas del Sistema

| Aspecto | Beneficio |
|---------|-----------|
| **Arquitectura Híbrida** | Aprovecha fortalezas de cada BD |
| **Separación de Capas** | Código mantenible y escalable |
| **API REST** | Integración fácil con otros sistemas |
| **Documentación Auto-generada** | Swagger/OpenAPI automático |
| **Containerización** | Despliegue reproducible |
| **Tracking Visual** | Experiencia de usuario intuitiva |

### 10.2 Limitaciones Actuales

| Limitación | Impacto | Solución Futura |
|------------|---------|-----------------|
| Sin autenticación | Acceso público a la API | Implementar JWT |
| OpenRouteService gratuito | Límite de requests | API key premium o self-hosted |
| Conexiones síncronas | Escalabilidad limitada | Pool de conexiones async |
| Sin caché | Consultas repetidas costosas | Redis para caching |

### 10.3 Mejoras Propuestas

1. **Corto Plazo**
   - Implementar autenticación JWT
   - Agregar paginación a todos los endpoints
   - Implementar rate limiting

2. **Mediano Plazo**
   - Migrar a conexiones asíncronas (asyncpg, motor)
   - Implementar WebSockets para tracking real-time
   - Agregar sistema de notificaciones

3. **Largo Plazo**
   - Kubernetes para orquestación
   - Microservicios separados por dominio
   - Machine Learning para optimización de rutas

### 10.4 Lecciones Aprendidas

1. **Arquitectura híbrida es viable** para sistemas con requisitos mixtos
2. **GeoJSON + 2dsphere** facilitan consultas geoespaciales complejas
3. **FastAPI + Pydantic** aceleran el desarrollo con validación automática
4. **Docker Compose** simplifica el entorno de desarrollo

---

## 📎 Anexos

### A. Estructura de Archivos

```
HybridLogisticsHub/
├── main.py                 # Punto de entrada
├── init_db.py              # Inicialización
├── requirements.txt        # Dependencias
├── docker-compose.yml      # Contenedores
├── README.md               # Guía rápida
├── database/
│   ├── __init__.py
│   ├── connection.py       # Conexiones BD
│   └── init.py             # Creación tablas
├── models/
│   ├── __init__.py
│   └── schemas.py          # Modelos Pydantic
├── routes/
│   ├── __init__.py
│   ├── clientes.py
│   ├── ordenes.py
│   ├── tracking.py
│   ├── geoespacial.py
│   └── sistema.py
├── services/
│   ├── __init__.py
│   ├── clientes.py
│   ├── ordenes.py
│   ├── tracking.py
│   └── geoespacial.py
├── static/
│   └── tracking_visual.html
└── docs/
    ├── MANUAL_USUARIO.md
    └── MEMORIA_TECNICA.md
```

### B. Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Host PostgreSQL | localhost |
| `POSTGRES_PORT` | Puerto PostgreSQL | 5433 |
| `POSTGRES_DB` | Base de datos | logistics_db |
| `POSTGRES_USER` | Usuario | postgres |
| `POSTGRES_PASSWORD` | Contraseña | postgres123 |
| `MONGO_HOST` | Host MongoDB | localhost |
| `MONGO_PORT` | Puerto MongoDB | 27017 |
| `MONGO_DB` | Base de datos | logistics_db |

---

*Curso: Sistemas de Bases de Datos II - Universidad de La Salle*

*Fecha: Noviembre 2025*
