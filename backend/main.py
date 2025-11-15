"""
Servidor Backend para el Sistema Integral de Vigilancia Vehicular (SIVC)
del Tecnológico de Culiacán.

Este servidor maneja la autenticación de los guardias (empleados) y
el proceso de dos pasos para el registro de incidencias:
1. Consulta (GET): Identifica al conductor basado en la placa.
2. Reporte (POST): Registra la incidencia y aplica la lógica de negocio.

Tecnologías usadas:
- FastAPI: Framework web asíncrono para Python, ideal para APIs rápidas.
- asyncpg: Conector asíncrono para PostgreSQL, muy eficiente.
- bcrypt: Librería para encriptar y verificar contraseñas de forma segura.
- dotenv: Para cargar variables de entorno desde un archivo .env.

Instrucciones para ejecutar el servidor:
1. Asegúrate de tener Python 3.8+ instalado.
2. Instala las dependencias: pip install -r requirements.txt
3. Configura el archivo .env con la URL de tu base de datos PostgreSQL.
4. Ejecuta el servidor con: uvicorn main:app --reload --host

"""

# --- 1. Importaciones de Librerías ---
import os  # Para leer variables de entorno (el .env)
import bcrypt  # Para encriptar y verificar contraseñas (hashes)
import asyncpg  # Conector asíncrono para PostgreSQL (muy rápido)
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel  # Para validar los datos JSON que envía Flutter
from dotenv import load_dotenv  # Para cargar el archivo .env
from fastapi.middleware.cors import CORSMiddleware  # Para permitir la conexión desde Flutter

# Carga el archivo .env (que contiene la URL de la base de datos)
load_dotenv()

# --- 2. Configuración de la Aplicación FastAPI ---
app = FastAPI(
    title="Servidor SIVC (Tec Culiacán)",
    description="Maneja el login y el registro de incidencias."
)

# --- 3. Configuración de CORS (Cross-Origin Resource Sharing) ---
# Esto es CRUCIAL. Le da permiso al celular (o navegador web)
# para que pueda hacer peticiones a este servidor, aunque estén en "dominios" diferentes.
app.add_middleware(
    CORSMiddleware,
    # "*" significa "permitir cualquier origen". Perfecto para desarrollo.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite métodos GET, POST, etc.
    allow_headers=["*"],  # Permite cualquier cabecera (como Content-Type)
)

# --- 4. Modelos de Datos (Pydantic) ---
# FastAPI usa esto para validar automáticamente que el JSON de Flutter
# venga con los campos correctos.

class LoginRequest(BaseModel):
    """Define la estructura esperada para el JSON de /login"""
    numero_empleado: str
    password: str

class IncidenciaRequest(BaseModel):
    """Define la estructura esperada para el JSON de /reportar"""
    placa: str  # La app envía la placa LIMPIA (ej: VJM131C)
    latitud: float
    longitud: float
    id_empleado: str  # Este es el 'numero_empleado' (Ej: g1)

# --- 5. Manejo de la Conexión a la Base de Datos (PostgreSQL) ---

async def get_db_pool(request: Request):
    """
    Función de dependencia. FastAPI la llamará en cada endpoint
    para inyectar el pool de conexiones de la base de datos.
    """
    return request.app.state.pool

@app.on_event("startup")
async def startup_db_client():
    """
    Se ejecuta UNA SOLA VEZ cuando 'uvicorn' arranca.
    Crea el "pool" de conexiones a PostgreSQL. Un pool es más eficiente
    que crear una conexión nueva para cada petición.
    """
    print("--- VERIFICANDO CONEXIÓN ---")
    # Lee la URL de conexión desde el archivo .env
    db_url = os.environ.get("DATABASE_URL")
    print(f"LEYENDO DATABASE_URL: {db_url}")
    print("---------------------------")
    
    if not db_url:
        print("ERROR CRÍTICO: No se encontró DATABASE_URL en el archivo .env")
        return

    app.state.pool = await asyncpg.create_pool(
        db_url,
        min_size=1,
        max_size=10
    )
    print("Pool de conexiones a PostgreSQL creado.")

@app.on_event("shutdown")
async def shutdown_db_client():
    """
    Se ejecuta UNA SOLA VEZ cuando 'uvicorn' se detiene (ej: con Ctrl+C).
    Cierra todas las conexiones del pool limpiamente.
    """
    if hasattr(app.state, 'pool'):
        await app.state.pool.close()
        print("Pool de conexiones cerrado.")


