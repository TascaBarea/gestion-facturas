# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Próxima sesión
**Objetivo:** CUADRE + mejoras pendientes

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

### Ya no pendientes (resueltos)
- ~~WooCommerce 69→10 columnas~~ → ya eran 7 en `_normalizar_pedidos_wc()`
- ~~YEAR_LIST dinámico~~ → pestañas se descubren por prefijo (ya dinámico)

---

## Sesión anterior (28/03/2026)
**Objetivo:** Google Drive + Documentos + seguridad + auth centralizado + WC retry

### Completado
- [x] Verificar Google Drive sync (nucleo/sync_drive.py ya implementado)
- [x] Página "Documentos" en Streamlit (streamlit_app/pages/documentos.py)
- [x] Seguridad: sanitizar importlib en gmail.py (path traversal)
- [x] Auth OAuth2 centralizado: gmail/auth_manager.py (5 scripts actualizados)
- [x] WooCommerce retry con backoff exponencial (3 intentos, 2/4/8s)
- [x] requirements.txt verificado (ya existía)
- [x] ESQUEMA actualizado a v5.4 (v5.3 + v5.4 añadidos)
- [x] Pendientes.md actualizado (varios items ya estaban resueltos)

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
