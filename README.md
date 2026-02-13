# mios-bot-asignacion-juzgados

**Autor:** Ramón Dario Rozo Torres 
**Versión:** 1.0.0

## 📋 Descripción General

Bot de asignación automática de juzgados para carteras de cobranza, basado en proximidad geográfica y múltiples bases de datos de clientes.  
El sistema consume información de carteras, geocodifica direcciones usando Google Maps y asigna el juzgado más adecuado para cada demanda, manteniendo métricas y control de ejecución por ambiente (`local`, `qa`, `staging`, `production`).


## 🤝 Contribución

Puedes abrir el repositorio aquí: [https://dev.azure.com/MontecheloPipelines/SquadMiosV2-old/_git/mios-bot-asignacion-juzgados](https://dev.azure.com/MontecheloPipelines/SquadMiosV2-old/_git/mios-bot-asignacion-juzgados)

### Flujo de Trabajo

1. Crear rama desde `master`:

   ```bash
   git checkout -b feature/nombre_tu_rama
   ```

2. Realizar cambios y commits descriptivos:

   ```bash
   git commit -m "feat: descripción clara del cambio"
   ```

3. Hacer push a tu rama:

   ```bash
   git push origin feature/nombre_tu_rama
   ```

4. Crear Pull Request hacia la rama de integración (`quality` o la definida por el equipo).  
5. Una vez aprobado, merge a `master` y coordinar despliegue.

### Estándares de Código

- Seguir la estructura de carpetas actual.
- Usar nomenclatura clara y consistente.
- Documentar funciones complejas.
- Probar localmente con Docker antes de subir cambios.
- Mantener actualizada la documentación de endpoints si se agregan o modifican.


## 🏗️ Arquitectura del Sistema

```text
┌───────────────────────┐      ┌──────────────────────────┐      ┌───────────────────────────┐
│   Frontend / Panel    │ ───► │ FastAPI (API REST)       │ ───► │ MySQL Cartera(s)          │
│   (Angular / Otros)   │      │ /app/main.py             │      │ (múltiples bases de datos)│
└───────────────────────┘      └──────────────────────────┘      └───────────────────────────┘
                                        │
                                        │
                                        ▼
                                ┌──────────────────────┐
                                │ Celery Worker / Beat │
                                │ (Procesos bot)       │
                                └────────┬─────────────┘
                                         │
                                         ▼
                                ┌──────────────────────┐
                                │ Redis (Broker)      │
                                └──────────────────────┘

                         ┌───────────────────────────────────────────────┐
                         │ Base de Datos de Configuración del Bot       │
                         │ (tabla bot_config: BDs, límites API, logs,   │
                         │  Google API Key por ambiente)                │
                         └───────────────────────────────────────────────┘
```

## 📦 Stack Tecnológico

### Backend

| Tecnología       | Versión / Librería     | Descripción                           |
| ---------------- | ---------------------- | ------------------------------------- |
| **Python**       | 3.10+ (recomendado)    | Lenguaje principal                    |
| **FastAPI**      | ^0.x                   | API REST                              |
| **Uvicorn**      | ^0.x                   | Servidor ASGI                         |
| **Celery**       | ^5.x                   | Procesamiento asíncrono               |
| **Redis**        | 7.x (Docker)           | Broker de mensajes                    |
| **SQLAlchemy**   | ^2.x                   | ORM / acceso a BD                     |
| **python-dotenv**| ^1.x                   | Manejo de `.env`                      |

### Base de Datos

| Tecnología      | Versión       | Descripción                                  |
| --------------- | ------------- | -------------------------------------------- |
| **MySQL**       | 5.7 / 8.0     | Motor principal de datos                     |
| **Múltiples BDs** |              | Cartera por BD y una BD de configuración    |
| **Scripts SQL** | `scripts/`    | Creación/rollback de tablas del bot         |
| **Seeds**       | Dumps de QA   | Datos iniciales para entornos `local/dev`   |

### DevOps / Infra

| Tecnología         | Versión    | Descripción                |
| ------------------ | ---------- | -------------------------- |
| **Docker**         | 20.10+     | Contenedorización          |
| **Docker Compose** | 1.29+      | Orquestación local         |
| **Flower**         | Latest     | Monitor de tareas Celery   |
| **Logs**           |            | Volumen Docker `logs_data`  |

## 📁 Estructura del Proyecto

```text
mios-bot-asignacion-juzgados/
├── app/
│   ├── config/                 # Configuración de BDs y bot
│   ├── core/                   # Lógica de negocio (asignación, geocodificación)
│   ├── utils/                  # Utilidades (DB, Google API, etc.)
│   ├── _init_.py               # Inicialización de la aplicación
│   ├── bot_control.py          # Control de estado del bot
│   ├── celery_app.py           # Configuración Celery
│   ├── main.py                 # Punto de entrada FastAPI
│   └── tasks.py                # Tareas Celery
├── scripts/
│   ├── database_setup.sql           # Crea tablas court_coordinates y lawsuit_court_assignments
│   ├── database_rollback.sql        # Elimina tablas del bot en la BD de carteras
│   └── seed_city_variants_bot_config.sql  # Inserta config key 'city_variants' en bot_config (BD bot_asignacion_config)
├── logs/                       # .gitignore; en Docker se usa volumen logs_data
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🧩 Componentes Principales

- **API FastAPI (`court-bot-api`):**
  - Exposición de endpoints REST para monitoreo, ejecución manual, estadísticas y recarga de configuración.

- **Celery Worker (`court-bot-worker`):**
  - Ejecuta en segundo plano la sincronización de juzgados y la asignación de juzgados a demandas.

- **Celery Beat (`court-bot-beat`):**
  - Programa y dispara las ejecuciones automáticas del bot.

- **Redis (`court-bot-redis`):**
  - Broker de mensajes para Celery.

- **Base de Datos:**
  - `bot_asignacion_config`
  - Contiene toda la configuración necesaria para que el bot funcione correctamente segun el ambiente definido en el archivo `.env`.

  - `miosv2_carteras_QA`
  - Contiene toda la información necesaria para que el bot funcione correctamente en cuanto a la asignación de juzgados.

## 🚀 Funcionalidades

### Funcionalidades Core

- **Asignación de Juzgados Multi-BD:**
  - Procesa demandas en múltiples bases de datos de carteras.
  - Asigna el juzgado más cercano según coordenadas y ciudad.

- **Geocodificación de Juzgados:**
  - Sincroniza y mantiene la tabla `court_coordinates` por BD.
  - Uso de Google Maps API según límites configurados en `bot_config`.

- **Control Centralizado del Bot:**
  - Estados: `running`, `stopped`, `no_api_credits`, `error`.
  - Control manual de inicio y detención (`/start`, `/stop`).
  - Estadísticas de uso de API y logs.

- **Métricas y Monitoreo:**
  - Estadísticas globales y por base de datos:
    - registros procesados
    - asignados
    - sin dirección / con errores
  - Detalle de juzgados geocodificados.

- **Multi Ambiente vía Configuración:**
  - `local`, `qa`, `staging`, `production`.
  - Cada ambiente con:
    - lista de BDs
    - límites de API
    - configuración de logs
    - Google API Key específica

## 🔍 Endpoints Principales

Algunos endpoints expuestos por `FastAPI` (ver detalles en `app/main.py`):

- `/` – Información general del servicio (nombre, versión, BDs, resumen de endpoints).
- `/health` – Salud del sistema y conexión a todas las BDs (incluye métricas globales).
- `/status` – Estado actual del bot y último error (si aplica).
- `/clients` – Listado de clientes procesados (paginado, filtros por estado y BD).
- `/execute` – Ejecución manual del bot (tarea Celery en segundo plano).
- `/stop` – Detiene el bot manualmente (bloquea ejecuciones automáticas).
- `/start` – Habilita nuevamente el bot después de un stop o error de créditos.
- `/logs` – Consulta de logs del bot (texto plano, número de líneas configurable).
- `/api-usage` – Uso de Google Maps API (diario, mensual, estado).
- `/databases/test` – Test de conexión a todas las BDs configuradas.
- `/databases/stats` – Estadísticas de asignaciones por BD (asignados/sin dirección, totales).
- `/databases/list` – Lista de BDs configuradas.
- `/databases/details` – Detalle de juzgados y asignaciones por BD.
- `/config/reload` – Recarga configuración desde BD (`BotConfig`, límites de API, logs, API Key).

Documentación automática de la API:

- `Swagger UI` – Documentación interactiva por defecto de FastAPI.
- [http://localhost:8001/docs](http://localhost:8001/docs)


## 🔒 Seguridad

- Credenciales y API Keys siempre vía:
  - `.env` (creds MySQL, etc.).
  - `bot_config` (Google API Key, `databases`, `api_limits`, `log_config`, `city_variants` por ambiente).
  - `city_variants`: grupos de nombres equivalentes de ciudades (ej. Bogotá/BOGOTÁ D.C., Cúcuta/San José de Cúcuta). Ver `scripts/seed_city_variants_bot_config.sql`.
- No exponer credenciales en el repositorio.
- Usar VPN/seguridad corporativa para acceder a BDs de QA/Producción.
- Configurar CORS restrictivo en producción.
- El backend debe permitir conexiones desde:
  - Frontend Angular (QA): https://qamios.groupcos.com
  - Frontend Angular (Producción): https://mysoul.groupcos.com 

---

## 🚀 Levantamiento y uso (con Docker)

El sistema **se levanta con Docker apuntando logica de negocio a ambiente QA** ya que crear el ambiente en desarrollo local es complicado y no es necesario. Los pasos son los siguientes.

### Requisitos previos

- **Docker** y **Docker Compose** instalados.
- Levantar siempre apuntando environment a ambiente **QA**: **VPN activa** antes de levantar el stack.
- Archivo **`.env`** configurado (copiar desde `.env.example`
- Solicitar las credenciales de la BD de QA al equipo de desarrollo)
- Redis se levanta en ip local 127.0.0.1 junto al puerto 6379.

### Paso a paso

1. **Ubicarse en la raíz del proyecto** (donde está `docker-compose.yml`):
   ```bash
   cd mios-bot-asignacion-juzgados
   ```

2. **Variables de entorno** Copiar archivo `.env.example` a `.env` y ajustar las variables de entorno apuntando a ambiente QA.

3. **Crear imágenes** Construir imágenes sin caché:
   ```bash
   docker compose build --no-cache
   ```

4. **Levantar todos los servicios**:
   - Con logs en consola:
     ```bash
     docker compose up
     ```
   - En segundo plano (detached):
     ```bash
     docker compose up -d
     ```

5. **Abrir Swagger** en el navegador para controlar el sistema:
   - **URL:** [http://localhost:8001/docs](http://localhost:8001/docs)
   - Ahí aparecen todos los endpoints. Para ejecutar uno: **"Try it out"** → rellenar parámetros si pide → **"Execute"** → ver el resultado (código HTTP y body).

**Notas importantes:**
- Cuando se levanta el sitema el bot no se inicia automaticamente, se debe iniciar manualmente mediante el endpoint `/start` o `/execute` desde Swagger UI.


## 📞 Soporte

- **Creador:** Jose Florez 
- **Modificado por:** Ramón Dario Rozo Torres 

## 🐞 Bugs o problemas conocidos

### Alcance al servidor de QA (172.17.8.141)
- Verificar que la VPN esté activa.
- Hacer un telnet a la ip 172.17.8.141 y puerto 3306 para verificar que se pueda conectar a la BD.
- Activar el telnet si no está activo en tu sistema operativo.
- Problemas de red entre docker y el servidor de QA por causas de networking 172.17.x.x, por lo que se debe:
  - Validar el comando `ip route` en tu sistema operativo para verificar que la red de docker no esté en el mismo segmento de red 172.17.x.x.
  - Cambiar la red por defecto de docker en el archivo `/etc/docker/daemon.json` agregando la siguiente configuración para evitar conflictos de networking 172.17.x.x:
    ```json
        {
          "bip": "172.30.0.1/16"
        }
    ```
 - Reiniciar Docker:
    ```bash
    sudo service docker restart
    ```
 - Validar la configuración con el comando `ip route` nuevamente.
 - Volver a realizar el telnet a la ip 172.17.8.141 y puerto 3306 para verificar que se pueda conectar a la BD.
 - Levantar el stack de docker nuevamente.

 - Si usas subsystem ubuntu sobre windows y WSL2 debe tambien crear el archivo .wslconfig dentro de windows en la ruta `C:\Users\TU_USUARIO\.wslconfig` y agregar la siguiente configuración:
    ```ini
      [wsl2]
      networkingMode=mirrored
      dnsTunneling=true
    ```
 - Reiniciar WSL2:
    ```bash
    wsl --shutdown
    ```
 - Volver a realizar el telnet a la ip 172.17.8.141 y puerto 3306 para verificar que se pueda conectar a la BD.
 - Levantar el stack de docker nuevamente.

### Error por permisos sobre `Permission denied: 'logs/bot_execution.log'`
 -Cambiar dueño de la carpeta logs a tu usuario
    ```bash
    sudo chown -R $USER:$USER logs
    ```
 - (Opcional, pero recomendable) Ajustar permisos
    ```bash
    chmod -R 775 logs
    ```
 - Bajar los contenedores de docker
    ```bash
    docker compose down
    ```
 - Levantar el stack de docker nuevamente.
    ```bash
    docker compose up
    ```


## 📄 Licencia

**© 2026 MONTECHELO S.A.S - Todos los derechos reservados**
