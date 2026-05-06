---
name: cierre
description: "Skill para cerrar sesiones de trabajo de forma estandarizada en el proyecto gestion-facturas. Activa esta skill cuando el usuario diga: cierre sesión, /cierre, cierra esto, vamos a cerrar la sesión, cierre Bloque X, cierra y haz push, cierre completo, cerrar y sincronizar, etc. Acepta argumento opcional con título descriptivo del bloque cerrado (ej: /cierre Bloque B). Si no se proporciona título, lo infiere del contexto reciente. Ejecuta el flujo completo en orden estricto: inventario de cambios, bump SPEC si procede, sincronizar tabla CLAUDE.md, cerrar tasks/todo.md, añadir lecciones a tasks/lessons.md, generar reporte en outputs/cierre_*.md, commit, push, sync VPS, verificar CI. Confirma con el usuario SOLO antes de git push origin y antes de ssh VPS — el resto es automático. Esta skill es el complemento operacional al doc maestro docs/SPEC_GESTION_FACTURAS_v4.md y a la skill gestion-facturas (que aporta contexto de diseño)."
---

# Skill `/cierre` — cierre de sesión estandarizado

Automatiza el flujo de cierre que se ha repetido en cada sesión productiva del proyecto. Garantiza que cada cierre actualice el SPEC, la tabla de versiones de CLAUDE.md, los archivos de `tasks/`, genere reporte en `outputs/`, haga commit + push y sincronice al VPS — en ese orden, sin saltarse pasos ni ejecutar nada externo sin confirmación.

## Cuándo dispararse

Frases típicas: "cierra esta sesión", "cierre sesión", "/cierre", "cierre Bloque X", "vamos a cerrar y hacer push", "cierra y sube", "cierre completo", "cerrar y sincronizar".

Argumento opcional — título descriptivo:
- Con título: `/cierre Bloque B + filtrado no-factura` → usa ese texto como base para el nombre del reporte y el mensaje del commit.
- Sin título: inferir del contexto reciente (último commit, contenido modificado, conversación).

## Flujo (orden estricto, no saltarse pasos)

### 1. Inventario de cambios

```bash
git status --short
git log --oneline -5
git diff --stat HEAD~1
```

Identifica:
- Qué archivos cambiaron desde el último commit no-cierre.
- Qué área se tocó (gmail/ventas/cuadre/parseo/docs/skills/tests).
- Si hay commits sin push, archivos sin stage, working tree sucio.

Si no hay cambios significativos: AVISA al usuario y pregunta si realmente quiere cerrar una sesión vacía.

### 2. Decidir bump del SPEC

Lee `docs/SPEC_GESTION_FACTURAS_v4.md` (cabecera + última entrada del CHANGELOG).

| Tipo de cambio | Bump |
|---|---|
| Cambio arquitectónico, decisión canónica, refactor de carpetas/flujo, deprecación de algo público | mayor (+0.1) |
| Feature nueva, bugfix que altera comportamiento observable, bump de versión de un módulo | minor (+0.01) |
| Solo docs, tests, typos, comentarios | no bump |

Si dudas: minor.

Edita el SPEC:
- Bump de la versión en la cabecera y en la línea "Versión: vX.Y" si existe.
- Nueva entrada al inicio del CHANGELOG (no al final): fecha + resumen + hashes de los commits relevantes.

Para bump mayor, pide confirmación explícita al usuario antes de aplicar.

### 3. Sincronizar tabla de versiones de CLAUDE.md

Localiza en `CLAUDE.md` la tabla con versiones de Gmail / Ventas / Cuadre / Parseo / SPEC. Si alguna cambió en esta sesión, actualizar la línea correspondiente.

### 4. Cerrar `tasks/todo.md`

- Marca como hechos los items completados en la sesión.
- Mueve a sección "Histórico" o "Cerrado" según convención del archivo.
- Añade items nuevos a la sección "Vivo" si surgieron durante la sesión.

### 5. Añadir lecciones a `tasks/lessons.md` (si hay)

Si la sesión generó reglas, patrones, anti-patterns o gotchas reutilizables: añadirlos siguiendo el formato existente. Si no hay lecciones nuevas, saltar este paso.

### 6. Generar reporte de cierre

Crear `outputs/cierre_<descripción-snake-case>_<YYYYMMDD>.md` con estructura:

