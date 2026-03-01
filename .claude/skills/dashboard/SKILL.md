---
name: dashboard
description: Genera dashboards de ventas (Comestibles + Tasca). Usar /dashboard para generar y abrir, /dashboard email para enviar por email, /dashboard cerrados para solo meses cerrados.
disable-model-invocation: true
argument-hint: "[email] [cerrados] [no-open]"
allowed-tools: Bash, Read
---

# Generar Dashboards

Ejecuta el generador de dashboards de ventas Barea.

## Interpretar argumentos

Los argumentos de $ARGUMENTS se combinan libremente:
- Sin argumentos: genera ambos dashboards y los abre en el navegador
- `email`: genera dashboards + PDF + envia email a socios (implica `--solo-cerrados`)
- `cerrados`: excluye el mes en curso (solo meses completamente cerrados)
- `no-open`: no abrir en navegador tras generar
- `test`: envia email solo a jaimefermo@gmail.com (override destinatarios)

## Construir el comando

Script: `python ventas_semana/generar_dashboard.py`

Flags disponibles:
- `--no-open` - no abrir navegador
- `--solo-cerrados` - excluir mes en curso
- `--email` - generar PDF y enviar email (siempre con `--no-open`)

Combinaciones tipicas:
- Solo generar: `python ventas_semana/generar_dashboard.py`
- Generar sin abrir: `python ventas_semana/generar_dashboard.py --no-open`
- Solo cerrados: `python ventas_semana/generar_dashboard.py --solo-cerrados`
- Email completo: `python ventas_semana/generar_dashboard.py --email --solo-cerrados --no-open`

Si el usuario pide `test`, hay que ejecutar via Python para override de destinatarios:
```python
import ventas_semana.generar_dashboard as gd
gd.EMAILS_FULL = ["jaimefermo@gmail.com"]
gd.EMAILS_COMES_ONLY = ["jaimefermo@gmail.com"]
gd.main(abrir_navegador=False, solo_meses_cerrados=True, enviar_email=True)
```

## Ejecutar

Ejecutar desde `C:/_ARCHIVOS/TRABAJO/Facturas/gestion-facturas/`.

## Interpretar resultado

Tras ejecutar, resumir:
- Items cargados por anio (Comestibles y Tasca)
- Dashboards generados (rutas)
- PDF generado (ruta, si aplica)
- Email enviado (destinatarios, si aplica)
- GitHub Pages publicado (si aplica)
- Cualquier error

Errores comunes:
- Excel abierto en otro programa: cerrar y reintentar
- Fallo de red: verificar conexion para GitHub Pages
- Fallo de email: verificar token OAuth en gmail/token.json
