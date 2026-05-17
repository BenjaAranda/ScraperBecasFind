import re

import scrapy
from scrapy.http import Response

from becas_scraper.items import BecaItem


class MineducSpider(scrapy.Spider):
    name = "mineduc_spider"
    allowed_domains = ["portal.becasycreditos.cl"]
    start_urls = ["https://portal.becasycreditos.cl"]

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
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                },
                callback=self.parse_landing,
                errback=self.errback,
            )

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                },
                callback=self.parse_landing,
                errback=self.errback,
            )

    async def parse_landing(self, response: Response):
        page = response.meta.get("playwright_page")

        try:
            await page.wait_for_selector("body", timeout=15000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            response = response.replace(body=content.encode("utf-8"))
        except Exception as e:
            self.logger.warning(f"Playwright wait fallback: {e}")
        finally:
            if page:
                await page.close()

        nav_links = response.css(
            "nav a[href], header a[href], .nav a[href], .menu a[href]"
        )
        beca_related = []
        keywords = [
            "beca", "credito", "concurso", "convocatoria",
            "postulacion", "postulación", "beneficio",
        ]

        for link in nav_links:
            href = link.attrib.get("href", "")
            text = (link.css("::text").get() or "").strip().lower()
            if any(kw in text or kw in href.lower() for kw in keywords):
                full_url = response.urljoin(href)
                if full_url not in beca_related:
                    beca_related.append(full_url)

        if not beca_related:
            beca_related = [
                response.urljoin("/becas"),
                response.urljoin("/concursos"),
                response.urljoin("/beneficios"),
                response.urljoin("/convocatorias"),
                response.urljoin("/postulacion"),
            ]

        self.logger.info(
            f"Encontrados {len(beca_related)} enlaces relacionados con becas"
        )

        for beca_url in beca_related:
            yield scrapy.Request(
                beca_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                },
                callback=self.parse_beca_list,
                errback=self.errback,
            )

        self.logger.info(
            "Extrayendo becas del listado principal (si existe)..."
        )
        for request in self.parse_list_items(response):
            yield request

    async def parse_beca_list(self, response: Response):
        page = response.meta.get("playwright_page")

        try:
            if page:
                await page.wait_for_selector("body", timeout=10000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                response = response.replace(body=content.encode("utf-8"))
        except Exception:
            pass

        card_selectors = [
            ".card", ".beca-card", ".concurso-item",
            "article", ".post", ".entry", ".resultado",
            "[class*='beca']", "[class*='beneficio']",
        ]

        items_found = 0
        for selector in card_selectors:
            cards = response.css(selector)
            if len(cards) >= 2:
                for card in cards[:50]:
                    try:
                        item = self.extract_beca_from_card(card, response.url)
                        if item and item.nombre:
                            items_found += 1
                            yield item
                    except Exception as e:
                        self.logger.debug(f"Error extrayendo card: {e}")
                        continue
                if items_found > 0:
                    break

        self.logger.info(
            f"Extraídos {items_found} items de {response.url}"
        )

        if items_found == 0:
            self.logger.info(
                f"Fallback: buscando enlaces de detalle en {response.url}"
            )
            for request in self.parse_list_items(response):
                yield request

        if page:
            await page.close()

    def parse_list_items(self, response: Response):
        links = response.css("a[href]")
        detail_links = []
        keywords = [
            "beca", "credito", "concurso", "convocatoria",
            "postulacion", "postulación", "beneficio",
        ]

        for link in links:
            href = link.attrib.get("href", "")
            text = (link.css("::text").get() or "").strip().lower()
            if any(kw in text or kw in href.lower() for kw in keywords):
                full_url = response.urljoin(href)
                if full_url not in detail_links and full_url != response.url:
                    detail_links.append(full_url)

        if not detail_links:
            for link in links[:100]:
                href = link.attrib.get("href", "")
                if (
                    href
                    and not href.startswith("#")
                    and not href.startswith("javascript:")
                    and not href.startswith("mailto:")
                    and not href.startswith("tel:")
                ):
                    full_url = response.urljoin(href)
                    if full_url not in detail_links and full_url != response.url:
                        detail_links.append(full_url)

        self.logger.info(
            f"Encontrados {len(detail_links)} enlaces de detalle"
        )

        for detail_url in detail_links[:60]:
            yield scrapy.Request(
                detail_url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 30000,
                    },
                },
                callback=self.parse_beca_detail,
                errback=self.errback,
            )

    async def parse_beca_detail(self, response: Response):
        page = response.meta.get("playwright_page")

        try:
            if page:
                await page.wait_for_selector("body", timeout=10000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                response = response.replace(body=content.encode("utf-8"))
        except Exception:
            pass

        item = BecaItem()
        item.url = response.url
        item.institucion = "Mineduc"

        title = (
            response.css("h1::text").get()
            or response.css("title::text").get()
            or response.css("h2::text").get()
            or ""
        )
        item.nombre = self.clean_text(title)

        description_el = response.css(
            (
                ".descripcion, .description, .content, .entry-content, "
                "article, main, .contenido, #contenido"
            )
        )
        description_text = ""
        if description_el:
            description_text = " ".join(
                description_el.css("p::text, li::text, div::text").getall()
            )
        if not description_text:
            description_text = " ".join(
                response.css("body p::text, body li::text").getall()
            )
        item.descripcion = self.clean_text(description_text)

        all_text = " ".join(response.css("body ::text").getall())

        date_patterns = [
            (
                r"(?:fecha\s*(?:de\s*)?(?:cierre|t[eé]rmino|finalizaci[oó]n|postulaci[oó]n))"
                r"[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"
            ),
            r"(?:cierre|t[eé]rmino)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
            r"(?:plazo|vigencia)\s*(?:hasta)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                item.fecha_cierre = match.group(1)
                break

        inicio_patterns = [
            (
                r"(?:fecha\s*(?:de\s*)?(?:inicio|apertura))"
                r"[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"
            ),
            r"(?:inicio|apertura)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
        ]
        for pattern in inicio_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                item.fecha_inicio = match.group(1)
                break

        rsh_match = re.search(
            (
                r"(?:RSH|Registro\s*Social\s*de\s*Hogares?)"
                r"[^.]*?(?:hasta|m[aá]ximo|≤|<=)?\s*:?\s*(\d{1,3})\s*%?"
            ),
            all_text,
            re.IGNORECASE,
        )
        if rsh_match:
            item.rsh_maximo = rsh_match.group(1)

        nem_match = re.search(
            (
                r"(?:NEM|Notas?\s*de\s*Ense[ñn]anza\s*Media)"
                r"[^.]*?(?:desde|m[ií]nimo|≥|>=)?\s*:?\s*([\d,.]+)"
            ),
            all_text,
            re.IGNORECASE,
        )
        if nem_match:
            item.nem_minimo = nem_match.group(1)

        monto_match = re.search(
            r"\$\s*([\d.,]+\s*(?:pesos|anual|mensual|semestral|CLP)?)",
            all_text,
            re.IGNORECASE,
        )
        if monto_match:
            item.monto = f"${monto_match.group(1).strip()}"

        region_match = re.search(
            r"(?:regi[oó]n|regiones?)[:\s]*([\w\s,áéíóúüñÁÉÍÓÚÜÑ]+?)(?:\.|$|\n)",
            all_text,
            re.IGNORECASE,
        )
        if region_match:
            item.regiones = region_match.group(1).strip()

        tipo_match = re.search(
            (
                r"(?:tipo\s*de\s*)?(?:beca|beneficio|cr[eé]dito)"
                r"[:\s]*([\w\sáéíóúüñÁÉÍÓÚÜÑ]+?)(?:\.|$|\n)"
            ),
            all_text,
            re.IGNORECASE,
        )
        if tipo_match:
            item.tipo_beca = tipo_match.group(1).strip()

        if page:
            await page.close()

        if item.nombre:
            yield item
        else:
            self.logger.debug(
                f"No se pudo extraer nombre de {response.url}"
            )

    def extract_beca_from_card(self, card, base_url: str):
        item = BecaItem()
        item.institucion = "Mineduc"

        item.nombre = self.clean_text(
            card.css(
                "h1::text, h2::text, h3::text, h4::text, h5::text, "
                ".titulo::text, .title::text"
            ).get()
            or ""
        )
        if not item.nombre:
            item.nombre = self.clean_text(
                card.css("a::text").get() or card.css("::text").get() or ""
            )
            if len(item.nombre) > 100:
                item.nombre = item.nombre[:100]

        link = card.css("a::attr(href)").get()
        if link:
            if link.startswith("/"):
                item.url = base_url.rstrip("/") + "/" + link.lstrip("/")
            else:
                item.url = link
        else:
            item.url = base_url

        item.descripcion = self.clean_text(
            " ".join(
                card.css(
                    "p::text, .descripcion::text, .description::text, "
                    ".resumen::text"
                ).getall()
            )
        )

        all_card_text = " ".join(card.css("::text").getall())
        date_match = re.search(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
            all_card_text,
        )
        if date_match:
            item.fecha_cierre = date_match.group(1)

        return item

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        return text

    def errback(self, failure):
        self.logger.error(
            f"Error en request: {failure.request.url} — {failure.value}"
        )
