---
applyTo: "**"
---

# Skill: Cierre de sesión

Cuando el usuario diga "cerramos sesión", "lo dejamos", "fin de sesión", "cerramos", "hasta aquí" o expresiones similares de finalización, ejecutar este workflow **en orden**:

## 1. Resumen de lo hecho

Listar brevemente los cambios realizados en la sesión:
- Archivos creados o eliminados
- Cambios en módulos (con versión anterior → nueva si aplica)
- Decisiones de diseño tomadas

## 2. Actualizar `tasks/todo.md`

- Marcar como completadas las tareas que se hayan cerrado
- Añadir nuevas tareas pendientes que hayan surgido
- Si el archivo no existe, crearlo con las pendientes conocidas

## 3. Actualizar `tasks/lessons.md`

**Solo si** ocurrió alguno de estos durante la sesión:
- Un error no obvio o un comportamiento inesperado
- Una regla que no estaba documentada y que vale la pena recordar
- Una decisión que probablemente habrá que tomar de nuevo

No añadir lecciones triviales ni repetir lo que ya está documentado.

## 4. Actualizar `docs/SPEC_GESTION_FACTURAS_v4.md`

**Solo si** hubo cambios arquitectónicos reales:
- Módulo nuevo o eliminado
- Flujo de datos cambiado
- Decisión de diseño con impacto duradero (estructura de carpetas, formato de archivos, protocolo de un módulo)

**No tocar la SPEC por**:
- Bugfixes o mejoras menores dentro de un módulo
- Cambios de configuración o constantes
- Tareas de limpieza sin impacto en arquitectura

Cuando sí se actualice: subir la versión menor (v4.1 → v4.2) y añadir entrada en el CHANGELOG al final del archivo.

## 5. Mostrar resumen antes de cerrar

Presentar al usuario un bloque conciso con:
```
## Resumen de sesión — DD/MM/YYYY

### Cambios
- ...

### Pendiente
- ...

### Documentación actualizada
- tasks/todo.md ✓ / tasks/lessons.md ✓ (si aplica) / SPEC v4.x ✓ (si aplica)
```

---

## Nota sobre documentación

**`docs/SPEC_GESTION_FACTURAS_v4.md` es el documento maestro único del proyecto.**
No existe ningún otro documento de arquitectura (el anterior ESQUEMA_PROYECTO_DEFINITIVO fue eliminado el 01/04/2026).
Toda referencia a arquitectura, módulos o flujos debe apuntar exclusivamente a la SPEC.
