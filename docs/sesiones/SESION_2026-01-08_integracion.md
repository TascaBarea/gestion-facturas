# SESIÓN 08/01/2026 - Integración y Creación Repositorio

**Versión:** v2.0 (proyecto integrado)  
**Duración:** ~4 horas  
**Autor:** Tasca Barea + Claude  

---

## 🎯 OBJETIVO DE LA SESIÓN

Integrar ParsearFacturas con ClasificadorMovimientos en un proyecto unificado y crear repositorio GitHub nuevo.

---

## ✅ LOGROS PRINCIPALES

### 1. Análisis completo del sistema
- Revisión de la Definición Funcional del proyecto
- 15+ preguntas estratégicas para definir requisitos al 96%
- Decisiones sobre nomenclatura, maestros y flujos

### 2. ESQUEMA_PROYECTO.md v2.1 creado
Documento maestro con 18 secciones:
- Contexto del negocio (TASCA BAREA SLL, CIF B87760575)
- Estructura de carpetas unificada
- Definición de archivos maestros
- Flujo de clasificación de movimientos
- Script Gmail → Dropbox → SEPA (FASE 5)
- Protocolo de sesiones con Claude

### 3. Repositorio GitHub creado
- **URL:** https://github.com/TascaBarea/gestion-facturas
- **213 archivos** subidos
- Estructura limpia desde cero
- Separado del repo antiguo (ParsearFacturas-main)

### 4. Decisiones de diseño tomadas

| Tema | Decisión |
|------|----------|
| Entidad | TASCA BAREA SLL (tasca, no restaurante), CIF B87760575 |
| Campo nombre proveedor | `PROVEEDOR` (unificado en todo el sistema) |
| Maestro proveedores | `MAESTRO_PROVEEDORES.xlsx` (fusión de 3 archivos) |
| Diccionario sinónimos | `DICCIONARIO_SINONIMOS.xlsx` |
| Archivos salida | `COMPRAS_XTxx.xlsx`, `MOVIMIENTOS_XTxx.xlsx`, `VENTAS_XTxx.xlsx` |
| Columnas banco | `CLASIFICACION_TIPO`, `CLASIFICACION_DETALLE` (se mantienen) |
| Columnas facturas | Añadir `ESTADO_PAGO`, `MOVIMIENTO_#` |
| Ficheros SEPA | `banco_datos/SEPA/SEPA_YYYYMMDD.xml` |
| Centro | Solo para movimientos banco (TASCA / COMESTIBLES) |
| Cuadre | Manual con `python cuadre.py` |
| Repositorio | Nuevo unificado `gestion-facturas` |

---

## 📁 ESTRUCTURA FINAL DEL REPOSITORIO

```
gestion-facturas/
├── main.py                    # ParsearFacturas
├── clasificador.py            # (pendiente crear)
├── banco/
│   ├── parser_n43.py
│   ├── router.py
│   └── clasificadores/
├── config/
├── datos/
│   ├── MAESTRO_PROVEEDORES.xlsx (pendiente unificar)
│   ├── DICCIONARIO_SINONIMOS.xlsx
│   └── DiccionarioProveedoresCategoria.xlsx
├── docs/
│   └── archivo/
├── extractores/ (~95 archivos)
├── nucleo/
├── outputs/
└── salidas/
```

---

## 📊 ARCHIVOS MAESTROS ANALIZADOS

| Archivo | Filas | Contenido |
|---------|-------|-----------|
| `Maestro_Proveedores_ACTUALIZADO.xlsx` | 53 | PROVEEDOR, CIF, IBAN, FORMA_PAGO |
| `EXTRACTORES_COMPLETO.xlsx` | 91 | + TIENE_EXTRACTOR, ARCHIVO_EXTRACTOR |
| `DiccionarioEmisorTitulo.xlsx` (Sheet1) | 50 | NOMBRE_EN_CONCEPTO → TITULO_FACTURA |
| `DiccionarioEmisorTitulo.xlsx` (Hoja1) | 183 | CUENTA → CLIENTE (de Kinema) |
| `DiccionarioProveedoresCategoria.xlsx` | 1,306 | ARTICULO → CATEGORIA |

---

## 🔄 FASES DE DESARROLLO DEFINIDAS

