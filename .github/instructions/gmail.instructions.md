---
applyTo: gmail/**
---

# Módulo Gmail — Conocimiento del dominio
<!-- gmail.py v1.14 — Actualizado 24/03/2026 -->

## Qué hace este módulo
Procesa emails de proveedores recibidos en la cuenta de empresa, extrae facturas adjuntas (PDF) e identifica pagos realizados. Se ejecuta automáticamente los viernes a las 03:00.

## Archivos intocables — NUNCA modificar
| Archivo | Por qué |
|---|---|
| `token.json` | Token OAuth2 activo — si se modifica, rompe la autenticación |
| `credentials.json` | Credenciales de la app Google — secreto de cliente |
| `token.json.backup` | Backup del token — no commitear, ya está en .gitignore |

## Token caducado
Si el script falla con error de autenticación o token expirado:
```bash
python gmail/renovar_token_business.py
```
Esto abre el navegador para re-autenticar. Solo necesario ocasionalmente.

## Reglas técnicas críticas
- **MIME type**: usar siempre `text/html` con barra **normal** (`/`), nunca invertida (`\`)
- **Scopes Gmail**: definidos en `gmail/auth.py` — no ampliar sin necesidad
- El módulo usa la cuenta de empresa (`business`), no la personal

## Flujo principal (gmail.py)
```
main()
  → autenticar (token.json + credentials.json)
  → buscar emails de proveedores no procesados
  → para cada email:
      → identificar proveedor (identificar.py)
      → descargar adjuntos PDF (descargar.py)
      → guardar en carpeta del proveedor (guardar.py)
      → renombrar según convención (renombrar.py)
      → marcar email como procesado
  → guardar estado en datos/emails_procesados.json
```

## Archivos de apoyo
| Archivo | Rol |
|---|---|
| `auth.py` | Gestión OAuth2 |
| `identificar.py` | Identifica el proveedor del email |
| `descargar.py` | Descarga adjuntos PDF |
| `guardar.py` | Guarda en carpeta correcta |
| `renombrar.py` | Renombra según convención |
| `buscar_emails_proveedores.py` | Búsqueda de emails por proveedor |
| `generar_sepa.py` | Genera remesas SEPA XML para pagos |
| `limpiar_emails_viejos.py` | Limpieza de emails ya procesados |

## Convención de renombrado de facturas
El módulo renombra los PDFs descargados según una convención estándar que facilita su identificación posterior en el proceso de cuadre.
