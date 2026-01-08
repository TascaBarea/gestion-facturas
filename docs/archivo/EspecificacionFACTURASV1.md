# Proyecto FACTURAS — Especificación funcional y técnica (V1)

## 1) Visión y alcance
- **Propósito**: extraer información de facturas PDF (y/o imágenes) y producir una **tabla de líneas** normalizada y un **Excel final** con hoja `Metadata`.
- **Alcance V1**: facturas multi-formato, mezcla de IVAs, descuentos y portes, duplicados, abonos y redondeo.
- **Fuera de alcance V1**: e-factura XML, SII, integración contable automática.

## 2) Glosario
- **NumeroArchivo**: dígitos iniciales del PDF (3–4).
- **Proveedor (normalizado)**: MAYÚSCULAS, sin acentos, sin puntos, SL/SA unificados.
- **Línea**: cada artículo/servicio con su tipo de IVA.
- **EsAbono**: factura rectificativa → bases negativas.

## 3) Entradas y supuestos
- **Formato**: PDFs, posible OCR.
- **Fecha**: de emisión (DD-MM-AA). Si falta → vacío + flag `FechaPendiente`.
- **Nº factura**: tal cual en el documento. Si falta → vacío + flag `NFacturaPendiente`.
- **Totales**: se validan contra suma de líneas (umbral 0,00 €).

## 4) Tabla final
Columnas y formato:
1. NumeroArchivo (XXXX/XXX)
2. Fecha (DD-MM-AA; si falta → vacío + `FechaPendiente`)
3. NºFactura (tal cual; si falta → vacío + `NFacturaPendiente`)
4. Proveedor (normalizado; `ProveedorOriginal` solo en JSON crudo)
5. Descripcion (texto línea, limpieza OCR mínima)
6. **BaseImponible** (`1234,56`, 2 decimales, sin miles/€; si se infiere → `BaseCalculada`)
7. **TipoIVA** (entero; ver conjunto permitido)
8. Observaciones (array de flags)

> **Eliminada** la columna **Categoría** de la salida. La clasificación se conserva para auditoría en `CLASIFICACION_DETALLE` con `score` fuzzy.

## 5) Reglas de cálculo
- **IVA permitido**: {0, 2, 4, 5, 7,5, 10, 21} para fechas **anteriores a 2025‑01‑01**; desde 2025: {0, 4, 10, 21}.
- **Precedencia IVA**: Línea > Resumen (validación/relleno) > Patrón proveedor > `IVA_Pendiente`.
- **Portes (regla global)**: eliminar y **prorratear** manteniendo el IVA original de cada línea; **cuadrar** al total con IVA. Excepciones documentadas por patrón.
- **Recalcular base**: si solo hay importe con IVA y se conoce TipoIVA: **Base = Importe/(1+IVA/100)**; flag `BaseCalculada`.
- **Cuadre**: umbral 0,00 €; ajuste en la línea de mayor base del tipo IVA.
- **Abonos**: bases negativas; flag `EsAbono`.

## 6) Duplicados
- **Inter‑PDF**: Proveedor+Fecha+NºFactura+ImporteTotal → conservar el PDF más reciente; otros: `DuplicadoDescartado`.
- **Alerta auxiliar**: si **NºFactura** ya existe en histórico, registrar **warning** para revisión.

## 7) Normalización de proveedor
- MAYÚSCULAS, sin acentos, sin puntos, unificar sufijos (SL/SA).
- `provider_aliases.yml` para alias (ej. FORMAGGIARTE→ZUCCA, ICATÚ→ICATU).
- Mantener `ProveedorOriginal` sólo en JSON crudo.

## 8) Salida Excel
- Un único Excel por lote con `Metadata` (periodo, nº proveedores, nº facturas/líneas, desglose IVA, incidencias).
- **TSV** solo como salida de diagnóstico bajo flag CLI (no oficial).

## 9) Pipeline
Ingesta → OCR → Parsing → Normalización → Cálculo → Cuadre → Abonos → Duplicados → Tabla → Excel → Registro.

## 10) Ordenación y primera columna
- Primera columna = `XXXX` o `XXX` sin guion.
- Orden: NumeroArchivo ascendente.

## 11) Validaciones duras
- Números deben ser numéricos.
- Fechas válidas dayfirst.
- IVA fuera conjunto permitido → `IVA_Pendiente`.

## 12) Trazabilidad
- `facturas_usadas` con motivo/protocolo.
- `CLASIFICACION_DETALLE`: registrar fuzzy score (umbral global 0,70), término elegido y candidatos.

## 13) Flags de Observaciones
- `FechaPendiente`, `NFacturaPendiente`, `IVA_Pendiente`, `EsAbono`, `DuplicadoDescartado`, `AjusteRedondeo`, `BaseCalculada`, `OCR_Requerido`.

## 14) Estándares de código
- Archivos PascalCase.
- Evitar `SettingWithCopyWarning`.
- Mensajes accionables.

## 15) Roadmap
- V1.0: parsing+normalización+Excel.
- V1.1: intra-PDF, Excel multi-año, portes test.
- V1.2: telefono_yoigo.
- V1.3: fuzzy matching con score.