### FASE 1 - Cimientos ✅ COMPLETADA
- [x] Análisis y definición funcional
- [x] ESQUEMA_PROYECTO.md v2.1
- [x] Repositorio GitHub creado
- [ ] Añadir ESQUEMA_PROYECTO.md al repo
- [ ] Crear MAESTRO_PROVEEDORES.xlsx unificado

### FASE 2 - Consolidar existente
- [ ] clasificador.py con menú interactivo
- [ ] Integrar parser_n43.py
- [ ] Añadir ESTADO_PAGO y MOVIMIENTO_# a Facturas
- [ ] Generar REVISAR_XTxx.txt

### FASE 3 - Ventas
- [ ] Parser Loyverse (receipts-*.csv)
- [ ] Parser WooCommerce
- [ ] VENTAS_XTxx.xlsx

### FASE 4 - Cuadre completo
- [ ] cuadre.py (Compras ↔ Banco)
- [ ] Cuadre Ventas ↔ Banco (TPV)

### FASE 5 - Automatización Gmail
- [ ] gmail_facturas.py
- [ ] Detección facturas en email
- [ ] Renombrado automático
- [ ] Subida a Dropbox
- [ ] Generación SEPA
- [ ] Ejecución automática viernes

---

## 📝 MOVIMIENTOS SIN FACTURA (lista cerrada)

| Tipo | CLASIFICACION_TIPO |
|------|-------------------|
| Seguros | SEGUROS |
| Comunidad de vecinos | COMUNIDAD |
| Impuestos (AEAT, Ayto) | IMPUESTOS |
| Seguros Sociales (TGSS) | SEGUROS SOCIALES |
| Nóminas | NOMINAS |
| IRPF/Retenciones | NOMINAS |
| Finiquitos | NOMINAS |
| Comisiones bancarias | COMISIONES BANCO |
| TPV abonos | TPV [CENTRO] |
| TPV comisiones | COMISIONES TPV |
| Traspasos entre cuentas | TRASPASO |
| Asociaciones (SGAE, etc.) | ASOCIACIONES |
| Alquiler local | ✅ SÍ requiere factura |

---

## 🛠️ COMANDOS GIT EJECUTADOS

```cmd
cd C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas
git init
git remote add origin https://github.com/TascaBarea/gestion-facturas.git
git add .
git commit -m "v1.0 - Proyecto integrado gestion-facturas"
git push -u origin main
```

**Resultado:** 213 archivos, 50,489 líneas de código subidas.

---

## 📋 PENDIENTE PRÓXIMA SESIÓN

### Prioridad ALTA
1. Añadir `ESQUEMA_PROYECTO.md` al repo (descargar y copiar a docs/)
2. Crear `clasificador.py` con menú interactivo
3. Crear `MAESTRO_PROVEEDORES.xlsx` unificado

### Prioridad MEDIA
4. Probar flujo completo ParsearFacturas → Clasificador
5. Conectar clasificador con Excel de facturas

### Para recordar
- El repo antiguo `ParsearFacturas-main` queda como backup
- Trabajar siempre en `gestion-facturas` a partir de ahora
- Ficheros N43 van en `banco_datos/N43/` (local, no Dropbox)
- Ficheros SEPA van en `banco_datos/SEPA/`

---

## 📎 ARCHIVOS ENTREGADOS

| Archivo | Descripción |
|---------|-------------|
| `ESQUEMA_PROYECTO.md` | Documento maestro v2.1 (18 secciones) |
| `SESION_2026-01-08_integracion.md` | Este resumen |

---

## 💡 NOTAS IMPORTANTES

1. **Kinema** asigna números de factura y CUENTA - es la fuente de verdad
2. **Nombre canónico** del proveedor: el que usa Kinema
3. **TEMP** se usa cuando Kinema aún no ha numerado (archivo empieza por trimestre)
4. **Script Gmail** (FASE 5): automático viernes, detecta facturas, renombra, sube a Dropbox, genera SEPA
5. **Ventas** entran en alcance (Loyverse + WooCommerce) - FASE 3

---

*Sesión finalizada: 08/01/2026*
*Próxima sesión: Continuar con FASE 1 (ESQUEMA al repo) y FASE 2 (clasificador.py)*
