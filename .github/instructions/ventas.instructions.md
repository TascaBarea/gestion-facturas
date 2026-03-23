---
applyTo: ventas_semana/**
---

# Módulo Ventas — Conocimiento del dominio
<!-- script_barea.py v4.7 — Actualizado 24/03/2026 -->

## Qué hace este módulo
Descarga ventas semanales de Loyverse (Tasca + Comestibles) y WooCommerce, actualiza el Excel maestro y genera dashboards HTML + PDF que se envían por email el lunes a las 03:00.

## Archivos clave
| Archivo | Rol |
|---|---|
| `script_barea.py` | Script principal — descarga, procesa, actualiza Excel, genera dashboards, envía email |
| `generar_dashboard.py` | Genera HTML de dashboards independientemente |
| `talleres_programados.json` | Inventario de eventos futuros (actualizado cada lunes automáticamente) |
| `.env` | API keys — **NUNCA tocar, NUNCA al repositorio** |
| `alta_evento.py` | Alta interactiva de eventos en WooCommerce (uso manual) |

## Flujo del email semanal (lunes 03:00)
```
main()
  → descargar Loyverse (Tasca + Comestibles)
  → descargar WooCommerce (pedidos)
  → generar_inventario_talleres()  ← actualiza talleres_programados.json
  → actualizar Excel maestro (Ventas Barea 2026.xlsx)
  → _generar_html_email()
      → sección ventas Tasca
      → sección ventas Comestibles + WooCommerce
      → _seccion_talleres()  ← bloque "Próximos eventos" desde talleres_programados.json
  → enviar email via Gmail API
```

## Estructura talleres_programados.json
```json
{
  "talleres": [
    {
      "id": 12345,
      "nombre": "Cata de vinos naturales",
      "fecha": "28/03/26",
      "hora_inicio": "18:30",
      "hora_fin": "20:00",
      "stock_quantity": 15,
      "stock_status": "instock",
      "precio": 35.0
    }
  ]
}
```
- `fecha`: siempre formato `DD/MM/YY`
- `stock_quantity`: null si WooCommerce no gestiona stock
- `stock_status`: `"instock"` | `"outofstock"`

## Fuentes de datos — fiabilidad
| Fuente | Fiabilidad |
|---|---|
| Loyverse ventas | ✅ Alta — datos de TPV reales |
| WooCommerce pedidos | ✅ Alta — pedidos online reales |
| WooCommerce stock | ❌ NO fiable — no usar para decisiones de inventario |
| Loyverse stock | ❌ NO fiable — no sincronizado |

## Convención de nombres de eventos en WooCommerce
- Formato: `"{nombre base} DD/MM/YY"` — la fecha siempre al final
- Descripción: `"HORARIO: de HH:MM a HH:MM"` en la primera línea
- `generar_inventario_talleres()` extrae estos campos automáticamente

## Reglas críticas
- `.env` — nunca modificar, nunca incluir en commits
- Excel maestro (`Ventas Barea 2026.xlsx`) — avisar antes de escribir, puede estar abierto
- El flag `--dashboard-mensual` genera PDF con solo meses cerrados y envía email a socios
- `cargar_historico_wc.py` — script separado para carga histórica de pedidos WC, no forma parte del flujo automático

## Parámetros del script
```bash
python ventas_semana/script_barea.py                    # modo semanal normal
python ventas_semana/script_barea.py --dashboard-mensual  # cierre mensual + email socios
```
