# TAREA: Ejecutar Scripts — Modo dual (subprocess local + API fallback)
<!-- Para ejecutar con: claude --autoaccept -->

> Ruta: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\streamlit_app\pages\ejecutar.py`
> API: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\api\`

---

## PROBLEMA

La página `ejecutar.py` depende de la API FastAPI (localhost:8000) para lanzar scripts.
Si la API no está corriendo, muestra "requiere backend local" y no hace nada.
La API rara vez está corriendo manualmente.

## SOLUCIÓN: Modo dual

1. **Modo LOCAL (subprocess):** Si detecta que está en Windows + las rutas locales existen → lanza scripts directamente con `subprocess.Popen`. NO necesita API.
2. **Modo API (fallback):** Si detecta que está en Linux (VPS) o si el usuario prefiere → intenta conectar con la API. Si no hay API, muestra aviso.

La detección es simple:
```python
import platform
import os

ES_LOCAL = platform.system() == 'Windows' and os.path.exists(r'C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas')
```

---

## IMPLEMENTACIÓN

### 1. Reescribir ejecutar.py completa

**Estructura:**

```python
import streamlit as st
import subprocess
import platform
import os
import sys
import time
import json
import threading
from datetime import datetime
from pathlib import Path

from utils.auth import require_role

require_role(["admin"])

# Detección de entorno
PROJECT_ROOT = Path(r'C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas')
PARSEO_ROOT = Path(r'C:\_ARCHIVOS\TRABAJO\Facturas\Parseo')
VENV_PYTHON = PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'
ES_LOCAL = platform.system() == 'Windows' and PROJECT_ROOT.exists()

st.title("▶️ Ejecutar scripts")

if not ES_LOCAL:
    st.warning("⚠️ Ejecución remota no disponible todavía. Accede desde el PC local (localhost:8503).")
    st.stop()
