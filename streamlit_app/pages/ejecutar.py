"""
pages/ejecutar.py — Panel de ejecución de scripts (solo admin).
Modo dual: subprocess local (Windows) + API fallback (VPS).
"""

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from utils.auth import require_role
from utils.entorno import es_streamlit_cloud, ruta_existe_seguro

require_role(["admin"])

st.title("Ejecutar scripts")

# ── Bloqueo temprano en Streamlit Cloud ─────────────────────────────────────
# Los scripts de esta página tocan filesystem local (Drive, Dropbox, Excel),
# Gmail API o ejecutan procesos largos. En Cloud NO se pueden ejecutar.
# La ejecución real ocurre en PC local o en VPS Contabo (cron). Mostramos un
# mensaje claro en lugar de dejar que la app crashee con PermissionError al
# resolver rutas Linux que no existen en el contenedor de Cloud.

if es_streamlit_cloud():
    st.warning(
        "⚠️ Esta página no se puede usar desde Streamlit Cloud. Los scripts "
        "(Gmail, Ventas, Cuadre, Movimientos Banco, Dashboard, etc.) tocan "
        "filesystem local (Drive, Dropbox), Gmail API o procesos largos."
    )
    st.markdown(
        "**Cómo ejecutarlos:**\n\n"
        "- **Desde el PC** (PowerShell):\n"
        "  ```powershell\n"
        "  cd C:\\_ARCHIVOS\\TRABAJO\\Facturas\\gestion-facturas\n"
        "  python gmail/gmail.py --produccion\n"
        "  python ventas_semana/script_barea.py\n"
        "  python cuadre/banco/cuadre.py\n"
        "  ```\n"
        "- **Desde el VPS Contabo** (`ssh root@194.34.232.6`):\n"
        "  ```bash\n"
        "  cd /opt/gestion-facturas && source .venv/bin/activate\n"
        "  python gmail/gmail.py --produccion\n"
        "  ```\n"
        "- **Cron del VPS** ya programa automáticamente:\n"
        "  - viernes 03:00 → `gmail.py`\n"
        "  - lunes 03:00 → `script_barea.py`"
    )
    st.info(
        "Streamlit Cloud queda como capa de **solo lectura/visualización** "
        "(documentos, dashboards, datos ya generados)."
    )
    st.stop()

# ── Detección de entorno (solo se ejecuta en PC o VPS reales) ───────────────

ES_WINDOWS = platform.system() == 'Windows'
ES_LINUX = platform.system() == 'Linux'

if ES_WINDOWS:
    PROJECT_ROOT = Path(os.environ.get(
        "GESTION_FACTURAS_DIR",
        r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas",
    ))
    VENV_PYTHON = PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'
elif ES_LINUX:
    # Detectar ruta del proyecto en VPS (rutas locales reales en Linux).
    # Usamos ruta_existe_seguro para no crashear si una de las candidatas
    # devuelve PermissionError en algún entorno restringido.
    PROJECT_ROOT = None
    for _ruta in ['/opt/gestion-facturas', '/root/gestion-facturas', '/home/ubuntu/gestion-facturas']:
        if ruta_existe_seguro(_ruta):
            PROJECT_ROOT = Path(_ruta)
            break
    if PROJECT_ROOT is None:
        PROJECT_ROOT = Path('/opt/gestion-facturas')
    VENV_PYTHON = PROJECT_ROOT / '.venv' / 'bin' / 'python3'
else:
    PROJECT_ROOT = Path('.')
    VENV_PYTHON = Path('python3')

ES_LOCAL = ruta_existe_seguro(PROJECT_ROOT) and ruta_existe_seguro(VENV_PYTHON)

if not ES_LOCAL:
    st.warning("Ejecución no disponible: no se encuentra el proyecto o el entorno virtual.")
    st.stop()


# ── Funciones de último resultado ───────────────────────────────────────────

