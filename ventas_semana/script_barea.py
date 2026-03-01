import os
import subprocess
import sys

# --- AUTO-INSTALACIÓN DE LIBRERÍAS ---
def install_requirements():
    libs = ["pandas", "openpyxl", "requests", "python-dotenv", "woocommerce"]
    for lib in libs:
        try:
            module_name = lib.replace("-", "_")
            __import__(module_name)
        except ImportError:
            print(f"Instalando {lib} para Jaime...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

import pandas as pd
import requests
from woocommerce import API
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Cargar configuración (relativo al script, no al cwd)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_script_dir, ".env")
_env_txt_path = os.path.join(_script_dir, ".env.txt")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
elif os.path.exists(_env_txt_path):
    load_dotenv(_env_txt_path)
else:
    print("ERROR: No encuentro el archivo .env")

PATH_VENTAS = os.getenv("PATH_VENTAS")
PATH_ARTICULOS = os.getenv("PATH_ARTICULOS")

# Nombres de tienda por token (para el print, no para datos)
STORE_NAMES = {"LOY_TOKEN_TASCA": "Tasca", "LOY_TOKEN_COMES": "Comes"}


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
                print(f"  ⚠️ API {endpoint}: HTTP {response.status_code}")
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
            print(f"  ⚠️ Error API {endpoint}: {e}")
            break

    return all_results


def fetch_lookup_data(token):
    """
    Descarga datos de referencia de Loyverse para resolver IDs a nombres:
    stores, pos_devices, employees, customers, categories, payment_types, items.
    """
    print("  📚 Cargando datos de referencia...")

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

    print(f"     {len(stores)} tiendas, {len(pos_devices)} TPVs, "
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


def save_to_excel(df, path, sheet_name, unique_col=None):
    """Guarda DataFrame en Excel, acumulando sin duplicados."""
    if df.empty:
        return

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
        print(f"  ERROR leyendo {sheet_name} de {path}: {e}")
        print(f"  ABORTANDO escritura para no perder datos existentes.")
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
        print(f"Error guardando {sheet_name}: {e}")


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
        print(f"  ⚠️ No existe {path}, saltando artículos")
        return

    try:
        old_df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception as e:
        print(f"  ⚠️ No se pudo leer pestaña '{sheet_name}': {e}")
        return

    if 'REF' not in old_df.columns:
        print(f"  ⚠️ Pestaña '{sheet_name}' no tiene columna REF")
        return

    # Buscar columnas dinámicamente
    col_precio = next((c for c in old_df.columns if c.startswith('Precio')), None)
    col_disponible = next((c for c in old_df.columns if c.startswith('Disponibles')), None)
    col_inventario = next((c for c in old_df.columns if c.startswith('En inventario')), None)
    col_existencias = next((c for c in old_df.columns if c.startswith('Existencias')), None)

    if not col_precio:
        print(f"  ⚠️ No se encontró columna 'Precio [...]' en '{sheet_name}'")
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
        print(f"  📝 {sheet_name}: {', '.join(parts)}")
    else:
        print(f"  ✅ {sheet_name}: sin cambios")


def main():
    lunes, domingo = calcular_semana_anterior()
    desde_iso = f"{lunes}T00:00:00.000Z"
    hasta_iso = f"{domingo}T23:59:59.999Z"

    print(f"--- Carga Barea: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    print(f"📅 Semana: {lunes.strftime('%d/%m/%Y')} (lun) a {domingo.strftime('%d/%m/%Y')} (dom)")
    print()

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
            df_wc = pd.json_normalize(all_orders)
            save_to_excel(df_wc, PATH_VENTAS, "WOOCOMMERCE", unique_col="id")
            print(f"✅ WooCommerce: {len(all_orders)} pedidos")
        else:
            print(f"✅ WooCommerce: sin pedidos esta semana")
    except Exception as e:
        print(f"❌ Error en WooCommerce: {e}")

    # 2. LOYVERSE (Tasca y Comestibles)
    stores = [("Tasca", "LOY_TOKEN_TASCA"), ("Comes", "LOY_TOKEN_COMES")]
    for name, tk_key in stores:
        token = os.getenv(tk_key)
        if not token:
            continue

        print(f"\n{'='*40}")
        print(f"📍 {name}")
        print(f"{'='*40}")

        # Cargar datos de referencia (tiendas, TPVs, empleados, clientes, etc.)
        lookups = fetch_lookup_data(token)

        # Descargar recibos de la semana
        print(f"  📥 Descargando recibos...")
        receipts = fetch_loyverse(token, "receipts",
                                  created_at_min=desde_iso,
                                  created_at_max=hasta_iso)

        if receipts:
            print(f"     {len(receipts)} recibos descargados")
            df_recibos, df_items = procesar_recibos(receipts, lookups)

            save_to_excel(df_recibos, PATH_VENTAS, f"{name}Recibos", "Número de recibo")
            save_to_excel(df_items, PATH_VENTAS, f"{name}Items", "unique_id")

            print(f"  ✅ {len(df_recibos)} recibos, {len(df_items)} items guardados")
        else:
            print(f"  ✅ Sin recibos esta semana")

        # 3. ACTUALIZAR ARTÍCULOS (siempre)
        sheet_articulos = "Tasca" if name == "Tasca" else "Comestibles"
        print(f"  📦 Descargando artículos e impuestos...")
        items_list = fetch_loyverse(token, "items")
        taxes_raw = fetch_loyverse(token, "taxes")
        taxes_by_id = {}
        for t in taxes_raw:
            taxes_by_id[t['id']] = {'name': t.get('name', ''), 'rate': t.get('rate', 0)}
        if items_list:
            update_articles_history(items_list, PATH_ARTICULOS, sheet_articulos,
                                    categories=lookups['categories'],
                                    taxes_by_id=taxes_by_id)

    # 4. REGENERAR DASHBOARD COMESTIBLES
    dashboard_mensual = "--dashboard-mensual" in sys.argv
    try:
        from ventas_semana.generar_dashboard import main as generar_dashboard
        generar_dashboard(
            abrir_navegador=False,
            solo_meses_cerrados=dashboard_mensual,
            enviar_email=dashboard_mensual,
        )
        print("Dashboard Comestibles regenerado"
              + (" (mensual + email)" if dashboard_mensual else ""))
    except Exception as e:
        print(f"Error regenerando dashboard: {e}")

    print()
    print("--- Proceso Finalizado ---")


if __name__ == "__main__":
    main()
