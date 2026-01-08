# 🚀 MEJORAS v2.0 - ParsearFacturas

## ¿Qué hay de nuevo?

| Mejora | ¿Qué hace? |
|--------|------------|
| **Logger** | Guarda registro de todo lo que pasa |

---

## 🔧 Cómo usar el LOGGER

### Paso 1: Importar al inicio de tu script
```python
from src.facturas.utils import crear_logger, log_factura, log_resumen
```

### Paso 2: Crear el logger
```python
logger = crear_logger()
logger.info("Empezando procesamiento...")
```

### Paso 3: Registrar cada factura
```python
# Cuando una factura se procesa bien:
log_factura(logger, "ZUBELZU", "A-51993", 1175.20, ok=True)

# Cuando falla:
log_factura(logger, "BERNAL", "???", 0, ok=False, error="No encontré el número")
```

### Paso 4: Resumen al final
```python
log_resumen(logger, 
    procesadas_ok=25, 
    procesadas_error=3, 
    total_euros=15420.50, 
    segundos=45.3
)
```

### ¿Dónde se guardan los logs?

En la carpeta `logs/`:
