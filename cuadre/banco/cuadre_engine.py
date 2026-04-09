"""
cuadre/banco/cuadre_engine.py — Motor de clasificación de movimientos bancarios v2.0

Módulo importable con las 3 capas de clasificación:
  Capa 1: Reglas estructurales (TPV, comisiones, nóminas, impuestos, etc.)
  Capa 2: Memoria histórica + cruce con facturas
  Capa 3: Sin clasificar → REVISAR

Usado tanto por el CLI (cuadre.py) como por Streamlit.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz

# ─── Reglas estructurales (Capa 1) ──────────────────────────────────────────

# (patrón regex, Categoria_Tipo, Categoria_Detalle template o None)
# Se evalúan en orden — la primera que matchea gana.
REGLAS_ESTRUCTURALES: list[tuple[str, str, str | None]] = [
    # TPV — por terminal
    (r"ABONO TPV.*0354272759", "TPV TALLERES",     None),
    (r"ABONO TPV.*0337410674", "TPV TASCA",        None),
    (r"ABONO TPV.*0354768939", "TPV COMESTIBLES",  None),
    (r"ABONO TPV.*6304473868", "TPV WOOCOMMERCE",  None),
    # Comisiones TPV
    (r"COMISIONES.*0354272759", "COMISION TPV TALLERES",     None),
    (r"COMISIONES.*0337410674", "COMISION TPV TASCA",        None),
    (r"COMISIONES.*0354768939", "COMISION TPV COMESTIBLES",  None),
    # Nóminas y SS
    (r"^NOMINA A ",           "NOMINAS",           None),
    (r"^SEGUROS SOCIALES",    "SEGUROS SOCIALES",  None),
    (r"TRANSFERENCIA A ELENA DE MIGUEL", "NOMINAS", "Elena de Miguel"),
    # Impuestos
    (r"^IMPUESTOS",           "IMPUESTOS",         None),
    (r"\bTGSS\b",             "IMPUESTOS",         None),
    (r"\bAEAT\b",             "IMPUESTOS",         None),
    # Operaciones bancarias
    (r"^INGRESO EFECTIVO",    "INGRESO",           None),
    (r"^REINTEGRO",           "A CAJA",            None),
    (r"^TRASPASO",            "TRASPASO",          None),
    (r"^TRANSFERENCIA DE ",   "ABONO DE TRANSFERENCIA", None),
    (r"COMISI[OÓ]N DIVISA",  "COMISION DIVISA",   None),
    (r"COMISIONES RECUENTO",  "COMISIONES",        None),
    (r"^SERVICIO DE TPV",     "SERVICIO DE TPV",   None),
    # Servicios públicos (extraer nombre del concepto)
    # NOTA: SOM ENERGIA y YOIGO tienen handlers especiales en Capa 2b,
    # así que las reglas de ELECTRICIDAD/TELEFONOS los excluyen.
    # Los patrones se evalúan contra concepto.upper() → negativos en MAYÚSCULAS
    (r"^ELECTRICIDAD (?!SOM ENERGIA)(.+?)(?:\s+FACTURA|\s*$)", "__EXTRACT_1__", None),
    (r"^TELEFONOS (?!YOIGO)(.+?)(?:\s+YC|\s*$)",              "__EXTRACT_1__", None),
]

# Suscripciones sin factura
SUSCRIPCIONES_SIN_FACTURA = {
    "LOYVERSE":     "LOYVERSE",
    "SPOTIFY":      "SPOTIFY",
    "NETFLIX":      "NETFLIX",
    "AMAZON PRIME": "AMAZON PRIME",
}

# Terminales TPV — para extraer remesa y calcular % comisión
COMERCIOS_TPV = {
    "0337410674": "TASCA",
    "0354272759": "TALLERES",
    "0354768939": "COMESTIBLES",
    "6304473868": "WOOCOMMERCE",
}

# ─── Nombres alquiler ────────────────────────────────────────────────────────
NOMBRES_ALQUILER_TRIGGER = "BENJAMIN ORTEGA Y JAIME"
PROPIETARIOS_ALQUILER = [
    (["ORTEGA ALONSO BENJAMIN", "BENJAMIN ORTEGA"], "Ortega"),
    (["FERNANDEZ MORENO JAIME", "JAIME FERNANDEZ"], "Fernández"),
]

# Suscripciones CON factura
SUSCRIPCIONES_CON_FACTURA = [
    {"clave": "MAKE.COM",  "titulo": "CELONIS INC.",  "aliases": ["CELONIS", "MAKE", "ONE WORLD TRADE"]},
    {"clave": "OPENAI",    "titulo": "OPENAI LLC",    "aliases": ["OPENAI", "CHATGPT"]},
]

# Comunidad de vecinos
PATRONES_COMUNIDAD = ["COM PROP", "COMUNIDAD PROP"]
PATRON_ISTA = "ISTA METERING"

# Som Energia / Yoigo
PATRON_SOM_ENERGIA = "SOM ENERGIA"
PATRON_SOM_REF = r"(FE?\d{6,})"
PATRON_YOIGO = "YOIGO"
PATRON_YOIGO_REGEX = r"Y?(C\d{9,})"

# Proveedores con pagos parciales
PROVEEDORES_PAGOS_PARCIALES = ["GARCIA VIVAS", "PANIFIESTO"]

# Reglas especiales compra tarjeta
REGLAS_ESPECIALES_TARJETA = [
    {"clave": "PANIFIESTO LAVAPIES", "titulo": "PANIFIESTO LAVAPIES SL"},
    {"clave": "AY MADRE LA FRUTA",   "titulo": "GARCIA VIVAS JULIO"},
]

# Fuzzy thresholds
UMBRAL_FUZZY_MINIMO = 0.70
UMBRAL_FUZZY_INDICAR = 0.85

# Regex para número de remesa TPV
PATRON_TPV_REMESA = r"\b\d{10}\b"
PATRON_TPV_COMERCIOS = r"\b(" + "|".join(COMERCIOS_TPV.keys()) + r")\b"


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Clasificacion:
    """Resultado de clasificar un movimiento."""
    tipo: str
    detalle: str = ""
    capa: int = 0          # 1, 2 o 3
    fuente: str = ""       # "regla", "memoria", "factura", "revisar"
    factura_ids: list = field(default_factory=list)  # Cód. de facturas vinculadas
    confianza: str = ""    # "alta", "media" o ""


@dataclass
class ResultadoCuadre:
    """Resultado completo de un proceso de cuadre."""
    df_tasca: pd.DataFrame
    df_comestibles: pd.DataFrame
    df_facturas: pd.DataFrame
    stats: dict
    log: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════════════════════

def normalizar_nombre(nombre: str) -> str:
    """Normaliza para comparación: mayúsculas, sin tildes, sin sufijos societarios."""
    if not isinstance(nombre, str):
        return ""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = nombre.upper().strip()
    for suf in ["S.L.L.", "S.L.U.", "S.L.", "SL", "S.A.", "SA", "S.C.A.", "SCA", "S.COOP."]:
        nombre = nombre.replace(suf, "")
    return " ".join(nombre.split())


def _to_date(val) -> Optional[pd.Timestamp]:
    """Convierte un valor a Timestamp, tolerando múltiples formatos."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return pd.to_datetime(val, errors="coerce", dayfirst=True)