````
# <Título del cierre>
**Sesión:** <fecha>
**Modo:** <auto-accept / interactivo>

## Resumen ejecutivo
<3-5 líneas>

## Cambios
<tabla de archivos modificados con descripción breve>

## Tests
<antes / después / CI run id si aplica>

## Commits
<hash + asunto>

## Sync VPS
<HEAD VPS = HEAD origin>

## Backlog actualizado
- Cerrado en esta sesión: <items>
- Vivo: <items>
- Nuevo descubierto: <items>

## Validación pendiente
<si hay algo a validar en producción la próxima ejecución>
````

### 7. Stage + commit (auto)

```bash
git add <archivos modificados, selectivamente — NUNCA git add .>
git diff --cached --stat
```

Mensaje del commit: leer los últimos 5 commits con `git log --oneline -5` para inferir el patrón actual del repo y respetarlo. Estructura típica observada:

````
<tipo>: <descripción breve>

<cuerpo: qué cambió, por qué, referencias>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
````

### 8. CONFIRMAR antes de push (PARADA OBLIGATORIA)

Detener ejecución. Mostrar al usuario:

````
Commit creado: <hash> — <asunto>

A continuación voy a:
  1. git push origin main
  2. ssh root@194.34.232.6 'cd /opt/gestion-facturas && git pull --ff-only'

¿Procedo?
````

NO continuar sin "sí" / "ok" / "procede" / equivalente explícito del usuario.

### 9. Push + sync VPS

```bash
git push origin main
ssh root@194.34.232.6 'cd /opt/gestion-facturas && git pull --ff-only && git rev-parse --short HEAD'
```

Verificar que VPS HEAD coincide con origin HEAD.

### 10. Verificar CI

```bash
gh run list --limit 1 --workflow=tests.yml
```

- `in_progress`: esperar 60-90s y reintentar (máx. 3 reintentos).
- `failure`: la sesión NO se considera cerrada. Investigar y arreglar antes de continuar.
- `success`: pasar al resumen final.

### 11. Resumen final al usuario

Mostrar tabla recap:
- Commits hechos (hash + asunto).
- Tests locales (passed/failed) y CI (run id + status).
- VPS HEAD == origin HEAD ✓.
- Backlog: cerrado vs vivo vs nuevo descubierto.
- Validación pendiente para próxima ejecución (si la hay).

## Reglas duras

- NUNCA auto-aprobar `git push` o `ssh VPS`. Siempre confirmación explícita en paso 8.
- NUNCA usar `git add .` — siempre paths selectivos.
- NUNCA usar `git push --force` ni `--force-with-lease`.
- NUNCA bumpear SPEC mayor sin confirmación explícita.
- NUNCA modificar `MEMORY.md` desde esta skill.
- Si la suite local de tests falla: PARAR. No cerrar la sesión. Avisar al usuario.
- Si CI falla tras push: la sesión NO está cerrada. Hay que arreglar antes.
- Si la rama actual no es `main`: PARAR y avisar al usuario.
- Si el working tree tiene archivos irrelevantes sin stage (settings, locks, generados): listarlos y pedir al usuario que decida.

## Convenciones de nombrado

- Reporte: `outputs/cierre_<descripción-snake>_<YYYYMMDD>.md`.
- Carpeta de outputs: solo crear si no existe.
- Mensaje commit cierre: ajustar a la convención que se observe en `git log --oneline -5`. Patrón típico actual: `docs: cierre <descripción> — <punto principal>`.
- Co-author footer obligatorio: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.

## Skills relacionadas

- `gestion-facturas` (skill maestra): consultar antes de tomar decisiones de bump SPEC mayor o de mover items entre "vivo" y "cerrado".
- `esquema`: documenta organización histórica del proyecto. Coexiste con `/cierre` sin solaparse.
- `plan`, `revisar`, `lecciones`: pendientes de evaluación de consolidación futura.

## Cuándo NO usar `/cierre`

- Sesión exploratoria sin commits (solo lectura, debugging sin escritura).
- Tests locales rojos.
- Merge conflict pendiente.
- Rama distinta a `main`.
- Working tree con cambios irrelevantes que no deben subirse y no se han limpiado.
- Sesión que dejó algo a medias y todavía no está listo para cerrar.
