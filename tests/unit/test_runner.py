"""
Tests para api/runner.py — ejecutor de scripts en background.
"""

import time
import threading
import pytest

from api.runner import (
    Job, JobStatus, SCRIPTS,
    get_scripts_info, get_job, get_running_job, list_jobs,
    launch_script, _jobs, _lock,
)
import api.runner as runner_mod


@pytest.fixture(autouse=True)
def limpiar_estado_runner():
    """Limpia el estado global del runner entre tests."""
    runner_mod._running_job = None
    runner_mod._jobs.clear()
    yield
    runner_mod._running_job = None
    runner_mod._jobs.clear()


# ── Job dataclass ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestJob:

    def test_defaults(self):
        j = Job(job_id="abc123", script="ventas")
        assert j.status == JobStatus.PENDING
        assert j.exit_code is None
        assert j.error == ""

    def test_to_dict_sin_log(self):
        j = Job(job_id="abc123", script="ventas")
        d = j.to_dict(include_log=False)
        assert "log_tail" in d
        assert "log" not in d
        assert d["job_id"] == "abc123"

    def test_to_dict_con_log(self):
        j = Job(job_id="abc123", script="ventas")
        j.log_lines.append("linea 1")
        d = j.to_dict(include_log=True)
        assert "log" in d
        assert d["log"] == ["linea 1"]

    def test_log_maxlen(self):
        j = Job(job_id="abc123", script="ventas")
        for i in range(300):
            j.log_lines.append(f"linea {i}")
        assert len(j.log_lines) == 200  # maxlen=200

    def test_log_tail(self):
        j = Job(job_id="abc123", script="ventas")
        for i in range(20):
            j.log_lines.append(f"linea {i}")
        d = j.to_dict(include_log=False)
        assert len(d["log_tail"]) == 10


# ── Scripts info ─────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestScriptsInfo:

    def test_scripts_definidos(self):
        info = get_scripts_info()
        assert "gmail" in info
        assert "ventas" in info
        assert "cuadre" in info
        assert "dashboard" in info

    def test_cuadre_requires_file(self):
        info = get_scripts_info()
        assert info["cuadre"]["requires_file"] is True

    def test_ventas_no_requires_file(self):
        info = get_scripts_info()
        assert info["ventas"]["requires_file"] is False

    def test_description_presente(self):
        info = get_scripts_info()
        for name, cfg in info.items():
            assert "description" in cfg
            assert cfg["description"]  # No vacío


# ── launch_script ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestLaunchScript:

    def test_script_desconocido(self):
        with pytest.raises(ValueError, match="desconocido"):
            launch_script("no_existe")

    def test_no_dos_simultaneos(self):
        """Si ya hay un job RUNNING, no se puede lanzar otro."""
        fake_job = Job(job_id="fake", script="ventas", status=JobStatus.RUNNING)
        runner_mod._running_job = fake_job

        with pytest.raises(ValueError, match="Ya hay un script"):
            launch_script("ventas")

    def test_job_completado_permite_nuevo(self):
        """Si el job anterior terminó, se puede lanzar otro."""
        fake_job = Job(job_id="fake", script="ventas", status=JobStatus.COMPLETED)
        runner_mod._running_job = fake_job

        # No debería lanzar ValueError (aunque el proceso real fallará
        # porque el script no existe en CI). Lo importante es que no
        # bloquea por lock.
        job = launch_script("ventas")
        assert job.script == "ventas"
        assert job.job_id in _jobs
        # Esperar un poco para que el thread arranque
        time.sleep(0.5)


# ── get/list jobs ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetListJobs:

    def test_get_job_no_existe(self):
        assert get_job("no_existe") is None

    def test_get_job_existe(self):
        j = Job(job_id="test1", script="ventas")
        _jobs["test1"] = j
        assert get_job("test1") is j

    def test_list_jobs_vacio(self):
        assert list_jobs() == []

    def test_list_jobs_orden(self):
        _jobs["a"] = Job(job_id="a", script="ventas", created_at="2026-01-01T00:00:00")
        _jobs["b"] = Job(job_id="b", script="gmail", created_at="2026-01-02T00:00:00")
        result = list_jobs(limit=10)
        assert result[0]["job_id"] == "b"  # Más reciente primero
        assert result[1]["job_id"] == "a"

    def test_list_jobs_limit(self):
        for i in range(5):
            _jobs[f"j{i}"] = Job(
                job_id=f"j{i}", script="ventas",
                created_at=f"2026-01-0{i+1}T00:00:00",
            )
        result = list_jobs(limit=3)
        assert len(result) == 3

    def test_get_running_job_none(self):
        assert get_running_job() is None

    def test_get_running_job_activo(self):
        j = Job(job_id="run1", script="ventas", status=JobStatus.RUNNING)
        runner_mod._running_job = j
        assert get_running_job() is j


# ── Historial cleanup ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHistorialCleanup:

    def test_limpia_al_llegar_a_max(self):
        """Cuando hay >= 50 jobs, se limpian los 10 más antiguos."""
        for i in range(50):
            _jobs[f"old{i:03d}"] = Job(
                job_id=f"old{i:03d}", script="ventas",
                created_at=f"2026-01-{(i % 28) + 1:02d}T{i % 24:02d}:00:00",
            )

        assert len(_jobs) == 50
        # Lanzar uno nuevo debería limpiar
        job = launch_script("ventas")
        time.sleep(0.3)
        # Ahora debería haber <= 41 (50 - 10 + 1)
        assert len(_jobs) <= 41
