# READMENORMA43.md

## Qué es esto
`norma43.py` convierte ficheros bancarios **Norma 43** (`.n43`) de **Banco Sabadell (empresa)** en un **Excel acumulado** con los movimientos, separado en **dos pestañas** (una por cuenta), con:

- **deduplicación** (si lo ejecutas dos veces con los mismos `.n43`, no duplica filas)
- **marcado de posibles duplicados/correcciones** (`DUPLICADO_POSIBLE`)
- **trazabilidad** (de qué fichero y línea sale cada movimiento)
- **archivado** de los `.n43` procesados

Está pensado para tu flujo semanal manual (2 ficheros como máximo normalmente).

---

## Requisitos
- Windows
- Python 3.10+
- Paquetes:
  - `pandas`
  - `openpyxl`

Instalación:

```bat
pip install pandas openpyxl
```

---

## Dónde van las cosas (rutas fijas)
El script tiene rutas configuradas dentro del propio archivo `norma43.py`:

### Excel de salida (acumulado)
Se crea/actualiza en:

`C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs\MovimientosSabadellYY.xlsx`

Donde `YY` es el año a 2 dígitos (ej.: `MovimientosSabadell26.xlsx`).

### Archivado de .n43 procesados
Después de procesar, los `.n43` se mueven a:

`C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\norma43\archivados\`

---

## Uso (paso a paso)
1) Descarga desde Sabadell los `.n43` (uno por cuenta, rango semanal).
2) Guárdalos en una carpeta local temporal (mejor fuera de Dropbox).
3) Abre CMD o PowerShell y ejecuta:

```bat
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\norma43
python norma43.py
```

4) El programa te pedirá la carpeta de entrada:

```
📥 Ruta de la carpeta que contiene los .n43:
```

Pega la ruta y Enter.

---

## Cuentas y pestañas
El script SOLO acepta dos cuentas (si aparece otra, para con error):

- Pestaña `COMESTIBLES` → cuenta que termina en **2404**
- Pestaña `TASCA` → cuenta que termina en **4495**

---

## Estructura del Excel (columnas)
En cada pestaña (`COMESTIBLES` / `TASCA`) se genera este formato:

- `MovimientoId`  
  Hash estable (clave de deduplicación).
- `#`  
  Contador de fila (se recalcula).
- `F. Operativa`  
  Fecha operativa (formato `DD-MM-YY`).
- `Concepto`  
  Texto concatenado de los registros 23 (`" | "` entre líneas).
- `F. Valor`  
  Fecha valor (formato `DD-MM-YY`).
- `Importe`  
  Número con 2 decimales. Negativos con `-`.
- `Saldo`  
  Si el N43 lo trae de forma detectable, con 2 decimales.
- `Referencia 1` / `Referencia 2`  
  Extracción **best-effort** desde el `Concepto` (E2E/REF/etc. si aparecen).
- `Estado`  
  `OK` o `DUPLICADO_POSIBLE`.
- `FicheroOrigen`  
  Nombre del `.n43` que lo generó.
- `LineaOrigen`  
  Número de línea (1-based) donde está el registro 22.

---

## Deduplicación (cómo funciona)
- Cada movimiento genera un `MovimientoId` a partir de:
  - la cuenta (últimos 4 dígitos)
  - la línea 22 completa
  - el bloque 23 completo asociado

Si un `MovimientoId` ya existe en la pestaña, **no se inserta**.

---

## DUPLICADO_POSIBLE (modo C1)
Si un movimiento nuevo NO coincide exactamente (hash distinto) pero parece el mismo:
- mismo importe (±0,01)
- fechas cercanas (±3 días)
- concepto similar (por tokens)

Entonces se inserta igualmente pero se marca:

- `Estado = DUPLICADO_POSIBLE`

Esto sirve para detectar “correcciones” o exportaciones con texto ligeramente distinto.

---

## Errores típicos y soluciones
### 1) Permisos / Dropbox lock
Si los `.n43` están en Dropbox, a veces están bloqueados o “online-only”.
Solución: copia los `.n43` a una carpeta local y procesa desde ahí.

### 2) Descargué un HTML en vez de N43
Si el fichero no empieza por `11`, el script lo rechazará.
Solución: revisa la exportación en Sabadell y el formato elegido.

### 3) Sale “Cuenta no reconocida”
Significa que el `.n43` no pertenece a 2404/4495.
Solución: revisa qué cuenta descargaste o ajusta el mapeo en `SHEET_BY_ACCOUNT_SUFFIX`.

---

## Notas técnicas (para futuro)
- El parseo del registro 22 es “best-effort” (robusto pero no perfecto).
  Si quieres precisión total por posiciones, se ajusta con un ejemplo real de Sabadell.
- Las referencias 1/2 también se mejoran con 2-3 ejemplos de conceptos reales.

---

## Licencia / uso
Uso interno del proyecto.