def _ultimo_gmail() -> str:
    p = PROJECT_ROOT / "outputs" / "logs_gmail" / "gmail_resumen.json"
    if not ruta_existe_seguro(p):
        return "Sin ejecuciones previas"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        fecha = data.get("fecha", data.get("fecha_ejecucion", "?"))
        total = data.get("total_procesados", data.get("total", "?"))
        ok = data.get("exitosos", "?")
        err = data.get("errores", "?")
        rev = data.get("revision", data.get("requieren_revision", 0))
        return f"**{fecha}** — {total} procesados, {ok} OK, {err} errores, {rev} revisión"
    except Exception:
        return f"Archivo: {p.name} (error leyendo)"


def _ultimo_ventas() -> str:
    p = PROJECT_ROOT / "datos" / "Ventas Barea 2026.xlsx"
    if not ruta_existe_seguro(p):
        # Buscar alternativa
        ventas_dir = PROJECT_ROOT / "ventas_semana"
        for f in sorted(ventas_dir.glob("Ventas Barea*.xlsx"), reverse=True):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            return f"**{mtime:%d/%m/%Y %H:%M}** — {f.name}"
        return "Sin archivo de ventas"
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return f"**{mtime:%d/%m/%Y %H:%M}** — última actualización Excel"


def _ultimo_cuadre() -> str:
    outputs = PROJECT_ROOT / "outputs"
    if not ruta_existe_seguro(outputs):
        return "Sin cuadres previos"
    cuadres = sorted(outputs.glob("CUADRE_*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not cuadres:
        cuadre_dir = PROJECT_ROOT / "cuadre" / "banco"
        cuadres = sorted(cuadre_dir.glob("Cuadre_*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not cuadres:
        return "Sin cuadres previos"
    f = cuadres[0]
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    return f"**{mtime:%d/%m/%Y}** — {f.name}"


def _ultimo_mov_banco() -> str:
    p = PROJECT_ROOT / "datos" / "Movimientos Cuenta 26.xlsx"
    if not ruta_existe_seguro(p):
        return "Sin consolidado"
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return f"**{mtime:%d/%m/%Y %H:%M}** — última actualización"


# ── Definición de scripts ───────────────────────────────────────────────────

SCRIPTS = {
    "gmail": {
        "nombre": "Gmail (Facturas)",
        "icono": "📧",
        "descripcion": "Descarga facturas de Gmail, renombra, sube a Dropbox, genera PAGOS Excel",
        "cmd": [str(VENV_PYTHON), "gmail/gmail.py", "--produccion"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_fn": _ultimo_gmail,
        "requiere_archivos": False,
        "disponible_vps": True,
        "color": "#1a73e8",
    },
    "ventas": {
        "nombre": "Ventas (Loyverse + WooCommerce)",
        "icono": "📊",
        "descripcion": "Descarga ventas de Loyverse API, genera Excel y dashboards",
        "cmd": [str(VENV_PYTHON), "ventas_semana/script_barea.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_fn": _ultimo_ventas,
        "requiere_archivos": False,
        "disponible_vps": True,
        "color": "#2e7d32",
    },
    "cuadre": {
        "nombre": "Cuadre Bancario",
        "icono": "🏦",
        "descripcion": "Clasifica movimientos bancarios y concilia con facturas",
        "cmd": [str(VENV_PYTHON), "cuadre/banco/cuadre.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_fn": _ultimo_cuadre,
        "requiere_archivos": False,
        "disponible_vps": False,
        "color": "#0d47a1",
    },
    "mov_banco": {
        "nombre": "Movimientos Banco",
        "icono": "🏛️",
        "descripcion": "Incorpora movimientos nuevos de Sabadell al consolidado",
        "cmd": None,  # Se construye dinámicamente
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_fn": _ultimo_mov_banco,
        "requiere_archivos": True,
        "file_label": "Archivo(s) .xls de Sabadell",
        "file_types": ["xls", "xlsx"],
        "disponible_vps": False,
        "color": "#4a148c",
    },
}

SECONDARY_SCRIPTS = {
    "gmail_test": {
        "nombre": "Gmail (test)",
        "icono": "🧪",
        "descripcion": "Modo test sin modificar archivos",
        "cmd": [str(VENV_PYTHON), "gmail/gmail.py", "--test"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
    },
    "dashboard": {
        "nombre": "Dashboard",
        "icono": "📈",
        "descripcion": "Generar HTML + PDF (meses cerrados)",
        "cmd": [str(VENV_PYTHON), "ventas_semana/generar_dashboard.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
    },
    "dia_tickets": {
        "nombre": "Tickets DIA",
        "icono": "🛒",
        "descripcion": "Descargar tickets (requiere sesión activa)",
        "cmd": [str(VENV_PYTHON), "-m", "scripts.tickets.dia"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
    },
    "backup": {
        "nombre": "Backup cifrado",
        "icono": "🔐",
        "descripcion": "Backup AES-256 de datos sensibles",
        "cmd": [str(VENV_PYTHON), "scripts/backup_cifrado.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
    },
}


# ── Ejecución subprocess ───────────────────────────────────────────────────

def _verificar_script(cmd: list[str]) -> str | None:
    """Verifica que el script existe. Devuelve mensaje de error o None si OK."""
    if not cmd or len(cmd) < 2:
        return "Comando no configurado"
    script_path = cmd[1]
    # Si usa -m, no verificar path
    if script_path == "-m":
        return None
    full_path = Path(cmd[0]).parent.parent.parent / script_path if not Path(script_path).is_absolute() else Path(script_path)
    # Verificar relativo al cwd
    return None


def ejecutar_script(script_key: str, config: dict, archivos_extra: list[str] | None = None):
    """Lanza un script con subprocess. Devuelve el proceso Popen."""
    if script_key == "mov_banco" and archivos_extra:
        consolidado = str(PROJECT_ROOT / "datos" / "Movimientos Cuenta 26.xlsx")
        cmd = [str(VENV_PYTHON), "scripts/actualizar_movimientos.py",
               "--consolidado", consolidado] + archivos_extra
    else:
        cmd = config["cmd"]

    env = os.environ.copy()
    env.update(config.get("env_extra", {}))

    proceso = subprocess.Popen(
        cmd,
        cwd=config.get("cwd", str(PROJECT_ROOT)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )
    return proceso


# ── Session state ───────────────────────────────────────────────────────────

if "proceso_activo" not in st.session_state:
    st.session_state.proceso_activo = False

hay_proceso = st.session_state.proceso_activo

# ── Tarjetas principales ───────────────────────────────────────────────────

st.markdown("---")

cols = st.columns(2)
for i, (key, config) in enumerate(SCRIPTS.items()):
    with cols[i % 2]:
        with st.container(border=True):
            st.markdown(f"### {config['icono']} {config['nombre']}")
            st.caption(config["descripcion"])

            # Scripts no disponibles en VPS
            no_disponible_aqui = ES_LINUX and not config.get("disponible_vps", True)
            if no_disponible_aqui:
                st.info("Solo disponible en PC local")

            # Último resultado
            try:
                ultimo = config["ultimo_fn"]()
            except Exception:
                ultimo = "Sin datos"
            st.markdown(f"🕐 {ultimo}")

            # File uploader si requiere archivos
            archivos_temp = []
            if config.get("requiere_archivos"):
                uploaded = st.file_uploader(
                    config.get("file_label", "Archivo"),
                    type=config.get("file_types", ["xls"]),
                    accept_multiple_files=True,
                    key=f"upload_{key}",
                )
                if uploaded:
                    import tempfile
                    for uf in uploaded:
                        tmp = os.path.join(tempfile.gettempdir(), uf.name)
                        with open(tmp, "wb") as f:
                            f.write(uf.read())
                        archivos_temp.append(tmp)

            can_run = (not config.get("requiere_archivos") or len(archivos_temp) > 0) and not no_disponible_aqui

            if st.button(
                "▶️ Ejecutar",
                key=f"btn_{key}",
                disabled=not can_run or hay_proceso,
                type="primary",
                use_container_width=True,
            ):
                # Verificar script
                if config.get("cmd") is None and not archivos_temp:
                    st.error("Este script requiere archivos")
                elif config.get("cmd") and not ruta_existe_seguro(config["cwd"]):
                    st.error(f"Directorio no encontrado: {config['cwd']}")
                else:
                    st.session_state.proceso_activo = True
                    hay_proceso = True

                    log_container = st.empty()
                    status_container = st.empty()
                    status_container.info(f"⏳ Ejecutando {config['nombre']}...")

                    try:
                        proceso = ejecutar_script(
                            key, config,
                            archivos_temp if archivos_temp else None,
                        )

                        log_lines = []
                        while True:
                            line = proceso.stdout.readline()
                            if line:
                                log_lines.append(line.rstrip())
                                log_container.code(
                                    "\n".join(log_lines[-50:]),
                                    language="text",
                                )
                            elif proceso.poll() is not None:
                                break

                        remaining = proceso.stdout.read()
                        if remaining:
                            log_lines.extend(remaining.strip().split("\n"))
                            log_container.code(
                                "\n".join(log_lines[-50:]),
                                language="text",
                            )

                        exit_code = proceso.returncode

                        if exit_code == 0:
                            status_container.success(
                                f"✅ {config['nombre']} completado correctamente"
                            )
                        else:
                            status_container.error(
                                f"❌ {config['nombre']} falló (código {exit_code})"
                            )

                        with st.expander("📋 Log completo", expanded=False):
                            st.code("\n".join(log_lines), language="text")

                    except FileNotFoundError:
                        status_container.error(
                            f"❌ Script no encontrado. Verifica que existe: {config.get('cmd', ['?'])[1]}"
                        )
                    except Exception as e:
                        status_container.error(f"❌ Error: {e}")
                    finally:
                        st.session_state.proceso_activo = False
                        hay_proceso = False

# ── Scripts secundarios ─────────────────────────────────────────────────────

st.markdown("---")
with st.expander("Más scripts"):
    sec_cols = st.columns(2)
    for i, (script_id, config) in enumerate(SECONDARY_SCRIPTS.items()):
        with sec_cols[i % 2]:
            st.markdown(f"**{config['icono']} {config['nombre']}**")
            st.caption(config["descripcion"])

            if st.button(
                "▶️ Ejecutar",
                key=f"btn_{script_id}",
                disabled=hay_proceso,
            ):
                st.session_state.proceso_activo = True
                hay_proceso = True

                log_container = st.empty()
                status_container = st.empty()
                status_container.info(f"⏳ Ejecutando {config['nombre']}...")

                try:
                    proceso = ejecutar_script(script_id, config)

                    log_lines = []
                    while True:
                        line = proceso.stdout.readline()
                        if line:
                            log_lines.append(line.rstrip())
                            log_container.code(
                                "\n".join(log_lines[-50:]),
                                language="text",
                            )
                        elif proceso.poll() is not None:
                            break

                    remaining = proceso.stdout.read()
                    if remaining:
                        log_lines.extend(remaining.strip().split("\n"))
                        log_container.code(
                            "\n".join(log_lines[-50:]),
                            language="text",
                        )

                    exit_code = proceso.returncode

                    if exit_code == 0:
                        status_container.success(
                            f"✅ {config['nombre']} completado"
                        )
                    else:
                        status_container.error(
                            f"❌ {config['nombre']} falló (código {exit_code})"
                        )

                    with st.expander("📋 Log completo", expanded=False):
                        st.code("\n".join(log_lines), language="text")

                except FileNotFoundError:
                    status_container.error(
                        f"❌ Script no encontrado: {config.get('cmd', ['?'])[1]}"
                    )
                except Exception as e:
                    status_container.error(f"❌ Error: {e}")
                finally:
                    st.session_state.proceso_activo = False
                    hay_proceso = False