```

### 2. Definir scripts disponibles

```python
SCRIPTS = {
    "gmail": {
        "nombre": "📧 Gmail — Facturas",
        "descripcion": "Descarga facturas de Gmail, identifica proveedor, sube a Dropbox, genera PAGOS Excel",
        "cmd": [str(VENV_PYTHON), "gmail/gmail.py", "--produccion"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_resultado": lambda: _leer_gmail_resumen(),
        "requiere_archivos": False,
    },
    "ventas": {
        "nombre": "📊 Ventas — Loyverse + WooCommerce",
        "descripcion": "Descarga ventas de Loyverse API y WooCommerce, genera Excel y dashboards",
        "cmd": [str(VENV_PYTHON), "ventas_semana/script_barea.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_resultado": lambda: _leer_ventas_resultado(),
        "requiere_archivos": False,
    },
    "cuadre": {
        "nombre": "🏦 Cuadre Bancario",
        "descripcion": "Clasifica movimientos bancarios y concilia con facturas",
        "cmd": [str(VENV_PYTHON), "cuadre/banco/cuadre.py"],
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_resultado": lambda: _leer_cuadre_resultado(),
        "requiere_archivos": False,
    },
    "mov_banco": {
        "nombre": "🏛️ Movimientos Banco",
        "descripcion": "Incorpora movimientos Sabadell al consolidado",
        "cmd": None,  # Se construye dinámicamente con archivos subidos
        "cwd": str(PROJECT_ROOT),
        "env_extra": {"PYTHONPATH": str(PROJECT_ROOT)},
        "ultimo_resultado": lambda: _leer_mov_banco_resultado(),
        "requiere_archivos": True,
    },
}
```

### 3. Funciones de último resultado

```python
def _leer_gmail_resumen():
    """Lee outputs/logs_gmail/gmail_resumen.json"""
    path = PROJECT_ROOT / 'outputs' / 'logs_gmail' / 'gmail_resumen.json'
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            fecha = data.get('fecha_ejecucion', '?')
            return (
                f"Última ejecución: {fecha[:16]}\n"
                f"Procesados: {data.get('total_procesados', '?')} | "
                f"OK: {data.get('exitosos', '?')} | "
                f"Revisión: {data.get('requieren_revision', '?')} | "
                f"Errores: {data.get('errores', '?')}"
            )
        except Exception:
            pass
    return "Sin datos de última ejecución"

def _leer_ventas_resultado():
    """Lee fecha de modificación del Excel de ventas"""
    # Buscar el archivo más reciente
    ventas_dir = PROJECT_ROOT / 'ventas_semana'
    for f in sorted(ventas_dir.glob('Ventas Barea*.xlsx'), reverse=True):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        return f"Último archivo: {f.name}\nModificado: {mtime:%d/%m/%Y %H:%M}"
    return "Sin datos"

def _leer_cuadre_resultado():
    """Busca último CUADRE_*.xlsx"""
    outputs = PROJECT_ROOT / 'outputs'
    cuadres = sorted(outputs.glob('CUADRE_*.xlsx'), reverse=True)
    if cuadres:
        f = cuadres[0]
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        return f"Último: {f.name}\nGenerado: {mtime:%d/%m/%Y %H:%M}"
    return "Sin datos"

def _leer_mov_banco_resultado():
    """Lee info del consolidado"""
    path = PROJECT_ROOT / 'datos' / 'Movimientos_Cuenta_26.xlsx'
    if path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return f"Consolidado: {path.name}\nModificado: {mtime:%d/%m/%Y %H:%M}"
    return "Sin datos"
```

### 4. Ejecución con subprocess + log en tiempo real

```python
def ejecutar_script(script_key, archivos_extra=None):
    """
    Lanza un script con subprocess y captura stdout/stderr en tiempo real.
    Devuelve (exit_code, log_completo).
    """
    config = SCRIPTS[script_key]
    
    if script_key == 'mov_banco' and archivos_extra:
        # Construir comando con archivos subidos
        consolidado = str(PROJECT_ROOT / 'datos' / 'Movimientos_Cuenta_26.xlsx')
        cmd = [str(VENV_PYTHON), 'scripts/actualizar_movimientos.py', '--consolidado', consolidado] + archivos_extra
    else:
        cmd = config['cmd']
    
    # Preparar entorno
    env = os.environ.copy()
    env.update(config.get('env_extra', {}))
    
    # Lanzar proceso
    proceso = subprocess.Popen(
        cmd,
        cwd=config['cwd'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env,
        bufsize=1,  # Line buffered
    )
    
    return proceso
```

### 5. UI — tarjetas + ejecución

Para cada script, mostrar una tarjeta con:
- Nombre + icono
- Descripción
- Último resultado (gris, pequeño)
- File uploader si requiere_archivos (solo mov_banco)
- Botón "▶️ Ejecutar"
- Cuando se ejecuta: mostrar log en st.code() que se actualiza con st.empty()
- Al terminar: st.success() o st.error()

```python
for key, config in SCRIPTS.items():
    with st.container(border=True):
        st.subheader(config['nombre'])
        st.caption(config['descripcion'])
        
        # Último resultado
        try:
            ultimo = config['ultimo_resultado']()
            st.text(ultimo)
        except Exception:
            st.text("Sin datos")
        
        archivos_temp = []
        if config.get('requiere_archivos'):
            uploaded = st.file_uploader(
                "Sube archivos .xls de Sabadell",
                type=['xls'],
                accept_multiple_files=True,
                key=f"upload_{key}"
            )
            if uploaded:
                # Guardar temporalmente
                import tempfile
                for uf in uploaded:
                    tmp = os.path.join(tempfile.gettempdir(), uf.name)
                    with open(tmp, 'wb') as f:
                        f.write(uf.read())
                    archivos_temp.append(tmp)
        
        # Botón ejecutar
        if st.button(f"▶️ Ejecutar", key=f"btn_{key}", disabled=(config.get('requiere_archivos') and not archivos_temp)):
            
            # Verificar que no hay otro script corriendo
            if 'proceso_activo' in st.session_state and st.session_state.proceso_activo:
                st.warning("Ya hay un script en ejecución. Espera a que termine.")
            else:
                st.session_state.proceso_activo = True
                
                log_container = st.empty()
                status_container = st.empty()
                
                status_container.info(f"⏳ Ejecutando {config['nombre']}...")
                
                try:
                    proceso = ejecutar_script(key, archivos_temp if archivos_temp else None)
                    
                    log_lines = []
                    while True:
                        line = proceso.stdout.readline()
                        if line:
                            log_lines.append(line.rstrip())
                            # Mostrar últimas 50 líneas
                            log_container.code('\n'.join(log_lines[-50:]), language='text')
                        elif proceso.poll() is not None:
                            break
                    
                    # Leer lo que quede
                    remaining = proceso.stdout.read()
                    if remaining:
                        log_lines.extend(remaining.strip().split('\n'))
                        log_container.code('\n'.join(log_lines[-50:]), language='text')
                    
                    exit_code = proceso.returncode
                    
                    if exit_code == 0:
                        status_container.success(f"✅ {config['nombre']} completado correctamente")
                    else:
                        status_container.error(f"❌ {config['nombre']} falló (código {exit_code})")
                    
                    # Mostrar log completo en expander
                    with st.expander("📋 Log completo", expanded=False):
                        st.code('\n'.join(log_lines), language='text')
                        
                except Exception as e:
                    status_container.error(f"❌ Error: {e}")
                finally:
                    st.session_state.proceso_activo = False
```

### 6. Scripts secundarios (en expander al final)

Añadir un expander "Scripts secundarios" con:
- Gmail (modo test): `gmail/gmail.py --test`
- Dashboard: `ventas_semana/generar_dashboard.py`  
- Tickets DIA: `scripts/tickets/dia.py`
- Backup: `scripts/backup_cifrado.py`

Mismo patrón de ejecución pero en un expander colapsado.

### 7. Session state para evitar re-ejecuciones

```python
if 'proceso_activo' not in st.session_state:
    st.session_state.proceso_activo = False
```

Deshabilitar TODOS los botones mientras hay un proceso corriendo.

---

## VERIFICACIÓN

1. Verificar que la página carga sin errores:
```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\streamlit_app
python -c "import ast; ast.parse(open('pages/ejecutar.py', encoding='utf-8').read()); print('OK')"
```

2. Verificar que VENV_PYTHON existe:
```bash
dir C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\.venv\Scripts\python.exe
```

3. Verificar que las rutas de los scripts existen:
```bash
dir C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\gmail.py
dir C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\ventas_semana\script_barea.py
dir C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\cuadre\banco\cuadre.py
dir C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\scripts\actualizar_movimientos.py
```
Si alguna ruta no existe, buscar la ruta correcta con `dir /s` y corregir en SCRIPTS.

4. Test rápido: ejecutar gmail en modo test desde la página para verificar que subprocess funciona:
```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
.venv\Scripts\python.exe gmail\gmail.py --test
```
Debe ejecutar sin errores (modo test no modifica nada).

---

## REGLAS

- NO depender de la API FastAPI para nada. Subprocess directo.
- NO tocar app.py, auth.py, ni el CSS
- Usar VENV_PYTHON (el python del virtualenv), NO el python del sistema
- PYTHONPATH debe incluir PROJECT_ROOT para que funcionen imports de nucleo/, config/
- Si un script no existe en la ruta configurada, mostrar aviso (no crash)
- El log debe ser streaming (línea a línea), no esperar a que termine
- Solo admin puede ejecutar (require_role ya está)
- Un solo script a la vez (session_state.proceso_activo)
- Preservar el estilo corporativo existente (Syne + DM Sans si hay CSS)
- Al terminar: recargar el último resultado de la tarjeta correspondiente
