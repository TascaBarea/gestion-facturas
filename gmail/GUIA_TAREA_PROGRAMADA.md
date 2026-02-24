# GUÍA DETALLADA: CONFIGURAR EJECUCIÓN AUTOMÁTICA (VIERNES 03:00)

## VISIÓN GENERAL

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIERNES 02:59                               │
│                    PC en suspensión                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VIERNES 03:00                               │
│   Windows despierta el PC automáticamente                        │
│   Se ejecuta: Programador de Tareas → Gmail_Facturas_Semanal     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│   gmail_auto.bat                                                 │
│   ├── cd a carpeta gmail                                        │
│   ├── python gmail.py --produccion                              │
│   │   ├── Conectar Gmail                                        │
│   │   ├── Descargar facturas                                    │
│   │   ├── Procesar con extractores                              │
│   │   ├── Generar Excel con pestaña SEPA                       │
│   │   ├── Copiar PDFs a Dropbox                                 │
│   │   └── Enviar email resumen                                  │
│   └── Registrar resultado en log                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│   EMAIL A tascabarea@gmail.com                                   │
│   ├── Resumen de facturas procesadas                            │
│   ├── Alertas rojas si hay errores                              │
│   └── Links a archivos                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## OPCIÓN A: CONFIGURACIÓN AUTOMÁTICA (RECOMENDADA)

### Paso 1: Ejecutar el script de configuración

1. Navega a: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\`
2. Click derecho en `gmail_auto_setup.bat`
3. Selecciona **"Ejecutar como administrador"**
4. Espera a que diga "TAREA CREADA EXITOSAMENTE"

### Paso 2: Verificar

1. Abre el **Programador de Tareas** (busca "Programador" en Windows)
2. En el panel izquierdo, haz clic en "Biblioteca del Programador de tareas"
3. Busca la tarea `Gmail_Facturas_Semanal`
4. Verifica que aparece "Viernes" en la columna "Desencadenadores"

---

## OPCIÓN B: CONFIGURACIÓN MANUAL PASO A PASO

### Paso 1: Abrir el Programador de Tareas

1. Presiona `Win + R`
2. Escribe `taskschd.msc`
3. Presiona Enter

### Paso 2: Crear nueva tarea

1. En el panel derecho, click en **"Crear tarea..."** (NO "Crear tarea básica")

### Paso 3: Pestaña "General"

```
┌─────────────────────────────────────────────────────────────────┐
│ GENERAL                                                          │
├─────────────────────────────────────────────────────────────────┤
│ Nombre: Gmail_Facturas_Semanal                                   │
│                                                                  │
│ Descripción: Procesa facturas de Gmail cada viernes a las 03:00 │
│                                                                  │
│ Opciones de seguridad:                                          │
│ ☑ Ejecutar tanto si el usuario inició sesión como si no        │
│ ☑ Ejecutar con los privilegios más altos                        │
│                                                                  │
│ Configurar para: Windows 10                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Paso 4: Pestaña "Desencadenadores"

1. Click en **"Nuevo..."**
2. Configurar así:

```
┌─────────────────────────────────────────────────────────────────┐
│ NUEVO DESENCADENADOR                                             │
├─────────────────────────────────────────────────────────────────┤
│ Comenzar la tarea: Según una programación                        │
│                                                                  │
│ Configuración:                                                   │
│ ○ Una vez                                                        │
│ ○ Diariamente                                                    │
│ ● Semanalmente  ←← SELECCIONAR ESTA                             │
│ ○ Mensualmente                                                   │
│                                                                  │
│ Iniciar: [fecha de hoy]  a las  03:00:00                        │
│                                                                  │
│ Repetir cada: 1 semanas en:                                     │
│ ☐ Lunes  ☐ Martes  ☐ Miércoles  ☐ Jueves                       │
│ ☑ Viernes  ☐ Sábado  ☐ Domingo                                  │
│                                                                  │
│ ☑ Habilitado                                                    │
└─────────────────────────────────────────────────────────────────┘
```

3. Click en **Aceptar**

### Paso 5: Pestaña "Acciones"

1. Click en **"Nueva..."**
2. Configurar así:

```
┌─────────────────────────────────────────────────────────────────┐
│ NUEVA ACCIÓN                                                     │
├─────────────────────────────────────────────────────────────────┤
│ Acción: Iniciar un programa                                      │
│                                                                  │
│ Programa o script:                                               │
│ C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\gmail_auto.bat │
│                                                                  │
│ Agregar argumentos (opcional):                                   │
│ [dejar vacío]                                                    │
│                                                                  │
│ Iniciar en (opcional):                                          │
│ C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail             │
└─────────────────────────────────────────────────────────────────┘
```

3. Click en **Aceptar**

### Paso 6: Pestaña "Condiciones" ⚠️ MUY IMPORTANTE

```
┌─────────────────────────────────────────────────────────────────┐
│ CONDICIONES                                                      │
├─────────────────────────────────────────────────────────────────┤
│ Inactividad:                                                     │
│ ☐ Iniciar la tarea solo si el equipo está inactivo durante...  │
│                                                                  │
│ Energía:                                                         │
│ ☐ Iniciar solo si el equipo usa corriente alterna              │
│ ☐ Detener si el equipo pasa a batería                          │
│ ☑ Reactivar el equipo para ejecutar esta tarea  ←← ACTIVAR     │
│                                                                  │
│ Red:                                                             │
│ ☐ Iniciar solo si la conexión de red está disponible           │
└─────────────────────────────────────────────────────────────────┘
```

