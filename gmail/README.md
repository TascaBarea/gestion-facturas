# GMAIL MODULE v1.4 - GUÍA DE INSTALACIÓN Y USO

## 📦 CONTENIDO DEL PAQUETE

```
gmail_v1.4/
├── gmail_v1.4_mejoras.py      # Parche con mejoras (aplicar sobre v1.1)
├── generar_sepa.py            # Generador de ficheros SEPA XML
├── gmail_auto.bat             # Script para ejecución automática
├── gmail_auto_setup.bat       # Configurador de tarea programada
├── modulo_vba_sepa.bas        # Código VBA para botón en Excel
├── extractores.zip            # Carpeta de extractores (ya tienes)
└── README.md                  # Este archivo
```

---

## 🔧 INSTALACIÓN PASO A PASO

### 1. EXTRACTORES (si no lo has hecho)

```batch
REM Extraer a esta ruta:
C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores\
```

Verifica que existen archivos como `cvne.py`, `felisa.py`, `francisco_guerra.py`, etc.

### 2. ACTUALIZAR gmail.py

Abre `gmail.py` y realiza estos cambios:

#### 2.1 Actualizar ruta de extractores

Buscar:
```python
EXTRACTORES_PATH: str = field(default="")
```

En `__post_init__`, cambiar:
```python
self.EXTRACTORES_PATH = os.path.join(self.BASE_PATH, "src", "extractores")
```

Por:
```python
self.EXTRACTORES_PATH = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores"
```

#### 2.2 Datos de empresa (IBANs, BIC, NIF)

Los datos sensibles se cargan automaticamente de `config/datos_sensibles.py`.
Ver `config/datos_sensibles.py.example` para la plantilla.

#### 2.3 Marcar correos como leídos

Buscar función `mover_a_procesados` y cambiar la llamada a modify:

```python
def mover_a_procesados(self, email_id: str):
    """Mueve email a etiqueta FACTURAS_PROCESADAS y marca como leído"""
    # ... código existente ...
    
    self.service.users().messages().modify(
        userId='me',
        id=email_id,
        body={
            'addLabelIds': [label_destino],
            'removeLabelIds': [label_origen, 'UNREAD'] if label_origen else ['UNREAD']  # <-- Añadir UNREAD
        }
    ).execute()
```

#### 2.4 Reemplazar ExcelGenerator

Copiar la clase `ExcelGeneratorV14` de `gmail_v1.4_mejoras.py` y reemplazar `ExcelGenerator`.

---

### 3. COPIAR ARCHIVOS AUXILIARES

```batch
REM Copiar scripts
copy generar_sepa.py "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\"
copy gmail_auto.bat "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\"
copy gmail_auto_setup.bat "C:\_ARCHIVOS\TRABAJO\Facturas\gestion-facturas\gmail\"
```

---

### 4. CONFIGURAR TAREA PROGRAMADA (Viernes 03:00)

1. **Ejecutar como administrador**: `gmail_auto_setup.bat`
2. Verificar en Programador de Tareas que existe `Gmail_Facturas_Semanal`
3. La tarea despertará el PC de suspensión automáticamente

---

### 5. AÑADIR BOTÓN SEPA AL EXCEL

1. Abrir Excel `PAGOS_Gmail_*.xlsx`
2. **Alt + F11** (Editor VBA)
3. **Insertar > Módulo**
4. Pegar contenido de `modulo_vba_sepa.bas`
5. Cerrar editor VBA
6. **Guardar como .xlsm** (Excel con macros habilitadas)
7. **Insertar > Formas > Rectángulo redondeado**
8. Escribir texto: "Generar SEPA XML"
9. Click derecho en forma > **Asignar macro** > `GenerarSEPAXML`
10. Guardar

---

## 📖 USO DEL SISTEMA

### FLUJO SEMANAL AUTOMÁTICO

