# TODO: Fase 0 — Preparar arquitectura sin romper nada
<!-- Para ejecutar con: claude --autoaccept -->
<!-- Sesión nocturna — 09/04/2026 -->
<!-- RIESGO: CERO. Solo crea carpetas, un JSON, y arregla 2 bugs de 1 línea. -->
<!-- Si algo falla, el proyecto sigue exactamente igual. -->

## CONTEXTO

Proyecto: gestion-facturas
Ruta: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\`
Spec maestra: `docs/SPEC_GESTION_FACTURAS_v4.md`

Este es el primer paso de una migración progresiva a arquitectura por capas:
- `core/` → Capa 1 (datos, modelos, config, utilidades)
- `engines/` → Capa 2 (lógica de negocio)
- `cli/` → Capa 3 (interfaces CLI)

En esta Fase 0 NO se mueve ni modifica lógica existente. Solo se prepara la estructura.

---

## TAREA 1: Crear carpetas con __init__.py

Crear estas carpetas (si no existen) con un `__init__.py` mínimo en cada una:

```
core/__init__.py
engines/__init__.py
cli/__init__.py
```

Contenido de cada `__init__.py`:

```python
# core/__init__.py
"""Capa 1 — Datos, modelos, configuración y utilidades compartidas."""

# engines/__init__.py
"""Capa 2 — Motores de negocio (parseo, gmail, cuadre, ventas)."""

# cli/__init__.py
"""Capa 3 — Interfaces de línea de comandos."""
```

---

## TAREA 2: Crear core/config.py

Crear `core/config.py` con configuración centralizada. Este archivo será la FUENTE ÚNICA de rutas del proyecto. Usa variables de entorno con fallback a las rutas Windows actuales de Jaime.

```python
"""
core/config.py — Configuración centralizada del proyecto.

FUENTE ÚNICA de rutas. Todos los módulos deben importar de aquí.
En Windows (Jaime): usa los fallback hardcoded.
En VPS (Contabo): lee de variables de entorno o .env
"""
import os
from pathlib import Path
from dataclasses import dataclass, field


VERSION = "5.17"


@dataclass
class Config:
    """Configuración del proyecto. Lee de env vars con fallback a rutas locales."""

    base_dir: Path = field(default_factory=lambda: Path(
        os.environ.get(
            "GESTION_FACTURAS_DIR",
            r"C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas"
        )
    ))

    parseo_dir: Path = field(default_factory=lambda: Path(
        os.environ.get(
            "PARSEO_DIR",
            r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo"
        )
    ))

    dropbox_base: Path = field(default_factory=lambda: Path(
        os.environ.get(
            "DROPBOX_BASE",
            r"C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD"
        )
    ))

    @property
    def datos_dir(self) -> Path:
        return self.base_dir / "datos"

    @property
    def outputs_dir(self) -> Path:
        return self.base_dir / "outputs"

    @property
    def maestro_path(self) -> Path:
        return self.datos_dir / "MAESTRO_PROVEEDORES.xlsx"

    @property
    def diccionario_path(self) -> Path:
        return self.datos_dir / "DiccionarioProveedoresCategoria.xlsx"

    @property
    def alias_path(self) -> Path:
        return self.datos_dir / "alias_diccionario.json"

    @property
    def emails_json_path(self) -> Path:
        return self.datos_dir / "emails_procesados.json"

    @property
    def extractores_dir(self) -> Path:
        return self.parseo_dir / "extractores"

    @classmethod
    def from_env(cls) -> "Config":
        """Carga config desde .env si existe, luego construye."""
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass  # dotenv no instalado, usar solo env vars del sistema
        return cls()


# Instancia global (singleton)
_config: Config | None = None


