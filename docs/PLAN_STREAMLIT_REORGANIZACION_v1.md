# PLAN: Reorganización Streamlit Tasca Barea
> Versión 1.0 — 05/04/2026
> Consensuado en sesión de planificación Jaime + Claude

---

## 1. VISIÓN

Convertir la app Streamlit de una colección de páginas sueltas en el **centro de control integral** de Tasca Barea. Al abrir el navegador, ver de un vistazo cómo está todo y poder actuar.

**Prioridad del usuario (ordenada):**
1. Saber qué facturas han llegado y si se parsearon bien
2. Ver el estado del cuadre bancario
3. Controlar ventas y márgenes sin abrir 3 sitios
4. Que todo funcione sin tener el PC encendido (futuro)

---

## 2. ESTRUCTURA DE NAVEGACIÓN

### Pantalla de inicio: Hub de navegación (Propuesta B)
4 tarjetas grandes, una por sección, cada una con un dato clave.
Click en tarjeta → navega a la primera página de esa sección.

### Sidebar: Secciones agrupadas (nativo `st.navigation`)
Siempre visible. Secciones con cabeceras. Badges rojos para alertas.

```
🏠 Inicio
─── COMPRAS ───
🔍 Parseo                  ← página principal de COMPRAS
📋 Facturas
👥 Proveedores
📖 Diccionario
📧 Log Gmail
─── VENTAS ───
📊 Dashboard               ← tal cual (por ahora)
📦 Artículos               ← nueva (futuro)
─── EVENTOS ───
📅 Calendario              ← tal cual
➕ Alta evento             ← tal cual
─── OPERACIONES ───
🏦 Cuadre                  ← tal cual
▶️  Scripts                 ← tal cual
📡 Monitor                 ← tal cual
```

**Total: 14 páginas** (9 existentes reorganizadas + 5 nuevas)

### Roles y visibilidad
| Rol     | Secciones visibles              |
|---------|----------------------------------|
| admin   | Todas                            |
| socio   | Ventas, Eventos                  |
| comes   | Ventas                           |
| eventos | Eventos                          |

---

## 3. CONTENIDO POR SECCIÓN

### 3.1 COMPRAS (prioridad 1)

#### 🔍 Parseo (NUEVA — página principal)
**Flujo:**
1. Seleccionar carpeta Dropbox (por trimestre: 1T26, 2T26...)
2. Elegir modo: todas las facturas / solo nuevas / factura concreta
3. Ejecutar parseo
4. Ver resultados en pantalla:
   - Tabla resumen: archivo, proveedor, líneas, cuadre (✅/⚠️/❌)
   - Expandir cada factura: líneas parseadas, desglose IVA, texto raw
   - Métricas globales: total OK, descuadres, sin extractor
5. Exportar a Excel (`COMPRAS_XTxx_YYYYMMDD.xlsx`)

**Requiere backend:**
- `GET /api/parseo/folders` → lista de carpetas Dropbox disponibles
- `GET /api/parseo/files/{folder}` → PDFs en esa carpeta
- `POST /api/parseo/run` → ejecutar parseo (body: carpeta, modo, archivos)
- `GET /api/parseo/results/{job_id}` → resultados del parseo

**Depende de:** Parseo repo (main.py v5.18, 104 extractores), importable desde backend.

#### 📋 Facturas (NUEVA — listado/consulta)
- Tabla filtrable: trimestre, proveedor, estado parseo, fecha, cuadre
- Fuente de datos: Excel COMPRAS generado por Parseo
- Click en factura → ver detalle (líneas, PDF original si posible)
- Sin edición (solo consulta)

**Requiere backend:**
- `GET /api/compras/{trimestre}` → datos del Excel COMPRAS

#### 👥 Proveedores (EXISTENTE — maestro.py reorganizado)
- Ya funciona: búsqueda, filtros, edición, alta
- Se mueve de la raíz del sidebar a sección COMPRAS
- Sin cambios de funcionalidad

#### 📖 Diccionario (NUEVA)
- Visualizar/buscar `DiccionarioProveedoresCategoria.xlsx`
- Filtrar por proveedor, categoría, tipo IVA
- Ver qué artículos faltan por categorizar
- Futuro: edición inline

**Requiere backend:**
- `GET /api/diccionario` → datos del Excel
- (futuro) `PUT /api/diccionario/{articulo}` → editar categoría

#### 📧 Log Gmail (EXISTENTE — log_gmail.py reorganizado)
- Ya funciona
- Se mueve a sección COMPRAS
- Sin cambios

---

### 3.2 VENTAS (diferido — se trabaja más adelante)

#### 📊 Dashboard (EXISTENTE)
- Se mueve tal cual a sección VENTAS
- Futuro: separar en dashboards por negocio (Tasca, Comestibles, WooCommerce)
- Futuro: añadir márgenes y comparativas YoY

#### 📦 Artículos (NUEVA — futuro)
- Catálogo de artículos Loyverse
- Cruce con DiccionarioProveedoresCategoria
- Análisis de rotación y rentabilidad

---

### 3.3 EVENTOS (sin cambios)

#### 📅 Calendario (EXISTENTE)
- Se mueve tal cual a sección EVENTOS

#### ➕ Alta evento (EXISTENTE)
- Se mueve tal cual a sección EVENTOS

---

### 3.4 OPERACIONES (sin cambios por ahora)

#### 🏦 Cuadre (EXISTENTE)
- Se mueve a sección OPERACIONES
- Futuro: añadir movimientos de cuenta como subpágina

