TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

BOT_NAME = "becas_scraper"

SPIDER_MODULES = ["becas_scraper.spiders"]
NEWSPIDER_MODULE = "becas_scraper.spiders"

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

COOKIES_ENABLED = True

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}

EXTENSIONS = {
    "scrapy.extensions.logstats.LogStats": 0,
    "scrapy.extensions.telnet.TelnetConsole": 0,
}

RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

DOWNLOAD_TIMEOUT = 60

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

FEED_EXPORT_ENCODING = "utf-8"

FEED_EXPORT_FIELDS = [
    "nombre", "institucion", "tipo_beca", "monto", "fecha_inicio",
    "fecha_cierre", "rsh_maximo", "nem_minimo", "regiones", "descripcion", "url",
]

ITEM_PIPELINES = {
    "becas_scraper.pipelines.BecaValidationPipeline": 100,
    "becas_scraper.pipelines.BecaNormalizationPipeline": 200,
    "becas_scraper.pipelines.BecaDeduplicationPipeline": 300,
    "becas_scraper.pipelines.CsvExportPipeline": 400,
}

FEEDS = {
    "output/becas_mineduc.csv": {
        "format": "csv",
        "encoding": "utf-8",
        "fields": [
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
        ],
        "item_export_kwargs": {
            "export_empty_fields": True,
            "include_headers_line": True,
        },
    },
}

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-sync",
        "--no-first-run",
        "--disable-default-apps",
        "--hide-scrollbars",
        "--metrics-recording-only",
        "--mute-audio",
        "--ignore-certificate-errors",
    ],
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