def get_config() -> Config:
    """Devuelve la configuración global (lazy singleton)."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
```

---

## TAREA 3: Exportar ALIAS_DICCIONARIO a JSON

Lee el diccionario `ALIAS_DICCIONARIO` que está hardcoded en `main.py` (Parseo) — son aproximadamente 200 líneas entre las líneas 520-720 del archivo.

Busca en `main.py` (que está en la carpeta Parseo: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\main.py`) el bloque:

```python
ALIAS_DICCIONARIO = {
    ...
}
```

Extrae todo el contenido de ese diccionario y guárdalo como JSON en:

```
datos/alias_diccionario.json
```

Formato:
```json
{
  "SABORES DE PATERNA": "SABORES PATERNA",
  "PATERNA": "SABORES PATERNA",
  "FELISA GOURMET": "FELISA",
  ...
}
```

IMPORTANTE:
- Las claves y valores deben ser strings
- Mantener todas las entradas, incluidas las de errores ortográficos (SERRRIN, BEDORAH, etc.)
- Encoding UTF-8
- Ordenar las claves alfabéticamente para facilitar mantenimiento
- No modificar main.py en este paso (el JSON es un duplicado, no un reemplazo todavía)

---

## TAREA 4: Fix detectar_trimestre() — año dinámico

En `main.py` (Parseo: `C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\main.py`), buscar la función `detectar_trimestre`.

Hay DOS líneas con el año hardcoded `T25`. Cambiar ambas para usar el año actual:

ANTES:
```python
return f'{num_tri}T25'
```

DESPUÉS:
```python
return f'{num_tri}T{datetime.now().year % 100}'
```

Hay dos ocurrencias de `return f'{num_tri}T25'` en esa función. Cambiar AMBAS.

También el fallback al final de la función debería devolver algo más útil:

ANTES:
```python
return datetime.now().strftime('%Y%m%d')
```

DESPUÉS:
```python
# Fallback: trimestre actual
q = (datetime.now().month - 1) // 3 + 1
return f'{q}T{datetime.now().year % 100}'
```

---

## TAREA 5: Sincronizar VERSION en settings.py

En `config/settings.py` (dentro de gestion-facturas), cambiar:

ANTES:
```python
VERSION = "5.14"
```

DESPUÉS:
```python
VERSION = "5.17"
```

---

## TAREA 6: Crear CLAUDE.md en raíz del proyecto

Crear `CLAUDE.md` en la raíz de `gestion-facturas/` con este contenido:

```markdown
# CLAUDE.md — gestion-facturas

## Qué es
Sistema de automatización contable para TASCA BAREA S.L.L. (bar + tienda gourmet en Madrid).
Gestiona: facturas proveedores, ventas, movimientos bancarios, cuadre.

## Arquitectura (en migración)
Objetivo: 3 capas. Migración progresiva en curso.

```
core/        → Capa 1: datos, modelos, config, utilidades (EN CONSTRUCCIÓN)
engines/     → Capa 2: lógica de negocio (EN CONSTRUCCIÓN)
cli/         → Capa 3: interfaces CLI (EN CONSTRUCCIÓN)
api/         → Capa 3: REST API (FastAPI, ya funcional)
streamlit_app/ → Capa 3: web UI (ya funcional)
```

Mientras se migra, la lógica sigue en los archivos originales:
- PARSEO: `Parseo/main.py` (ruta separada)
- GMAIL: `compras/gmail.py`
- CUADRE: `compras/cuadre.py` y `cuadre/banco/cuadre_v2.py`
- VENTAS: `ventas/script_barea.py`

## Comandos principales
- Parseo: `cd Parseo && python main.py -i "carpeta" -o "salida.xlsx"`
- Gmail: `cd compras && python gmail.py --produccion`
- Cuadre: `python -m cuadre.banco.cuadre --desde 01/01/2026 --hasta 31/03/2026`
- Ventas: `cd ventas && python script_barea.py`
- API: `python -m api.server`
- Tests: `pytest tests/unit/ -v`

## Config
Configuración centralizada en `core/config.py` (nuevo).
Datos sensibles en `config/datos_sensibles.py` (gitignored).
Env vars para cloud: GESTION_FACTURAS_DIR, DROPBOX_BASE, PARSEO_DIR.

## Reglas de negocio invariables
1. **Portes** → SIEMPRE distribuir proporcionalmente, NUNCA línea separada
2. **JPG** → procesar o rellenar mínimos (#, FECHA, PROVEEDOR), NUNCA rechazar
3. **CUADRE** → genera su propio archivo, NUNCA modifica COMPRAS
4. **Fuzzy matching** → umbral ≥85% para proveedores
5. **Fallback PDF** → pdfplumber → PyMuPDF → tesseract OCR (spa)
6. **Portes fórmula** → `(coste_envío × (1 + IVA_envío/100)) / (1 + IVA_productos/100)`

## Crear un extractor nuevo
1. Copiar `Parseo/extractores/_plantilla.py`
2. Configurar: nombre, cif, iban, metodo_pdf
3. Implementar: `extraer_lineas(texto) → [{articulo, base, iva, ...}]`
4. Decorador `@registrar('NOMBRE', 'ALIAS1', 'ALIAS2')` → auto-registro
5. NO tocar `__init__.py`
6. `_convertir_importe()` heredado de `ExtractorBase` — no reimplementar

## Datos de referencia
- MAESTRO_PROVEEDORES: ~195 proveedores, ~585 aliases
- DiccionarioProveedoresCategoria: ~1.254 artículos
- alias_diccionario.json: mapeo nombre archivo → nombre diccionario
- Cuentas: Tasca ES78 0081 0259 1000 0184 4495 | Comestibles ES76 0081 0259 1700 0199 2404

## Excel estilos
- Tasca: TableStyleMedium9 (azul)
- Comestibles: TableStyleMedium4 (verde)
- Facturas: TableStyleMedium3 (rojo)
- Formato cifras: español 1.234,56 €

## Spec maestra
`docs/SPEC_GESTION_FACTURAS_v4.md` — fuente de verdad para toda decisión arquitectónica.
```

---

## TAREA 7: Verificar que nada se rompió

Ejecutar los tests existentes:

```bash
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
pytest tests/unit/ -v
```

Si algún test falla, investigar y arreglar. Los cambios de esta fase NO deberían romper nada porque:
- Las carpetas nuevas están vacías (excepto __init__.py)
- El JSON es una copia nueva, no reemplaza nada
- Los 2 fixes son en archivos específicos (main.py y settings.py)
- CLAUDE.md es un archivo nuevo

---

## VERIFICACIÓN FINAL

Al terminar, confirmar que existen estos archivos nuevos:

```
gestion-facturas/
├── core/
│   ├── __init__.py          ✅ NUEVO
│   └── config.py            ✅ NUEVO
├── engines/
│   └── __init__.py          ✅ NUEVO
├── cli/
│   └── __init__.py          ✅ NUEVO
├── datos/
│   └── alias_diccionario.json  ✅ NUEVO
├── CLAUDE.md                ✅ NUEVO
├── config/
│   └── settings.py          ✅ MODIFICADO (VERSION = "5.17")
└── [Parseo/main.py]         ✅ MODIFICADO (detectar_trimestre año dinámico)
```

Y que `pytest tests/unit/ -v` pasa todos los tests.

---

## NOTAS PARA CLAUDE CODE

- El proyecto tiene 2 ubicaciones: `gestion-facturas/` (principal) y `Parseo/` (extractores + main.py de parseo). Ambas en `C:\_ARCHIVOS\TRABAJO\Facturas\`.
- NO mover archivos existentes en esta fase.
- NO cambiar imports existentes en esta fase.
- Si hay dudas sobre una tarea, SALTAR y continuar con la siguiente.
- Al terminar, actualizar `tasks/todo.md` con lo completado.
