# 🚚 HybridLogisticsHub

Sistema de gestión logística con arquitectura híbrida **PostgreSQL + MongoDB** y visualización de tracking en tiempo real.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue)
![MongoDB](https://img.shields.io/badge/MongoDB-8-green)

---

## 📋 Requisitos Previos

- **Python 3.10+**
- **Docker Desktop** (para las bases de datos)
- **Git**

---

## 🚀 Instalación y Ejecución

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/HybridLogisticsHub.git
cd BaseDeGatos2Final
```

### 2️⃣ Iniciar las bases de datos con Docker

```bash
docker-compose up -d
```

Esto levanta:
- **PostgreSQL** en el puerto `5433`
- **MongoDB** en el puerto `27017`

> ⚠️ Espera unos segundos a que los contenedores estén listos antes de continuar.

### 3️⃣ Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 4️⃣ Inicializar la base de datos

```bash
python init_db.py
```

Esto crea las tablas, índices y genera **100 órdenes de ejemplo** con coordenadas de Arequipa.

### 5️⃣ Ejecutar el servidor

```bash
python -m uvicorn main:app --reload --port 8000
```

### 6️⃣ ¡Listo! Accede a la aplicación

| Recurso | URL |
|---------|-----|
| 🗺️ **Tracking Visual** | http://localhost:8000/static/tracking_visual.html |
| 📖 **Documentación API** | http://localhost:8000/docs |
| 📖 **Documentación (ReDoc)** | http://localhost:8000/redoc |

---

## 🗺️ Tracking Visual

La página de tracking permite:

- ✅ Ver todas las órdenes pendientes y en tránsito
- ✅ Simular entregas individuales o múltiples
- ✅ Ver rutas reales por calles (OpenRouteService)
- ✅ Seguimiento en tiempo real con vehículos animados
- ✅ Progreso y velocidad de cada entrega

---

## 📁 Estructura del Proyecto

```
HybridLogisticsHub/
├── main.py                 # Punto de entrada FastAPI
├── init_db.py              # Script de inicialización de BD
├── requirements.txt        # Dependencias Python
├── docker-compose.yml      # Contenedores PostgreSQL y MongoDB
│
├── database/               # Conexiones y configuración de BD
│   ├── connection.py       # Conexiones PostgreSQL y MongoDB
│   └── init.py             # Funciones de inicialización
│
├── models/                 # Modelos Pydantic
│   └── schemas.py          # Esquemas de datos
│
├── routes/                 # Endpoints de la API
│   ├── clientes.py         # CRUD de clientes
│   ├── ordenes.py          # CRUD de órdenes
│   ├── tracking.py         # Seguimiento de envíos
│   ├── geoespacial.py      # Consultas geoespaciales
│   └── sistema.py          # Health check y estadísticas
│
├── services/               # Lógica de negocio
│   ├── clientes.py         # Servicio de clientes
│   ├── ordenes.py          # Servicio de órdenes
│   ├── tracking.py         # Servicio de tracking
│   └── geoespacial.py      # Servicio geoespacial
│
└── static/                 # Archivos estáticos
    └── tracking_visual.html # Página de tracking visual
```

---

## 🔌 API Endpoints

### Sistema
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/stats` | Estadísticas del sistema |

### Clientes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/clientes` | Listar clientes |
| GET | `/clientes/{id}` | Obtener cliente |
| POST | `/clientes` | Crear cliente |
| PUT | `/clientes/{id}` | Actualizar cliente |
| DELETE | `/clientes/{id}` | Eliminar cliente |

### Órdenes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/ordenes` | Listar órdenes |
| GET | `/ordenes/{id}` | Obtener orden |
| POST | `/ordenes` | Crear orden |
| PUT | `/ordenes/{id}` | Actualizar orden |
| PUT | `/ordenes/{id}/estado` | Cambiar estado de orden |
| DELETE | `/ordenes/{id}` | Eliminar orden |

### Tracking
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/tracking/{orden_id}` | Obtener tracking de orden |
| POST | `/tracking` | Registrar evento de tracking |
| GET | `/tracking/{orden_id}/historial` | Historial de tracking |

### Geoespacial
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/geo/cercanas` | Órdenes cercanas a un punto |
| GET | `/geo/zona` | Órdenes en una zona |

---

## ⚙️ Configuración

Las conexiones a las bases de datos se configuran en `database/connection.py`:

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `POSTGRES_HOST` | localhost | Host de PostgreSQL |
| `POSTGRES_PORT` | 5433 | Puerto de PostgreSQL |
| `POSTGRES_DB` | logistics_db | Base de datos |
| `POSTGRES_USER` | postgres | Usuario |
| `POSTGRES_PASSWORD` | postgres123 | Contraseña |
| `MONGO_HOST` | localhost | Host de MongoDB |
| `MONGO_PORT` | 27017 | Puerto de MongoDB |
| `MONGO_DB` | logistics_db | Base de datos |

---

## 🛑 Detener el Sistema

Para detener los contenedores de Docker:

```bash
docker-compose down
```

Para detener y eliminar los volúmenes (borra todos los datos):

```bash
docker-compose down -v
```

---

## 👥 Autores

- Desarrollado para el curso de **Sistemas de Bases de Datos II**
- Universidad de La Salle

---

## 📄 Licencia

Hecho por puro pavipollo y Jorge.
