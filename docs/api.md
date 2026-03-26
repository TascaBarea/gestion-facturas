# API Reference — Barea API

FastAPI backend para gestion-facturas. Puerto 8000.

```bash
python -m api.server            # arranque normal
python -m api.server --reload   # desarrollo (auto-reload)
```

## Autenticación

RBAC 2 niveles via Bearer token (`Authorization: Bearer <key>`):

| Nivel | Variable .env | Acceso |
|-------|---------------|--------|
| admin | `API_KEY` | Lectura + escritura (scripts, uploads, MAESTRO writes) |
| readonly | `API_KEY_READONLY` | Solo lectura (status, datos, listas) |

- `DEV_MODE=true` → bypass auth completo (solo desarrollo local)
- Sin keys configuradas y sin DEV_MODE → error 500

## Endpoints

### Públicos (sin auth)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check. Devuelve status, timestamp, pc_name |

### Protegidos — lectura (admin o readonly)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/status` | Estado procesos automáticos (gmail, ventas, cuadre) |
| GET | `/api/alerts` | Alertas activas: procesos atrasados o con errores |
| GET | `/api/data/{filename}` | Sirve ficheros JSON de datos (solo .json, path traversal protegido) |
| GET | `/api/scripts` | Lista scripts disponibles + job en ejecución |
| GET | `/api/jobs` | Últimos N jobs ejecutados (default 10) |
| GET | `/api/jobs/{job_id}` | Detalle de un job: estado, log, exit code. `?full_log=true` para log completo |
| GET | `/api/maestro` | Lista completa de proveedores del MAESTRO |
| GET | `/api/cuadre/detail` | Detalle del último cuadre (cuadre_resumen.json) |
| GET | `/api/gmail/stats` | Estadísticas Gmail: última ejecución, facturas procesadas |

### Admin — escritura (solo admin key)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/scripts/{script_name}` | Lanza script en background. `?archivo=path` para cuadre |
| POST | `/api/upload/n43` | Sube archivo N43/Excel para cuadre (multipart/form-data) |
| PUT | `/api/maestro/{name}` | Actualiza proveedor existente (partial update) |
| POST | `/api/maestro` | Crea nuevo proveedor |

## Scripts disponibles

| Nombre | Archivo | Descripción | Args por defecto |
|--------|---------|-------------|------------------|
| `gmail` | gmail/gmail.py | Procesar emails y facturas | `--produccion` |
| `gmail_test` | gmail/gmail.py | Gmail modo test | `--test` |
| `ventas` | ventas_semana/script_barea.py | Descargar ventas semanales | — |
| `dashboard` | ventas_semana/generar_dashboard.py | Generar dashboards HTML + PDF | `--no-open --solo-cerrados` |
| `dashboard_email` | ventas_semana/generar_dashboard.py | Dashboards + enviar email | `--no-open --solo-cerrados --email` |
| `cuadre` | cuadre/banco/cuadre.py | Cuadre bancario | requiere `--archivo` |

## Runner

- 1 job concurrente (threading lock global)
- Timeout: 600s (10 min)
- Buffer log: 200 líneas (deque circular)
- Historial: máximo 50 jobs (purga los 10 más antiguos al llenar)
- Estados: `pending` → `running` → `completed` | `failed`

## MAESTRO CRUD

Modelos Pydantic para validación:

**ProveedorUpdate** (partial update — todos los campos opcionales):
CUENTA, CLASE, CIF, IBAN, FORMA_PAGO, EMAIL, ALIAS, TIENE_EXTRACTOR,
ARCHIVO_EXTRACTOR, TIPO_CATEGORIA, CATEGORIA_FIJA, METODO_PDF, ACTIVO, NOTAS

**ProveedorCreate** (extiende Update):
PROVEEDOR (obligatorio) + todos los campos de Update

**Flow de escritura:**
1. `verificar_no_abierto()` — rename temporal para detectar bloqueo Excel
2. `leer_maestro()` — lee cabeceras + datos dinámicamente
3. Buscar/validar — case-insensitive, FORMA_PAGO en {TF, TJ, RC, EF, ""}
4. `backup_maestro()` — copia en datos/backups/ con timestamp
5. `guardar_maestro()` — escribe preservando todas las columnas

## Seguridad

- **Path traversal**: `os.path.basename()` + `os.path.realpath()` containment check
- **CORS**: lista explícita en `.env` CORS_ORIGINS, fallback localhost:8501
- **Uploads**: max 10MB, extensiones {.n43, .xlsx, .xls}, validación magic bytes:
  - XLSX: `PK` (ZIP header)
  - XLS: `D0CF` (OLE header)
  - N43: primer byte es dígito
- **Scripts**: args validados contra path traversal (`..` prohibido, dirs permitidos: temp, datos/)

## Configuración (.env)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `API_KEY` | "" | Token admin (lectura + escritura) |
| `API_KEY_READONLY` | "" | Token solo lectura |
| `API_HOST` | 127.0.0.1 | Host de escucha |
| `API_PORT` | 8000 | Puerto |
| `DEV_MODE` | false | Bypass auth (true/1/yes) |
| `CORS_ORIGINS` | "" | Orígenes permitidos, separados por coma |

## Códigos de error

| Código | Significado |
|--------|-------------|
| 400 | Parámetros inválidos (nombre fichero, extensión, path traversal, archivo vacío) |
| 401 | API key inválida o ausente |
| 403 | Se requiere admin key (en endpoints de escritura) |
| 404 | Recurso no encontrado (fichero, job, proveedor) |
| 409 | Conflicto (job en ejecución, proveedor duplicado, Excel abierto) |
| 422 | Validación fallida (campos vacíos, FORMA_PAGO inválida) |
| 500 | Error interno (lectura MAESTRO, API_KEY no configurada) |

## Integración Streamlit

- `streamlit_app/utils/data_client.py` — cliente HTTP para la API
- Fallback: si backend no disponible, lee datos estáticos de Netlify
- Detecta backend con `GET /health` (timeout 3s)

## Arranque

- `barea_api.bat` — script con watchdog auto-restart
- Registrado en Task Scheduler de Windows
- PYTHONPATH incluye project root para resolver nucleo/, config/
