#!/usr/bin/env python3
"""
CLI runner para el scraper de becas.
Soporta ejecución individual de spiders y subida CSV a la API de BecasFind.

Uso:
    python run_spider.py mineduc                          # Ejecuta solo el spider Mineduc
    python run_spider.py mineduc --upload                 # Ejecuta y sube el CSV a la API
    python run_spider.py mineduc --api-url http://...     # Especifica URL de la API
    python run_spider.py all                              # Ejecuta todos los spiders
"""

import argparse
import csv
import os
import sys
from typing import Optional

import requests
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


API_LOGIN_URL = "http://localhost:8080/api/auth/login"
API_IMPORT_URL = "http://localhost:8080/api/becas/importar-csv"
ADMIN_EMAIL = "admin@becasfind.cl"
ADMIN_PASSWORD = "admin123"


def login_to_api(api_base_url: str) -> Optional[str]:
    login_url = f"{api_base_url.rstrip('/')}/api/auth/login"
    try:
        resp = requests.post(
            login_url,
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("data", {}).get("token") or data.get("token")
        if token:
            print(f"[AUTH] Token JWT obtenido: {token[:30]}...")
            return token
        print("[AUTH] Error: no se encontró token en la respuesta")
        return None
    except requests.RequestException as e:
        print(f"[AUTH] Error de conexión: {e}")
        return None


def upload_csv(api_base_url: str, token: str, csv_path: str) -> None:
    import_url = f"{api_base_url.rstrip('/')}/api/becas/importar-csv"
    try:
        with open(csv_path, "rb") as f:
            resp = requests.post(
                import_url,
                files={"file": (os.path.basename(csv_path), f, "text/csv")},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
        resp.raise_for_status()
        result = resp.json()
        data = result.get("data", result)
        print(f"[UPLOAD] Creadas: {data.get('creadas', 0)}, "
              f"Actualizadas: {data.get('actualizadas', 0)}, "
              f"Errores: {data.get('errores', 0)}")
        if data.get("mensajesError"):
            for msg in data["mensajesError"][:5]:
                print(f"  ⚠ {msg}")
    except requests.RequestException as e:
        print(f"[UPLOAD] Error subiendo CSV: {e}")


def run_spider(spider_name: str) -> bool:
    settings = get_project_settings()
    settings.set("FEEDS", {
        f"output/becas_{spider_name}.csv": {
            "format": "csv",
            "encoding": "utf-8-sig",
            "fields": [
                "nombre", "institucion", "tipo_beca", "monto",
                "fecha_inicio", "fecha_cierre", "rsh_maximo",
                "nem_minimo", "regiones", "descripcion", "url",
            ],
            "item_export_kwargs": {
                "export_empty_fields": True,
                "include_headers_line": True,
            },
        },
    })

    process = CrawlerProcess(settings, install_root_handler=False)
    process.crawl(f"{spider_name}_spider")
    process.start()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="BecasFind Scraper CLI — Extrae becas de portales chilenos y genera CSV"
    )
    parser.add_argument(
        "spider",
        nargs="?",
        default="mineduc",
        choices=["mineduc", "all"],
        help="Spider a ejecutar (default: mineduc)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Subir CSV a la API de BecasFind tras el scraping",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8080",
        help="URL base de la API BecasFind (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directorio de salida para CSV (default: output/)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.spider == "all":
        spiders = ["mineduc"]
    else:
        spiders = [args.spider]

    for spider_name in spiders:
        print(f"\n{'='*60}")
        print(f" Ejecutando spider: {spider_name}")
        print(f"{'='*60}\n")
        run_spider(spider_name)

    if args.upload:
        print(f"\n{'='*60}")
        print(f" Subiendo CSV a la API: {args.api_url}")
        print(f"{'='*60}\n")
        token = login_to_api(args.api_url)
        if token:
            for spider_name in spiders:
                csv_path = os.path.join(args.output_dir, f"becas_{spider_name}.csv")
                if os.path.exists(csv_path):
                    upload_csv(args.api_url, token, csv_path)
                else:
                    print(f"[UPLOAD] CSV no encontrado: {csv_path}")
        else:
            print("[ERROR] No se pudo obtener token JWT. Abortando upload.")


if __name__ == "__main__":
    main()
