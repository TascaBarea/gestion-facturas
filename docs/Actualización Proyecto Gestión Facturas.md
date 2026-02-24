Aquí tienes el documento **ESQUEMA\_PROYECTO\_DEFINITIVO\_v3\_0.md** actualizado. He integrado toda la nueva arquitectura de ventas, la lógica de los dos tokens para Tasca y Comestibles, el histórico de artículos (Opción B) y los nuevos protocolos de seguridad.

# ---

**📐 ESQUEMA PROYECTO GESTIÓN-FACTURAS**

**Versión:** 3.0 (Evolución Integrada)  
**Fecha:** 06/02/2026  
**Estado:** 🛠️ EN DESARROLLO \- Módulo de Ventas e Históricos

## ---

**1\. VISIÓN GENERAL (SISTEMA 360º)**

┌─────────────────────────────────────────────────────────────────────────────┐  
│                         GESTIÓN-FACTURAS BAREA                              │  
│             Sistema Integrado de Ventas, Compras y Artículos                │  
├─────────────────────────────────────────────────────────────────────────────┤  
│                                                                             │  
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │  
│   │    Ⓐ    │    │    Ⓑ    │    │    Ⓒ    │    │    Ⓓ    │    │    Ⓔ    │   │  
│   │ PARSEO  │    │  GMAIL  │    │ VENTAS  │    │ CUADRE  │    │ARTÍCULOS│   │  
│   │  ✅ 85% │    │  ✅ 90% │    │ 🛠️ 20%  │    │  ✅ 70% │    │ 🛠️ 10%  │   │  
│   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘   │  
│        │              │              │              │              │        │  
│        ▼              ▼              ▼              ▼              ▼        │  
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │  
│   │ COMPRAS │    │  PAGOS  │    │ VENTAS  │    │ CUADRE  │    │HISTÓRICO│   │  
│   │  .xlsx  │    │  .xlsx  │    │  .xlsx  │    │ .xlsx   │    │ COSTES  │   │  
│   └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘   │  
└─────────────────────────────────────────────────────────────────────────────┘

## ---

**2\. NUEVOS MÓDULOS DE CONTROL (BAREA 2026\)**

### **Ⓒ MÓDULO VENTAS (Consolidación Semanal)**

* **Origen de Datos:** \* **Loyverse Account 1 (Tasca):** Token API independiente.  
  * **Loyverse Account 2 (Comestibles):** Token API independiente.  
  * **WooCommerce (Web):** API REST (tascabarea.com) para cursos y talleres.  
* **Frecuencia:** Automatizado cada **Lunes a las 03:00 AM**.  
* **Lógica Anti-duplicados:** Validación por Receipt ID (Loyverse) y Order ID (WooCommerce) antes de escribir en Excel.

### **Ⓔ MÓDULO ARTÍCULOS (Trazabilidad de Productores)**

* **Función:** Seguimiento de los \+100 pequeños productores.  
* **Lógica de Histórico (Opción B):** No se sobrescribe la información. Si el script detecta un cambio en el **Coste** o **Precio de Venta**, genera una nueva fila con la fecha actual.  
* **Objetivo:** Análisis de márgenes y control de inflación de proveedores artesanales.

## ---

**3\. MAPA DE DIRECTORIOS ACTUALIZADO**

Plaintext

C:\\\_ARCHIVOS\\TRABAJO\\Facturas\\gestion-facturas\\  
├── gmail\\                  \# Extracción de facturas (Viernes 03:00)  
├── ventas\_semana\\          \# Módulo de integración Ventas/Web (Lunes 03:00)  
│   ├── script\_barea.py     \# Motor Python 3.13  
│   └── .env                \# PROTOCOLO SEGURIDAD (Tokens y contraseñas)  
└── datos\\                  \# Bases de datos maestras  
    ├── Ventas Barea 2026.xlsx  
    │   ├── TascaRecibos / TascaItems  
    │   ├── ComesRecibos / ComesItems  
    │   └── WOOCOMMERCE     \# Histórico total de cursos y talleres  
    └── Articulos 26.xlsx  
        ├── Histórico Tasca  
        └── Histórico Comestibles

## ---

**4\. PROTOCOLO DE SEGURIDAD Y AUTOMATIZACIÓN**

### **🔒 Seguridad de Credenciales**

Se implementa un entorno aislado mediante un archivo .env que contiene:

1. **Keys de WooCommerce:** Consumer Key y Secret.  
2. **Tokens Loyverse:** Segregados por unidad de negocio.  
3. **Windows Auth:** Credenciales de usuario jaimeportatil\\jaime para permitir el despertado del sistema desde suspensión.

### **⏰ Cronograma de Tareas (Windows Task Scheduler)**

| Día | Hora | Proceso | Objetivo |
| :---- | :---- | :---- | :---- |
| **Viernes** | 03:00 | gmail\_bot.py | Descarga de facturas de proveedores. |
| **Lunes** | 03:00 | script\_barea.py | Consolidación de ventas y actualización de costes. |

## ---

**CHANGELOG (Continuación)**

### **v3.0 (06/02/2026)**

* 🛠️ **INICIO Módulo Ventas:** Integración de Loyverse (Doble Token) y WooCommerce.  
* ✅ **Definido Histórico de Artículos:** Implementada lógica de registro por cambios de precio (Opción B).  
* ✅ **Arquitectura de Seguridad:** Diseño de sistema basado en variables de entorno .env.  
* ✅ **Sincronización de Tareas:** Configurado despertado automático de Windows para lunes de madrugada.

---

**Jaime, el documento ya refleja vuestro nuevo sistema. ¿Quieres que te pase ahora el código Python para empezar las pruebas con estos módulos?**