**⚠️ CRÍTICO**: Marca la casilla **"Reactivar el equipo para ejecutar esta tarea"**

### Paso 7: Pestaña "Configuración"

```
┌─────────────────────────────────────────────────────────────────┐
│ CONFIGURACIÓN                                                    │
├─────────────────────────────────────────────────────────────────┤
│ ☑ Permitir que la tarea se ejecute a petición                   │
│ ☑ Ejecutar la tarea lo antes posible si no se inició...        │
│ ☐ Si se produce un error, reintentar cada: 1 minuto            │
│ ☑ Detener tarea si se ejecuta más de: 1 hora                   │
│ ☐ Si la tarea no finaliza a petición, forzar detención         │
│                                                                  │
│ Si la tarea ya se está ejecutando:                              │
│ [No iniciar una instancia nueva ▼]                              │
└─────────────────────────────────────────────────────────────────┘
```

### Paso 8: Guardar

1. Click en **Aceptar**
2. Te pedirá contraseña de Windows - introdúcela
3. La tarea queda creada

---

## VERIFICAR QUE FUNCIONA

### Prueba 1: Ejecutar manualmente

1. En el Programador de Tareas, busca `Gmail_Facturas_Semanal`
2. Click derecho → **"Ejecutar"**
3. Espera ~30 segundos
4. Revisa:
   - El log en: `C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\outputs\logs_gmail\`
   - Tu email: debería llegar el resumen

### Prueba 2: Verificar historial

1. Click derecho en la tarea → **"Propiedades"**
2. Pestaña **"Historial"**
3. Debería aparecer la ejecución con "La operación se completó correctamente"

### Prueba 3: Simular despertar (opcional)

1. Pon el PC en suspensión
2. Espera al viernes a las 03:00
3. El PC debería encenderse solo y procesar

---

## CONFIGURACIÓN DE ENERGÍA (IMPORTANTE)

Para que Windows pueda despertar el PC, necesitas verificar esto:

### En Windows:

1. Panel de Control → Opciones de energía
2. Click en "Cambiar la configuración del plan" de tu plan activo
3. Click en "Cambiar la configuración avanzada de energía"
4. Busca "Suspensión" → "Permitir temporizadores de reactivación"
5. Configura como **"Habilitar"**

```
┌─────────────────────────────────────────────────────────────────┐
│ Opciones de energía avanzadas                                    │
├─────────────────────────────────────────────────────────────────┤
│ ▼ Suspensión                                                     │
│   ├── Suspender tras: 30 minutos                                │
│   ├── Permitir suspensión híbrida: Activado                     │
│   └── Permitir temporizadores de reactivación: Habilitar ←←    │
└─────────────────────────────────────────────────────────────────┘
```

### En BIOS (si no funciona lo anterior):

Algunos equipos necesitan habilitar "Wake on RTC" o "Wake on Timer" en la BIOS.

---

## SOLUCIÓN DE PROBLEMAS

### El PC no se despierta

1. Verifica "Permitir temporizadores de reactivación" en Opciones de energía
2. Verifica que marcaste "Reactivar el equipo" en la tarea
3. Prueba con el comando: `powercfg -waketimers` (debe mostrar tu tarea)

### La tarea no se ejecuta

1. Verifica que el usuario tiene permisos de administrador
2. Verifica que la ruta del .bat es correcta
3. Revisa el historial de la tarea para ver errores

### Error "El sistema no puede encontrar el archivo"

1. Verifica que `gmail_auto.bat` existe en la ruta especificada
2. Verifica que la ruta en "Iniciar en" es correcta

### Error de Python

1. Verifica que Python está en el PATH del sistema
2. Prueba ejecutar manualmente: `python gmail.py --test`

---

## RESUMEN DE ARCHIVOS NECESARIOS

```
C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\
├── gmail.py                  ← Script principal (v1.4)
├── gmail_auto.bat            ← Script batch para tarea programada
├── gmail_auto_setup.bat      ← Configurador automático
├── generar_sepa.py           ← Generador de ficheros SEPA
├── credentials.json          ← Credenciales Google Cloud (ya existe)
├── token.json                ← Token Gmail (ya existe)
└── ...
```

---

## CAMBIAR DÍA U HORA DE EJECUCIÓN

Si quieres que se ejecute otro día u otra hora:

1. Abre Programador de Tareas
2. Busca `Gmail_Facturas_Semanal`
3. Click derecho → **"Propiedades"**
4. Pestaña **"Desencadenadores"**
5. Selecciona el desencadenador → **"Editar"**
6. Cambia el día/hora
7. **Aceptar** → **Aceptar**

---

## DESACTIVAR TEMPORALMENTE

Si quieres pausar la ejecución automática:

1. Abre Programador de Tareas
2. Busca `Gmail_Facturas_Semanal`
3. Click derecho → **"Deshabilitar"**

Para reactivar: Click derecho → **"Habilitar"**

---

## ELIMINAR LA TAREA

Si quieres eliminar la tarea programada:

```batch
schtasks /delete /tn "Gmail_Facturas_Semanal" /f
```

O desde el Programador de Tareas: Click derecho → **"Eliminar"**

---

*Versión 1.4 - Febrero 2026*
*TASCA BAREA S.L.L.*