#### ▶️ Scripts (EXISTENTE — ejecutar.py)
- Se mueve a sección OPERACIONES

#### 📡 Monitor (EXISTENTE — monitor.py)
- Se mueve a sección OPERACIONES

---

## 4. CAMBIOS EN BACKEND (FastAPI)

### Endpoints nuevos necesarios
| Método | Ruta | Auth | Propósito |
|--------|------|------|-----------|
| GET | /api/parseo/folders | api_key | Listar carpetas Dropbox por trimestre |
| GET | /api/parseo/files/{folder} | api_key | Listar PDFs en carpeta |
| POST | /api/parseo/run | admin | Ejecutar parseo (async job) |
| GET | /api/parseo/results/{job_id} | api_key | Resultados del parseo |
| GET | /api/compras/{trimestre} | api_key | Datos Excel COMPRAS |
| GET | /api/diccionario | api_key | Datos DiccionarioProveedoresCategoria |

### Integración Parseo ↔ Backend
El backend necesita importar el módulo Parseo. Opciones:
- **Opción A:** Symlink de Parseo/ dentro de gestion-facturas/ (como ya hace nucleo/)
- **Opción B:** Copiar extractores al repo gestion-facturas
- **Opción C:** Llamar a main.py como subprocess

Recomendación: **Opción A** (symlink) — mínimo cambio, máxima compatibilidad.

---

## 5. CAMBIOS EN FRONTEND (Streamlit)

### Archivos a modificar
- `app.py` → reorganizar ALL_PAGES con secciones st.navigation
- `utils/auth.py` → actualizar ROLE_PAGES con nuevas páginas

### Archivos nuevos
```
pages/
├── inicio.py              ← Hub B (4 tarjetas)
├── parseo.py              ← Parseo interactivo
├── facturas.py            ← Listado de facturas
├── diccionario.py         ← DiccionarioProveedoresCategoria
└── articulos.py           ← Catálogo (futuro)
```

### Archivos existentes a renombrar/mover
```
ventas.py          → sin cambios (se reubica en sección VENTAS)
cuadre.py          → sin cambios (se reubica en sección OPERACIONES)
maestro.py         → sin cambios (se reubica en sección COMPRAS)
log_gmail.py       → sin cambios (se reubica en sección COMPRAS)
calendario_eventos.py → sin cambios (se reubica en sección EVENTOS)
alta_evento.py     → sin cambios (se reubica en sección EVENTOS)
ejecutar.py        → sin cambios (se reubica en sección OPERACIONES)
monitor.py         → sin cambios (se reubica en sección OPERACIONES)
documentos.py      → evaluar si se mantiene o se integra en OPERACIONES
```

---

## 6. PLAN DE EJECUCIÓN

### Fase 1 — Reestructurar app (1 sesión)
- Modificar app.py: secciones en st.navigation
- Crear inicio.py (Hub B con 4 tarjetas)
- Actualizar auth.py con nuevos ROLE_PAGES
- Reorganizar páginas existentes (sin cambiar funcionalidad)
- **Resultado:** App reorganizada con nueva estructura, todo lo existente funciona

### Fase 2 — Página Parseo standalone (1 sesión)
- Crear parseo.py con extractores embebidos (los 4 de prueba)
- Upload de PDFs via file_uploader (sin backend)
- Ver resultados + exportar Excel
- **Resultado:** Parseo funcional para demos, sin backend

### Fase 3 — Backend parseo (2-3 sesiones)
- Nuevos endpoints: /api/parseo/*
- Integrar Parseo repo (symlink + imports)
- Conectar parseo.py de Streamlit con backend
- **Resultado:** Parseo completo con 104 extractores desde el navegador

### Fase 4 — Facturas + Diccionario (1-2 sesiones)
- Crear facturas.py (listado filtrable desde COMPRAS Excel)
- Crear diccionario.py (visualización DiccionarioProveedoresCategoria)
- Endpoints backend: /api/compras, /api/diccionario
- **Resultado:** Sección COMPRAS completa

### Fase 5 — Dashboards Ventas (futuro)
- Rediseñar dashboards por negocio
- Añadir márgenes, comparativas YoY
- Página Artículos

### Fase 6 — Cloud (futuro)
- Migrar backend a servidor cloud
- Eliminar dependencia del PC de Jaime
- Automatización completa

---

## 7. IDENTIDAD VISUAL

### Colores
| Elemento | Color | Hex |
|----------|-------|-----|
| Acento primario (botones, activo) | Bermellón/Granate | #CA3026 / #8B0000 |
| Sidebar fondo | Gradiente oscuro | #1A1A1A → #2A1A1A |
| Sección Comestibles | Soft Sage | #ACC8A2 |
| Sección Eventos | Amarillo Dorado | #F6AA00 |

### Tipografía
- Headings: Syne
- Body: DM Sans
- Mono/datos: sistema monospace

### Principios
- Fondo oscuro en sidebar, contenido en claro
- Badges rojos solo para alertas reales (no decorativos)
- Métricas con formato español (1.234,56 €)
- Semáforos: verde=OK, ámbar=atención, rojo=error

---

## 8. NOTAS

- Este documento sustituye cualquier planificación anterior sobre Streamlit
- Las fases son secuenciales — cada una funciona independientemente
- Fase 1 se puede hacer en una sesión con Claude Code
- El parseo.py standalone (Fase 2) ya está generado con 4 extractores de prueba
- Para Fase 3, se necesita que Parseo sea importable desde el backend
