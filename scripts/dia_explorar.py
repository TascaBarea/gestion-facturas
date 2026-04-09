"""
Script de exploración: dia.es usando requests + cookies exportadas.

Enfoque: en vez de automatizar un navegador (que Dia bloquea),
usamos requests HTTP directos con cookies de una sesión ya logueada.

Paso 1: login manual en tu navegador
Paso 2: exportar cookies con extensión (o desde DevTools)
Paso 3: este script usa esas cookies para acceder a la API interna de Dia

Uso: python scripts/dia_explorar.py
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def explorar_con_requests():
    """Intenta acceder a la API interna de Dia con requests simples."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.dia.es/",
        "Origin": "https://www.dia.es",
    })

    # 1. Probar login via API directa
    print("1. Intentando login via API...")
    from config.datos_sensibles import DIA_EMAIL, DIA_PASSWORD

    # Probar endpoint de login (descubierto en exploración anterior)
    login_urls = [
        "https://www.dia.es/api/v3/eservice-back/auth/login",
        "https://www.dia.es/api/v1/auth/login",
        "https://api-customers.dia.es/api/v1/auth/login",
        "https://www.dia.es/orders/api/v3/eservice-back/auth/login",
    ]

    login_payloads = [
        {"email": DIA_EMAIL, "password": DIA_PASSWORD},
        {"username": DIA_EMAIL, "password": DIA_PASSWORD},
    ]

    for url in login_urls:
        for payload in login_payloads:
            try:
                r = session.post(url, json=payload, timeout=10)
                print(f"   POST {url}")
                print(f"   Payload: {list(payload.keys())}")
                print(f"   Status: {r.status_code}")
                if r.status_code < 400:
                    print(f"   Response: {r.text[:500]}")
                    # Guardar cookies de sesión
                    if r.cookies:
                        print(f"   Cookies: {dict(r.cookies)}")
                elif r.status_code != 404:
                    print(f"   Response: {r.text[:300]}")
                print()
            except Exception as e:
                print(f"   {url} → Error: {e}\n")

    # 2. Probar endpoints sin auth (descubrir estructura)
    print("\n2. Explorando endpoints públicos...")
    endpoints = [
        "https://www.dia.es/api/v3/eservice-back/health",
        "https://www.dia.es/api/v3/eservice-back/user",
        "https://www.dia.es/api/v3/eservice-back/user/profile",
        "https://www.dia.es/api/v3/eservice-back/orders",
        "https://www.dia.es/api/v3/eservice-back/tickets",
        "https://www.dia.es/api/v3/eservice-back/purchases",
        "https://www.dia.es/api/v3/eservice-back/receipts",
        "https://api-customers.dia.es/api/v1/user",
        "https://api-customers.dia.es/api/v1/tickets",
    ]

    for url in endpoints:
        try:
            r = session.get(url, timeout=10)
            print(f"   GET {url}")
            print(f"   Status: {r.status_code}")
            if r.status_code < 400:
                print(f"   Response: {r.text[:500]}")
            elif r.status_code == 401:
                print(f"   (Requiere auth)")
            print()
        except Exception as e:
            print(f"   {url} → Error: {e}\n")

    print("\n=== Exploración completada ===")


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    explorar_con_requests()
