"""
init_db.py - Script de inicialización de bases de datos
Crea tablas en PostgreSQL e índices geoespaciales en MongoDB
"""

import random
from datetime import datetime, timedelta
from database import get_postgres_connection, get_mongo_database
from database.init import init_postgres, init_mongodb


# Almacén Central - Arequipa
ALMACEN_CENTRAL = {
    "nombre": "Almacén Central Arequipa",
    "direccion": "Av. Industrial 100, Parque Industrial, Arequipa",
    "coordenadas": [-71.5347295522896, -16.4025001658711]  # [lng, lat]
}

# Direcciones de destino en Arequipa
DIRECCIONES_AREQUIPA = [
    "Calle Mercaderes 123, Cercado, Arequipa",
    "Av. Ejército 456, Cayma, Arequipa",
    "Calle San Juan de Dios 789, Cercado, Arequipa",
    "Av. Dolores 321, José Luis Bustamante y Rivero, Arequipa",
    "Calle Álvarez Thomas 654, Yanahuara, Arequipa",
    "Av. Lambramani 987, Cercado, Arequipa",
    "Calle Ugarte 147, Cercado, Arequipa",
    "Av. Cayma 258, Cayma, Arequipa",
    "Calle Bolívar 369, Cercado, Arequipa",
    "Av. Parra 741, Miraflores, Arequipa",
    "Calle La Merced 852, Cercado, Arequipa",
    "Av. Goyeneche 963, Cercado, Arequipa",
    "Calle Puente Grau 174, Cercado, Arequipa",
    "Av. Independencia 285, Cercado, Arequipa",
    "Calle Rivero 396, Cercado, Arequipa",
    "Av. Venezuela 417, Cerro Colorado, Arequipa",
    "Calle Siglo XX 528, Cercado, Arequipa",
    "Av. Arequipa 639, Sachaca, Arequipa",
    "Calle Colón 741, Cercado, Arequipa",
    "Av. Progreso 852, Miraflores, Arequipa",
]

# Coordenadas de diferentes zonas de Arequipa [lng, lat]
COORDENADAS_AREQUIPA = [
    [-71.5375, -16.3989],  # Plaza de Armas
    [-71.5580, -16.3850],  # Cayma
    [-71.5280, -16.4180],  # José Luis Bustamante
    [-71.5450, -16.3920],  # Yanahuara
    [-71.5100, -16.4050],  # Miraflores
    [-71.5600, -16.4100],  # Cerro Colorado
    [-71.5700, -16.4200],  # Sachaca
    [-71.5200, -16.3900],  # Cercado Norte
    [-71.5400, -16.4300],  # Socabaya
    [-71.4900, -16.4000],  # Paucarpata
    [-71.5150, -16.4150],  # Mariano Melgar
    [-71.5050, -16.3850],  # Alto Selva Alegre
    [-71.5300, -16.3800],  # Selva Alegre
    [-71.5650, -16.3950],  # Zamácola
    [-71.5500, -16.4050],  # Umacollo
]

# Nombres de clientes
NOMBRES = [
    "Carlos", "María", "Juan", "Ana", "Pedro", "Lucía", "Miguel", "Carmen", 
    "José", "Rosa", "Luis", "Elena", "Fernando", "Patricia", "Ricardo", 
    "Silvia", "Alberto", "Gabriela", "Jorge", "Mónica", "Andrés", "Claudia",
    "Eduardo", "Verónica", "Roberto", "Diana", "Francisco", "Laura", "Manuel", "Sofía"
]

APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "González", "Hernández", 
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Reyes", "Morales", "Jiménez", "Ruiz", "Álvarez", "Romero",
    "Vargas", "Castillo", "Mendoza", "Quispe", "Mamani", "Chávez", "Huanca"
]

# Descripciones de paquetes
DESCRIPCIONES_PAQUETES = [
    "Electrodoméstico - Televisor 55 pulgadas",
    "Electrodoméstico - Refrigeradora",
    "Electrodoméstico - Lavadora automática",
    "Electrodoméstico - Microondas",
    "Electrónico - Laptop",
    "Electrónico - Smartphone",
    "Electrónico - Tablet",
    "Electrónico - Auriculares inalámbricos",
    "Mueble - Silla de oficina",
    "Mueble - Mesa de centro",
    "Mueble - Estante de madera",
    "Ropa - Paquete de vestimenta",
    "Ropa - Calzado deportivo",
    "Alimentos - Canasta de productos",
    "Libros - Colección educativa",
    "Juguetes - Set de construcción",
    "Deportes - Bicicleta",
    "Deportes - Equipamiento de gimnasio",
    "Hogar - Set de ollas",
    "Hogar - Juego de sábanas",
    "Farmacia - Medicamentos",
    "Mascotas - Alimento para perros",
    "Ferretería - Herramientas eléctricas",
    "Cosmética - Kit de belleza",
    "Oficina - Impresora multifuncional",
]

ESTADOS_ORDEN = ["Pendiente", "En Proceso", "En Tránsito", "Entregado", "Cancelado"]


def generate_random_coordinate_near(base_coord, radius_km=0.5):
    """
    Genera una coordenada aleatoria cerca de una coordenada base.
    radius_km: radio en kilómetros
    """
    # Aproximación: 1 grado ≈ 111 km
    delta = radius_km / 111.0
    lng = base_coord[0] + random.uniform(-delta, delta)
    lat = base_coord[1] + random.uniform(-delta, delta)
    return [lng, lat]


