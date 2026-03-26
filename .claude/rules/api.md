---
description: Reglas de seguridad y desarrollo para la API FastAPI
globs: api/**
---

- NUNCA editar `api/.env` sin permiso explícito (contiene API_KEY)
- Seguridad implementada (no eliminar):
  - Path traversal: `os.path.basename()` + `os.path.realpath()` containment check
  - CORS: lista explícita en `.env` CORS_ORIGINS, fallback localhost:8501
  - Uploads: max 10MB, extensiones .n43/.xlsx/.xls, validación magic bytes
- RBAC 2 niveles:
  - `require_api_key()` → admin + readonly (GET endpoints)
  - `require_admin_key()` → solo admin (POST/PUT, scripts, uploads, MAESTRO writes)
  - `DEV_MODE=true` → bypass auth (solo desarrollo local)
- Runner: 1 job concurrente (threading lock), timeout 600s, historial max 50
- Maestro writes: siempre `verificar_no_abierto()` + `backup_maestro()` antes de guardar
- FORMA_PAGO válidas: TF, TJ, RC, EF, vacío
- Tests: ejecutar `pytest tests/unit/test_api_security.py` tras cambios de seguridad
- Arranque: `barea_api.bat` watchdog auto-restart, registrado en Task Scheduler
- Doc completa: ver `docs/api.md`
