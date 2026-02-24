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
        version="wc/v3"
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
            response = requests.get(base_url, headers=headers, params=params)

            if response.status_code in (401, 403, 404) and api_version == "v1.0" and page == 0:
                api_version = "v2"
                base_url = f"https://api.loyverse.com/{api_version}/{endpoint}"
                response = requests.get(base_url, headers=headers)
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

    try:
        with pd.ExcelWriter(path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            try:
                existing_df = pd.read_excel(path, sheet_name=sheet_name)
                # Normalizar nombres de columna de datos antiguos
                existing_df.rename(columns=_COL_RENAMES, inplace=True)

                if unique_col and unique_col in df.columns and unique_col in existing_df.columns:
                    df[unique_col] = df[unique_col].astype(str)
                    existing_df[unique_col] = existing_df[unique_col].astype(str)
                    df = df[~df[unique_col].isin(existing_df[unique_col])]

                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
            except Exception:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception as e:
        print(f"Error guardando {sheet_name}: {e}")


def update_articles_history(new_items_raw, path, sheet_name):
    """Actualiza Coste y Precio en el Excel de artículos."""
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

    col_precio = None
    for col in old_df.columns:
        if col.startswith('Precio'):
            col_precio = col
            break

    if not col_precio:
        print(f"  ⚠️ No se encontró columna 'Precio [...]' en '{sheet_name}'")
        return

    api_items = {}
    for item in new_items_raw:
        for v in item.get('variants', []):
            sku = v.get('sku', '')
            if sku:
                api_items[str(sku)] = {
                    'cost': v.get('cost'),
                    'price': v.get('default_price'),
                }

    cambios = 0
    for idx, row in old_df.iterrows():
        ref = str(row.get('REF', '')).strip()
        if ref in api_items:
            api = api_items[ref]
            cambio = False
            if api.get('cost') is not None and api['cost'] != row.get('Coste'):
                old_df.at[idx, 'Coste'] = api['cost']
                cambio = True
            if api.get('price') is not None and api['price'] != row.get(col_precio):
                old_df.at[idx, col_precio] = api['price']
                cambio = True
            if cambio:
                cambios += 1

    if cambios > 0:
        with pd.ExcelWriter(path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            old_df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  📝 {sheet_name}: {cambios} artículos actualizados (coste/precio)")
    else:
        print(f"  ✅ {sheet_name}: sin cambios de precio")


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
        items_list = fetch_loyverse(token, "items")
        if items_list:
            update_articles_history(items_list, PATH_ARTICULOS, sheet_articulos)

    print()
    print("--- Proceso Finalizado ---")


if __name__ == "__main__":
    main()
