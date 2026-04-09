#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_memoria.py — Genera clasificaciones_historicas.json desde un CUADRE existente.

Lee las pestañas Tasca y Comestibles de un CUADRE ya clasificado y genera
un JSON con la memoria histórica de conceptos → categorías.

Reglas de confianza:
  - Concepto siempre clasificado igual → "alta"
  - Concepto clasificado ≥70% igual    → "media" + alternativas
  - Concepto ambiguo (<70%)            → excluido

USO:
    python -m cuadre.banco.generar_memoria \\
        --cuadre "outputs/Cuadre_020125-311225.xlsx" \\
        --output "datos/clasificaciones_historicas.json"

    # Solo analizar sin escribir:
    python -m cuadre.banco.generar_memoria \\
        --cuadre "outputs/Cuadre_020125-311225.xlsx" --dry-run
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def generar_memoria(cuadre_path: str | Path) -> dict:
    """
    Lee un CUADRE clasificado y genera el diccionario de memoria.

    Returns:
        dict {concepto: {tipo, confianza, veces, alternativas?}}
    """
    cuadre_path = Path(cuadre_path)
    xlsx = pd.ExcelFile(cuadre_path)

    # Recopilar todas las clasificaciones: concepto → [tipo1, tipo1, tipo2, ...]
    clasificaciones: dict[str, list[str]] = {}

    for sheet in xlsx.sheet_names:
        sn = sheet.strip().upper()
        if sn not in ("TASCA", "COMESTIBLES"):
            continue

        df = pd.read_excel(xlsx, sheet_name=sheet)
        if "Concepto" not in df.columns or "Categoria_Tipo" not in df.columns:
            print(f"  ⚠️  Hoja '{sheet}' sin columnas esperadas, saltando")
            continue

        for _, row in df.iterrows():
            concepto = str(row.get("Concepto", "")).strip()
            tipo = str(row.get("Categoria_Tipo", "")).strip()

            if not concepto or not tipo or tipo == "REVISAR":
                continue

            clasificaciones.setdefault(concepto, []).append(tipo)

    # Generar memoria con reglas de confianza
    memoria = {}
    excluidos = 0

    for concepto, tipos in clasificaciones.items():
        counter = Counter(tipos)
        total = len(tipos)
        tipo_principal, veces_principal = counter.most_common(1)[0]

        ratio = veces_principal / total

        if ratio >= 0.99:
            # Siempre igual → alta
            entry = {
                "tipo": tipo_principal,
                "confianza": "alta",
                "veces": total,
            }
        elif ratio >= 0.70:
            # Mayoritariamente igual → media + alternativas
            alternativas = [t for t, _ in counter.most_common() if t != tipo_principal]
            entry = {
                "tipo": tipo_principal,
                "confianza": "media",
                "veces": total,
                "alternativas": alternativas,
            }
        else:
            # Demasiado ambiguo → excluir
            excluidos += 1
            continue

        memoria[concepto] = entry

    print(f"  Conceptos procesados: {len(clasificaciones)}")
    print(f"  Memoria generada: {len(memoria)} conceptos")
    print(f"  Excluidos (ambiguos): {excluidos}")

    alta = sum(1 for v in memoria.values() if v["confianza"] == "alta")
    media = sum(1 for v in memoria.values() if v["confianza"] == "media")
    print(f"  Alta confianza: {alta}")
    print(f"  Media confianza: {media}")

    return memoria


def main():
    parser = argparse.ArgumentParser(
        description="Genera clasificaciones_historicas.json desde un CUADRE existente",
    )
    parser.add_argument("--cuadre", required=True, help="Ruta al CUADRE clasificado (.xlsx)")
    parser.add_argument("--output", "-o", help="Ruta de salida JSON (default: datos/clasificaciones_historicas.json)")
    parser.add_argument("--dry-run", action="store_true", help="Solo analizar, no escribir")

    args = parser.parse_args()

    cuadre_path = Path(args.cuadre)
    if not cuadre_path.exists():
        print(f"❌ Archivo no encontrado: {cuadre_path}")
        return

    print(f"GENERAR MEMORIA — {cuadre_path.name}")
    memoria = generar_memoria(cuadre_path)

    if args.dry_run:
        print("\n  (dry-run: no se escribió ningún archivo)")
        # Mostrar top 10 tipos
        from collections import Counter as C
        tipos = C(v["tipo"] for v in memoria.values())
        print("\n  Top 10 tipos:")
        for tipo, count in tipos.most_common(10):
            print(f"    {count:>4}× {tipo}")
        return

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).resolve().parent.parent.parent / "datos" / "clasificaciones_historicas.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ Guardado: {output_path}")
    print(f"     {len(memoria)} conceptos")


if __name__ == "__main__":
    main()
