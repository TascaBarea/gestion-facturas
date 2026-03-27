"""
api/runner.py — Ejecutor de scripts en background con job tracking.

Ejecuta scripts Python del proyecto en subprocesos, capturando stdout/stderr
en un buffer circular. Solo permite 1 script a la vez (lock global).
"""

import os
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from api.config import PROJECT_ROOT


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    script: str
    args: list[str] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    exit_code: Optional[int] = None
    log_lines: deque = field(default_factory=lambda: deque(maxlen=200))
    error: str = ""

    def to_dict(self, include_log: bool = False) -> dict:
        d = {
            "job_id": self.job_id,
            "script": self.script,
            "args": self.args,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "error": self.error,
        }
        if include_log:
            d["log"] = list(self.log_lines)
        else:
            d["log_tail"] = list(self.log_lines)[-10:] if self.log_lines else []
        return d


# ── Definición de scripts disponibles ─────────────────────────────────────────

SCRIPTS = {
    "gmail": {
        "script": os.path.join("gmail", "gmail.py"),
        "cwd": os.path.join(PROJECT_ROOT, "gmail"),
        "args_default": ["--produccion"],
        "description": "Procesar emails y facturas",
    },
    "gmail_test": {
        "script": os.path.join("gmail", "gmail.py"),
        "cwd": os.path.join(PROJECT_ROOT, "gmail"),
        "args_default": ["--test"],
        "description": "Gmail en modo test (sin modificar archivos)",
    },
    "ventas": {
        "script": os.path.join("ventas_semana", "script_barea.py"),
        "description": "Descargar ventas semanales",
    },
    "dashboard": {
        "script": os.path.join("ventas_semana", "generar_dashboard.py"),
        "args_default": ["--no-open", "--solo-cerrados"],
        "description": "Generar dashboards HTML + PDF",
    },
    "dashboard_email": {
        "script": os.path.join("ventas_semana", "generar_dashboard.py"),
        "args_default": ["--no-open", "--solo-cerrados", "--email"],
        "description": "Generar dashboards + enviar email",
    },
    "cuadre": {
        "script": os.path.join("cuadre", "banco", "cuadre.py"),
        "args_default": [],
        "description": "Cuadre bancario (requiere --archivo)",
        "requires_file": True,
    },
    "dia_tickets": {
        "script": os.path.join("scripts", "dia_tickets.py"),
        "args_default": [],
        "description": "Descargar tickets de Dia (requiere sesión activa)",
    },
    "dia_tickets_stats": {
        "script": os.path.join("scripts", "dia_tickets.py"),
        "args_default": ["--stats"],
        "description": "Estadísticas de tickets Dia descargados",
    },
}

# ── Estado global ─────────────────────────────────────────────────────────────

_lock = threading.Lock()
_running_job: Optional[Job] = None
_jobs: dict[str, Job] = {}  # job_id → Job (últimos 50)
_MAX_JOBS_HISTORY = 50
_TIMEOUT_SECONDS = 600  # 10 minutos


def get_scripts_info() -> dict:
    """Devuelve info de scripts disponibles."""
    return {
        name: {
            "description": cfg["description"],
            "requires_file": cfg.get("requires_file", False),
        }
        for name, cfg in SCRIPTS.items()
    }


def get_job(job_id: str) -> Optional[Job]:
    """Devuelve un job por ID."""
    return _jobs.get(job_id)


def get_running_job() -> Optional[Job]:
    """Devuelve el job en ejecución, si hay alguno."""
    return _running_job


def list_jobs(limit: int = 10) -> list[dict]:
    """Lista los últimos N jobs."""
    jobs = sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)
    return [j.to_dict() for j in jobs[:limit]]


def launch_script(script_name: str, extra_args: list[str] | None = None) -> Job:
    """Lanza un script en background. Devuelve el Job creado.

    Raises ValueError si el script no existe o ya hay uno en ejecución.
    """
    global _running_job

    if script_name not in SCRIPTS:
        raise ValueError(f"Script desconocido: {script_name}")

    with _lock:
        if _running_job and _running_job.status == JobStatus.RUNNING:
            raise ValueError(
                f"Ya hay un script en ejecución: {_running_job.script} "
                f"(job {_running_job.job_id})"
            )

    cfg = SCRIPTS[script_name]
    now = datetime.now().isoformat(timespec="seconds")

    job = Job(
        job_id=uuid.uuid4().hex[:12],
        script=script_name,
        args=cfg.get("args_default", []) + (extra_args or []),
        created_at=now,
    )

    # Limpiar historial si hay demasiados
    if len(_jobs) >= _MAX_JOBS_HISTORY:
        oldest = sorted(_jobs.keys(), key=lambda k: _jobs[k].created_at)
        for k in oldest[:10]:
            del _jobs[k]

    _jobs[job.job_id] = job

    with _lock:
        _running_job = job

    thread = threading.Thread(target=_run_job, args=(job, cfg), daemon=True)
    thread.start()

    return job


def _run_job(job: Job, cfg: dict):
    """Ejecuta el script en un subproceso (thread worker)."""
    global _running_job

    job.status = JobStatus.RUNNING
    job.started_at = datetime.now().isoformat(timespec="seconds")

    script_path = os.path.join(PROJECT_ROOT, cfg["script"])
    work_dir = cfg.get("cwd", PROJECT_ROOT)
    cmd = [sys.executable, script_path] + job.args
    job.log_lines.append(f"[{job.started_at}] Ejecutando: {' '.join(cmd)}")
    job.log_lines.append(f"[{job.started_at}] Directorio: {work_dir}")

    # PYTHONPATH incluye project root para resolver nucleo/, config/, etc.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": PROJECT_ROOT}

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        # Leer output línea a línea
        start = time.time()
        for line in proc.stdout:
            job.log_lines.append(line.rstrip())
            if time.time() - start > _TIMEOUT_SECONDS:
                proc.kill()
                job.log_lines.append(f"[TIMEOUT] Proceso terminado tras {_TIMEOUT_SECONDS}s")
                break

        proc.wait(timeout=30)
        job.exit_code = proc.returncode

        if job.exit_code == 0:
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.FAILED
            job.error = f"Exit code: {job.exit_code}"

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.log_lines.append(f"[ERROR] {e}")

    finally:
        job.finished_at = datetime.now().isoformat(timespec="seconds")
        job.log_lines.append(f"[{job.finished_at}] Finalizado: {job.status.value}")
        with _lock:
            if _running_job and _running_job.job_id == job.job_id:
                _running_job = None
