import os
import sys
import logging
import shutil

# Forzar UTF-8 en stdout/stderr (Windows cp1252 no soporta emojis)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import pandas as pd
except ImportError:
    print("ERROR: Faltan dependencias. Ejecuta: pip install -r requirements.txt")
    sys.exit(1)
import requests
from woocommerce import API
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Cargar configuración (relativo al script, no al cwd)
_script_dir = os.path.dirname(os.path.abspath(__file__))

# --- Logging -----------------------------------------------------------
_logs_dir = os.path.join(os.path.dirname(_script_dir), "outputs", "logs_ventas")
os.makedirs(_logs_dir, exist_ok=True)
_log_file = os.path.join(_logs_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

log = logging.getLogger("barea")
log.setLevel(logging.DEBUG)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

_fh = logging.FileHandler(_log_file, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
log.addHandler(_fh)

_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(_ch)
# ------------------------------------------------------------------------

_env_path = os.path.join(_script_dir, ".env")
_env_txt_path = os.path.join(_script_dir, ".env.txt")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
elif os.path.exists(_env_txt_path):
    load_dotenv(_env_txt_path)
else:
    log.error("No encuentro el archivo .env")

PATH_VENTAS = os.getenv("PATH_VENTAS")
PATH_ARTICULOS = os.getenv("PATH_ARTICULOS")
PATH_HISTORICO = os.path.join(os.path.dirname(_script_dir), "datos", "Ventas Barea Historico.xlsx")

# Nombres de tienda por token
STORE_NAMES = {"LOY_TOKEN_TASCA": "Tasca", "LOY_TOKEN_COMES": "Comes"}

# Destinatarios email semanal (fácil de ampliar)
EMAILS_RESUMEN_SEMANAL = ["jaimefermo@gmail.com"]

# Gmail OAuth (reutiliza credenciales del módulo gmail/)
_GMAIL_DIR = os.path.join(os.path.dirname(_script_dir), "gmail")
_GMAIL_TOKEN = os.path.join(_GMAIL_DIR, "token.json")

# Backup de Excel antes de escribir
_BACKUP_DIR = os.path.join(os.path.dirname(_script_dir), "datos", "backups")
_backed_up = set()  # archivos ya respaldados en esta ejecución


def calcular_semana_anterior():
    """
    Calcula lunes y domingo de la semana anterior.
    Ejemplo: ejecutando el lunes 23/02, devuelve lunes 16/02 y domingo 22/02.
    """
    hoy = datetime.now().date()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    lunes = lunes_actual - timedelta(days=7)
    domingo = lunes_actual - timedelta(days=1)
    return lunes, domingo


def get_wc_api():
    return API(
        url=os.getenv("WC_URL"),
        consumer_key=os.getenv("WC_KEY"),
        consumer_secret=os.getenv("WC_SECRET"),
        version="wc/v3",
        timeout=30
    )


def fetch_loyverse(token, endpoint, created_at_min=None, created_at_max=None):
    """
    Descarga datos de Loyverse con paginación automática por cursor.
    Soporta filtros created_at_min y created_at_max (v1.0).
    """
    headers = {"Authorization": f"Bearer {token}"}
    all_results = []
    cursor = None
    page = 0

    api_version = "v1.0"
    base_url = f"https://api.loyverse.com/{api_version}/{endpoint}"

    while True:
        params = {"limit": 250}
        if created_at_min and api_version == "v1.0":
            params["created_at_min"] = created_at_min
        if created_at_max and api_version == "v1.0":
            params["created_at_max"] = created_at_max
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)

            if response.status_code in (401, 403, 404) and api_version == "v1.0" and page == 0:
                api_version = "v2"
                base_url = f"https://api.loyverse.com/{api_version}/{endpoint}"
                response = requests.get(base_url, headers=headers, timeout=30)
                if response.status_code != 200:
                    break
            elif response.status_code != 200:
                log.warning("API %s: HTTP %s", endpoint, response.status_code)
                break

            data = response.json()
            key = endpoint.split('/')[-1]
            items = data.get(key, [])

            if not items:
                break

            all_results.extend(items)
            page += 1

            if api_version == "v2":
                break

            cursor = data.get("cursor")
            if not cursor:
                break

        except Exception as e:
            log.warning("Error API %s: %s", endpoint, e)
            break

    return all_results


def fetch_lookup_data(token):
    """
    Descarga datos de referencia de Loyverse para resolver IDs a nombres:
    stores, pos_devices, employees, customers, categories, payment_types, items.
    """
    log.info("  Cargando datos de referencia...")

    stores = {}
    for s in fetch_loyverse(token, "stores"):
        stores[s['id']] = s.get('name', '')

    pos_devices = {}
    for d in fetch_loyverse(token, "pos_devices"):
        pos_devices[d['id']] = d.get('name', '')

    employees = {}
    for e in fetch_loyverse(token, "employees"):
        employees[e['id']] = e.get('name', '')

    categories = {}
    for c in fetch_loyverse(token, "categories"):
        categories[c['id']] = c.get('name', '')

    customers = {}
    for c in fetch_loyverse(token, "customers"):
        email = c.get('email', '') or ''
        phone = c.get('phone_number', '') or ''
        contacts = ', '.join(filter(None, [email, phone]))
        customers[c['id']] = {'name': c.get('name', ''), 'contacts': contacts}

    payment_types = {}
    for p in fetch_loyverse(token, "payment_types"):
        payment_types[p['id']] = p.get('name', '')

    # Items: variant_id → {category, cost}
    items_by_variant = {}
    for item in fetch_loyverse(token, "items"):
        cat_name = categories.get(item.get('category_id', ''), '')
        for v in item.get('variants', []):
            vid = v.get('variant_id') or v.get('id', '')
            items_by_variant[vid] = {
                'category': cat_name,
                'cost': v.get('cost', 0) or 0,
            }

    log.info(f"     {len(stores)} tiendas, {len(pos_devices)} TPVs, "
          f"{len(employees)} empleados, {len(customers)} clientes, "
          f"{len(categories)} categorías, {len(items_by_variant)} variantes")

    return {
        'stores': stores,
        'pos_devices': pos_devices,
        'employees': employees,
        'customers': customers,
        'payment_types': payment_types,
        'items_by_variant': items_by_variant,
        'categories': categories,
    }


def resolve(lookup_dict, key, default=''):
    """Busca un ID en un dict de lookup. Devuelve default si no existe."""
    if not key:
        return default
    val = lookup_dict.get(key, default)
    if isinstance(val, dict):
        return val.get('name', default)
    return val


def parse_fecha(fecha_str):
    """Parsea fecha ISO de la API a datetime."""
    if not fecha_str:
        return None
    try:
        return datetime.strptime(str(fecha_str)[:19], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return fecha_str


def procesar_recibos(receipts, lookups):
    """
    Convierte recibos de la API a dos DataFrames:
    - df_recibos: resumen por recibo (19 columnas)
    - df_items: detalle por item (22 + unique_id)
    """
    filas_recibos = []
    filas_items = []

    for r in receipts:
        fecha = parse_fecha(r.get('receipt_date') or r.get('created_at'))
        r_num = r.get('receipt_number', '')
        r_type = 'Venta' if r.get('receipt_type') == 'SALE' else 'Reembolso'

        # Resolver IDs
        tienda = resolve(lookups['stores'], r.get('store_id'))
        tpv = resolve(lookups['pos_devices'], r.get('pos_device_id'))
        cajero = resolve(lookups['employees'], r.get('employee_id'))
        cust_id = r.get('customer_id')
        cust_data = lookups['customers'].get(cust_id, {}) if cust_id else {}
        cliente = cust_data.get('name', '')
        contactos = cust_data.get('contacts', '')

        # Totales del recibo (total_money ya es post-descuento)
        total = float(r.get('total_money', 0) or 0)
        tax = float(r.get('total_tax', 0) or 0)
        disc = float(r.get('total_discount', 0) or 0)
        tip = float(r.get('tip', 0) or 0)

        # Tipo de pago
        tipo_pago = ''
        payments = r.get('payments', [])
        if isinstance(payments, list) and payments:
            pt_id = payments[0].get('payment_type_id', '')
            tipo_pago = resolve(lookups['payment_types'], pt_id, pt_id)

        # Estado
        estado = 'Cerrado'
        if r.get('cancelled_at'):
            estado = 'Cancelado'

        # Costo y beneficio a nivel recibo (suma de line items)
        costo_total = 0.0
        descripcion_parts = []
        nota_recibo = r.get('note', '') or ''

        # --- Procesar line items ---
        for line_idx, item in enumerate(r.get('line_items', [])):
            variant_id = item.get('variant_id', '')
            variant_info = lookups['items_by_variant'].get(variant_id, {})

            categoria = variant_info.get('category', '')
            cost_unit = item.get('cost') or variant_info.get('cost', 0) or 0
            qty = item.get('quantity', 0)
            item_cost = float(cost_unit) * float(qty) if cost_unit else 0

            brutas = float(item.get('gross_total_money', 0) or 0)
            netas = float(item.get('total_money', 0) or 0)
            desc_item = float(item.get('total_discount', 0) or 0)
            tax_item = float(item.get('total_tax', 0) or 0)
            beneficio = round(netas - item_cost, 2)

            costo_total += item_cost

            item_name = item.get('item_name', '')
            # Descripción para recibo
            qty_str = f"{qty:g}" if isinstance(qty, (int, float)) else str(qty)
            descripcion_parts.append(f"{qty_str} x {item_name}")

            nota_item = item.get('line_note', '') or item.get('note', '') or ''

            filas_items.append({
                'Fecha': fecha,
                'Número de recibo': r_num,
                'Tipo de recibo': r_type,
                'Categoria': categoria,
                'REF': item.get('sku', ''),
                'Artículo': item_name,
                'Variante': item.get('variant_name', '') or '',
                'Modificadores aplicados': '',
                'Cantidad': qty,
                'Ventas brutas': round(brutas, 2),
                'Descuentos': round(desc_item, 2),
                'Ventas netas': round(netas, 2),
                'Costo de los bienes': round(item_cost, 2),
                'Beneficio bruto': beneficio,
                'Impuestos': round(tax_item, 2),
                'TPV': tpv,
                'Tienda': tienda,
                'Nombre del cajero': cajero,
                'Nombre del cliente': cliente,
                'Contactos del cliente': contactos,
                'Comentario': nota_item or nota_recibo,
                'Estado': estado,
                'unique_id': f"{r_num}_{line_idx}",
            })

        beneficio_recibo = round(total - costo_total, 2)
        descripcion = ', '.join(descripcion_parts)

        filas_recibos.append({
            'Fecha': fecha,
            'Número de recibo': r_num,
            'Tipo de recibo': r_type,
            'Ventas brutas': round(total + disc, 2),
            'Descuentos': round(disc, 2),
            'Ventas netas': round(total, 2),
            'Impuestos': round(tax, 2),
            'Propinas': round(tip, 2),
            'Total recaudado': round(total, 2),
            'Costo de los bienes': round(costo_total, 2),
            'Beneficio bruto': beneficio_recibo,
            'Tipo de pago': tipo_pago,
            'Descripción': descripcion,
            'TPV': tpv,
            'Tienda': tienda,
            'Nombre del cajero': cajero,
            'Nombre del cliente': cliente,
            'Contactos del cliente': contactos,
            'Estado': estado,
        })

    df_recibos = pd.DataFrame(filas_recibos)
    df_items = pd.DataFrame(filas_items)
    return df_recibos, df_items


# Mapeo para normalizar columnas de datos antiguos
_COL_RENAMES = {
    'Numero de recibo': 'Número de recibo',
    'Articulo': 'Artículo',
    'Descripcion': 'Descripción',
}


def _verificar_archivo_no_abierto(ruta):
    """Comprueba que el archivo Excel no esté abierto. Devuelve True si está libre."""
    if not os.path.exists(ruta):
        return True
    try:
        with open(ruta, 'a'):
            return True
    except PermissionError:
        log.error("El archivo '%s' está abierto en Excel. Ciérralo y reintenta.",
                  os.path.basename(ruta))
        return False


def _backup_excel(path):
    """Crea backup del Excel antes de la primera escritura de esta ejecución."""
    if path in _backed_up or not os.path.exists(path):
        return
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    nombre = os.path.basename(path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(_BACKUP_DIR, f"{os.path.splitext(nombre)[0]}_{ts}.xlsx")
    try:
        shutil.copy2(path, destino)
        _backed_up.add(path)
        log.debug("Backup: %s", destino)
    except Exception as e:
        log.warning("No se pudo crear backup de %s: %s", nombre, e)


def save_to_excel(df, path, sheet_name, unique_col=None):
    """Guarda DataFrame en Excel, acumulando sin duplicados."""
    if df.empty:
        return

    if not _verificar_archivo_no_abierto(path):
        log.error("ABORTANDO escritura de %s — archivo bloqueado.", sheet_name)
        return

    _backup_excel(path)

    if not os.path.exists(path):
        df.to_excel(path, sheet_name=sheet_name, index=False)
        return

    # Leer datos existentes ANTES de abrir el writer (evita perderlos si falla)
    existing_df = None
    try:
        existing_df = pd.read_excel(path, sheet_name=sheet_name)
        existing_df.rename(columns=_COL_RENAMES, inplace=True)
    except ValueError:
        pass  # Hoja no existe todavia, se creara nueva
    except Exception as e:
        log.error("Error leyendo %s de %s: %s", sheet_name, path, e)
        log.error("ABORTANDO escritura para no perder datos existentes.")
        return

    if existing_df is not None and not existing_df.empty:
        if unique_col and unique_col in df.columns and unique_col in existing_df.columns:
            df[unique_col] = df[unique_col].astype(str)
            existing_df[unique_col] = existing_df[unique_col].astype(str)
            df = df[~df[unique_col].isin(existing_df[unique_col])]
        combined_df = pd.concat([existing_df, df], ignore_index=True)
    else:
        combined_df = df

    try:
        with pd.ExcelWriter(path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception as e:
        log.error("Error guardando %s: %s", sheet_name, e)


def _strip_html(text):
    """Elimina tags HTML de un string."""
    import re as _re
    if not text:
        return ''
    return _re.sub(r'<[^>]+>', '', str(text)).strip()


def update_articles_history(new_items_raw, path, sheet_name, categories=None, taxes_by_id=None):
    """
    Actualiza el Excel de artículos con gestión completa:
    - ALTAS: añade artículos nuevos de Loyverse
    - BAJAS: marca artículos eliminados (ESTADO=BAJA + FECHA_BAJA)
    - PRECIOS: actualiza Coste/Precio, registra cambios en Historial_Precios
    """
    import re as _re

    if not os.path.exists(path):
        log.warning("No existe %s, saltando artículos", path)
        return

    try:
        old_df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception as e:
        log.warning("No se pudo leer pestaña '%s': %s", sheet_name, e)
        return

    if 'REF' not in old_df.columns:
        log.warning("Pestaña '%s' no tiene columna REF", sheet_name)
        return

    # Buscar columnas dinámicamente
    col_precio = next((c for c in old_df.columns if c.startswith('Precio')), None)
    col_disponible = next((c for c in old_df.columns if c.startswith('Disponibles')), None)
    col_inventario = next((c for c in old_df.columns if c.startswith('En inventario')), None)
    col_existencias = next((c for c in old_df.columns if c.startswith('Existencias')), None)

    if not col_precio:
        log.warning("No se encontró columna 'Precio [...]' en '%s'", sheet_name)
        return

    # Añadir ESTADO y FECHA_BAJA si no existen
    if 'ESTADO' not in old_df.columns:
        old_df['ESTADO'] = ''
    if 'FECHA_BAJA' not in old_df.columns:
        old_df['FECHA_BAJA'] = ''

    # Columnas de impuestos: extraer tasa de cada columna
    tax_cols = [c for c in old_df.columns if c.startswith('impuesto')]
    tax_col_rates = {}
    for tc in tax_cols:
        m = _re.search(r'\((\d+)%\)', tc)
        if m:
            tax_col_rates[int(m.group(1))] = tc

    categories = categories or {}
    taxes_by_id = taxes_by_id or {}

    # Construir dict de artículos API por SKU
    api_items = {}
    for item in new_items_raw:
        cat_name = categories.get(item.get('category_id', ''), '')
        for v in item.get('variants', []):
            sku = v.get('sku', '')
            if sku:
                # Tasas IVA del artículo
                item_tax_rates = set()
                for tid in (item.get('tax_ids') or []):
                    tax_info = taxes_by_id.get(tid)
                    if tax_info:
                        rate = tax_info.get('rate', 0)
                        item_tax_rates.add(int(rate) if rate >= 1 else int(rate * 100))

                api_items[str(sku)] = {
                    'cost': v.get('cost'),
                    'price': v.get('default_price'),
                    'handle': item.get('handle', ''),
                    'name': item.get('item_name', ''),
                    'category': cat_name,
                    'description': _strip_html(item.get('description', '')),
                    'sold_by_weight': item.get('sold_by_weight', False),
                    'track_stock': item.get('track_stock', False),
                    'barcode': v.get('barcode', '') or '',
                    'option1_name': item.get('option1_name', '') or '',
                    'option1_value': v.get('option1_value', '') or '',
                    'option2_name': item.get('option2_name', '') or '',
                    'option2_value': v.get('option2_value', '') or '',
                    'option3_name': item.get('option3_name', '') or '',
                    'option3_value': v.get('option3_value', '') or '',
                    'tax_rates': item_tax_rates,
                }

    # Seguridad: si la API devuelve muy pocos artículos, no marcar BAJAS
    refs_excel = set()
    for _, row in old_df.iterrows():
        ref = str(row.get('REF', '')).strip()
        if ref:
            refs_excel.add(ref)

    marcar_bajas = len(api_items) >= len(refs_excel) * 0.5

    # Contadores
    hoy = datetime.now().strftime('%Y-%m-%d')
    cambios_precio = []
    altas = 0
    bajas = 0
    precios_actualizados = 0
    subidas_coste = 0
    bajadas_coste = 0
    subidas_pvp = 0
    bajadas_pvp = 0
    reactivados = 0

    # === 1. ACTUALIZAR existentes + detectar BAJAS ===
    for idx, row in old_df.iterrows():
        ref = str(row.get('REF', '')).strip()
        if not ref:
            continue
        estado_actual = str(row.get('ESTADO', '') or '').strip()

        if ref in api_items:
            api = api_items[ref]

            # Reactivar si era BAJA
            if estado_actual == 'BAJA':
                old_df.at[idx, 'ESTADO'] = ''
                old_df.at[idx, 'FECHA_BAJA'] = ''
                reactivados += 1

            # Comprobar cambios de precio (convertir a float por si Excel tiene strings)
            coste_old = row.get('Coste')
            precio_old = row.get(col_precio)
            try:
                coste_old = float(coste_old) if pd.notna(coste_old) else None
            except (ValueError, TypeError):
                coste_old = None
            try:
                precio_old = float(precio_old) if pd.notna(precio_old) else None
            except (ValueError, TypeError):
                precio_old = None

            if api.get('cost') is not None and api['cost'] != coste_old:
                old_df.at[idx, 'Coste'] = api['cost']
                if coste_old is not None and coste_old > 0:
                    var_pct = round((api['cost'] - coste_old) / coste_old * 100, 1)
                    cambios_precio.append({
                        'Fecha': hoy, 'REF': ref,
                        'Nombre': row.get('Nombre', ''), 'Tienda': sheet_name,
                        'Campo': 'Coste', 'Anterior': round(coste_old, 4),
                        'Nuevo': round(api['cost'], 4), 'Variacion%': var_pct,
                    })
                    if api['cost'] > coste_old:
                        subidas_coste += 1
                    else:
                        bajadas_coste += 1
                precios_actualizados += 1

            if api.get('price') is not None and api['price'] != precio_old:
                old_df.at[idx, col_precio] = api['price']
                if precio_old is not None and precio_old > 0:
                    var_pct = round((api['price'] - precio_old) / precio_old * 100, 1)
                    cambios_precio.append({
                        'Fecha': hoy, 'REF': ref,
                        'Nombre': row.get('Nombre', ''), 'Tienda': sheet_name,
                        'Campo': 'Precio', 'Anterior': round(precio_old, 2),
                        'Nuevo': round(api['price'], 2), 'Variacion%': var_pct,
                    })
                    if api['price'] > precio_old:
                        subidas_pvp += 1
                    else:
                        bajadas_pvp += 1
                precios_actualizados += 1
        else:
            # No está en API → BAJA (si no lo estaba ya)
            if marcar_bajas and estado_actual != 'BAJA':
                old_df.at[idx, 'ESTADO'] = 'BAJA'
                old_df.at[idx, 'FECHA_BAJA'] = hoy
                bajas += 1

    # === 2. ALTAS: artículos nuevos ===
    new_rows = []
    for sku, api in api_items.items():
        if sku not in refs_excel:
            row_data = {
                'Handle': api['handle'],
                'REF': sku,
                'Nombre': api['name'],
                'Categoria': api['category'],
                'Vendido por peso': 'Y' if api['sold_by_weight'] else 'N',
                'Coste': api['cost'],
                'Codigo de barras': api['barcode'],
                'REF del componente': None,
                'Cantidad del componente': None,
                'Seguir el Inventario': 'Y' if api['track_stock'] else 'N',
                col_precio: api['price'],
                'ESTADO': '',
                'FECHA_BAJA': '',
            }

            # Columna Descripción (buscar nombre exacto en DataFrame)
            col_desc = next((c for c in old_df.columns if 'escripci' in c), None)
            if col_desc:
                row_data[col_desc] = api['description']

            # Opciones
            for i in range(1, 4):
                col_on = next((c for c in old_df.columns if c.startswith(f'Opci') and f'{i} nombre' in c), None)
                col_ov = next((c for c in old_df.columns if c.startswith(f'Opci') and f'{i} valor' in c), None)
                if col_on:
                    row_data[col_on] = api.get(f'option{i}_name', '')
                if col_ov:
                    row_data[col_ov] = api.get(f'option{i}_value', '')

            if col_disponible:
                row_data[col_disponible] = 'Y'
            if col_inventario:
                row_data[col_inventario] = None
            if col_existencias:
                row_data[col_existencias] = None

            # Impuestos
            for rate, col_name in tax_col_rates.items():
                row_data[col_name] = 'Y' if rate in api['tax_rates'] else 'N'

            new_rows.append(row_data)
            altas += 1

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        old_df = pd.concat([old_df, new_df], ignore_index=True)

    # === 3. GUARDAR ===
    hubo_cambios = altas > 0 or bajas > 0 or precios_actualizados > 0 or reactivados > 0

    # Leer historial existente antes de abrir el writer
    df_old_hist = pd.DataFrame()
    if cambios_precio:
        try:
            df_old_hist = pd.read_excel(path, sheet_name='Historial_Precios')
        except Exception:
            pass

    if hubo_cambios or cambios_precio:
        with pd.ExcelWriter(path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            if hubo_cambios:
                old_df.to_excel(writer, sheet_name=sheet_name, index=False)
            if cambios_precio:
                df_hist = pd.concat([df_old_hist, pd.DataFrame(cambios_precio)], ignore_index=True)
                df_hist.to_excel(writer, sheet_name='Historial_Precios', index=False)

    # === 4. RESUMEN CONSOLA ===
    parts = []
    if altas:
        parts.append(f"{altas} altas")
    if bajas:
        parts.append(f"{bajas} bajas")
    if reactivados:
        parts.append(f"{reactivados} reactivados")
    if precios_actualizados:
        det = []
        if subidas_coste:
            det.append(f"{subidas_coste} subidas coste")
        if bajadas_coste:
            det.append(f"{bajadas_coste} bajadas coste")
        if subidas_pvp:
            det.append(f"{subidas_pvp} subidas PVP")
        if bajadas_pvp:
            det.append(f"{bajadas_pvp} bajadas PVP")
        parts.append(f"{precios_actualizados} precios ({', '.join(det)})")

    if parts:
        log.info(f"  {sheet_name}: {', '.join(parts)}")
    else:
        log.info("  %s: sin cambios", sheet_name)


def check_iva_anomalies(path, sheet_name):
    """
    Detecta anomalías de IVA en artículos tras la actualización semanal:
    - Artículos con varios tipos de IVA marcados simultáneamente
    - IVA al 0% (caso excepcional, reportar siempre)
    - IVA al 21% en categorías donde no debería (solo permitido en
      VINOS, BODEGA, LICORES, VERMÚS, CACHARRERÍA, BAZAR, EXPERIENCIAS)
    """
    import re as _re

    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception:
        return

    tax_cols = [c for c in df.columns if c.startswith('impuesto')]
    if not tax_cols:
        return

    # Extraer tasa de cada columna IVA
    tax_col_rates = {}
    for tc in tax_cols:
        m = _re.search(r'\((\d+)%\)', tc)
        if m:
            tax_col_rates[tc] = int(m.group(1))

    # Keywords de categorías permitidas con 21%
    CATS_21_KEYWORDS = ['VINO', 'BODEGA', 'LICOR', 'VERM',
                        'CACHARR', 'BAZAR', 'EXPERIENCIA']

    anomalias = []

    for _, row in df.iterrows():
        ref = str(row.get('REF', '')).strip()
        nombre = str(row.get('Nombre', ''))[:50]
        categoria = str(row.get('Categoria', '') or '')
        estado = str(row.get('ESTADO', '') or '').strip()

        if estado == 'BAJA' or not ref:
            continue

        # IVAs activos
        ivas = [tax_col_rates[tc] for tc in tax_cols
                if row.get(tc) == 'Y' and tc in tax_col_rates]

        # Multi-IVA
        if len(ivas) > 1:
            anomalias.append(f"MULTI-IVA: {ref} {nombre} - IVAs: {ivas}")

        # IVA 0% (único)
        if ivas == [0]:
            anomalias.append(f"IVA 0%: {ref} {nombre} ({categoria})")

        # IVA 21% fuera de categorías permitidas
        if 21 in ivas and len(ivas) == 1:
            cat_upper = categoria.upper()
            if not any(kw in cat_upper for kw in CATS_21_KEYWORDS):
                anomalias.append(
                    f"IVA 21% SOSPECHOSO: {ref} {nombre} ({categoria})")

    if anomalias:
        log.warning("%s: %d anomalías IVA:", sheet_name, len(anomalias))
        for a in anomalias:
            log.warning("    - %s", a)
    else:
        log.info("  %s: IVA sin anomalías", sheet_name)


def _to_float(val):
    """Convierte a float, soportando formato español ('3,51') y NaN."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return 0.0
    return float(s.replace(",", "."))


def _fmt_eur(n):
    """Formatea número como moneda española: x.xxx,xx €"""
    s = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if n < 0 else ''}{s} €"


def _fmt_num(n):
    """Formatea entero con separador de miles."""
    return f"{int(n):,}".replace(",", ".")


def _pct_var(actual, anterior):
    """Calcula variación porcentual. Devuelve None si anterior es 0."""
    if not anterior or anterior == 0:
        return None
    return (actual - anterior) / anterior * 100


def _var_html(pct):
    """Genera HTML de variación con flecha y color."""
    if pct is None:
        return '<span style="color:#999">—</span>'
    color = "#155724" if pct >= 0 else "#721C24"
    bg = "#D4EDDA" if pct >= 0 else "#F8D7DA"
    arrow = "▲" if pct >= 0 else "▼"
    return (f'<span style="color:{color};background:{bg};padding:2px 6px;'
            f'border-radius:3px;font-size:12px">{arrow} {abs(pct):.1f}%</span>')


def _cargar_items_historico(tienda):
    """
    Carga todos los Items de una tienda (Tasca o Comestibles) de todos los años.
    Devuelve un único DataFrame con columnas normalizadas a float.
    """
    hojas = []

    # Histórico (2023, 2024, 2025)
    if os.path.exists(PATH_HISTORICO):
        xl = pd.ExcelFile(PATH_HISTORICO)
        prefijo = "Tasca" if tienda == "Tasca" else "Comestibles"
        for s in xl.sheet_names:
            if s.startswith(f"{prefijo}Item"):
                df = pd.read_excel(PATH_HISTORICO, sheet_name=s)
                hojas.append(df)

    # Año actual
    if os.path.exists(PATH_VENTAS):
        sheet_actual = f"{tienda}Items" if tienda == "Tasca" else "ComesItems"
        try:
            df = pd.read_excel(PATH_VENTAS, sheet_name=sheet_actual)
            hojas.append(df)
        except Exception:
            pass

    if not hojas:
        return pd.DataFrame()

    df_all = pd.concat(hojas, ignore_index=True)

    # Normalizar columnas numéricas (formato español en datos 2024)
    for col in ['Ventas netas', 'Cantidad', 'Ventas brutas', 'Descuentos',
                'Costo de los bienes', 'Beneficio bruto', 'Impuestos']:
        if col in df_all.columns:
            df_all[col] = df_all[col].apply(_to_float)

    # Asegurar Fecha como datetime
    df_all['Fecha'] = pd.to_datetime(df_all['Fecha'], errors='coerce')

    return df_all


def _cargar_recibos_historico(tienda):
    """Carga todos los Recibos de una tienda de todos los años."""
    hojas = []

    if os.path.exists(PATH_HISTORICO):
        xl = pd.ExcelFile(PATH_HISTORICO)
        prefijo = "Tasca" if tienda == "Tasca" else "Comestibles"
        for s in xl.sheet_names:
            if s.startswith(f"{prefijo}Recibos"):
                df = pd.read_excel(PATH_HISTORICO, sheet_name=s)
                hojas.append(df)

    if os.path.exists(PATH_VENTAS):
        sheet_actual = f"{tienda}Recibos" if tienda == "Tasca" else "ComesRecibos"
        try:
            df = pd.read_excel(PATH_VENTAS, sheet_name=sheet_actual)
            hojas.append(df)
        except Exception:
            pass

    if not hojas:
        return pd.DataFrame()

    df_all = pd.concat(hojas, ignore_index=True)
    for col in ['Ventas netas', 'Ventas brutas', 'Descuentos', 'Total recaudado',
                'Costo de los bienes', 'Beneficio bruto', 'Impuestos']:
        if col in df_all.columns:
            df_all[col] = df_all[col].apply(_to_float)
    df_all['Fecha'] = pd.to_datetime(df_all['Fecha'], errors='coerce')
    return df_all


def _filtrar_semana(df, lunes, domingo):
    """Filtra DataFrame por rango de fechas (lunes a domingo)."""
    mask = (df['Fecha'].dt.date >= lunes) & (df['Fecha'].dt.date <= domingo)
    return df[mask]


def _filtrar_ytd(df, hasta_fecha):
    """Filtra desde 1 de enero del año de hasta_fecha hasta hasta_fecha inclusive."""
    year = hasta_fecha.year
    inicio = datetime(year, 1, 1).date()
    mask = (df['Fecha'].dt.date >= inicio) & (df['Fecha'].dt.date <= hasta_fecha)
    return df[mask]


def _semana_equivalente_año_anterior(lunes, domingo):
    """Calcula la semana equivalente del año anterior (misma semana ISO)."""
    iso_year, iso_week, _ = lunes.isocalendar()
    from datetime import date
    # Primer jueves del año anterior determina semana 1
    jan4 = date(iso_year - 1, 1, 4)
    start_week1 = jan4 - timedelta(days=jan4.weekday())
    lunes_ant = start_week1 + timedelta(weeks=iso_week - 1)
    domingo_ant = lunes_ant + timedelta(days=6)
    return lunes_ant, domingo_ant


def _calcular_resumen_tienda(tienda, lunes, domingo):
    """
    Calcula resumen completo para una tienda:
    - Semana actual vs semana anterior vs misma semana año anterior
    - YTD actual vs YTD año anterior
    - Top 10 productos por facturación y por unidades
    """
    df_items = _cargar_items_historico(tienda)
    df_recibos = _cargar_recibos_historico(tienda)

    if df_items.empty or df_recibos.empty:
        return None

    # Semana actual
    items_sem = _filtrar_semana(df_items, lunes, domingo)
    recibos_sem = _filtrar_semana(df_recibos, lunes, domingo)

    # Semana anterior
    lunes_prev = lunes - timedelta(days=7)
    domingo_prev = lunes - timedelta(days=1)
    items_prev = _filtrar_semana(df_items, lunes_prev, domingo_prev)
    recibos_prev = _filtrar_semana(df_recibos, lunes_prev, domingo_prev)

    # Misma semana año anterior
    lunes_ya, domingo_ya = _semana_equivalente_año_anterior(lunes, domingo)
    items_ya = _filtrar_semana(df_items, lunes_ya, domingo_ya)
    recibos_ya = _filtrar_semana(df_recibos, lunes_ya, domingo_ya)

    # YTD actual (hasta domingo de la semana procesada)
    items_ytd = _filtrar_ytd(df_items, domingo)
    recibos_ytd = _filtrar_ytd(df_recibos, domingo)

    # YTD año anterior (mismo rango)
    domingo_ya_ytd = domingo.replace(year=domingo.year - 1)
    items_ytd_ya = _filtrar_ytd(df_items, domingo_ya_ytd)
    recibos_ytd_ya = _filtrar_ytd(df_recibos, domingo_ya_ytd)

    def kpis(items_df, recibos_df):
        ventas = items_df['Ventas netas'].sum() if not items_df.empty else 0
        tickets = recibos_df['Número de recibo'].nunique() if not recibos_df.empty else 0
        ticket_medio = ventas / tickets if tickets > 0 else 0
        return {'ventas': ventas, 'tickets': tickets, 'ticket_medio': ticket_medio}

    sem = kpis(items_sem, recibos_sem)
    prev = kpis(items_prev, recibos_prev)
    ya = kpis(items_ya, recibos_ya)
    ytd = kpis(items_ytd, recibos_ytd)
    ytd_ya = kpis(items_ytd_ya, recibos_ytd_ya)

    # Top 10 por facturación
    top_eur = pd.DataFrame()
    if not items_sem.empty:
        top_eur = (items_sem.groupby('Artículo')
                   .agg(ventas=('Ventas netas', 'sum'), cantidad=('Cantidad', 'sum'))
                   .sort_values('ventas', ascending=False)
                   .head(10))
        # Añadir variación vs semana anterior y año anterior
        if not items_prev.empty:
            prev_grp = items_prev.groupby('Artículo')['Ventas netas'].sum()
            top_eur['ventas_prev'] = top_eur.index.map(lambda x: prev_grp.get(x, 0))
        else:
            top_eur['ventas_prev'] = 0
        if not items_ya.empty:
            ya_grp = items_ya.groupby('Artículo')['Ventas netas'].sum()
            top_eur['ventas_ya'] = top_eur.index.map(lambda x: ya_grp.get(x, 0))
        else:
            top_eur['ventas_ya'] = 0

    # Top 10 por unidades
    top_uds = pd.DataFrame()
    if not items_sem.empty:
        top_uds = (items_sem.groupby('Artículo')
                   .agg(cantidad=('Cantidad', 'sum'), ventas=('Ventas netas', 'sum'))
                   .sort_values('cantidad', ascending=False)
                   .head(10))
        if not items_prev.empty:
            prev_grp_q = items_prev.groupby('Artículo')['Cantidad'].sum()
            top_uds['cantidad_prev'] = top_uds.index.map(lambda x: prev_grp_q.get(x, 0))
        else:
            top_uds['cantidad_prev'] = 0
        if not items_ya.empty:
            ya_grp_q = items_ya.groupby('Artículo')['Cantidad'].sum()
            top_uds['cantidad_ya'] = top_uds.index.map(lambda x: ya_grp_q.get(x, 0))
        else:
            top_uds['cantidad_ya'] = 0

    # WooCommerce
    wc_ventas = 0
    wc_pedidos = 0
    if tienda == "Comes" and os.path.exists(PATH_VENTAS):
        try:
            df_wc = pd.read_excel(PATH_VENTAS, sheet_name="WOOCOMMERCE")
            if 'date_created' in df_wc.columns:
                df_wc['Fecha'] = pd.to_datetime(df_wc['date_created'], errors='coerce')
                wc_sem = _filtrar_semana(df_wc, lunes, domingo)
                wc_pedidos = len(wc_sem)
                if 'total' in df_wc.columns:
                    wc_ventas = wc_sem['total'].apply(_to_float).sum()
        except Exception:
            pass

    return {
        'sem': sem, 'prev': prev, 'ya': ya,
        'ytd': ytd, 'ytd_ya': ytd_ya,
        'top_eur': top_eur, 'top_uds': top_uds,
        'lunes_prev': lunes_prev, 'domingo_prev': domingo_prev,
        'lunes_ya': lunes_ya, 'domingo_ya': domingo_ya,
        'wc_ventas': wc_ventas, 'wc_pedidos': wc_pedidos,
    }


def _generar_html_email(lunes, domingo, datos_tasca, datos_comes):
    """Genera el HTML del email de resumen semanal."""

    def _seccion_kpis(titulo, color, d):
        """Genera HTML de KPIs para una tienda."""
        if d is None:
            return f'<h2 style="color:{color}">{titulo}</h2><p>Sin datos esta semana</p>'

        sem, prev, ya = d['sem'], d['prev'], d['ya']
        ytd, ytd_ya = d['ytd'], d['ytd_ya']

        html = f'''
        <h2 style="color:{color};border-bottom:2px solid {color};padding-bottom:5px;margin-top:25px">
            {titulo}
        </h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:15px">
            <tr style="background:#F7F8FA">
                <th style="text-align:left;padding:8px;border:1px solid #DDD;width:25%"></th>
                <th style="text-align:right;padding:8px;border:1px solid #DDD;width:25%">Esta semana</th>
                <th style="text-align:center;padding:8px;border:1px solid #DDD;width:25%">vs Sem. anterior</th>
                <th style="text-align:center;padding:8px;border:1px solid #DDD;width:25%">vs Año anterior</th>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Ventas netas</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-size:16px;font-weight:bold">{_fmt_eur(sem['ventas'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['ventas'], prev['ventas']))}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['ventas'], ya['ventas']))}</td>
            </tr>
            <tr style="background:#F7F8FA">
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Tickets</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-size:16px;font-weight:bold">{_fmt_num(sem['tickets'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['tickets'], prev['tickets']))}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['tickets'], ya['tickets']))}</td>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Ticket medio</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-size:16px;font-weight:bold">{_fmt_eur(sem['ticket_medio'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['ticket_medio'], prev['ticket_medio']))}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(sem['ticket_medio'], ya['ticket_medio']))}</td>
            </tr>
        </table>

        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
            <tr style="background:{color}20">
                <th style="text-align:left;padding:8px;border:1px solid #DDD;width:22%">YTD {domingo.year}</th>
                <th style="text-align:right;padding:8px;border:1px solid #DDD;width:26%">Acumulado</th>
                <th style="text-align:right;padding:8px;border:1px solid #DDD;width:26%">{domingo.year - 1}</th>
                <th style="text-align:center;padding:8px;border:1px solid #DDD;width:26%">vs YTD {domingo.year - 1}</th>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Ventas netas</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-weight:bold">{_fmt_eur(ytd['ventas'])}</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD">{_fmt_eur(ytd_ya['ventas'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(ytd['ventas'], ytd_ya['ventas']))}</td>
            </tr>
            <tr style="background:#F7F8FA">
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Tickets</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-weight:bold">{_fmt_num(ytd['tickets'])}</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD">{_fmt_num(ytd_ya['tickets'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(ytd['tickets'], ytd_ya['tickets']))}</td>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #DDD;font-weight:bold">Ticket medio</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD;font-weight:bold">{_fmt_eur(ytd['ticket_medio'])}</td>
                <td style="text-align:right;padding:8px;border:1px solid #DDD">{_fmt_eur(ytd_ya['ticket_medio'])}</td>
                <td style="text-align:center;padding:8px;border:1px solid #DDD">{_var_html(_pct_var(ytd['ticket_medio'], ytd_ya['ticket_medio']))}</td>
            </tr>
        </table>'''
        return html

    def _tabla_top10(titulo, df_top, col_valor, col_prev, col_ya, fmt_fn):
        """Genera tabla HTML de top 10 productos."""
        if df_top.empty:
            return ''
        rows = ''
        for i, (nombre, row) in enumerate(df_top.iterrows()):
            bg = 'background:#F7F8FA;' if i % 2 == 1 else ''
            val = row[col_valor]
            val_prev = row.get(col_prev, 0)
            val_ya = row.get(col_ya, 0)
            nombre_corto = str(nombre)[:35]
            rows += f'''
            <tr style="{bg}">
                <td style="padding:6px 8px;border:1px solid #DDD;text-align:center">{i+1}</td>
                <td style="padding:6px 8px;border:1px solid #DDD">{nombre_corto}</td>
                <td style="text-align:right;padding:6px 8px;border:1px solid #DDD;font-weight:bold">{fmt_fn(val)}</td>
                <td style="text-align:center;padding:6px 8px;border:1px solid #DDD">{_var_html(_pct_var(val, val_prev))}</td>
                <td style="text-align:center;padding:6px 8px;border:1px solid #DDD">{_var_html(_pct_var(val, val_ya))}</td>
            </tr>'''
        return f'''
        <h3 style="margin:15px 0 5px;color:#555">{titulo}</h3>
        <table style="width:100%;border-collapse:collapse;margin-bottom:15px;font-size:13px">
            <tr style="background:#F7F8FA">
                <th style="padding:6px 8px;border:1px solid #DDD;width:5%">#</th>
                <th style="text-align:left;padding:6px 8px;border:1px solid #DDD;width:35%">Producto</th>
                <th style="text-align:right;padding:6px 8px;border:1px solid #DDD;width:20%">Valor</th>
                <th style="text-align:center;padding:6px 8px;border:1px solid #DDD;width:20%">vs Sem.ant</th>
                <th style="text-align:center;padding:6px 8px;border:1px solid #DDD;width:20%">vs Año ant</th>
            </tr>
            {rows}
        </table>'''

    # Construir email completo
    sem_str = f"{lunes.strftime('%d/%m/%Y')} — {domingo.strftime('%d/%m/%Y')}"

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;max-width:700px;margin:0 auto;color:#333">
    <div style="background:#1B2A4A;padding:20px;text-align:center;border-radius:8px 8px 0 0">
        <h1 style="color:white;margin:0;font-size:22px">Resumen Semanal de Ventas</h1>
        <p style="color:#B8C5D9;margin:5px 0 0;font-size:14px">{sem_str}</p>
    </div>
    <div style="padding:20px;border:1px solid #DDD;border-top:none;border-radius:0 0 8px 8px">
'''

    # TASCA
    html += _seccion_kpis("TASCA BAREA", "#1B2A4A", datos_tasca)
    if datos_tasca and not datos_tasca['top_eur'].empty:
        html += _tabla_top10("Top 10 por facturación", datos_tasca['top_eur'],
                             'ventas', 'ventas_prev', 'ventas_ya', _fmt_eur)
        html += _tabla_top10("Top 10 por unidades", datos_tasca['top_uds'],
                             'cantidad', 'cantidad_prev', 'cantidad_ya',
                             lambda x: f"{x:,.1f}".replace(",", "."))

    # COMESTIBLES
    html += _seccion_kpis("COMESTIBLES BAREA", "#1B5E20", datos_comes)
    if datos_comes and not datos_comes['top_eur'].empty:
        html += _tabla_top10("Top 10 por facturación", datos_comes['top_eur'],
                             'ventas', 'ventas_prev', 'ventas_ya', _fmt_eur)
        html += _tabla_top10("Top 10 por unidades", datos_comes['top_uds'],
                             'cantidad', 'cantidad_prev', 'cantidad_ya',
                             lambda x: f"{x:,.1f}".replace(",", "."))

    # WOOCOMMERCE
    if datos_comes and datos_comes['wc_pedidos'] > 0:
        html += f'''
        <h3 style="margin:15px 0 5px;color:#555">WooCommerce</h3>
        <p>{datos_comes['wc_pedidos']} pedidos — {_fmt_eur(datos_comes['wc_ventas'])}</p>'''

    # CALENDARIO TALLERES
    html += _seccion_talleres()

    html += f'''
        <hr style="border:none;border-top:1px solid #DDD;margin:20px 0">
        <p style="color:#999;font-size:11px;text-align:center">
            Generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}
            por script_barea.py
        </p>
    </div>
</body>
</html>'''

    return html


def _seccion_talleres():
    """Genera el bloque HTML con los talleres/catas/eventos futuros.

    Lee talleres_programados.json, filtra los que aún no han pasado y
    devuelve una tabla HTML lista para insertar en el email semanal.
    Devuelve cadena vacía si no hay eventos futuros o el JSON no existe.
    """
    import json
    json_path = os.path.join(_script_dir, "talleres_programados.json")
    if not os.path.exists(json_path):
        return ''

    try:
        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return ''

    hoy = datetime.now().date()
    futuros = []
    for t in data.get('talleres', []):
        try:
            fecha_dt = datetime.strptime(t['fecha'], '%d/%m/%y').date()
        except (ValueError, KeyError):
            continue
        if fecha_dt >= hoy:
            futuros.append((fecha_dt, t))

    if not futuros:
        return ''

    futuros.sort(key=lambda x: x[0])

    filas = ''
    for i, (fecha_dt, t) in enumerate(futuros):
        bg = 'background:#F7F8FA;' if i % 2 == 1 else ''
        nombre = t.get('nombre') or '(sin nombre)'
        fecha_str = fecha_dt.strftime('%d/%m/%Y')
        hora = ''
        if t.get('hora_inicio'):
            hora = t['hora_inicio']
            if t.get('hora_fin'):
                hora += f" - {t['hora_fin']}"

        stock_qty = t.get('stock_quantity')
        stock_status = t.get('stock_status', 'instock')
        if stock_qty is None:
            plazas_txt = 'Sin límite'
            plazas_color = '#1B5E20'
        elif stock_status == 'outofstock' or stock_qty <= 0:
            plazas_txt = 'Completo'
            plazas_color = '#B71C1C'
        else:
            plazas_txt = f'{stock_qty} disponible{"s" if stock_qty != 1 else ""}'
            plazas_color = '#1B5E20' if stock_qty > 3 else '#E65100'

        precio = t.get('precio', 0)
        precio_txt = f"{precio:.0f} €" if precio else ''

        filas += f'''
        <tr style="{bg}">
            <td style="padding:7px 10px;border:1px solid #DDD;font-weight:bold">{nombre}</td>
            <td style="padding:7px 10px;border:1px solid #DDD;white-space:nowrap">{fecha_str}</td>
            <td style="padding:7px 10px;border:1px solid #DDD;white-space:nowrap">{hora}</td>
            <td style="padding:7px 10px;border:1px solid #DDD;color:{plazas_color};font-weight:bold">{plazas_txt}</td>
            <td style="padding:7px 10px;border:1px solid #DDD;text-align:right">{precio_txt}</td>
        </tr>'''

    return f'''
    <h3 style="margin:20px 0 8px;color:#555;border-bottom:1px solid #DDD;padding-bottom:4px">
        Próximos eventos ({len(futuros)})
    </h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:10px">
        <tr style="background:#1B2A4A;color:white">
            <th style="padding:7px 10px;text-align:left">Evento</th>
            <th style="padding:7px 10px;text-align:left">Fecha</th>
            <th style="padding:7px 10px;text-align:left">Horario</th>
            <th style="padding:7px 10px;text-align:left">Plazas</th>
            <th style="padding:7px 10px;text-align:right">Precio</th>
        </tr>
        {filas}
    </table>'''


def _conectar_gmail_envio():
    """Conecta con Gmail API para envío. Devuelve service o None."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        log.warning("google-auth/google-api-python-client no instalados")
        return None

    if not os.path.exists(_GMAIL_TOKEN):
        log.warning("No existe %s", _GMAIL_TOKEN)
        return None

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    creds = Credentials.from_authorized_user_file(_GMAIL_TOKEN, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_GMAIL_TOKEN, "w") as f:
                f.write(creds.to_json())
        else:
            log.warning("Credenciales Gmail expiradas")
            return None

    return build("gmail", "v1", credentials=creds)


def enviar_email_semanal(lunes, domingo):
    """
    Genera y envía el email de resumen semanal con:
    - KPIs Tasca + Comestibles (ventas, tickets, ticket medio)
    - Comparativa vs semana anterior y misma semana año anterior
    - YTD vs YTD año anterior
    - Top 10 productos por facturación y por unidades
    - WooCommerce si hubo pedidos
    """
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    log.info("Generando resumen semanal por email...")

    # Calcular datos
    datos_tasca = _calcular_resumen_tienda("Tasca", lunes, domingo)
    datos_comes = _calcular_resumen_tienda("Comes", lunes, domingo)

    if datos_tasca is None and datos_comes is None:
        log.info("  Sin datos de ventas, no se envía email")
        return

    # Generar HTML
    html = _generar_html_email(lunes, domingo, datos_tasca, datos_comes)

    # Conectar y enviar
    service = _conectar_gmail_envio()
    if not service:
        log.warning("No se pudo conectar con Gmail para enviar resumen")
        return

    sem_str = f"{lunes.strftime('%d/%m')} - {domingo.strftime('%d/%m/%Y')}"
    asunto = f"Resumen Ventas Semanal ({sem_str})"

    for email_dest in EMAILS_RESUMEN_SEMANAL:
        try:
            message = MIMEMultipart("mixed")
            message["To"] = email_dest
            message["Subject"] = asunto
            message.attach(MIMEText(html, "html"))
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            log.info("  Email enviado a %s", email_dest)
        except Exception as e:
            log.error("Error enviando a %s: %s", email_dest, e)


def _parse_gbp_num(s):
    """Convierte '28.276' a int."""
    return int(s.replace('.', '').replace(',', ''))


def _parse_gbp_email(html, subject):
    """
    Parsea el HTML del email mensual de Google Business Profile.
    Extrae: interacciones, llamadas, chat, indicaciones, visitas web,
    vistas perfil, búsquedas, menú (con variaciones %), top 3 búsquedas.
    """
    import re as _re

    MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
             'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
             'octubre': 10, 'noviembre': 11, 'diciembre': 12}

    ms = _re.search(r'de (\w+) de (\d{4})', subject)
    if not ms:
        return None
    mes = MESES.get(ms.group(1).lower())
    anio = int(ms.group(2))
    if not mes:
        return None

    # Limpiar HTML a texto con separadores
    text = _re.sub(r'<[^>]+>', '|', html)
    text = _re.sub(r'[\n\r\t ]+', ' ', text)
    text = _re.sub(r'\|[\s|]+\|', '|', text)
    text = _re.sub(r'\|+', '|', text)
    text = _re.sub(r'\| \|', '|', text)

    def _extract(label_pattern):
        """Extrae valor numérico + variación% asociada a una métrica."""
        p = r'([\d.,]+) \| (?:usuarios han solicitado )?' + label_pattern
        m = _re.search(p, text, _re.IGNORECASE)
        val = _parse_gbp_num(m.group(1)) if m else None
        var = None
        if m:
            after = text[m.end():m.end()+50]
            mv = _re.search(r'([+-]\d+)%', after)
            var = int(mv.group(1)) if mv else None
        return val, var

    # Interacciones
    mi = _re.search(r'conseguiste\s+([\d.]+)\s+interacciones', text)
    interacciones = _parse_gbp_num(mi.group(1)) if mi else None

    llamadas, _ = _extract(r'llamadas')
    chat, _ = _extract(r'clics en el chat')
    indicaciones, ind_v = _extract(r'(?:usuarios han solicitado )?indicaciones')
    web, web_v = _extract(r'visitas al sitio web')
    vistas, vis_v = _extract(r'vistas del perfil')
    busq, busq_v = _extract(r'b[uú]squedas')
    menu, menu_v = _extract(r'visualizaciones del men[uú]')

    # Top 3 búsquedas: buscar en texto limpio "rank | term | volumen"
    # Usar texto con pipes menos agresivo para preservar estructura
    text2 = _re.sub(r'<[^>]+>', '|', html)
    text2 = _re.sub(r'[\n\r\t ]+', ' ', text2)
    text2 = _re.sub(r'(\| )+', '|', text2)
    tops = _re.findall(r'\|(\d) \|([a-zA-ZáéíóúñüÁÉÍÓÚÑÜ ]+)\|([\d.]+) \|', text2)
    if not tops:
        tops = _re.findall(r'\|(\d)\|([a-zA-ZáéíóúñüÁÉÍÓÚÑÜ ]+)\|([\d.]+)\|', text2)

    top3 = []
    for _, term, vol in tops[:3]:
        term = term.strip()
        if term:
            top3.append((term, _parse_gbp_num(vol)))

    return {
        'Mes': mes, 'Anio': anio, 'Interacciones': interacciones,
        'Llamadas': llamadas, 'Chat': chat,
        'Indicaciones': indicaciones, 'Indicaciones_Var': ind_v,
        'Visitas_Web': web, 'Visitas_Web_Var': web_v,
        'Vistas_Perfil': vistas, 'Vistas_Perfil_Var': vis_v,
        'Busquedas': busq, 'Busquedas_Var': busq_v,
        'Menu': menu, 'Menu_Var': menu_v,
        'Top1_Busqueda': top3[0][0] if len(top3) > 0 else None,
        'Top1_Volumen': top3[0][1] if len(top3) > 0 else None,
        'Top2_Busqueda': top3[1][0] if len(top3) > 1 else None,
        'Top2_Volumen': top3[1][1] if len(top3) > 1 else None,
        'Top3_Busqueda': top3[2][0] if len(top3) > 2 else None,
        'Top3_Volumen': top3[2][1] if len(top3) > 2 else None,
    }


def recoger_google_business(target_year):
    """
    Lee emails de Google Business Profile del último año, parsea métricas
    y guarda en pestaña GoogleBusiness del Excel de ventas.
    Se ejecuta el 1er lunes del mes (junto con dashboard mensual).
    """
    import base64 as _b64

    log.info("Recogiendo datos de Google Business Profile...")

    service = _conectar_gmail_envio()
    if not service:
        log.warning("No se pudo conectar con Gmail")
        return

    def _find_html(payload):
        if payload.get('mimeType') == 'text/html' and payload.get('body', {}).get('data'):
            return _b64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        for part in payload.get('parts', []):
            r = _find_html(part)
            if r:
                return r
        return None

    # Buscar emails de informe GBP
    results = service.users().messages().list(
        userId='me',
        q='subject:"informe de rendimiento" Tasca Barea newer_than:2y',
        maxResults=30
    ).execute()

    all_data = []
    seen = set()
    for m in results.get('messages', []):
        msg = service.users().messages().get(userId='me', id=m['id'], format='full').execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        subject = headers.get('Subject', '')

        html = _find_html(msg['payload'])
        if not html:
            continue

        data = _parse_gbp_email(html, subject)
        if data:
            key = (data['Mes'], data['Anio'])
            if key not in seen:
                seen.add(key)
                all_data.append(data)

    if not all_data:
        log.info("  No se encontraron emails de Google Business Profile")
        return

    # Filtrar por año objetivo
    datos_anio = [d for d in all_data if d['Anio'] == target_year]

    if not datos_anio:
        log.info("  No hay datos de %s", target_year)
        return

    # Crear DataFrame y guardar
    df = pd.DataFrame(datos_anio)
    df = df.sort_values(['Anio', 'Mes'])

    # Columnas en orden
    col_order = ['Mes', 'Anio', 'Interacciones', 'Llamadas', 'Chat',
                 'Indicaciones', 'Indicaciones_Var',
                 'Visitas_Web', 'Visitas_Web_Var',
                 'Vistas_Perfil', 'Vistas_Perfil_Var',
                 'Busquedas', 'Busquedas_Var',
                 'Menu', 'Menu_Var',
                 'Top1_Busqueda', 'Top1_Volumen',
                 'Top2_Busqueda', 'Top2_Volumen',
                 'Top3_Busqueda', 'Top3_Volumen']
    df = df[[c for c in col_order if c in df.columns]]

    save_to_excel(df, PATH_VENTAS, "GoogleBusiness", unique_col="Mes")
    log.info("  %d meses guardados en GoogleBusiness", len(datos_anio))
    for d in sorted(datos_anio, key=lambda x: x['Mes']):
        log.info("    %02d/%d: %s interacciones, %s indicaciones, %s búsquedas",
                 d['Mes'], d['Anio'], d['Interacciones'], d['Indicaciones'], d['Busquedas'])


def _limpiar_nombre_taller(nombre_raw, fecha_str):
    """Limpia el nombre de un taller extraído del producto WooCommerce.

    - Elimina la fecha si quedó dentro del nombre
    - Quita sufijos de tienda ('Comestibles Barea', 'Tasca Barea')
    - Quita guiones sobrantes
    """
    import re as _re
    nombre = nombre_raw
    # Quitar la fecha si aparece dentro del trozo antes de dividir
    nombre = nombre.replace(fecha_str, '')
    # Quitar sufijos de tienda
    for sufijo in ('Comestibles Barea', 'Tasca Barea', 'Comestibles', 'Tasca'):
        nombre = _re.sub(r'\s*' + _re.escape(sufijo) + r'\s*', ' ', nombre, flags=_re.IGNORECASE)
    # Limpiar guiones/espacios sobrantes al inicio y fin
    nombre = _re.sub(r'^[-\s]+|[-\s]+$', '', nombre)
    nombre = _re.sub(r'\s{2,}', ' ', nombre)
    return nombre.strip()


def generar_inventario_talleres():
    """
    Busca todos los productos WooCommerce publicados con una fecha (DD/MM/YY)
    en el nombre, extrae el horario del description y guarda el resultado en
    ventas_semana/talleres_programados.json.
    Llamado cada lunes por main() para mantener el inventario actualizado en el repo.
    Incluye stock_quantity, stock_status y price para el calendario de eventos.
    """
    import json
    import re as _re

    output_path = os.path.join(_script_dir, "talleres_programados.json")
    patron_fecha = _re.compile(r'\b(\d{1,2}/\d{2}/\d{2})\b')
    patron_hora  = _re.compile(r'HORARIO:\s*de\s*(\d{1,2}:\d{2})(?:\s*a\s*(\d{1,2}:\d{2}))?', _re.IGNORECASE)

    def _strip_html(text):
        return _re.sub(r'<[^>]+>', ' ', text or '').strip()

    wc = get_wc_api()
    talleres = []
    page = 1

    while True:
        productos = wc.get("products", params={"per_page": 100, "page": page, "status": "publish"}).json()
        if not isinstance(productos, list) or not productos:
            break

        for p in productos:
            nombre_raw = _strip_html(p.get("name", ""))
            m_fecha = patron_fecha.search(nombre_raw)
            if not m_fecha:
                continue

            fecha_str = m_fecha.group(1)
            # Normalizar a DD/MM/YY con día de dos dígitos para consistencia
            try:
                fecha_dt = datetime.strptime(fecha_str, "%d/%m/%y")
            except ValueError:
                try:
                    fecha_dt = datetime.strptime(fecha_str, "%-d/%m/%y")
                except ValueError:
                    continue
            fecha_norm = fecha_dt.strftime("%d/%m/%y")

            # Extraer nombre limpio: trozo antes de la fecha, sin sufijos de tienda
            nombre_base = nombre_raw.split(fecha_str)[0]
            nombre_limpio = _limpiar_nombre_taller(nombre_base, fecha_str)

            desc = _strip_html(p.get("description", ""))
            m_hora = patron_hora.search(desc)

            # Plazas: stock_quantity puede ser None si WC no gestiona stock
            stock_qty = p.get("stock_quantity")
            stock_status = p.get("stock_status", "instock")  # instock / outofstock
            try:
                precio = float(p.get("price") or p.get("regular_price") or 0)
            except (ValueError, TypeError):
                precio = 0.0

            talleres.append({
                "id": p["id"],
                "nombre": nombre_limpio,
                "fecha": fecha_norm,
                "hora_inicio": m_hora.group(1) if m_hora else None,
                "hora_fin":    m_hora.group(2) if (m_hora and m_hora.group(2)) else None,
                "stock_quantity": stock_qty,
                "stock_status": stock_status,
                "precio": precio,
            })
            log.info("  Taller: %s %s %s", fecha_norm,
                     talleres[-1]["nombre"][:40],
                     talleres[-1]["hora_inicio"] or "(sin hora)")

        page += 1
        if len(productos) < 100:
            break

    resultado = {
        "generado": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "talleres": talleres,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    log.info("Inventario talleres guardado: %d taller(es) → %s", len(talleres), output_path)


def _normalizar_pedidos_wc(orders):
    """Convierte la lista de pedidos WooCommerce en un DataFrame limpio.

    Genera 7 columnas útiles (1 fila por pedido) en lugar de las ~69 que
    produce pd.json_normalize. La columna 'items_resumen' consolida todos
    los productos del pedido en un string legible sin HTML.
    """
    import re as _re

    def _limpiar_nombre_item(text):
        """Elimina tags HTML y espacios sobrantes del nombre de un producto."""
        if not text:
            return ''
        text = _re.sub(r'<[^>]+>', ' ', str(text))
        text = _re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    filas = []
    for o in orders:
        line_items = o.get("line_items", [])
        partes = []
        total_uds = 0
        for item in line_items:
            qty = item.get("quantity", 1)
            name = _limpiar_nombre_item(item.get("name", ""))
            total_uds += qty
            partes.append(name)
        try:
            total_eur = f"{float(o.get('total', 0)):.2f}".replace(".", ",") + " €"
        except (ValueError, TypeError):
            total_eur = o.get("total", "")
        fecha_raw = o.get("date_created", "")[:10]
        try:
            from datetime import datetime as _dt
            fecha_fmt = _dt.strptime(fecha_raw, "%Y-%m-%d").strftime("%d-%m-%y")
        except ValueError:
            fecha_fmt = fecha_raw
        filas.append({
            "id":            o.get("id"),
            "fecha":         fecha_fmt,
            "estado":        o.get("status"),
            "estado_pago":   o.get("payment_method_title"),
            "total":         total_eur,
            "items_resumen": ", ".join(partes) if partes else "",
            "num_items":     total_uds,
        })
    return pd.DataFrame(filas)


def main():
    lunes, domingo = calcular_semana_anterior()
    desde_iso = f"{lunes}T00:00:00.000Z"
    hasta_iso = f"{domingo}T23:59:59.999Z"

    log.info("--- Carga Barea: %s ---", datetime.now().strftime('%Y-%m-%d %H:%M'))
    log.info("Semana: %s (lun) a %s (dom)", lunes.strftime('%d/%m/%Y'), domingo.strftime('%d/%m/%Y'))

    # 1. WOOCOMMERCE (filtrado por semana)
    try:
        wc = get_wc_api()
        all_orders = []
        page = 1
        while True:
            orders = wc.get("orders", params={
                "per_page": 100,
                "page": page,
                "after": desde_iso,
                "before": hasta_iso,
            }).json()
            if not isinstance(orders, list) or len(orders) == 0:
                break
            all_orders.extend(orders)
            page += 1
            if len(orders) < 100:
                break
        if all_orders:
            df_wc = _normalizar_pedidos_wc(all_orders)
            save_to_excel(df_wc, PATH_VENTAS, "WOOCOMMERCE", unique_col="id")
            log.info("WooCommerce: %d pedidos", len(all_orders))
        else:
            log.info("WooCommerce: sin pedidos esta semana")
    except Exception as e:
        log.error("Error en WooCommerce: %s", e)

    # 2. LOYVERSE (Tasca y Comestibles)
    stores = [("Tasca", "LOY_TOKEN_TASCA"), ("Comes", "LOY_TOKEN_COMES")]
    for name, tk_key in stores:
        token = os.getenv(tk_key)
        if not token:
            continue

        log.info("=" * 40)
        log.info(name)
        log.info("=" * 40)

        # Cargar datos de referencia (tiendas, TPVs, empleados, clientes, etc.)
        lookups = fetch_lookup_data(token)

        # Descargar recibos de la semana
        log.info("  Descargando recibos...")
        receipts = fetch_loyverse(token, "receipts",
                                  created_at_min=desde_iso,
                                  created_at_max=hasta_iso)

        if receipts:
            log.info("     %d recibos descargados", len(receipts))
            df_recibos, df_items = procesar_recibos(receipts, lookups)

            save_to_excel(df_recibos, PATH_VENTAS, f"{name}Recibos", "Número de recibo")
            save_to_excel(df_items, PATH_VENTAS, f"{name}Items", "unique_id")

            log.info("  %d recibos, %d items guardados", len(df_recibos), len(df_items))
        else:
            log.info("  Sin recibos esta semana")

        # 3. ACTUALIZAR ARTÍCULOS (siempre)
        sheet_articulos = "Tasca" if name == "Tasca" else "Comestibles"
        log.info("  Descargando artículos e impuestos...")
        items_list = fetch_loyverse(token, "items")
        taxes_raw = fetch_loyverse(token, "taxes")
        taxes_by_id = {}
        for t in taxes_raw:
            taxes_by_id[t['id']] = {'name': t.get('name', ''), 'rate': t.get('rate', 0)}
        if items_list:
            update_articles_history(items_list, PATH_ARTICULOS, sheet_articulos,
                                    categories=lookups['categories'],
                                    taxes_by_id=taxes_by_id)

        # 3b. CHEQUEO ANOMALÍAS IVA (tras actualizar artículos)
        check_iva_anomalies(PATH_ARTICULOS, sheet_articulos)

    # 4. REGENERAR DASHBOARDS (Comestibles + Tasca)
    dashboard_mensual = "--dashboard-mensual" in sys.argv
    try:
        # Asegurar que el proyecto raiz esta en sys.path para el import
        _project_root = os.path.dirname(_script_dir)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        from ventas_semana.generar_dashboard import main as generar_dashboard
        generar_dashboard(
            abrir_navegador=False,
            solo_meses_cerrados=dashboard_mensual,
            enviar_email=dashboard_mensual,
        )
        log.info("Dashboards regenerados%s",
                 " (mensual + PDF + email)" if dashboard_mensual else "")
    except Exception as e:
        log.error("Error regenerando dashboards: %s", e)

    # 5. GOOGLE BUSINESS PROFILE (1er lunes del mes)
    if dashboard_mensual:
        try:
            recoger_google_business(domingo.year)
        except Exception as e:
            log.error("Error recogiendo Google Business: %s", e)

    # 6. INVENTARIO TALLERES — antes del email para que el email use datos frescos
    try:
        generar_inventario_talleres()
    except Exception as e:
        log.error("Error generando inventario talleres: %s", e)

    # 7. EMAIL RESUMEN SEMANAL
    try:
        enviar_email_semanal(lunes, domingo)
    except Exception as e:
        log.error("Error enviando email semanal: %s", e)

    log.info("--- Proceso Finalizado ---")


if __name__ == "__main__":
    main()
