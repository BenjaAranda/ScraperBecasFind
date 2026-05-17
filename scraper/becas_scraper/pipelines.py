import csv
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from scrapy.exceptions import DropItem
from scrapy import signals

from becas_scraper.items import BecaItem
from becas_scraper.utils.normalizers import (
    parse_date,
    extract_rsh,
    extract_nem,
    extract_monto,
    normalize_region,
    normalize_tipo_beca,
    extract_institucion_from_url,
    truncate_description,
)

logger = logging.getLogger(__name__)

CSV_HEADER = [
    "nombre",
    "institucion",
    "tipo_beca",
    "monto",
    "fecha_inicio",
    "fecha_cierre",
    "rsh_maximo",
    "nem_minimo",
    "regiones",
    "descripcion",
    "url",
]


class BecaValidationPipeline:

    def process_item(self, item: BecaItem) -> BecaItem:
        if not item.nombre or not item.nombre.strip():
            raise DropItem(f"Item sin nombre: {item.url}")

        if not item.fecha_cierre or not item.fecha_cierre.strip():
            logger.warning(f"Beca sin fecha_cierre: {item.nombre}")

        item.nombre = item.nombre.strip()
        item.institucion = item.institucion.strip() if item.institucion else ""
        item.url = item.url.strip() if item.url else ""

        return item


class BecaNormalizationPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        crawler.signals.connect(pipe.spider_opened, signal=signals.spider_opened)
        return pipe

    def spider_opened(self, spider):
        self._spider_name = spider.name

    def process_item(self, item: BecaItem) -> BecaItem:
        item.fecha_inicio = parse_date(item.fecha_inicio)
        item.fecha_cierre = parse_date(item.fecha_cierre)

        if item.fecha_inicio and item.fecha_cierre:
            try:
                inicio = datetime.strptime(item.fecha_inicio, "%Y-%m-%d")
                cierre = datetime.strptime(item.fecha_cierre, "%Y-%m-%d")
                if inicio > cierre:
                    item.fecha_inicio, item.fecha_cierre = item.fecha_cierre, item.fecha_inicio
            except ValueError:
                pass

        item.regiones = normalize_region(item.regiones)

        item.tipo_beca = normalize_tipo_beca(item.tipo_beca)

        combined_text = f"{item.nombre} {item.descripcion or ''} {item.monto or ''}"
        if not item.rsh_maximo:
            item.rsh_maximo = extract_rsh(combined_text)
        if not item.nem_minimo:
            item.nem_minimo = extract_nem(combined_text)
        if not item.monto:
            item.monto = extract_monto(combined_text)

        if not item.institucion:
            item.institucion = extract_institucion_from_url(item.url)
        if not item.institucion:
            item.institucion = (
                self._spider_name.replace("_spider", "").title()
                if hasattr(self, "_spider_name") and self._spider_name
                else ""
            )

        item.descripcion = truncate_description(item.descripcion)

        item.scraped_at = datetime.now(timezone.utc).isoformat()

        return item


class BecaDeduplicationPipeline:

    def __init__(self):
        self.seen: set[tuple] = set()

    def process_item(self, item: BecaItem) -> Optional[BecaItem]:
        key = (item.nombre.strip().lower(), item.institucion.strip().lower())
        if key in self.seen:
            logger.debug(f"Duplicado ignorado: {item.nombre}")
            return None
        self.seen.add(key)
        return item


class CsvExportPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        pipe = cls()
        crawler.signals.connect(pipe.spider_opened, signal=signals.spider_opened)
        return pipe

    def spider_opened(self, spider):
        self._spider_name = spider.name

    def __init__(self):
        self.items: list[BecaItem] = []

    def process_item(self, item: BecaItem) -> BecaItem:
        self.items.append(item)
        return item

    def close_spider(self):
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        name = getattr(self, "_spider_name", "unknown").replace("_spider", "")
        out_path = os.path.join(output_dir, f"becas_{name}.csv")

        logger.info(f"Exportando {len(self.items)} becas a {out_path}")

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=CSV_HEADER,
                extrasaction="ignore",
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            for item in self.items:
                writer.writerow({
                    "nombre": item.nombre,
                    "institucion": item.institucion,
                    "tipo_beca": item.tipo_beca,
                    "monto": item.monto,
                    "fecha_inicio": item.fecha_inicio,
                    "fecha_cierre": item.fecha_cierre,
                    "rsh_maximo": item.rsh_maximo,
                    "nem_minimo": item.nem_minimo,
                    "regiones": item.regiones,
                    "descripcion": item.descripcion,
                    "url": item.url,
                })

        logger.info(f"Exportacion CSV completada: {out_path}")
