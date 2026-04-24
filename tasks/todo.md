# todo.md — Plan de sesión activa
<!-- Reemplazar sección "Sesión actual" al iniciar cada sesión nueva -->
<!-- Estados: [ ] pendiente | [x] completado | [~] en progreso | [!] bloqueado -->

---

## Próxima sesión
**Objetivo:** resolver listado Drive en `/documentos` Cloud + favicon Comestibles + deuda requirements.

### Pendientes priorizados

- [ ] **ALTO — `/documentos` en Cloud no lista archivos reales** (porque `gmail/token.json` está `.gitignored`). Decidir entre:
  - **Opción A (recomendada)**: botones "Abrir en Drive" por sección con URL directo a la carpeta correspondiente. Cero credenciales en Cloud. `/documentos` queda como vista de estructura + navegación rápida. Implementación: refactor `streamlit_app/pages/documentos.py` para mostrar botones en lugar de listados, usando URLs de Drive (añadir mapping folder_id → URL).
  - **Opción B**: pegar `token.json` como secret en Streamlit Cloud dashboard. Más complejo (token OAuth expira, requiere rotación manual, mayor superficie de seguridad).

- [ ] **MEDIO — favicon Comestibles Barea en Streamlit**.
  - Asset: `Logo_BAREA_COMESTIBLES_RESOLUCION_WEB.png` (óvalo La Rumán, ~1507×1980) en `G:\Mi unidad\Barea - Datos Compartidos\Articulos\`.
  - La imagen tal cual NO funciona como favicon 16×16 (queda borrón amarillo). Necesita versión recortada ~512×512 priorizando cara.
  - Configurar en `st.set_page_config(page_icon=...)` en `streamlit_app/app.py`.

- [ ] **BAJO — deuda técnica `requirements.txt` duplicados**. Documentado en `tasks/nota_requirements.md` y SPEC §13.10. Evaluar:
  - Opción A: consolidar en `requirements.txt` raíz único, configurar Streamlit Cloud para leerlo.
  - Opción B: `streamlit_app/requirements.txt` contiene solo `-r ../requirements.txt`.
  - Opción C: mantener duplicación + test CI que detecte divergencia.

### Activación cron viernes 03:00 en VPS (decisión operativa)
- [ ] Si 2-3 ejecuciones gmail.py consecutivas OK en VPS → activar cron.

### Otros pendientes arrastrados
- [ ] Añadir sync Drive también a `scripts/mov_banco.py` (paralelo a `actualizar_movimientos.py`) — omitido por scope.
- [ ] Borrar `generar_refresh_token_dropbox.py` (gitignored, ya cumplió su función Fase X.2).
- [ ] Revisar REVISAR reales del run 24/04: La Mar de Tazones, Solicitud factura imagen.

---

## Sesión 24/04/2026
**Objetivo:** Bloque E (gmail VPS) + verificación DIA/ECOMS + `/documentos` v2 en Streamlit.

### Completado
- [x] Bloque E: primer disparo real `gmail.py --produccion` en VPS. 12 emails, 6 exitosos, 4 REVISAR, 0 errores. `[DROPBOX OK]` + `[DRIVE OK]` verificados.
- [x] Verificación DIA/ECOMS end-to-end. Formato 3 (factura canje) OK: fecha 20/04, ref FF202600000014, total 4,68 €, 3 líneas cuadre OK.
- [x] SPEC v4.5 → v4.6 (Bloque E + verificación DIA, commit `bc970a7`).
- [x] `/documentos` v2 en Streamlit Cloud: 6 secciones declarativas (Ventas, Compras, Movimientos Banco, Artículos, Maestro, Cuadres), pestañas Año en curso/Histórico donde aplica. Commit `572f155`.
- [x] Fix cadena de 4 bugs post-deploy `/documentos`:
  - `d803bf0` — Google API libs en `streamlit_app/requirements.txt`.
  - `c820b65` — deps transitivas (`pdfplumber`, `rapidfuzz`), `sys.path` defensivo en `app.py`, logging visible con `traceback.format_exc()`.
  - `410858f` — `config/loader.py` con cascada `secrets → env → legacy → default`; `config/settings.py` migrado.
  - `5530c10` — loader captura `ImportError`, no solo `ModuleNotFoundError`.
- [x] Tests nuevos: `test_config_loader.py` (6 casos, simulación Cloud con `monkeypatch(__import__)`), `test_documentos_config.py` (6 casos AST-based). Suite: 158 passed.
- [x] SPEC v4.6 → v4.7 con `/documentos` v2 + `config/loader` + §13.9 + §13.10 deuda requirements.
- [x] Autopsia: `tasks/cierre_sesion_24abr_documentos.md`.

### Reforma destinos cloud — estado final
- [x] R.1 gmail v1.21 — MAESTRO solo-lectura (`ec83c8f`).
- [x] R.2 gmail v1.22 — destinos cloud definitivos (`f72daf9`).
- [x] R.3 cuadre.py sync Drive (`20105ac`).
- [x] R.4 rutas PC → G:\ (`73d6d8e`).
- [x] R.5 migración física Drive.
- [x] R.6 push + pull VPS + smoke tests.
- [x] Fix token VPS (scope `drive`).
- [x] Bloque E ejecutado 24/04.

### Backlog 20/04/2026 (SPEC v4.5 §14)
- [x] 20A — Google Drive sync scope `drive` (cerrado 21/04).
- [ ] 20B — Ruta Windows hardcoded `C:\...\datos\Articulos 26.xlsx` (ahora `Articulos_2026.xlsx` en PC tras C2). Migrar VPS `.env` a `pathlib.Path` con `GESTION_FACTURAS_DIR`.
- [ ] 20C — `datos/Ventas Barea Historico.xlsx` ausente en VPS. Ahora está en Drive (`Ventas/Histórico/`, id `1JbaTVqa_Ojl87wALmLjTzdZtoY1FzDZ_`) — evaluar lectura desde Drive en VPS vs copia scp.
- [ ] 20D — Deploy key VPS sin write access en GitHub → regenerar o condicionar push a PC.
- [ ] v4.6 refactor — `ventas_semana/cargar_historico_wc.py:89` escribe total como string `"60,00 €"`. Pasar a floats nativos manteniendo lectura compatible.

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
| 2026-04-23 | Reforma destinos cloud R.1-R.6 + fix token VPS | ✅ | SPEC v4.6 |
| 2026-04-24 | Bloque E + DIA/ECOMS + `/documentos` v2 + config/loader | ✅ | SPEC v4.7, 5 commits, autopsia en tasks/cierre_sesion_24abr_documentos.md |