def insert_sample_data():
    """
    Inserta 100 elementos de ejemplo variados en Arequipa.
    """
    print("\n" + "=" * 50)
    print("Insertando 100 elementos de ejemplo en Arequipa...")
    print("=" * 50)
    
    conn = get_postgres_connection()
    cursor = conn.cursor()
    
    try:
        clientes_creados = []
        ordenes_creadas = []
        
        # Crear 30 clientes variados
        print("\n📦 Creando 30 clientes...")
        for i in range(30):
            nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
            email = f"cliente{i+1}_{nombre.lower().replace(' ', '.')}@email.com"
            telefono = f"+51 9{random.randint(10000000, 99999999)}"
            direccion = random.choice(DIRECCIONES_AREQUIPA)
            
            cursor.execute("""
                INSERT INTO clientes (nombre, email, telefono, direccion)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id;
            """, (nombre, email, telefono, direccion))
            
            result = cursor.fetchone()
            if result:
                clientes_creados.append(result[0])
        
        conn.commit()
        print(f"✓ {len(clientes_creados)} clientes creados")
        
        if not clientes_creados:
            print("⚠ No se crearon clientes nuevos (pueden existir)")
            cursor.execute("SELECT id FROM clientes LIMIT 30;")
            clientes_creados = [row[0] for row in cursor.fetchall()]
        
        # Crear 100 órdenes
        print("\n📦 Creando 100 órdenes...")
        for i in range(100):
            cliente_id = random.choice(clientes_creados)
            descripcion = random.choice(DESCRIPCIONES_PAQUETES)
            estado = random.choice(ESTADOS_ORDEN)
            direccion_destino = random.choice(DIRECCIONES_AREQUIPA)
            
            cursor.execute("""
                INSERT INTO ordenes (cliente_id, descripcion, estado, direccion_origen, direccion_destino)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (cliente_id, descripcion, estado, ALMACEN_CENTRAL["direccion"], direccion_destino))
            
            orden_id = cursor.fetchone()[0]
            ordenes_creadas.append((orden_id, estado))
        
        conn.commit()
        print(f"✓ {len(ordenes_creadas)} órdenes creadas")
        
        # Insertar tracking en MongoDB
        print("\n📍 Creando registros de tracking en MongoDB...")
        db = get_mongo_database()
        tracking = db["tracking"]
        
        documentos_tracking = []
        dispositivos = [f"GPS-{str(i).zfill(3)}" for i in range(1, 21)]
        
        for orden_id, estado in ordenes_creadas:
            # Número de puntos de tracking según estado
            if estado == "Pendiente":
                num_puntos = 1  # Solo ubicación inicial (almacén)
            elif estado == "En Proceso":
                num_puntos = random.randint(1, 3)
            elif estado == "En Tránsito":
                num_puntos = random.randint(3, 8)
            elif estado == "Entregado":
                num_puntos = random.randint(5, 12)
            else:  # Cancelado
                num_puntos = random.randint(1, 3)
            
            # Generar puntos de tracking
            base_time = datetime.utcnow() - timedelta(days=random.randint(0, 7))
            dispositivo = random.choice(dispositivos)
            
            for j in range(num_puntos):
                # Primer punto siempre es el almacén central
                if j == 0:
                    coord = ALMACEN_CENTRAL["coordenadas"]
                else:
                    # Puntos intermedios: coordenadas aleatorias en Arequipa
                    base_zona = random.choice(COORDENADAS_AREQUIPA)
                    coord = generate_random_coordinate_near(base_zona, radius_km=0.3)
                
                timestamp = base_time + timedelta(hours=j * random.randint(1, 4))
                
                doc = {
                    "orden_id": orden_id,
                    "ubicacion": {
                        "type": "Point",
                        "coordinates": coord
                    },
                    "timestamp": timestamp,
                    "activo": (j == num_puntos - 1),  # Solo el último está activo
                    "velocidad_kmh": round(random.uniform(20, 80), 1) if j > 0 else 0,
                    "rumbo": round(random.uniform(0, 360), 1),
                    "metadata": {
                        "dispositivo_id": dispositivo,
                        "precision_metros": round(random.uniform(3, 15), 1)
                    }
                }
                documentos_tracking.append(doc)
        
        # Insertar todos los documentos de tracking
        if documentos_tracking:
            result = tracking.insert_many(documentos_tracking)
            print(f"✓ {len(result.inserted_ids)} documentos de tracking insertados")
        
        # Resumen
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE DATOS INSERTADOS:")
        print("=" * 50)
        print(f"  • Clientes: {len(clientes_creados)}")
        print(f"  • Órdenes: {len(ordenes_creadas)}")
        print(f"  • Registros de tracking: {len(documentos_tracking)}")
        print(f"\n  📍 Almacén Central: {ALMACEN_CENTRAL['direccion']}")
        print(f"     Coordenadas: {ALMACEN_CENTRAL['coordenadas']}")
        
        # Conteo por estado
        estados_conteo = {}
        for _, estado in ordenes_creadas:
            estados_conteo[estado] = estados_conteo.get(estado, 0) + 1
        print("\n  📦 Órdenes por estado:")
        for estado, conteo in estados_conteo.items():
            print(f"     - {estado}: {conteo}")
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Error insertando datos de ejemplo: {e}")
        raise
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
        print("Inicializando PostgreSQL...")
        init_postgres()
        print("✓ PostgreSQL inicializado\n")
        
        print("Inicializando MongoDB...")
        init_mongodb()
        print("✓ MongoDB inicializado\n")
        
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
