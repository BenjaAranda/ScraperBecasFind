# Scraper BecasFind

Pipeline de extracción y normalización de becas estudiantiles para [BecasFind](https://github.com/BenjaAranda/BecasFind). Obtiene información desde portales chilenos, valida los registros y genera archivos CSV listos para importar en la plataforma.

## Fuentes disponibles

- Ministerio de Educación de Chile (Mineduc).
- DUOC UC.

## Tecnologías

- Python 3
- Scrapy
- Playwright
- scrapy-playwright
- pandas
- requests

## Funcionalidades

- Ejecución individual o conjunta de spiders.
- Navegación de páginas dinámicas con Playwright.
- Normalización y validación de campos.
- Eliminación de registros duplicados.
- Exportación UTF-8 a CSV.
- Carga opcional de resultados en la API de BecasFind.

## Instalación

```bash
git clone https://github.com/BenjaAranda/ScraperBecasFind.git
cd ScraperBecasFind/scraper
python -m venv .venv
```

Activa el entorno virtual y ejecuta:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Uso

```bash
python run_spider.py mineduc
python run_spider.py duoc
python run_spider.py all
```

Para importar el CSV en una API local de BecasFind:

```bash
python run_spider.py all --upload --api-url http://localhost:8080
```

Consulta todas las opciones con `python run_spider.py --help`.

## Uso responsable

Verifica los términos de uso y las reglas de acceso de cada fuente antes de ejecutar el scraper. Mantén una frecuencia moderada de solicitudes y revisa los datos generados antes de importarlos.
