# INFORME EJECUTIVO - ANÁLISIS DE PROYECTO
## Sistema ParsearFacturas - TASCA BAREA SLL

**Fecha:** 12/12/2025  
**Analista:** Director de Proyectos TI Senior  
**Documento:** Evaluación crítica y recomendaciones estratégicas

---

## 1. DIAGNÓSTICO EJECUTIVO

### Estado Real vs. Percibido

| Aspecto | Estado Percibido | Estado Real |
|---------|-----------------|-------------|
| Completitud | ~75% | **40-45%** |
| Listo para producción | Casi | **No** |
| Automatización | Parcial | **Manual con scripts** |
| Mantenibilidad | Aceptable | **Crítica** |

**Conclusión brutal:** El proyecto tiene una base técnica sólida pero está construido sobre **arena movediza**. Funciona para demos pero no para operación real.

---

## 2. PUNTOS DÉBILES CRÍTICOS (Por orden de impacto)

### 🔴 CRÍTICO 1: Arquitectura Monolítica No Sostenible

**Problema:** Un único archivo Python de **6,000+ líneas** con:
- 57+ extractores específicos por proveedor embebidos
- Sin separación de responsabilidades
- Lógica de negocio mezclada con extracción de datos
- Patrones regex hardcodeados

**Impacto:**
- Cada nuevo proveedor = modificar archivo principal
- Un bug en un extractor puede romper todo el sistema
- Imposible hacer testing unitario efectivo
- Tiempo de onboarding de nuevo desarrollador: **semanas**

**Deuda técnica acumulada:** ~40 horas para refactorizar

---

### 🔴 CRÍTICO 2: Fragilidad ante Cambios de Formato PDF

**Problema observado en esta sesión:**
- pypdf vs pdfplumber extraen texto **diferente** del mismo PDF
- Espacios internos en números (`1 0` vs `10`)
- Orden de columnas cambia según la librería
- **Cada proveedor puede cambiar su formato de factura sin aviso**

**Impacto:**
- Sistema rompe silenciosamente cuando proveedor actualiza su software
- Requiere intervención manual constante
- No hay forma de detectar degradación automáticamente

**Ejemplo real de hoy:**
```
BERZAL antes: "206017 Mantequilla 10 5,48"
BERZAL ahora: "206017 Mantequilla 1 0 5,48" (espacio en IVA)
```

**Solución estructural necesaria:** Sistema de validación que detecte cuando un patrón deja de funcionar ANTES de que afecte a producción.

---

### 🔴 CRÍTICO 3: Sin Cobertura de IBANs (79% pendiente)

**Números reales:**
- 141 proveedores requieren IBAN para pago automático
- Solo 30 tienen IBAN registrado (21%)
- **111 proveedores = pago manual obligatorio**

**Impacto:**
- El sistema SEPA es inútil para el 79% de proveedores
- ROI del proyecto: **negativo hasta resolver esto**
- Cada viernes seguirá siendo trabajo manual

**Tiempo estimado para completar:**
- Extracción de facturas históricas: 8h
- Campaña de contacto a proveedores: 2-3 semanas
- **Bloqueante hasta enero 2026 en el mejor caso**

---

### 🟠 ALTO 4: Sin Testing Automatizado

**Situación actual:**
- Cero tests unitarios
- Cero tests de integración
- Cero tests de regresión
- Validación = ejecutar manualmente y revisar Excel

**Consecuencias observadas:**
- Cada nueva versión puede romper extractores anteriores
- No hay forma de saber si v3.50 rompió algo que v3.41 hacía bien
- Debugging reactivo vs. proactivo

**Costo de no tener tests:**
- 2-4 horas de debugging por sesión de desarrollo
- Riesgo de errores en pagos reales

---

### 🟠 ALTO 5: Excel como "Base de Datos"

**MAESTROS.xlsx actúa como:**
- Base de datos de proveedores
- Catálogo de artículos
- Registro de IBANs
- Log de procesamiento

**Problemas inherentes:**
- Sin integridad referencial
- Sin control de concurrencia
- Sin histórico de cambios
- Límite de 1M filas (no escalable)
- Corrupción silenciosa posible

---

### 🟠 ALTO 6: Sin Trazabilidad End-to-End

**No existe registro de:**
- Qué facturas entraron al sistema
- Cuáles se procesaron correctamente
- Cuáles fallaron y por qué
- Qué pagos se generaron
- Si los pagos se ejecutaron

**Impacto en auditoría:** Imposible responder a Hacienda si pregunta "¿por qué pagaron X a proveedor Y?"

---

### 🟡 MEDIO 7: Dependencia de Sesiones con Claude

**Observación crítica:** El desarrollo depende de sesiones de pair-programming con IA donde:
- El conocimiento vive en transcripts, no en documentación
- Cada sesión reconstruye contexto desde cero
- No hay transferencia de conocimiento estructurada

**Riesgo:** Si el desarrollador principal no está disponible, nadie puede mantener el sistema.

---

## 3. PUNTOS DE MEJORA PRIORITARIOS

### Inmediato (Esta semana)

| Acción | Esfuerzo | Impacto |
|--------|----------|---------|
| Separar extractores en módulos | 8h | Alto |
| Crear 10 tests básicos con facturas reales | 4h | Alto |
| Documentar formato de cada proveedor | 4h | Medio |
| Validación de IBAN antes de SEPA | 2h | Crítico |

