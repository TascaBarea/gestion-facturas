---
name: plan
description: Crea o actualiza el plan de sesion en tasks/todo.md. Usar al inicio de una sesion para establecer objetivos, o durante la sesion para actualizar progreso.
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# Plan de Sesion

Gestiona el archivo `tasks/todo.md` del proyecto. Sigue estos pasos:

## 1. Leer todo.md actual

Lee `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\tasks\todo.md`.

## 2. Evaluar estado

- Si hay una sesion activa con items pendientes: mostrar al usuario que hay trabajo en curso y preguntar si continuar o iniciar sesion nueva
- Si no hay sesion activa o todos los items estan completados: preparar nueva sesion

## 3. Nueva sesion (si procede)

- Mover la sesion anterior a la tabla Historial (fecha, objetivo, estado, notas breves)
- Crear nueva seccion "Sesion actual" con:
  - Fecha: fecha de hoy
  - Objetivo: preguntar al usuario o inferir de la conversacion
  - Plan: lista de tareas con [ ] pendiente

## 4. Actualizar sesion existente (si procede)

- Marcar [x] las tareas completadas
- Añadir nuevas tareas descubiertas durante el trabajo
- Actualizar seccion Notas con decisiones o problemas
- Si la sesion termina: completar seccion Resultado

## 5. Mostrar estado

Mostrar al usuario el plan actualizado con progreso.
