"""
api/server.py — Servidor FastAPI para gestion-facturas.

Fase 0+1: health, status, data, ejecución de scripts.
Ejecutar: python -m api.server
"""

import json
import logging
import os
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("api.server")

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.auth import require_api_key, require_admin_key
from api.config import PROJECT_ROOT, API_HOST, API_PORT, CORS_ORIGINS
from pydantic import BaseModel

from api.runner import (
    get_scripts_info, launch_script, get_job, get_running_job, list_jobs,
)
from api.maestro import (
    leer_maestro_simple, actualizar_proveedor, crear_proveedor,
    ProveedorUpdate, ProveedorCreate,
)

app = FastAPI(title="Barea API", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
# Orígenes permitidos: desde .env (CORS_ORIGINS) o fallback seguro.
# En DEV_MODE se permite localhost; en producción solo orígenes explícitos.
_default_origins = ["http://127.0.0.1:8501", "http://localhost:8501"]
_origins = CORS_ORIGINS if CORS_ORIGINS else _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
# 60 requests/minuto por IP. /health exento.
_RATE_LIMIT = 60
_RATE_WINDOW = 60  # segundos
_rate_log: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    # Limpiar entradas antiguas
    _rate_log[client_ip] = [t for t in _rate_log[client_ip] if now - t < _RATE_WINDOW]

    if len(_rate_log[client_ip]) >= _RATE_LIMIT:
        logger.warning("Rate limit excedido para %s", client_ip)
        return JSONResponse(
            status_code=429,
            content={"detail": "Demasiadas peticiones. Espera un momento."},
        )

    _rate_log[client_ip].append(now)
    return await call_next(request)


# ── Endpoints públicos ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check público — confirma que el backend está vivo."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ── Endpoints protegidos (requieren API key) ─────────────────────────────────

@app.get("/api/status", dependencies=[Depends(require_api_key)])
def status():
    """Estado de los procesos automáticos (última ejecución, logs)."""
    procesos = {}

    logs_gmail = os.path.join(PROJECT_ROOT, "outputs", "logs_gmail")
    _leer_ultimo_log(procesos, "gmail", logs_gmail)

    logs_barea = os.path.join(PROJECT_ROOT, "outputs", "logs_barea")
    _leer_ultimo_log(procesos, "ventas", logs_barea)

    cuadre_path = os.path.join(PROJECT_ROOT, "outputs", "cuadre_resumen.json")
    if os.path.exists(cuadre_path):
        try:
            with open(cuadre_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            procesos["cuadre"] = {
                "ultima_ejecucion": data.get("fecha_ejecucion", ""),
                "estado": "ok",
            }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Error leyendo cuadre_resumen.json: %s", e)
            procesos["cuadre"] = {"estado": "error", "detalle": str(e)}

    return {
        "procesos": procesos,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/alerts", dependencies=[Depends(require_api_key)])
def alerts():
    """Alertas activas: procesos atrasados o con errores."""
    alertas = []
    ahora = datetime.now()

    checks = {
        "gmail": {"dir": os.path.join(PROJECT_ROOT, "outputs", "logs_gmail"), "max_dias": 9},
        "ventas": {"dir": os.path.join(PROJECT_ROOT, "outputs", "logs_barea"), "max_dias": 9},
    }

    for modulo, cfg in checks.items():
        if not os.path.isdir(cfg["dir"]):
            continue
        auto_logs = sorted(
            f for f in os.listdir(cfg["dir"])
            if f.startswith("auto_") and f.endswith(".log")
        )
        if not auto_logs:
            alertas.append({"module": modulo, "level": "warning", "message": "Sin ejecuciones"})
            continue

        ultimo = auto_logs[-1]
        fecha_str = ultimo.replace("auto_", "").replace(".log", "")
        try:
            fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            dias = (ahora - fecha_dt).days
        except ValueError:
            continue

        # Comprobar si el último log tiene errores
        path = os.path.join(cfg["dir"], ultimo)
        tiene_error = False
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                ultimas = f.readlines()[-10:]
            texto = " ".join(ultimas).upper()
            tiene_error = "ERROR" in texto and "EXITO" not in texto
        except OSError as e:
            logger.warning("Error leyendo log %s: %s", path, e)

        if tiene_error:
            alertas.append({
                "module": modulo, "level": "error",
                "message": f"Última ejecución falló ({fecha_str})",
            })
        elif dias > cfg["max_dias"] * 2:
            alertas.append({
                "module": modulo, "level": "error",
                "message": f"Hace {dias} días (sin ejecutar)",
            })
        elif dias > cfg["max_dias"]:
            alertas.append({
                "module": modulo, "level": "warning",
                "message": f"Hace {dias} días (atención)",
            })

    return {"alerts": alertas, "timestamp": ahora.isoformat(timespec="seconds")}


@app.get("/api/data/{filename}", dependencies=[Depends(require_api_key)])
def get_data_file(filename: str):
    """Sirve ficheros JSON de datos (ventas_comes, ventas_tasca, etc.)."""
    # Seguridad: solo nombre base, sin separadores de directorio
    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre de fichero no válido")

    if not safe_name.endswith(".json"):
        raise HTTPException(status_code=400, detail="Solo ficheros .json")

    data_dir = os.path.join(tempfile.gettempdir(), "barea_streamlit_data", "data")
    dirs_permitidos = [data_dir, os.path.join(PROJECT_ROOT, "outputs")]

    for base_dir in dirs_permitidos:
        candidato = os.path.join(base_dir, safe_name)
        # Verificar que el path resuelto está dentro del directorio permitido
        real_path = os.path.realpath(candidato)
        real_base = os.path.realpath(base_dir)
        if not real_path.startswith(real_base + os.sep) and real_path != real_base:
            continue
        if os.path.exists(real_path):
            with open(real_path, "r", encoding="utf-8") as f:
                return json.load(f)

    raise HTTPException(status_code=404, detail=f"{safe_name} no encontrado")


# ── Endpoints de ejecución de scripts ─────────────────────────────────────────

@app.get("/api/scripts", dependencies=[Depends(require_api_key)])
def scripts_available():
    """Lista scripts disponibles para ejecutar."""
    running = get_running_job()
    return {
        "scripts": get_scripts_info(),
        "running": running.to_dict() if running else None,
    }


@app.post("/api/scripts/{script_name}", dependencies=[Depends(require_admin_key)])
def run_script(script_name: str, archivo: str | None = None):
    """Lanza un script en background. Devuelve job_id para seguimiento.

    Query params:
        archivo: upload_id devuelto por /api/upload/n43, o path en datos/
    """
    extra_args = []
    if archivo:
        # Resolver upload_id opaco → path real
        if archivo in _upload_registry:
            real_path = _upload_registry.pop(archivo)
        else:
            # Compatibilidad: path directo (solo desde datos/)
            if ".." in archivo:
                raise HTTPException(status_code=400, detail="Path no permitido: contiene '..'")
            real_path = os.path.realpath(archivo)
        dirs_permitidos = [
            os.path.realpath(tempfile.gettempdir()),
            os.path.realpath(os.path.join(PROJECT_ROOT, "datos")),
        ]
        if not any(real_path.startswith(d + os.sep) or real_path == d for d in dirs_permitidos):
            raise HTTPException(
                status_code=400,
                detail="Path fuera de directorios permitidos (temp, datos/)",
            )
        extra_args = ["--archivo", real_path]

    try:
        job = launch_script(script_name, extra_args)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"job_id": job.job_id, "script": script_name, "status": job.status.value}


@app.get("/api/jobs", dependencies=[Depends(require_api_key)])
def jobs_list(limit: int = 10):
    """Lista los últimos N jobs ejecutados."""
    return {"jobs": list_jobs(limit)}


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def job_detail(job_id: str, full_log: bool = False):
    """Detalle de un job: estado, log, exit code."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado")
    return job.to_dict(include_log=full_log)


_UPLOAD_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_UPLOAD_EXTENSIONS = {".n43", ".xlsx", ".xls"}
# Magic bytes: XLSX=PK (ZIP), XLS=D0CF (OLE), N43=texto (empieza con dígitos)
_MAGIC_XLSX = b"PK"
_MAGIC_XLS = b"\xd0\xcf\x11\xe0"
# Registro de uploads: upload_id → path real (no exponer paths al cliente)
_upload_registry: dict[str, str] = {}


@app.post("/api/upload/n43", dependencies=[Depends(require_admin_key)])
async def upload_n43(file: UploadFile):
    """Sube un archivo N43/Excel para cuadre. Devuelve path temporal."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    # Validar tamaño
    if len(content) > _UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo demasiado grande ({len(content)} bytes). Máximo: {_UPLOAD_MAX_BYTES // (1024*1024)} MB",
        )

    # Validar extensión
    ext = os.path.splitext(file.filename or "upload.xlsx")[1].lower() or ".xlsx"
    if ext not in _UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión '{ext}' no permitida. Permitidas: {', '.join(sorted(_UPLOAD_EXTENSIONS))}",
        )

    # Validar magic bytes según extensión
    if ext == ".xlsx" and not content[:2].startswith(_MAGIC_XLSX):
        raise HTTPException(status_code=400, detail="El archivo no parece ser un XLSX válido")
    if ext == ".xls" and not content[:4].startswith(_MAGIC_XLS):
        raise HTTPException(status_code=400, detail="El archivo no parece ser un XLS válido")
    if ext == ".n43" and not content[:1].isdigit():
        raise HTTPException(status_code=400, detail="El archivo no parece ser un N43 válido")

    upload_id = uuid.uuid4().hex[:12]
    tmp_path = os.path.join(
        tempfile.gettempdir(), f"cuadre_upload_{upload_id}{ext}"
    )
    with open(tmp_path, "wb") as f:
        f.write(content)
    _upload_registry[upload_id] = tmp_path
    return {"upload_id": upload_id, "size": len(content), "filename": file.filename}


# ── Endpoints MAESTRO_PROVEEDORES ─────────────────────────────────────────────

@app.get("/api/maestro", dependencies=[Depends(require_api_key)])
def maestro_list():
    """Lista completa de proveedores del MAESTRO."""
    try:
        proveedores = leer_maestro_simple()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo MAESTRO: {e}")
    return {
        "proveedores": proveedores,
        "total": len(proveedores),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.put("/api/maestro/{proveedor_name}", dependencies=[Depends(require_admin_key)])
def maestro_update(proveedor_name: str, body: ProveedorUpdate):
    """Actualiza un proveedor existente (partial update)."""
    cambios = body.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=422, detail="No hay campos para actualizar.")
    try:
        prov = actualizar_proveedor(proveedor_name, cambios)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"proveedor": prov, "message": "Proveedor actualizado."}


