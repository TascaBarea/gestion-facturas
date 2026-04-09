# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Próxima sesión
**Objetivo:** CUADRE + pendientes menores

### Pendientes seguridad
- [ ] Cambiar contraseñas Streamlit (las 4 son "2017") → decisión del usuario

### Pendientes Dia Tickets
- [ ] Integración Drive para subir tickets
- [ ] Login automático (JWT ~30 min, Playwright bloqueado por anti-bot)

### Pendiente Streamlit Cloud
- [ ] Verificar que el usuario cambió NETLIFY_DATA_URL a GitHub Pages en secrets

### Mejoras técnicas
- [ ] CUADRE: conectar con COMPRAS para ESTADO_PAGO automático
- [ ] CUADRE bugs: VINOS DE ARGANZA, SPOTIFY, Comunidad vecinos
- [ ] Documentar instalación OCR

### Alta evento — posibles mejoras futuras
- [ ] Calendario HTML visual (fechas coloreadas) — descartado por ahora, riesgo alto
- [ ] Cruce WC ↔ Loyverse para plazas pagadas online vs tienda (fuzzy matching)
- [ ] Email automático al organizador con enlace privado (requiere Gmail API)

---

## Sesión anterior (28-31/03/2026)
**Objetivo:** Drive + seguridad + alta evento completa + mov_banco

### Completado (28/03)
- [x] Verificar Google Drive sync + página "Documentos" en Streamlit
- [x] Seguridad: sanitizar importlib en gmail.py (path traversal)
- [x] Auth OAuth2 centralizado: gmail/auth_manager.py (5 scripts actualizados)
- [x] WooCommerce retry con backoff exponencial (3 intentos, 2/4/8s)
- [x] ESQUEMA actualizado a v5.4

### Completado (30/03)
- [x] mov_banco.py: fix encoding UTF-8, ejecutado con archivos Sabadell reales
- [x] Fix barea_auto.bat: PYTHONPATH + _to_float import + alerta_fallo scope
- [x] Ejecución manual ventas semanales (03:00 falló por PYTHONPATH)

### Completado (31/03)
- [x] Alta evento: selector cascada tipo→subtipo + detección conflictos fecha
- [x] Alta evento: soporte CERRADO (plazas pagadas/pendientes + enlace WhatsApp)
- [x] Alta evento: modo test ([TEST] privado + limpieza desde Streamlit)
- [x] Alta evento: lista fechas ocupadas antes del calendario
- [x] Alta evento: fix tipo ticket-event + categorías + tag Producto_destacado
- [x] Alta evento: fix meta_data _start_date_picker/_end_date_picker (calendario web)
- [x] Calendario Streamlit: columna Tipo (CERRADO/Abierto) + enlace privado
- [x] historico_eventos.py: Excel con 39 eventos desde WC (11 columnas)
- [x] Fix producto 3350 (CATA ESPECIAL 14/05/26): tipo + categorías + meta_data

---

## Sesión 27/03/2026
**Objetivo:** Contraseñas Streamlit + config Claude + Dia tickets + migración Netlify + auditoría

### Completado
- [x] Streamlit Cloud: contraseñas configuradas (plaintext, "2017")
- [x] `.claude/rules/` (api, extractores, excel) + `docs/api.md`
- [x] CLAUDE.md v4.2 (eliminar duplicados, punteros a rules/ y docs/)
- [x] Dia Tickets: script funcional, 200 tickets descargados con líneas productos
- [x] Dia Tickets: anti-duplicación (registro JSON + doble check)
- [x] Dia Tickets: registrado en runner API (dia_tickets, dia_tickets_stats)
- [x] Fix gmail_auto.bat: añadir PYTHONPATH para resolver nucleo/
- [x] Gmail ejecutado manualmente (11 procesados, 7 exitosos)
- [x] Migración Netlify → GitHub Pages completada y verificada
- [x] Fix .gitignore (cubrir datos/backups/, dia_tickets/, dia_session.json)
- [x] Fix SSL en data_client.py (verificación habilitada por defecto)
- [x] Backup cifrado: scripts/backup_cifrado.py (AES-256, 14 archivos, 162 KB)
- [x] Primer backup creado con contraseña Cascorro&Abades
- [x] Auditoría seguridad completa (1 crítico, 1 alto corregido, 10 medio, 4 bajo)
- [x] Plan migración archivos a Google Drive (Estrategia B aprobada)

### Notas
- El JWT de Dia.es expira en ~30 min, Playwright bloqueado por anti-bot → login manual necesario
- Contraseña backup cifrado: Cascorro&Abades (misma que Dia — usuario la eligió pese a recomendación)
- GitHub Pages URL: https://tascabarea.github.io/gestion-facturas
- El usuario debe cambiar NETLIFY_DATA_URL en Streamlit Cloud secrets

---

## Historial

| Fecha | Objetivo | Estado | Notas |
|-------|----------|--------|-------|
| 2026-03-12 | Auditoría Parseo v5.18 + limpieza | ✅ | 70 _convertir_europeo consolidados, dead code, VERSION unificada |
| 2026-03-13 | Análisis Gmail + docs + extractores | ✅ | CLAUDE.md v3.0, tasks/ creados, 2 skills |
| 2026-03-27 | Config + Dia + Netlify→GH Pages + seguridad | ✅ | Ver detalle arriba |