### Corto plazo (2 semanas)

| Acción | Esfuerzo | Impacto |
|--------|----------|---------|
| Campaña recolección IBANs TOP 40 | 16h | Crítico |
| Migrar MAESTROS a SQLite | 16h | Alto |
| Implementar logging estructurado | 4h | Medio |
| CI/CD básico con GitHub Actions | 8h | Medio |

### Medio plazo (1 mes)

| Acción | Esfuerzo | Impacto |
|--------|----------|---------|
| Extractor Gmail con OAuth2 | 16h | Alto |
| Orquestador/Scheduler | 8h | Alto |
| Dashboard de estado (web simple) | 16h | Medio |
| Sistema de alertas (Telegram/Email) | 4h | Medio |

---

## 4. ESTIMACIÓN DE TIEMPOS REALISTA

### Para MVP Funcional (Automatización básica viernes)

| Componente | Horas | Dependencias |
|------------|-------|--------------|
| Completar IBANs (50%) | 20h | Contacto proveedores |
| Extractor Gmail | 16h | OAuth2 setup |
| Conectar componentes | 8h | Gmail + Parser + SEPA |
| Testing básico | 8h | Facturas de ejemplo |
| Scheduler | 4h | Servidor disponible |
| **TOTAL MVP** | **56h** | **4-6 semanas** |

### Para Sistema Robusto (Producción real)

| Componente | Horas | Dependencias |
|------------|-------|--------------|
| MVP completo | 56h | - |
| Tests automatizados (80% cobertura) | 24h | Refactorización |
| Migración a SQLite | 16h | - |
| Trazabilidad completa | 16h | BD funcionando |
| Manejo de errores y reintentos | 8h | - |
| Documentación operativa | 8h | Sistema estable |
| **TOTAL ROBUSTO** | **128h** | **3-4 meses** |

### Para Sistema Empresarial (Escalable, auditable)

| Componente | Horas | Dependencias |
|------------|-------|--------------|
| Sistema robusto | 128h | - |
| API REST para integración | 24h | - |
| Interfaz web de gestión | 40h | API lista |
| Conciliación bancaria automática | 24h | Norma 43 parser |
| Multi-usuario con permisos | 16h | - |
| Backup y disaster recovery | 8h | - |
| **TOTAL EMPRESARIAL** | **240h** | **6-8 meses** |

---

## 5. ANÁLISIS DE RIESGOS

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Proveedor cambia formato PDF | Alta | Alto | Sistema de validación + alertas |
| Error en pago SEPA | Media | Crítico | Validación IBAN + revisión manual |
| Pérdida de MAESTROS.xlsx | Media | Crítico | Backup automático + SQLite |
| Desarrollador no disponible | Media | Alto | Documentación + tests |
| Gmail bloquea acceso | Baja | Alto | App password alternativa |
| Banco rechaza fichero SEPA | Media | Medio | Validación previa + modo test |

---

## 6. RECOMENDACIONES ESTRATÉGICAS

### Opción A: Consolidar lo existente (Recomendada)
- **Inversión:** 56-80 horas
- **Plazo:** 6-8 semanas
- **Resultado:** Sistema funcional para 50% de proveedores
- **ROI:** Positivo en 3 meses

### Opción B: Rediseño completo
- **Inversión:** 200+ horas
- **Plazo:** 4-6 meses
- **Resultado:** Sistema empresarial completo
- **ROI:** Positivo en 12 meses
- **Riesgo:** Alto (scope creep)

### Opción C: Solución comercial
- **Inversión:** 200-500€/mes (Holded, Contasimple, etc.)
- **Plazo:** 2-4 semanas de setup
- **Resultado:** Solución probada pero menos personalizada
- **ROI:** Inmediato pero costo recurrente

---

## 7. CONCLUSIÓN FINAL

**El proyecto tiene valor** pero está en una encrucijada:

1. **Lo bueno:** 74.6% de facturas se parsean, generador SEPA funciona, estructura clara
2. **Lo malo:** 79% sin IBAN, código monolítico, sin tests, Excel como BD
3. **Lo feo:** Cada sesión de desarrollo es apagar fuegos en vez de construir

**Mi recomendación como Director de Proyectos:**

> **Pausar el desarrollo de nuevos extractores** y dedicar las próximas 2-3 semanas a:
> 1. Recolectar IBANs (sin esto, todo lo demás es académico)
> 2. Crear 20 tests con facturas reales (proteger lo que funciona)
> 3. Separar extractores en módulos (hacer el código mantenible)
>
> Solo después, continuar con Gmail y automatización.

**El mayor riesgo ahora mismo no es técnico, es operativo:** están invirtiendo tiempo en perfeccionar el 74.6% mientras el 79% de IBANs pendientes bloquea cualquier automatización real.

---

*"Un sistema que funciona el 75% del tiempo pero no puede pagar al 79% de proveedores tiene un ROI negativo."*

---

**Próximos pasos sugeridos:**
1. ✅ Revisar este informe con stakeholders
2. 📋 Decidir entre Opción A, B o C
3. 📧 Iniciar campaña de IBANs esta semana
4. 🧪 Crear suite de tests básica antes de más desarrollo

---

*Informe preparado el 12/12/2025*