@app.post("/api/maestro", dependencies=[Depends(require_admin_key)])
def maestro_create(body: ProveedorCreate):
    """Crea un nuevo proveedor."""
    data = body.model_dump(exclude_none=True)
    try:
        prov = crear_proveedor(data)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"proveedor": prov, "message": "Proveedor creado."}


# ── Endpoints read-only adicionales ──────────────────────────────────────────

@app.get("/api/cuadre/detail", dependencies=[Depends(require_api_key)])
def cuadre_detail():
    """Detalle del último cuadre: resumen JSON generado por cuadre.py."""
    cuadre_path = os.path.join(PROJECT_ROOT, "outputs", "cuadre_resumen.json")
    if not os.path.exists(cuadre_path):
        raise HTTPException(status_code=404, detail="Sin datos de cuadre disponibles")
    try:
        with open(cuadre_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo cuadre: {e}")


@app.get("/api/gmail/stats", dependencies=[Depends(require_api_key)])
def gmail_stats():
    """Estadísticas del módulo Gmail: última ejecución, facturas procesadas."""
    json_path = os.path.join(PROJECT_ROOT, "outputs", "gmail_resumen.json")
    if not os.path.exists(json_path):
        # Intentar leer del log más reciente
        logs_dir = os.path.join(PROJECT_ROOT, "outputs", "logs_gmail")
        if not os.path.isdir(logs_dir):
            raise HTTPException(status_code=404, detail="Sin datos de Gmail disponibles")
        logs = sorted(f for f in os.listdir(logs_dir) if f.endswith(".log"))
        if not logs:
            raise HTTPException(status_code=404, detail="Sin logs de Gmail")
        ultimo = logs[-1]
        return {
            "ultimo_log": ultimo,
            "fecha": ultimo.replace(".log", ""),
            "detalle": "Resumen JSON no disponible. Consulta el log.",
        }
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo stats Gmail: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _leer_ultimo_log(procesos: dict, nombre: str, directorio: str):
    """Lee el último auto_*.log de un directorio y extrae info."""
    if not os.path.isdir(directorio):
        return
    auto_logs = sorted(
        f for f in os.listdir(directorio)
        if f.startswith("auto_") and f.endswith(".log")
    )
    if not auto_logs:
        return
    ultimo = auto_logs[-1]
    fecha_str = ultimo.replace("auto_", "").replace(".log", "")

    path = os.path.join(directorio, ultimo)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
        ultimas = [l.rstrip() for l in lineas[-5:]]
    except OSError as e:
        logger.warning("Error leyendo log %s: %s", path, e)
        ultimas = []

    procesos[nombre] = {
        "ultima_ejecucion": fecha_str,
        "log": ultimo,
        "ultimas_lineas": ultimas,
    }


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import uvicorn
    reload = "--reload" in sys.argv
    print(f"Barea API arrancando en http://{API_HOST}:{API_PORT}"
          f"{' (reload)' if reload else ''}")
    uvicorn.run("api.server:app", host=API_HOST, port=API_PORT, reload=reload)
