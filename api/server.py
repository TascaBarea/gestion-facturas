"""
api/server.py — Servidor FastAPI para gestion-facturas.

Fase 0+1: health, status, data, ejecución de scripts.
Ejecutar: python -m api.server
"""

import json
import os
import platform
import tempfile
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.auth import require_api_key
from api.config import PROJECT_ROOT, API_HOST, API_PORT
from api.runner import (
    get_scripts_info, launch_script, get_job, get_running_job, list_jobs,
)

app = FastAPI(title="Barea API", version="0.1.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints públicos ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check público — confirma que el backend está vivo."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pc_name": platform.node(),
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
        except Exception:
            pass

    return {
        "procesos": procesos,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/data/{filename}", dependencies=[Depends(require_api_key)])
def get_data_file(filename: str):
    """Sirve ficheros JSON de datos (ventas_comes, ventas_tasca, etc.)."""
    data_dir = os.path.join(tempfile.gettempdir(), "barea_streamlit_data", "data")

    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Solo ficheros .json")

    candidatos = [
        os.path.join(data_dir, filename),
        os.path.join(PROJECT_ROOT, "outputs", filename),
    ]

    for path in candidatos:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    raise HTTPException(status_code=404, detail=f"{filename} no encontrado")


# ── Endpoints de ejecución de scripts ─────────────────────────────────────────

@app.get("/api/scripts", dependencies=[Depends(require_api_key)])
def scripts_available():
    """Lista scripts disponibles para ejecutar."""
    running = get_running_job()
    return {
        "scripts": get_scripts_info(),
        "running": running.to_dict() if running else None,
    }


@app.post("/api/scripts/{script_name}", dependencies=[Depends(require_api_key)])
def run_script(script_name: str, archivo: str | None = None):
    """Lanza un script en background. Devuelve job_id para seguimiento.

    Query params:
        archivo: path del archivo (para cuadre)
    """
    extra_args = []
    if archivo:
        extra_args = ["--archivo", archivo]

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


@app.post("/api/upload/n43", dependencies=[Depends(require_api_key)])
async def upload_n43(file: UploadFile):
    """Sube un archivo N43/Excel para cuadre. Devuelve path temporal."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    ext = os.path.splitext(file.filename or "upload.xlsx")[1] or ".xlsx"
    tmp_path = os.path.join(
        tempfile.gettempdir(), f"cuadre_upload_{uuid.uuid4().hex[:8]}{ext}"
    )
    with open(tmp_path, "wb") as f:
        f.write(content)
    return {"path": tmp_path, "size": len(content), "filename": file.filename}


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
    except Exception:
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