# --- 6. Endpoints (Rutas de la API) ---

@app.get("/")
async def root():
    """Ruta raíz de bienvenida. Útil para probar si el servidor está en línea."""
    return {"mensaje": "Servidor SIVC del Tec Culiacán está en línea."}

@app.post("/login")
async def login(login_request: LoginRequest, pool = Depends(get_db_pool)):
    """
    Endpoint para autenticar a un empleado (guardia).
    Recibe el 'numero_empleado' y 'password' en texto plano.
    """
    async with pool.acquire() as conn:
        # Busca al empleado por su ID único
        empleado = await conn.fetchrow(
            "SELECT * FROM empleados WHERE numero_empleado = $1",
            login_request.numero_empleado
        )

        if not empleado:
            # Si no existe, devuelve 404
            raise HTTPException(status_code=404, detail="ID de Empleado no encontrado.")

        # --- Verificación de Contraseña (bcrypt) ---
        # 1. Convierte la contraseña de Flutter (str) a bytes (utf-8)
        password_bytes = login_request.password.encode('utf-8')
        
        # 2. Convierte el hash de la BD (str) a bytes (utf-8)
        hash_bytes = empleado['password_hash'].encode('utf-8')
        
        # 3. bcrypt compara los dos hashes. Es la única forma segura.
        password_valida = bcrypt.checkpw(password_bytes, hash_bytes)
        
        # Imprime el resultado en la consola del servidor (para depuración)
        print(f"--- COMPROBANDO LOGIN: {password_valida} ---")

        if not password_valida:
            # Si bcrypt dice 'False', devuelve 401
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

        # Si todo es correcto, devuelve 200 OK con los datos del empleado
        return {
            "mensaje": "Login exitoso",
            "nombre": empleado['nombre_completo'],
            "numero_empleado": empleado['numero_empleado']
        }

# --- ENDPOINT DE CONSULTA (PASO 1) ---
@app.get("/vehiculo/{placa}")
async def get_info_vehiculo(placa: str, pool = Depends(get_db_pool)):
    """
    Endpoint para SOLO CONSULTAR la información de una placa.
    No registra ninguna incidencia. Cumple la regla de "primero identificar".
    La 'placa' llega como un parámetro en la URL (ej: /vehiculo/VJM131C)
    """
    print(f"--- CONSULTANDO PLACA (GET): {placa} ---")
    async with pool.acquire() as conn:
        
        # --- CONSULTA SQL ROBUSTA ---
        # Esta consulta busca la placa del conductor:
        # 1. JOIN: Une 'vehiculos' (v) con 'conductores' (c).
        # 2. WHERE: Limpia la placa de la BD (TRIM, REPLACE, UPPER) y la
        #    compara con la placa limpia (en mayúsculas) que envía la app.
        # Esta es la consulta que probamos en pgAdmin y SÍ FUNCIONA.
        conductor_data = await conn.fetchrow(
            """
            SELECT v.placa, v.modelo, v.estado, c.nombre_completo
            FROM vehiculos v 
            JOIN conductores c ON v.id_conductor = c.id_conductor
            WHERE TRIM(UPPER(REPLACE(REPLACE(v.placa, '-', ''), ' ', ''))) = $1
            """, 
            placa.upper() # Aseguramos que la placa de entrada también esté en mayúsculas
        )
        
        if not conductor_data:
            # Si la consulta (con el JOIN) no devuelve filas, es 404.
            print(f"ALERTA 404: No se encontró la placa '{placa}' en la BD o no tiene conductor asignado.")
            raise HTTPException(status_code=404, detail=f"Placa '{placa}' no registrada o sin conductor asignado.")
        
        print(f"PLACA ENCONTRADA: {conductor_data['placa']} (Conductor: {conductor_data['nombre_completo']})")
        
        # Busca cuántas faltas tiene ya registradas
        conteo = await conn.fetchval(
            "SELECT COUNT(*) FROM incidencias WHERE placa = $1",
            conductor_data['placa'] # Usamos la placa real de la BD (con guiones/espacios)
        )

        # Devuelve el JSON con toda la info a la app Flutter
        return {
            "placa": conductor_data['placa'],
            "modelo": conductor_data['modelo'],
            "estado": conductor_data['estado'],
            "nombre_conductor": conductor_data['nombre_completo'],
            "faltas_actuales": conteo
        }