def _fmt_fecha(ts: Optional[pd.Timestamp]) -> str:
    if ts is None or pd.isna(ts):
        return ""
    return ts.strftime("%d-%m-%y")


# ═══════════════════════════════════════════════════════════════════════════════
# CuadreEngine
# ═══════════════════════════════════════════════════════════════════════════════

class CuadreEngine:
    """Motor de clasificación de movimientos bancarios."""

    def __init__(
        self,
        memoria_path: Optional[str | Path] = None,
        maestro_path: Optional[str | Path] = None,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.log_lines: list[str] = []

        # Estado por ejecución
        self.facturas_usadas: set = set()
        self.vinculos: dict[int, list[tuple[str, int]]] = {}  # fac_id → [(prefijo, mov_num)]
        self._remesas_usadas: set = set()

        # Memoria histórica
        self.memoria: dict = {}
        if memoria_path:
            self._cargar_memoria(Path(memoria_path))

        # MAESTRO → índice de aliases
        self.indice_aliases: dict[str, str] = {}
        self.df_fuzzy = pd.DataFrame(columns=["NOMBRE_EN_CONCEPTO", "TITULO_FACTURA"])
        if maestro_path:
            self._cargar_maestro(Path(maestro_path))

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _cargar_memoria(self, path: Path):
        if not path.exists():
            self._log(f"Memoria no encontrada: {path}")
            return
        with open(path, "r", encoding="utf-8") as f:
            self.memoria = json.load(f)
        self._log(f"Memoria cargada: {len(self.memoria)} conceptos")

    def _cargar_maestro(self, path: Path):
        if not path.exists():
            self._log(f"MAESTRO no encontrado: {path}")
            return
        df = pd.read_excel(path)
        rows = []
        for _, r in df.iterrows():
            prov = str(r.get("PROVEEDOR", "")).strip()
            if not prov:
                continue
            rows.append({"NOMBRE_EN_CONCEPTO": normalizar_nombre(prov), "TITULO_FACTURA": prov})
            alias_str = str(r.get("ALIAS", "")).strip()
            if alias_str and alias_str.lower() != "nan":
                for a in alias_str.split(","):
                    a = a.strip()
                    if a:
                        rows.append({"NOMBRE_EN_CONCEPTO": normalizar_nombre(a), "TITULO_FACTURA": prov})
        self.df_fuzzy = pd.DataFrame(rows)
        self.indice_aliases = dict(zip(self.df_fuzzy["NOMBRE_EN_CONCEPTO"], self.df_fuzzy["TITULO_FACTURA"]))
        self._log(f"MAESTRO cargado: {len(df)} proveedores, {len(self.df_fuzzy)} aliases")

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        self.log_lines.append(msg)
        if self.verbose:
            print(f"  [LOG] {msg}")

    # ── Carga de archivos de entrada ──────────────────────────────────────────

    def cargar_movimientos(self, path: str | Path) -> dict[str, pd.DataFrame]:
        """Carga MOV_BANCO. Devuelve dict {nombre_hoja: DataFrame}."""
        path = Path(path)
        xlsx = pd.ExcelFile(path)
        resultado = {}
        for sheet in xlsx.sheet_names:
            sn = sheet.strip().upper()
            if sn in ("TASCA", "COMESTIBLES"):
                df = pd.read_excel(xlsx, sheet_name=sheet)
                # Normalizar fechas
                for col in ["F. Operativa", "F. Valor"]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                # Normalizar importes
                if "Importe" in df.columns:
                    df["Importe"] = pd.to_numeric(df["Importe"], errors="coerce").fillna(0)
                resultado[sheet.strip()] = df
        self._log(f"MOV_BANCO cargado: {', '.join(f'{k}: {len(v)} mov' for k, v in resultado.items())}")
        return resultado

    def cargar_facturas_historico(self, path: str | Path) -> pd.DataFrame:
        """Carga facturas históricas (formato Cód./Cuenta/Título/...)."""
        df = pd.read_excel(Path(path), sheet_name="Facturas")
        # Normalizar al formato común
        df = df.rename(columns={"Título": "PROVEEDOR"})
        if "NOMBRE" not in df.columns:
            df["NOMBRE"] = df["PROVEEDOR"].astype(str) + " " + df["Fec.Fac."].astype(str)
        if "OBS" not in df.columns:
            df["OBS"] = ""
        # Preservar Origen solo si tiene formato "T NNN" / "C NNN"
        if "Origen" in df.columns:
            patron_valido = re.compile(r"^[TC]\s+\d+")
            df["Origen"] = df["Origen"].apply(
                lambda x: x if isinstance(x, str) and patron_valido.match(x) else ""
            )
        else:
            df["Origen"] = ""
        if "Total" in df.columns:
            df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
        if "Fec.Fac." in df.columns:
            df["Fec.Fac."] = pd.to_datetime(df["Fec.Fac."], errors="coerce", dayfirst=True)
        self._log(f"Facturas históricas: {len(df)} registros")
        return df

    def cargar_facturas_provisional(self, path: str | Path) -> pd.DataFrame:
        """Carga facturas provisionales (formato NOMBRE/PROVEEDOR/...)."""
        df = pd.read_excel(Path(path))
        # Ya viene en formato correcto, solo normalizar
        if "Origen" not in df.columns:
            df["Origen"] = ""
        else:
            # Limpiar Origen (contiene timestamps de Gmail — sobreescribir)
            df["Origen"] = ""
        if "OBS" not in df.columns:
            df["OBS"] = ""
        if "Total" in df.columns:
            df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
        if "Fec.Fac." in df.columns:
            df["Fec.Fac."] = pd.to_datetime(df["Fec.Fac."], errors="coerce", dayfirst=True)
        self._log(f"Facturas provisionales: {len(df)} registros")
        return df

    def unificar_facturas(
        self,
        hist: Optional[pd.DataFrame] = None,
        prov: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Unifica facturas históricas + provisionales en un solo DataFrame."""
        partes = []
        if hist is not None and len(hist) > 0:
            partes.append(hist)
        if prov is not None and len(prov) > 0:
            partes.append(prov)
        if not partes:
            return pd.DataFrame(columns=["PROVEEDOR", "Fec.Fac.", "Factura", "Total", "Origen", "OBS"])
        df = pd.concat(partes, ignore_index=True)
        # Asegurar columna id interna
        if "Cód." not in df.columns:
            df.insert(0, "Cód.", range(1, len(df) + 1))
        self._log(f"Facturas unificadas: {len(df)} total")
        return df

    # ── Filtro por rango de fechas ────────────────────────────────────────────

    def filtrar_por_fechas(
        self, df: pd.DataFrame, desde: datetime, hasta: datetime
    ) -> pd.DataFrame:
        """Filtra movimientos por rango de fechas sobre F. Operativa."""
        if "F. Operativa" not in df.columns:
            return df
        mask = (df["F. Operativa"] >= pd.Timestamp(desde)) & (df["F. Operativa"] <= pd.Timestamp(hasta))
        filtrado = df[mask].copy().reset_index(drop=True)
        self._log(f"Filtrado {len(filtrado)} de {len(df)} movimientos ({desde.strftime('%d/%m/%Y')} - {hasta.strftime('%d/%m/%Y')})")
        return filtrado

    # ══════════════════════════════════════════════════════════════════════════
    # CAPA 1 — Reglas estructurales
    # ══════════════════════════════════════════════════════════════════════════

    def _capa1_reglas(self, concepto: str, importe: float, fecha_valor, df_mov: pd.DataFrame) -> Optional[Clasificacion]:
        """Aplica reglas estructurales fijas. Devuelve Clasificacion o None."""
        c_upper = concepto.upper().strip()

        # 1a. TPV con detalle de remesa
        if c_upper.startswith("ABONO TPV") or c_upper.startswith("COMISIONES"):
            result = self._clasificar_tpv(c_upper, importe, fecha_valor, df_mov)
            if result:
                return result

        # 1b. Suscripciones sin factura
        for clave, tipo in SUSCRIPCIONES_SIN_FACTURA.items():
            if clave in c_upper:
                return Clasificacion(tipo=tipo, detalle="Sin factura", capa=1, fuente="regla")

        # 1c. Reglas regex genéricas
        for patron, tipo_tpl, detalle_tpl in REGLAS_ESTRUCTURALES:
            m = re.search(patron, c_upper)
            if m:
                # Resolver tipo con grupo de captura si __EXTRACT_1__
                tipo = m.group(1).strip() if tipo_tpl == "__EXTRACT_1__" and m.lastindex else tipo_tpl
                detalle = detalle_tpl or ""
                return Clasificacion(tipo=tipo, detalle=detalle, capa=1, fuente="regla")

        return None

    def _clasificar_tpv(self, concepto: str, importe: float, fecha_valor, df_mov: pd.DataFrame) -> Optional[Clasificacion]:
        """Clasifica ABONO TPV y COMISIONES con detalle de remesa y % comisión."""
        comercio_match = re.search(PATRON_TPV_COMERCIOS, concepto)
        if not comercio_match:
            return None

        numero_comercio = comercio_match.group()
        nombre_comercio = COMERCIOS_TPV.get(numero_comercio, "DESCONOCIDO")

        remesa_match = re.findall(PATRON_TPV_REMESA, concepto)
        numero_remesa = remesa_match[-1] if remesa_match else ""

        fecha_date = _to_date(fecha_valor)
        fd = fecha_date.date() if fecha_date and pd.notna(fecha_date) else None
        clave_control = (fd, numero_comercio, numero_remesa)

        if concepto.startswith("ABONO TPV"):
            if (clave_control, "ABONO") in self._remesas_usadas:
                return Clasificacion(tipo="REVISAR", detalle=f"{numero_remesa} (posible duplicado)", capa=1, fuente="regla")
            self._remesas_usadas.add((clave_control, "ABONO"))
            return Clasificacion(tipo=f"TPV {nombre_comercio}", detalle=numero_remesa, capa=1, fuente="regla")

        if concepto.startswith("COMISIONES"):
            if (clave_control, "COMISION") in self._remesas_usadas:
                return Clasificacion(tipo="REVISAR", detalle=f"{numero_remesa} (posible duplicado)", capa=1, fuente="regla")
            self._remesas_usadas.add((clave_control, "COMISION"))

            # Calcular % comisión buscando el abono correspondiente
            pct_str = ""
            if df_mov is not None and not df_mov.empty and numero_remesa:
                try:
                    abonos = df_mov[
                        (df_mov["Concepto"].str.upper().str.startswith("ABONO TPV")) &
                        (df_mov["Concepto"].str.contains(numero_comercio, na=False)) &
                        (df_mov["Concepto"].str.contains(numero_remesa, na=False))
                    ]
                    if not abonos.empty:
                        abono_imp = abs(float(abonos.iloc[0]["Importe"]))
                        if abono_imp > 0:
                            pct = round((abs(float(importe)) / abono_imp) * 100, 3)
                            pct_str = f" ({pct:.2f}%)"
                except Exception:
                    pass

            return Clasificacion(
                tipo=f"COMISION TPV {nombre_comercio}",
                detalle=f"{numero_remesa}{pct_str}",
                capa=1, fuente="regla",
            )

        return None

    # ══════════════════════════════════════════════════════════════════════════
    # CAPA 2a — Memoria histórica
    # ══════════════════════════════════════════════════════════════════════════

    def _capa2a_memoria(self, concepto: str) -> Optional[Clasificacion]:
        """Busca concepto exacto en memoria histórica."""
        entry = self.memoria.get(concepto.strip())
        if not entry:
            return None
        confianza = entry.get("confianza", "media")
        tipo = entry["tipo"]
        detalle = ""
        if confianza == "media":
            detalle = "(confianza media)"
        return Clasificacion(
            tipo=tipo, detalle=detalle, capa=2, fuente="memoria", confianza=confianza,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CAPA 2b — Cruce con facturas
    # ══════════════════════════════════════════════════════════════════════════

    def _capa2b_facturas(
        self,
        concepto: str,
        importe: float,
        fecha_valor,
        fecha_operativa,
        df_fact: pd.DataFrame,
        nombre_hoja: str,
        mov_num: int,
    ) -> Optional[Clasificacion]:
        """Intenta vincular el movimiento con una factura por importe + fuzzy + fecha."""
        if df_fact is None or df_fact.empty:
            return None

        c_upper = concepto.upper().strip()

        # ── Casos especiales que corren antes del cruce genérico ──

        # Alquiler
        if NOMBRES_ALQUILER_TRIGGER in c_upper:
            return self._cruce_alquiler(fecha_valor, df_fact, nombre_hoja)

        # Comunidad de vecinos + ISTA
        if any(p in c_upper for p in PATRONES_COMUNIDAD):
            return self._cruce_comunidad(fecha_valor, df_fact)

        # Som Energia — buscar por referencia en concepto
        if PATRON_SOM_ENERGIA in c_upper:
            result = self._cruce_som_energia(concepto, importe, df_fact)
            if result:
                return result

        # Yoigo — buscar por referencia en concepto
        if PATRON_YOIGO in c_upper:
            result = self._cruce_yoigo(concepto, df_fact)
            if result:
                return result

        # Suscripciones con factura (MAKE.COM, OPENAI)
        for susc in SUSCRIPCIONES_CON_FACTURA:
            if susc["clave"] in c_upper:
                return self._cruce_suscripcion_con_factura(susc, fecha_valor, df_fact)

        # ── Cruce genérico por importe + fuzzy ──

        # Extraer nombre del emisor según el tipo de movimiento
        nombre_emisor = self._extraer_nombre_emisor(c_upper)
        if not nombre_emisor:
            return None

        # Resolver alias via MAESTRO
        nombre_resuelto, _ = self._buscar_mejor_alias(nombre_emisor)

        return self._buscar_factura_candidata(
            nombre_resuelto, importe, fecha_valor, fecha_operativa, df_fact,
        )

    def _extraer_nombre_emisor(self, concepto: str) -> str:
        """Extrae el nombre del emisor del concepto bancario."""
        if concepto.startswith("TRANSFERENCIA A"):
            return concepto.replace("TRANSFERENCIA A", "").strip()
        if concepto.startswith("ADEUDO RECIBO"):
            return concepto.replace("ADEUDO RECIBO", "").strip()
        if concepto.startswith("COMPRA TARJ"):
            # Casos especiales tarjeta
            for regla in REGLAS_ESPECIALES_TARJETA:
                if regla["clave"] in concepto:
                    return regla["titulo"]
            # Nombre a partir posición 30
            try:
                return concepto[30:].split("-")[0].strip()
            except (IndexError, TypeError):
                return ""
        return ""

    def _buscar_mejor_alias(self, nombre: str) -> tuple[str, bool]:
        """Busca match en MAESTRO. Devuelve (nombre_resuelto, encontrado)."""
        nombre_norm = normalizar_nombre(nombre)
        if not self.indice_aliases:
            return nombre, False

        exact = self.indice_aliases.get(nombre_norm)
        if exact:
            return exact, True

        mejor_score = 0.0
        mejor_titulo = nombre
        for alias, titulo in self.indice_aliases.items():
            score = fuzz.token_sort_ratio(normalizar_nombre(nombre), alias) / 100
            if score > mejor_score:
                mejor_score = score
                mejor_titulo = titulo

        return (mejor_titulo, mejor_score >= 0.85) if mejor_score >= 0.60 else (nombre, False)

    def _similitud(self, a: str, b: str) -> float:
        return fuzz.token_sort_ratio(normalizar_nombre(a), normalizar_nombre(b)) / 100

    def _similitud_con_aliases(self, nombre_emisor: str, titulo_factura: str) -> float:
        """Calcula similitud incluyendo aliases del MAESTRO."""
        mejor = self._similitud(nombre_emisor, titulo_factura)
        titulo_norm = normalizar_nombre(titulo_factura)
        aliases = self.df_fuzzy.loc[
            self.df_fuzzy["TITULO_FACTURA"] == nombre_emisor, "NOMBRE_EN_CONCEPTO"
        ]
        for alias_norm in aliases:
            score = fuzz.token_sort_ratio(alias_norm, titulo_norm) / 100
            if score > mejor:
                mejor = score
        return mejor

    def _buscar_factura_candidata(
        self,
        nombre_emisor: str,
        importe: float,
        fecha_valor,
        fecha_operativa,
        df_fact: pd.DataFrame,
    ) -> Optional[Clasificacion]:
        """Cruce genérico: importe exacto + fuzzy + ventana temporal."""
        importe_abs = round(abs(float(importe)), 2)
        candidatas = df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01].copy()

        if candidatas.empty:
            return None  # Sin match por importe → dejar para Capa 3

        # Fuzzy scores
        candidatas = candidatas.copy()
        candidatas["_score"] = candidatas["PROVEEDOR"].apply(
            lambda t: self._similitud_con_aliases(nombre_emisor, t)
        )

        # Filtrar por umbral
        ok = candidatas[candidatas["_score"] >= UMBRAL_FUZZY_MINIMO].copy()
        if ok.empty:
            # Ninguna pasa fuzzy — intentar desambiguar por nombre parcial
            mejor = candidatas.loc[candidatas["_score"].idxmax()]
            return Clasificacion(
                tipo="REVISAR",
                detalle=f"¿#{mejor['Cód.']} {mejor['PROVEEDOR']}? (fuzzy {mejor['_score']*100:.0f}%)",
                capa=2, fuente="factura",
            )

        # Excluir ya usadas
        disponibles = ok[~ok["Cód."].isin(self.facturas_usadas)].copy()
        if disponibles.empty:
            mejor_usada = ok.loc[ok["_score"].idxmax()]
            return Clasificacion(
                tipo="REVISAR",
                detalle=f"Posible duplicado con #{mejor_usada['Cód.']}",
                capa=2, fuente="factura",
            )

        # Desempatar por fecha
        fecha_mov = _to_date(fecha_valor)
        if fecha_mov is None or pd.isna(fecha_mov):
            fecha_mov = _to_date(fecha_operativa)

        if fecha_mov is not None and pd.notna(fecha_mov):
            disponibles["_dias"] = (disponibles["Fec.Fac."] - fecha_mov).dt.days
            ventana = disponibles[(disponibles["_dias"] >= -90) & (disponibles["_dias"] <= 15)].copy()
            if not ventana.empty:
                ventana["_dias_abs"] = ventana["_dias"].abs()
                ventana = ventana.sort_values("_dias_abs")
                fila = ventana.iloc[0]
                return self._fila_a_clasificacion(fila, nombre_emisor)

        # Sin fecha → mejor fuzzy
        fila = disponibles.loc[disponibles["_score"].idxmax()]
        return self._fila_a_clasificacion(fila, nombre_emisor)

    def _fila_a_clasificacion(self, fila, nombre_emisor: str) -> Clasificacion:
        """Convierte una fila de factura candidata en Clasificacion."""
        cod = fila["Cód."]
        titulo = fila["PROVEEDOR"]
        score = fila["_score"]
        ref = fila.get("Factura", "")
        self.facturas_usadas.add(cod)

        detalle_parts = [f"#{cod}"]
        if pd.notna(ref) and str(ref).strip():
            detalle_parts.append(f"({ref})")
        if score < UMBRAL_FUZZY_INDICAR:
            detalle_parts.append(f"(fuzzy {score*100:.0f}%)")

        return Clasificacion(
            tipo=titulo,
            detalle=" ".join(detalle_parts),
            capa=2, fuente="factura",
            factura_ids=[int(cod)],
        )

    # ── Cruces especiales ─────────────────────────────────────────────────────

    def _cruce_alquiler(self, fecha_valor, df_fact: pd.DataFrame, nombre_hoja: str) -> Clasificacion:
        fecha_v = _to_date(fecha_valor)
        facturas_encontradas = []
        for titulos, label in PROPIETARIOS_ALQUILER:
            patron = "|".join([t.upper() for t in titulos])
            df_prop = df_fact[
                df_fact["PROVEEDOR"].str.upper().str.contains(patron, na=False, regex=True)
            ].copy()
            if not df_prop.empty and fecha_v is not None and pd.notna(fecha_v):
                mismo_mes = df_prop[
                    (df_prop["Fec.Fac."].dt.month == fecha_v.month) &
                    (df_prop["Fec.Fac."].dt.year == fecha_v.year) &
                    (~df_prop["Cód."].isin(self.facturas_usadas))
                ]
                if not mismo_mes.empty:
                    cod = mismo_mes.iloc[0]["Cód."]
                    self.facturas_usadas.add(cod)
                    facturas_encontradas.append(int(cod))

        if facturas_encontradas:
            detalle = ", ".join(f"#{c}" for c in facturas_encontradas)
            if len(facturas_encontradas) < 2:
                mes_str = fecha_v.strftime("%m/%Y") if fecha_v and pd.notna(fecha_v) else "?"
                detalle += f" (falta 1 factura {mes_str})"
            return Clasificacion(tipo="ALQUILER", detalle=detalle, capa=2, fuente="factura", factura_ids=facturas_encontradas)

        mes_str = fecha_v.strftime("%m/%Y") if fecha_v and pd.notna(fecha_v) else "?"
        return Clasificacion(tipo="ALQUILER", detalle=f"Sin facturas para {mes_str}", capa=2, fuente="factura")

    def _cruce_comunidad(self, fecha_valor, df_fact: pd.DataFrame) -> Clasificacion:
        fecha_mov = _to_date(fecha_valor)
        df_ista = df_fact[df_fact["PROVEEDOR"].str.upper().str.contains(PATRON_ISTA, na=False)].copy()

        if not df_ista.empty and fecha_mov is not None and pd.notna(fecha_mov):
            disponibles = df_ista[~df_ista["Cód."].isin(self.facturas_usadas)].copy()
            if not disponibles.empty:
                disponibles["_dist"] = abs((disponibles["Fec.Fac."] - fecha_mov).dt.days)
                disponibles = disponibles.sort_values("_dist")
                ids = []
                for _, fila in disponibles.head(2).iterrows():
                    cod = fila["Cód."]
                    self.facturas_usadas.add(cod)
                    ids.append(int(cod))
                if ids:
                    return Clasificacion(
                        tipo="COMUNIDAD DE VECINOS",
                        detalle=", ".join(f"#{c}" for c in ids),
                        capa=2, fuente="factura",
                        factura_ids=ids,
                    )

        return Clasificacion(tipo="COMUNIDAD DE VECINOS", detalle="", capa=2, fuente="factura")

    def _cruce_som_energia(self, concepto: str, importe: float, df_fact: pd.DataFrame) -> Optional[Clasificacion]:
        c_upper = concepto.upper()
        match = re.search(PATRON_SOM_REF, c_upper)
        if match:
            num_factura = match.group(1)
            fila = df_fact[df_fact["Factura"].astype(str).str.upper().str.contains(num_factura, na=False)]
            if not fila.empty:
                cod = fila.iloc[0]["Cód."]
                if cod in self.facturas_usadas:
                    return Clasificacion(tipo="REVISAR", detalle=f"Posible duplicado con #{cod}", capa=2, fuente="factura")
                self.facturas_usadas.add(cod)
                return Clasificacion(
                    tipo="SOM ENERGIA SCCL",
                    detalle=f"#{cod} ({num_factura})",
                    capa=2, fuente="factura",
                    factura_ids=[int(cod)],
                )

        # Fallback por importe
        importe_abs = round(abs(float(importe)), 2)
        candidatas = df_fact[abs(df_fact["Total"] - importe_abs) <= 0.01]
        som = candidatas[candidatas["PROVEEDOR"].str.upper().str.contains(PATRON_SOM_ENERGIA, na=False)]
        if len(som) == 1:
            fila = som.iloc[0]
            cod = fila["Cód."]
            if cod in self.facturas_usadas:
                return Clasificacion(tipo="REVISAR", detalle=f"Posible duplicado con #{cod}", capa=2, fuente="factura")
            self.facturas_usadas.add(cod)
            ref = fila.get("Factura", "")
            detalle = f"#{cod}"
            if pd.notna(ref) and str(ref).strip():
                detalle += f" ({ref})"
            return Clasificacion(tipo="SOM ENERGIA SCCL", detalle=detalle, capa=2, fuente="factura", factura_ids=[int(cod)])

        return None

    def _cruce_yoigo(self, concepto: str, df_fact: pd.DataFrame) -> Optional[Clasificacion]:
        c_upper = concepto.upper()
        match = re.search(PATRON_YOIGO_REGEX, c_upper)
        if not match:
            return Clasificacion(tipo="REVISAR", detalle="YOIGO: No se encontró número de factura", capa=2, fuente="factura")

        numero_original = match.group(0)
        numero_sin_y = match.group(1)

        df_yoigo = df_fact[
            df_fact["PROVEEDOR"].str.upper().str.contains("XFERA|YOIGO|MASMOVIL", na=False, regex=True)
        ].copy()

        if df_yoigo.empty:
            return Clasificacion(tipo="REVISAR", detalle=f"YOIGO: No hay facturas XFERA ({numero_original})", capa=2, fuente="factura")

        df_yoigo["_ref_norm"] = df_yoigo["Factura"].astype(str).str.upper().str.strip()

        # Buscar por ref exacta
        for ref in (numero_original, numero_sin_y):
            exacto = df_yoigo[df_yoigo["_ref_norm"] == ref]
            if not exacto.empty:
                cod = exacto.iloc[0]["Cód."]
                if cod in self.facturas_usadas:
                    return Clasificacion(tipo="REVISAR", detalle=f"Posible duplicado con #{cod}", capa=2, fuente="factura")
                self.facturas_usadas.add(cod)
                return Clasificacion(
                    tipo="XFERA MOVILES SAU",
                    detalle=f"#{cod} ({ref})",
                    capa=2, fuente="factura",
                    factura_ids=[int(cod)],
                )

        # Fuzzy fallback ≥90%
        mejor_score = 0
        mejor_fila = None
        for _, fila in df_yoigo.iterrows():
            score = max(
                fuzz.ratio(numero_original, fila["_ref_norm"]),
                fuzz.ratio(numero_sin_y, fila["_ref_norm"]),
            )
            if score > mejor_score and fila["Cód."] not in self.facturas_usadas:
                mejor_score = score
                mejor_fila = fila

        if mejor_score >= 90 and mejor_fila is not None:
            cod = mejor_fila["Cód."]
            self.facturas_usadas.add(cod)
            return Clasificacion(
                tipo="XFERA MOVILES SAU",
                detalle=f"#{cod} ({mejor_fila['_ref_norm']}) [fuzzy {mejor_score}%]",
                capa=2, fuente="factura",
                factura_ids=[int(cod)],
            )

        return Clasificacion(tipo="REVISAR", detalle=f"Factura YOIGO no encontrada ({numero_original})", capa=2, fuente="factura")

    def _cruce_suscripcion_con_factura(self, susc: dict, fecha_valor, df_fact: pd.DataFrame) -> Clasificacion:
        titulo = susc["titulo"]
        patron = "|".join([titulo.upper()] + [a.upper() for a in susc["aliases"]])
        df_prov = df_fact[
            df_fact["PROVEEDOR"].str.upper().str.contains(patron, na=False, regex=True)
        ].copy()

        if df_prov.empty:
            return Clasificacion(tipo="REVISAR", detalle=f"No hay facturas de {titulo}", capa=2, fuente="factura")

        fecha_v = _to_date(fecha_valor)
        if fecha_v is None or pd.isna(fecha_v):
            return Clasificacion(tipo="REVISAR", detalle=f"{titulo} - fecha inválida", capa=2, fuente="factura")

        mismo_mes = df_prov[
            (df_prov["Fec.Fac."].dt.month == fecha_v.month) &
            (df_prov["Fec.Fac."].dt.year == fecha_v.year) &
            (~df_prov["Cód."].isin(self.facturas_usadas))
        ]
        if not mismo_mes.empty:
            cod = mismo_mes.iloc[0]["Cód."]
            self.facturas_usadas.add(cod)
            return Clasificacion(
                tipo=titulo,
                detalle=f"#{cod} {titulo}",
                capa=2, fuente="factura",
                factura_ids=[int(cod)],
            )

        return Clasificacion(
            tipo="REVISAR",
            detalle=f"Sin factura de {titulo} para {fecha_v.strftime('%m/%Y')}",
            capa=2, fuente="factura",
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CAPA 3 — Sin clasificar
    # ══════════════════════════════════════════════════════════════════════════

    def _capa3_revisar(self, concepto: str) -> Clasificacion:
        """Genera clasificación REVISAR con sugerencia si hay pistas en el concepto."""
        c_upper = concepto.upper()
        sugerencia = ""
        # Intentar extraer algo útil del concepto
        for prefijo in ("TRANSFERENCIA A", "ADEUDO RECIBO", "COMPRA TARJ"):
            if prefijo in c_upper:
                nombre = c_upper.split(prefijo)[-1].strip()[:40]
                if nombre:
                    sugerencia = f"Concepto contiene: {nombre}"
                break
        return Clasificacion(tipo="REVISAR", detalle=sugerencia, capa=3, fuente="revisar")

    # ══════════════════════════════════════════════════════════════════════════
    # CLASIFICADOR PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    def clasificar_movimiento(
        self,
        concepto: str,
        importe: float,
        fecha_valor,
        fecha_operativa,
        df_fact: pd.DataFrame,
        df_mov: pd.DataFrame,
        nombre_hoja: str,
        mov_num: int,
    ) -> Clasificacion:
        """Aplica las 3 capas en orden. La primera que resuelve, gana."""
        concepto = str(concepto).strip()

        # Capa 1 — Reglas estructurales
        c1 = self._capa1_reglas(concepto, importe, fecha_valor, df_mov)
        if c1:
            self._log(f"[{nombre_hoja} #{mov_num}] CAPA1 → {c1.tipo}: {c1.detalle}")
            return c1

        # Capa 2 — Memoria + Facturas
        c2a = self._capa2a_memoria(concepto)
        c2b = self._capa2b_facturas(concepto, importe, fecha_valor, fecha_operativa, df_fact, nombre_hoja, mov_num)

        # Resolución: factura gana sobre memoria (más específica)
        if c2b and c2b.tipo != "REVISAR":
            self._log(f"[{nombre_hoja} #{mov_num}] CAPA2b → {c2b.tipo}: {c2b.detalle}")
            return c2b
        if c2a:
            self._log(f"[{nombre_hoja} #{mov_num}] CAPA2a → {c2a.tipo}: {c2a.detalle}")
            return c2a
        # Si 2b devolvió REVISAR con info útil, usarlo
        if c2b:
            self._log(f"[{nombre_hoja} #{mov_num}] CAPA2b(REVISAR) → {c2b.detalle}")
            return c2b

        # Capa 3 — Fallback
        c3 = self._capa3_revisar(concepto)
        self._log(f"[{nombre_hoja} #{mov_num}] CAPA3 → REVISAR: {c3.detalle}")
        return c3

    # ══════════════════════════════════════════════════════════════════════════
    # PROCESAMIENTO COMPLETO
    # ══════════════════════════════════════════════════════════════════════════

    def procesar(
        self,
        movimientos: dict[str, pd.DataFrame],
        df_facturas: pd.DataFrame,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> ResultadoCuadre:
        """
        Ejecuta el cuadre completo.

        Args:
            movimientos: dict con DataFrames de movimientos por hoja (Tasca, Comestibles)
            df_facturas: DataFrame unificado de facturas
            desde/hasta: filtro de fechas (opcional)

        Returns:
            ResultadoCuadre con DataFrames y estadísticas
        """
        # Reset estado
        self.facturas_usadas = set()
        self.vinculos = {}
        self._remesas_usadas = set()
        self.log_lines = []

        self._log(f"CUADRE ENGINE v2.0 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Memoria: {len(self.memoria)} conceptos")

        stats = {
            "capa1": 0, "capa2a": 0, "capa2b": 0, "capa3": 0,
            "total": 0,
            "por_hoja": {},
        }

        resultados_hojas: dict[str, pd.DataFrame] = {}

        for nombre_hoja, df_mov in movimientos.items():
            # Filtrar por fechas si se especifican
            if desde and hasta:
                df_mov = self.filtrar_por_fechas(df_mov, desde, hasta)

            # Reset remesas por hoja (no facturas)
            self._remesas_usadas = set()

            self._log(f"\n{'='*60}\nPROCESANDO: {nombre_hoja} ({len(df_mov)} movimientos)\n{'='*60}")

            # Asegurar columnas de salida
            df = df_mov.copy()
            df["Categoria_Tipo"] = ""
            df["Categoria_Detalle"] = ""

            hoja_stats = {"total": len(df), "capa1": 0, "capa2a": 0, "capa2b": 0, "capa3": 0}

            for idx, row in df.iterrows():
                concepto = row.get("Concepto", "")
                importe = row.get("Importe", 0)
                fecha_valor = row.get("F. Valor")
                fecha_operativa = row.get("F. Operativa")
                mov_num = row.get("#", idx)

                result = self.clasificar_movimiento(
                    concepto, importe, fecha_valor, fecha_operativa,
                    df_facturas, df_mov, nombre_hoja, mov_num,
                )

                df.at[idx, "Categoria_Tipo"] = result.tipo
                df.at[idx, "Categoria_Detalle"] = result.detalle

                # Registrar vínculos
                if result.tipo != "REVISAR" and result.factura_ids:
                    prefijo = "T" if "tasca" in nombre_hoja.lower() else "C"
                    for fid in result.factura_ids:
                        self.vinculos.setdefault(fid, []).append((prefijo, mov_num))

                # Stats
                capa_key = f"capa{result.capa}" if result.capa in (1, 2, 3) else "capa3"
                if result.capa == 2:
                    capa_key = "capa2a" if result.fuente == "memoria" else "capa2b"
                stats[capa_key] += 1
                hoja_stats[capa_key] += 1

            stats["total"] += len(df)
            stats["por_hoja"][nombre_hoja] = hoja_stats
            resultados_hojas[nombre_hoja] = df

        # Generar columna Origen en facturas
        df_fact_out = df_facturas.copy()
        df_fact_out["Origen"] = self._generar_columna_origen(df_fact_out)

        # Formatear fechas para salida
        for nombre, df in resultados_hojas.items():
            resultados_hojas[nombre] = self._formatear_fechas(df)
        df_fact_out = self._formatear_fechas(df_fact_out)

        # Eliminar columnas internas
        for nombre, df in resultados_hojas.items():
            resultados_hojas[nombre] = df.drop(
                columns=[c for c in df.columns if c.startswith("_")], errors="ignore"
            )

        return ResultadoCuadre(
            df_tasca=resultados_hojas.get("Tasca", pd.DataFrame()),
            df_comestibles=resultados_hojas.get("Comestibles", pd.DataFrame()),
            df_facturas=df_fact_out,
            stats=stats,
            log=self.log_lines,
        )

    # ── Origen en facturas ────────────────────────────────────────────────────

    def _generar_columna_origen(self, df_fact: pd.DataFrame) -> pd.Series:
        """Genera la columna Origen para la hoja Facturas."""
        origenes = []
        for _, row in df_fact.iterrows():
            fac_id = row.get("Cód.")
            if fac_id is None or pd.isna(fac_id):
                origenes.append("")
                continue
            try:
                fac_id = int(fac_id)
            except (ValueError, TypeError):
                origenes.append("")
                continue

            refs = self.vinculos.get(fac_id, [])
            if not refs:
                origenes.append("")
                continue

            refs_sorted = sorted(refs, key=lambda x: x[1])

            # Detectar proveedor de pagos parciales
            titulo = str(row.get("PROVEEDOR", row.get("Título", ""))).upper()
            es_parcial = any(p in titulo for p in PROVEEDORES_PAGOS_PARCIALES)

            if es_parcial and len(refs_sorted) > 1:
                origenes.append(f"Pagos parciales ({len(refs_sorted)})")
            elif len(refs_sorted) <= 4:
                origenes.append(", ".join(f"{h} {n}" for h, n in refs_sorted))
            else:
                primeros = ", ".join(f"{h} {n}" for h, n in refs_sorted[:4])
                origenes.append(f"{primeros} (+{len(refs_sorted) - 4})")

        return pd.Series(origenes, index=df_fact.index)

    # ── Formateo de salida ────────────────────────────────────────────────────

    @staticmethod
    def _formatear_fechas(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in ["F. Operativa", "F. Valor", "Fec.Fac."]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                df[col] = df[col].dt.strftime("%d-%m-%y")
                df[col] = df[col].fillna("")
        return df

    @staticmethod
    def eliminar_columnas_unnamed(df: pd.DataFrame) -> pd.DataFrame:
        cols = [c for c in df.columns if str(c).startswith("Unnamed")]
        return df.drop(columns=cols) if cols else df

    # ══════════════════════════════════════════════════════════════════════════
    # GUARDAR RESULTADO
    # ══════════════════════════════════════════════════════════════════════════

    def guardar_excel(self, resultado: ResultadoCuadre, ruta: str | Path):
        """Guarda el resultado en un archivo Excel con formato correcto."""
        ruta = Path(ruta)
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            if not resultado.df_tasca.empty:
                df = self.eliminar_columnas_unnamed(resultado.df_tasca)
                df.to_excel(writer, sheet_name="Tasca", index=False)
            if not resultado.df_comestibles.empty:
                df = self.eliminar_columnas_unnamed(resultado.df_comestibles)
                df.to_excel(writer, sheet_name="Comestibles", index=False)
            if not resultado.df_facturas.empty:
                df = self.eliminar_columnas_unnamed(resultado.df_facturas)
                # Reordenar: Origen antes de OBS
                cols = list(df.columns)
                for obs_col in ("OBS", "OBSERVACIONES"):
                    if obs_col in cols and "Origen" in cols:
                        cols.remove("Origen")
                        cols.insert(cols.index(obs_col), "Origen")
                        df = df[cols]
                        break
                df.to_excel(writer, sheet_name="Facturas", index=False)

    def guardar_log(self, resultado: ResultadoCuadre, ruta: str | Path):
        """Guarda el log de decisiones."""
        ruta = Path(ruta)
        ruta_log = ruta.with_name(ruta.stem + "_log.txt")
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("LOG DE DECISIONES — CUADRE ENGINE v2.0\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            for line in resultado.log:
                f.write(line + "\n")
        return ruta_log

    def exportar_json_streamlit(self, resultado: ResultadoCuadre, ruta_json: str | Path):
        """Exporta resumen JSON para el puente de datos Streamlit."""
        stats = resultado.stats
        hojas = {}
        revisar_detalle = []

        for nombre, df in [("Tasca", resultado.df_tasca), ("Comestibles", resultado.df_comestibles)]:
            if df.empty:
                continue
            n_total = len(df)
            n_revisar = len(df[df["Categoria_Tipo"] == "REVISAR"])
            n_ok = n_total - n_revisar
            hojas[nombre] = {
                "total": n_total, "ok": n_ok, "revisar": n_revisar,
                "pct_ok": round(100 * n_ok / n_total, 1) if n_total else 0,
            }
            for _, row in df[df["Categoria_Tipo"] == "REVISAR"].head(25).iterrows():
                revisar_detalle.append({
                    "hoja": nombre,
                    "fecha": str(row.get("F. Operativa", "")),
                    "concepto": str(row.get("Concepto", ""))[:80],
                    "importe": float(row.get("Importe", 0)),
                    "detalle": str(row.get("Categoria_Detalle", ""))[:100],
                })

        total_mov = stats["total"]
        total_revisar = stats["capa3"]
        resumen = {
            "fecha_ejecucion": datetime.now().isoformat(timespec="seconds"),
            "hojas": hojas,
            "clasificacion": {
                "capa1_reglas": stats["capa1"],
                "capa2a_memoria": stats["capa2a"],
                "capa2b_facturas": stats["capa2b"],
                "capa3_revisar": stats["capa3"],
            },
            "total": {
                "total": total_mov,
                "ok": total_mov - total_revisar,
                "revisar": total_revisar,
                "pct_ok": round(100 * (total_mov - total_revisar) / total_mov, 1) if total_mov else 0,
            },
            "revisar_detalle": revisar_detalle[:50],
        }

        ruta = Path(ruta_json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)

    # ══════════════════════════════════════════════════════════════════════════
    # MODO APRENDER
    # ══════════════════════════════════════════════════════════════════════════

    def aprender_de_cuadre(self, cuadre_path: str | Path, memoria_path: str | Path):
        """
        Lee un CUADRE corregido y actualiza la memoria histórica (merge).

        Nuevos conceptos → añadir.
        Misma categoría → incrementar veces.
        Categoría diferente → recalcular confianza.
        """
        cuadre_path = Path(cuadre_path)
        memoria_path = Path(memoria_path)

        # Cargar memoria existente
        memoria = {}
        if memoria_path.exists():
            with open(memoria_path, "r", encoding="utf-8") as f:
                memoria = json.load(f)

        xlsx = pd.ExcelFile(cuadre_path)

        for sheet in xlsx.sheet_names:
            sn = sheet.strip().upper()
            if sn not in ("TASCA", "COMESTIBLES"):
                continue
            df = pd.read_excel(xlsx, sheet_name=sheet)
            if "Concepto" not in df.columns or "Categoria_Tipo" not in df.columns:
                continue

            for _, row in df.iterrows():
                concepto = str(row.get("Concepto", "")).strip()
                tipo = str(row.get("Categoria_Tipo", "")).strip()
                if not concepto or not tipo or tipo == "REVISAR":
                    continue

                if concepto in memoria:
                    entry = memoria[concepto]
                    if entry["tipo"] == tipo:
                        entry["veces"] = entry.get("veces", 1) + 1
                        entry["confianza"] = "alta"
                    else:
                        # Categoría diferente → registrar alternativa
                        alts = entry.get("alternativas", [])
                        if tipo not in alts:
                            alts.append(tipo)
                        entry["alternativas"] = alts
                        total = entry.get("veces", 1) + 1
                        entry["veces"] = total
                        # Recalcular confianza
                        if len(alts) == 0:
                            entry["confianza"] = "alta"
                        else:
                            entry["confianza"] = "media"
                else:
                    memoria[concepto] = {
                        "tipo": tipo,
                        "confianza": "alta",
                        "veces": 1,
                    }

        # Guardar
        with open(memoria_path, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=2)

        self._log(f"Memoria actualizada: {len(memoria)} conceptos → {memoria_path}")
        return len(memoria)
