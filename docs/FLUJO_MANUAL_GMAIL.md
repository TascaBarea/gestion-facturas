# Flujo manual de gmail.py

**Decisión:** 05/05/2026 — `gmail.py` se ejecuta a mano desde el PC con Claude Code. **No hay cron.**

> Nota histórica: hasta esta fecha, el VPS tenía solo un header huérfano `# Gmail facturas - viernes 03:00` en el crontab que nunca se llegó a activar. Era una intención registrada que se confundió en sesiones posteriores con un cron real. La realidad es que `gmail.py` siempre se ha lanzado a mano.

---

## Por qué manual y no automático

El flujo de `gmail.py` requiere **validación humana caso por caso**:
- Detección de filas zombi (TOTAL vacío) que indican un extractor faltante.
- Casos `REVISAR` (proveedor sin alta en MAESTRO).
- `[DRIVE FALLO]`, `[OCR FALLO]`, `Extractor no encontrado`.
- Formatos PDF que cambian entre facturas del mismo proveedor.

Un cron silencioso acumula problemas días/semanas sin que nadie los vea. Caso documentado: la factura JALEO 27/04/2026 se quedó zombi 7 días hasta que se procesó manualmente el 04/05 y se notó al revisar el log.

Otros crons (`script_barea.py` para ventas los lunes, backups diarios) **siguen automáticos** porque su flujo es mecánico y sin peculiaridades.

---

## Comando único

```bash
cd c:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas
PYTHONPATH=. python gmail/gmail.py --produccion
```

`PYTHONPATH=.` es necesario porque `gmail/gmail.py` importa `nucleo.*` y `core.*` y Python no encuentra esos paquetes sin él. Sin `PYTHONPATH=.` falla con `ModuleNotFoundError: No module named 'nucleo'` (regla en `lessons.md`).

Alternativa con `tee` para guardar log local además del log interno de gmail.py:
```bash
PYTHONPATH=. python gmail/gmail.py --produccion 2>&1 | tee outputs/logs_gmail/$(date +%Y-%m-%d)_manual.log
```

---

## Cuándo lanzar

Criterio del usuario, pero como referencia:

- **Mínimo recomendado**: 1-2 veces por semana para no acumular emails sin procesar.
- **Antes de fin de mes**: imprescindible para el cierre Kinema (modelo 303, IVA).
- **Tras sesión de extractor nuevo**: siempre conviene una pasada para procesar facturas pendientes que ya tienen extractor.

---

## Pre-checks antes de ejecutar

1. **Excels NO abiertos** en Excel/LibreOffice — buscar lock files `~$*.xlsx` en:
   - `G:\Mi unidad\Barea - Datos Compartidos\Compras\Año en curso\`
   - `C:\Users\jaime\Dropbox\File inviati\TASCA BAREA S.L.L\CONTABILIDAD\FACTURAS 2026\FACTURAS RECIBIDAS\<TRIMESTRE>\`
   - **`outputs/` del propio repo** (gmail.py escribe ahí también; un lock zombi tras crash de Excel bloquea la ejecución con `ARCHIVO BLOQUEADO`).
2. **Drive Desktop activo** — icono visible en la bandeja del sistema (Windows). Sin él, los Excels en `G:\` no se sincronizan a la nube.
3. **Cobertura/internet estable** — el OAuth Drive y la API Gmail necesitan conexión. Cobertura inestable rompió el flujo OAuth el 04/05 mañana.
4. **Token válido** — si fue regenerado hace mucho, comprobar `python -c "import json; print(json.load(open('gmail/token.json'))['expiry'])"`. Si caducó, ver "Renovar token" abajo.

---

## Cómo leer el log

Cada ejecución genera `outputs/logs_gmail/YYYY-MM-DD.log`. Buscar (en orden de gravedad):

| Patrón | Significado | Acción |
|---|---|---|
| `[DRIVE FALLO]` | API Drive falló (típicamente 403) | Renovar token con scope drive (ver abajo) |
| `[OCR FALLO]` | OCR no extrajo texto | Verificar PDF original; ¿escaneado de mala calidad? |
| `Extractor no encontrado: X.py` | Proveedor en MAESTRO con `ARCHIVO_EXTRACTOR=X.py` que no existe | Crear el extractor en `Parseo/extractores/X.py` |
| `REVISAR` | Email sin proveedor identificado | Alta MAESTRO + extractor o asignar manualmente |
| `ALERTA ROJA` | Total faltante o discrepancia detectada | Investigar PDF + extractor |

Tras procesar, **verificar Excels canónicos**:
- `G:\...\PAGOS_Gmail_2T26.xlsx` — fila por factura, FORMA_PAGO + ESTADO_PAGO.
- `G:\...\Facturas 2T26 Provisional.xlsx` — fuente que Kinema lee.
- `Dropbox\...\Facturas 2T26 Provisional.xlsx` — copia de seguridad off-Drive.

Filas zombi (TOTAL vacío) = extractor del proveedor a revisar/crear.

---

## Renovar token (si caduca)

```bash
cd c:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas
cp gmail/token.json gmail/token.json.bak.$(date +%Y%m%d)
rm gmail/token.json
python gmail/renovar_token_business.py
# autorizar en navegador con cuenta tascabarea@gmail.com
# aceptar 4 scopes: gmail.readonly, gmail.modify, business.manage, drive
```

Verificar:
```bash
python -c "import json; t = json.load(open('gmail/token.json')); print('scopes:', t.get('scopes')); print('len:', len(t.get('scopes')))"
# esperado: 4 scopes incluyendo drive
```

Deploy al VPS si se quisiera ejecutar ahí (no es el flujo actual):
```bash
scp gmail/token.json root@194.34.232.6:/opt/gestion-facturas/gmail/token.json
```

---

## Reactivar el cron en el futuro (si se quisiera)

```bash
ssh root@194.34.232.6
crontab -e
# añadir línea, por ejemplo:
#   0 3 * * 5  cd /opt/gestion-facturas && /usr/bin/python3 gmail/gmail.py --produccion >> /var/log/gmail_cron.log 2>&1
# guardar
crontab -l   # verificar
```

Antes de reactivar, considerar:
- ¿Sigue siendo válida la razón de "validación humana caso por caso"? Si sí → no reactivar.
- Si se reactiva, plantar también una alerta automática (email/Slack) cuando aparezca `[DRIVE FALLO]`, `Extractor no encontrado` o `ALERTA ROJA` en el log para no perder el feedback humano.

Backup del crontab anterior a esta decisión: `/opt/gestion-facturas/backups/crontab_pre_20260505.txt` en VPS.