# --- ENDPOINT DE REPORTE (PASO 2) ---
@app.post("/reportar")
async def reportar_incidencia(incidencia: IncidenciaRequest, pool = Depends(get_db_pool)):
    """
    Endpoint para REGISTRAR una nueva incidencia y aplicar la lógica de negocio (3 Faltas).
    Se ejecuta cuando el guardia presiona "Confirmar Falta".
    """
    print(f"--- REPORTANDO PLACA (POST): {incidencia.placa} ---")
    
    # 'async with conn.transaction()' es crucial.
    # Si algo falla (ej: el UPDATE), toda la operación (el INSERT)
    # se revierte (rollback). Es todo o nada.
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                # 1. Volvemos a buscar/validar al conductor (usando la misma consulta robusta)
                conductor_data = await conn.fetchrow(
                    """
                    SELECT v.placa, v.estado, c.nombre_completo, c.telefono
                    FROM vehiculos v 
                    JOIN conductores c ON v.id_conductor = c.id_conductor
                    WHERE TRIM(UPPER(REPLACE(REPLACE(v.placa, '-', ''), ' ', ''))) = $1
                    """, 
                    incidencia.placa.upper()
                )

                if not conductor_data:
                    # Este chequeo es por seguridad, aunque la app ya lo hizo
                    raise HTTPException(status_code=404, detail=f"Placa '{incidencia.placa}' no registrada.")

                # De aquí en adelante, usamos la placa REAL de la BD (con guiones, ej: VJM131C)
                placa_real_db = conductor_data['placa']
                nombre_conductor = conductor_data['nombre_completo']

                # 2. REGLA: Verificar estado de bloqueo
                if conductor_data['estado'] == 'BLOQUEADO':
                    return {"mensaje": f"ACCESO DENEGADO. El vehículo de {nombre_conductor} ya se encuentra BLOQUEADO."}

                # 3. Obtener el ID numérico (PK) del empleado
                id_empleado_db = await conn.fetchval(
                    "SELECT id_empleado FROM empleados WHERE numero_empleado = $1",
                    incidencia.id_empleado
                )
                if not id_empleado_db:
                    raise HTTPException(status_code=404, detail="ID de Empleado no válido.")

                # 4. REGLA: Registrar la nueva incidencia
                await conn.execute(
                    """
                    INSERT INTO incidencias (placa, id_empleado, latitud, longitud, descripcion)
                    VALUES ($1, $2, $3, $4, 'Infracción registrada por app')
                    """,
                    placa_real_db,
                    id_empleado_db,
                    incidencia.latitud,
                    incidencia.longitud
                )

                # 5. Contar el total de incidencias (ahora incluye la que acabamos de registrar)
                conteo = await conn.fetchval(
                    "SELECT COUNT(*) FROM incidencias WHERE placa = $1",
                    placa_real_db
                )

                # 6. Aplicar la Lógica de Negocio (Tus reglas)
                
                # REGLA: 3ra incidencia = BLOQUEO
                if conteo >= 3:
                    await conn.execute(
                        "UPDATE vehiculos SET estado = 'BLOQUEADO' WHERE placa = $1",
                        placa_real_db
                    )
                    return {
                        "mensaje": f"¡BLOQUEO Y NOTIFICACIÓN! El vehículo de {nombre_conductor} tiene {conteo} faltas. Acceso Denegado."
                    }
                
                # REGLA: 1ra incidencia = AVISO
                elif conteo == 1:
                    return {
                        "mensaje": f"PRIMER AVISO: Falta #{conteo} registrada para {nombre_conductor}. (Se notifica a Admin y Conductor)"
                    }
                
                # Incidencias 2
                else: 
                    return {
                        "mensaje": f"ADVERTENCIA: Falta #{conteo} registrada para {nombre_conductor}. Próxima falta resultará en bloqueo."
                    }
            
            except Exception as e:
                # Si algo falla (ej: error SQL), la transacción hace "rollback"
                print(f"\n--- ERROR INTERNO DEL SERVIDOR (POSTGRESQL) ---\n{str(e)}\n----------------------------------------\n")
                raise HTTPException(status_code=500, detail=f"Error interno al procesar el reporte: {str(e)}")

# --- Comando para ejecutar el servidor ---
# En la terminal, dentro de D:\ReconocimientoPlacas\backend y con el .venv activo:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000