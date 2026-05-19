import re

import scrapy
from scrapy.http import Response

from becas_scraper.items import BecaItem


class DuocSpider(scrapy.Spider):
    name = "duoc_spider"
    allowed_domains = ["www.duoc.cl"]
    start_urls = ["https://www.duoc.cl/admision/financiamiento/becas-duocuc/"]

    custom_settings = {
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "commit",
                        "timeout": 60000,
                    },
                },
                callback=self.parse,
                errback=self.errback,
            )

    async def parse(self, response: Response):
        page = response.meta.get("playwright_page")
        data = []
        try:
            await page.wait_for_selector('.vc_tta-panel', timeout=20000)
            data = await page.evaluate("""
                () => {
                    let panels = document.querySelectorAll('.vc_tta-panel');
                    let results = [];
                    for (let panel of panels) {
                        let heading = panel.querySelector('.vc_tta-panel-heading, h4');
                        let body = panel.querySelector('.vc_tta-panel-body');
                        let title = heading ? heading.innerText.trim() : '';
                        let bodyText = body ? body.innerText.trim() : '';
                        if (title && bodyText) {
                            results.push({title: title, body: bodyText});
                        }
                    }
                    return results;
                }
            """)
        except Exception as e:
            self.logger.error(f"Error extrayendo datos del DOM: {e}")
        finally:
            if page:
                await page.close()

        items_yielded = 0
        seen_tabs = set()

        for entry in data:
            tab_text = entry["title"]
            body_text = entry["body"]

            if not tab_text or not body_text:
                continue

            if "?" in tab_text:
                continue

            if tab_text in seen_tabs:
                continue
            seen_tabs.add(tab_text)

            item = BecaItem()
            item.nombre = tab_text.strip()
            item.institucion = "DUOC UC"
            item.url = response.url
            item.tipo_beca = self.infer_tipo_beca(tab_text)

            item.descripcion = self.extract_description(body_text)

            item.monto = self.extract_monto_from_text(body_text)

            date_text = self.extract_field(body_text, [
                "Cuando postular", "Fecha postulacion", "Fecha postulación",
                "Plazo", "Vigencia",
            ])
            if date_text:
                item.fecha_cierre = self.extract_date(date_text)

            item.regiones = "RM"

            items_yielded += 1
            yield item

        self.logger.info(
            f"Extraídos {items_yielded} items de {response.url}"
        )

    def extract_description(self, text: str) -> str:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        headings = {
            "descripcion", "descripción", "descripci\u00f3n",
            "beneficio", "cuando postular", "como postular",
            "requisitos", "cuando", "como",
        }
        content_paragraphs = []
        for p in paragraphs:
            first_line = p.split("\n")[0].strip().lower()
            if first_line in headings:
                continue
            content_paragraphs.append(p)
        return self.clean_text(" ".join(content_paragraphs))[:500]

    def extract_field(self, text: str, field_names: list[str]) -> str:
        for name in field_names:
            pattern = re.compile(
                rf"{re.escape(name)}\s*\n+(.+?)(?:\n(?:{'|'.join(re.escape(f) for f in field_names)})\n|\Z)",
                re.DOTALL | re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return ""

    def extract_date(self, text: str) -> str:
        patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{4}-\d{2}-\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""

    def extract_monto_from_text(self, text: str) -> str:
        patterns = [
            (
                r"(\d{1,3})\s*%\s*(?:y\s*(\d{1,3})\s*%)?.*?(?:descuento|rebaja|exenci[oó]n|beca)",
                lambda m: (
                    f"{m.group(1)}% y {m.group(2)}% de descuento en arancel"
                    if m.group(2)
                    else f"{m.group(1)}% de descuento en arancel"
                ),
            ),
            (
                r"(?:descuento|rebaja|exenci[oó]n)\s+(?:de\s+(?:un|hasta|del?)\s*)?(\d{1,3})\s*%",
                lambda m: f"{m.group(1)}% de descuento en arancel",
            ),
            (
                r"\$\s*([\d.,]+\s*(?:pesos|anual|mensual|semestral|CLP)?)",
                lambda m: f"${m.group(1).strip()}",
            ),
            (
                r"exenci[oó]n\s+total\s+(?:de\s+)?(?:los\s+)?aranceles?",
                lambda m: "Exención total de aranceles",
            ),
        ]

        for pattern, formatter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return formatter(match)

        return ""

    def infer_tipo_beca(self, text: str) -> str:
        if not text:
            return "Beca General"
        text_lower = text.lower()
        mapping = [
            ("deport", "Beca Deportiva"),
            ("hermano", "Beca de Arancel"),
            ("padre", "Beca de Arancel"),
            ("madre", "Beca de Arancel"),
            ("liceo", "Beca de Arancel"),
            ("politécnico", "Beca de Arancel"),
            ("politecnico", "Beca de Arancel"),
            ("aliment", "Beca de Alimentación"),
            ("transporte", "Beca de Transporte"),
            ("residencia", "Beca de Residencia"),
            ("fotocopia", "Beca de Fotocopias"),
            ("excelencia", "Beca de Excelencia Académica"),
            ("discapacidad", "Beca de Discapacidad"),
            ("indigena", "Beca Indígena"),
            ("indígena", "Beca Indígena"),
            ("conectividad", "Beca de Conectividad"),
            ("computador", "Beca de Computador"),
            ("notebook", "Beca de Computador"),
            ("baes", "Beca de Alimentación"),
            ("tne", "Beca de Transporte"),
            ("nivelacion", "Beca de Nivelación Académica"),
            ("nivelación", "Beca de Nivelación Académica"),
        ]
        for keyword, tipo in mapping:
            if keyword in text_lower:
                return tipo
        return "Beca de Arancel"

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        return text

    def errback(self, failure):
        self.logger.error(
            f"Error en request: {failure.request.url} - {failure.value}"
        )
