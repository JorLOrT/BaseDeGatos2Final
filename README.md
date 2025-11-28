# HybridLogisticsHub 🚚

Sistema de logística con arquitectura de bases de datos híbrida que combina **PostgreSQL** (datos transaccionales) y **MongoDB** (datos geoespaciales y tracking en tiempo real).

## 📋 Tabla de Contenidos

- [Arquitectura](#-arquitectura)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [API Endpoints](#-api-endpoints)
- [Estructura del Proyecto](#-estructura-del-proyecto)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (REST API)                       │
├─────────────────────────────────────────────────────────────┤
│                          │                                  │
│    ┌────────────────────┴────────────────────┐              │
│    │                                         │              │
│    ▼                                         ▼              │
│ ┌──────────────────┐              ┌──────────────────┐      │
│ │   PostgreSQL     │              │    MongoDB       │      │
│ │   (psycopg2)     │              │   (PyMongo)      │      │
│ ├──────────────────┤              ├──────────────────┤      │
│ │ • Clientes       │              │ • Tracking       │      │
│ │ • Órdenes        │              │ • Ubicaciones    │      │
│ │ • Transacciones  │              │ • Geoespacial    │      │
│ │   ACID           │              │   (2dsphere)     │      │
│ └──────────────────┘              └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Bases de Datos

| Base de Datos | Uso | Driver |
|---------------|-----|--------|
| **PostgreSQL** | Datos transaccionales (clientes, órdenes) con ACID | `psycopg2` |
| **MongoDB** | Tracking GPS y búsquedas geoespaciales | `PyMongo` |

---

## 📦 Requisitos

- Python 3.9+
- Docker y Docker Compose (recomendado)
- O instalaciones locales de PostgreSQL y MongoDB

---

## 🚀 Instalación

### 1. Clonar/Navegar al proyecto

```bash
cd HybridLogisticsHub
```

### 2. Levantar las bases de datos con Docker

```bash
docker-compose up -d
```

Esto iniciará:
- **PostgreSQL** en `localhost:5432`
- **MongoDB** en `localhost:27017`

### 3. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 4. Inicializar las bases de datos

```bash
python init_db.py
```

Este script:
- Crea las tablas `clientes` y `ordenes` en PostgreSQL
- Crea la colección `tracking` en MongoDB
- Configura el índice geoespacial `2dsphere`
- Opcionalmente inserta datos de ejemplo

### 5. Ejecutar la API

```bash
python main.py
```

O con uvicorn directamente:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en: **http://localhost:8000**

Documentación interactiva: **http://localhost:8000/docs**

---

## 📖 Uso

### Verificar estado del sistema

```bash
curl http://localhost:8000/health
```

### Crear una orden con cliente (Transacción ACID)

```bash
curl -X POST http://localhost:8000/ordenes \
  -H "Content-Type: application/json" \
  -d '{
    "cliente": {
      "nombre": "María García",
      "email": "maria.garcia@email.com",
      "telefono": "+57 310 555 1234",
      "direccion": "Carrera 7 #45-12, Bogotá"
    },
    "descripcion": "Paquete frágil - electrodomésticos",
    "direccion_origen": "Bodega Norte, Bogotá",
    "direccion_destino": "Calle 80 #15-30, Medellín"
  }'
```

### Registrar ubicación GPS (Tracking)

```bash
curl -X POST http://localhost:8000/tracking/1 \
  -H "Content-Type: application/json" \
  -d '{
    "latitud": 4.7110,
    "longitud": -74.0721,
    "velocidad_kmh": 60.5,
    "dispositivo_id": "GPS-001"
  }'
```

### Consulta Federada (PostgreSQL + MongoDB)

```bash
curl http://localhost:8000/ordenes/1/ubicacion
```

### Búsqueda Geoespacial

```bash
curl "http://localhost:8000/busqueda-cercana?latitud=4.7110&longitud=-74.0721&radio_metros=5000"
```

### Actualizar estado (con sincronización)

```bash
curl -X PUT http://localhost:8000/ordenes/1/estado \
  -H "Content-Type: application/json" \
  -d '{"estado": "Entregado"}'
```

---

## 🔌 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Información de la API |
| `GET` | `/health` | Estado de las conexiones |
| `POST` | `/ordenes` | Crear orden + cliente (transacción ACID) |
| `GET` | `/ordenes` | Listar órdenes |
| `POST` | `/tracking/{orden_id}` | Registrar ubicación GPS |
| `GET` | `/ordenes/{orden_id}/ubicacion` | Consulta federada (PG + Mongo) |
| `GET` | `/busqueda-cercana` | Búsqueda geoespacial por radio |
| `PUT` | `/ordenes/{orden_id}/estado` | Actualizar estado (+ sincronización) |

---

## 📁 Estructura del Proyecto

```
HybridLogisticsHub/
├── main.py              # API FastAPI con todos los endpoints
├── db.py                # Módulo de conexión a PostgreSQL y MongoDB
├── init_db.py           # Script de inicialización de bases de datos
├── requirements.txt     # Dependencias de Python
├── docker-compose.yml   # Configuración Docker para las BDs
└── README.md            # Este archivo
```

---

## 🗄️ Modelado de Datos

### PostgreSQL - Tabla `clientes`

```sql
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(20),
    direccion TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### PostgreSQL - Tabla `ordenes`

```sql
CREATE TABLE ordenes (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id),
    descripcion TEXT NOT NULL,
    estado VARCHAR(50) DEFAULT 'Pendiente',
    direccion_origen TEXT NOT NULL,
    direccion_destino TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### MongoDB - Colección `tracking`

```json
{
    "_id": "ObjectId",
    "orden_id": 1,
    "ubicacion": {
        "type": "Point",
        "coordinates": [-74.0721, 4.7110]
    },
    "timestamp": "ISODate",
    "activo": true,
    "velocidad_kmh": 60.5,
    "metadata": {
        "dispositivo_id": "GPS-001",
        "precision_metros": 5.0
    }
}
```

---

## 🔧 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | Host de PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` |
| `POSTGRES_DB` | Base de datos | `logistics_db` |
| `POSTGRES_USER` | Usuario | `postgres` |
| `POSTGRES_PASSWORD` | Contraseña | `postgres123` |
| `MONGO_HOST` | Host de MongoDB | `localhost` |
| `MONGO_PORT` | Puerto de MongoDB | `27017` |
| `MONGO_DB` | Base de datos | `logistics_db` |

---

## 📝 Notas Técnicas

### Transacciones ACID (PostgreSQL)
El endpoint `POST /ordenes` implementa transacciones con `commit/rollback` para garantizar que no se cree una orden si falla la creación del cliente.

### Índices Geoespaciales (MongoDB)
Se utiliza un índice `2dsphere` en el campo `ubicacion` para búsquedas eficientes por proximidad usando `$nearSphere`.

### Sincronización entre BDs
Cuando una orden cambia a estado "Entregado", se dispara un evento que actualiza `activo: false` en los documentos de tracking correspondientes en MongoDB.

---

## 📄 Licencia

Este proyecto es de uso académico para el curso de Sistemas de Bases de Datos II.