```
VIERNES 03:00
    │
    ▼
┌─────────────────────────────────────────┐
│  PC se despierta de suspensión          │
│  gmail_auto.bat se ejecuta              │
│  gmail.py --produccion                   │
│                                         │
│  • Lee emails de carpeta FACTURAS       │
│  • Descarga PDFs                        │
│  • Extrae datos con extractores         │
│  • Genera PAGOS_Gmail_XTYY.xlsx         │
│  • Copia PDFs a Dropbox                 │
│  • Envía email resumen                  │
│  • Marca emails como leídos             │
│  • Mueve a FACTURAS_PROCESADAS          │
└─────────────────────────────────────────┘
    │
    ▼
EMAIL A tascabarea@gmail.com
    │
    ▼
TÚ REVISAS EL EXCEL (cuando quieras)
```

### GENERAR FICHERO SEPA PARA EL BANCO

1. **Abrir** `PAGOS_Gmail_XTYY.xlsm`
2. **Ir a pestaña SEPA**
3. **Marcar con ✓** las transferencias a pagar (columna INCLUIR)
4. **Seleccionar IBAN ordenante** en desplegable (columna J)
5. **Pulsar botón** "Generar SEPA XML"
6. **Subir fichero** `SEPA_YYYYMMDD_HHMMSS.xml` al banco

---

## 📋 ESTRUCTURA PESTAÑA SEPA

```
┌─────────────────────────────────────────────────────────────────────────┐
│ DATOS DEL ORDENANTE                                                      │
│ Nombre:     TASCA BAREA S.L.L.                                          │
│ NIF-Sufijo: REDACTED_NIF                                                │
│ BIC:        REDACTED_BIC                                                    │
│ IBANs:      TASCA: ES78...4495  |  COMESTIBLES: ES76...2404            │
├─────────────────────────────────────────────────────────────────────────┤
│ # │ INCLUIR │ PROVEEDOR │ CIF │ IBAN_BENEF │ IMPORTE │ REF │ CONCEPTO  │
│   │   ✓     │           │     │            │         │     │           │
│   │         │           │     │            │         │     │           │
│                                                                         │
│ FECHA_EJECUCION │ IBAN_ORDENANTE (desplegable) │ ARCHIVO                │
│                 │ [ES78...4495 ▼]              │                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Error: "Extractor no encontrado"

Verificar que la ruta en CONFIG es correcta:
```python
EXTRACTORES_PATH = r"C:\_ARCHIVOS\TRABAJO\Facturas\Parseo\extractores"
```

Y que los archivos .py existen en esa carpeta.

### Error: Token expirado

Si el token Gmail falla:
1. Eliminar `token.json`
2. Ejecutar `python gmail.py --test`
3. Se abrirá navegador para re-autorizar
4. El nuevo token se guarda automáticamente

### La tarea programada no se ejecuta

1. Verificar que el PC está en **suspensión** (no apagado)
2. Abrir Programador de Tareas
3. Buscar `Gmail_Facturas_Semanal`
4. Click derecho > Ejecutar (para probar manualmente)
5. Revisar historial de la tarea

### El fichero SEPA no se genera

1. Verificar que hay transferencias marcadas con ✓
2. Verificar que todas tienen IBAN ordenante seleccionado
3. Ejecutar manualmente: `python generar_sepa.py`
4. Ver errores en consola

---

## 📊 ESTADÍSTICAS

- **91 extractores** dedicados para proveedores
- **98.9%** compatibilidad con facturas conocidas
- **Ejecución automática** cada viernes
- **Notificación por email** con resumen
- **Fichero SEPA XML** según estándar ISO 20022 (AEB 2025)

---

## 📞 SOPORTE

Si hay problemas, revisa:
1. Log en `outputs/logs_gmail/YYYY-MM-DD.log`
2. Email de notificación en `tascabarea@gmail.com`
3. Consola al ejecutar `python gmail.py --test`

---

*Versión 1.4 - Febrero 2026*
*TASCA BAREA S.L.L.*
