import re
from datetime import datetime, date
from typing import Optional

import dateutil.parser


DATE_FORMATS = [
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{2}/\d{2}/\d{4}"),
    re.compile(r"\d{2}-\d{2}-\d{4}"),
    re.compile(r"\d{2}/\d{2}/\d{2}"),
    re.compile(r"\d{1,2}\s+de\s+\w+\s+(de\s+)?\d{4}", re.IGNORECASE),
]

REGION_ABBR_MAP = {
    "arica": "XV", "arica y parinacota": "XV",
    "tarapaca": "I", "tarapacá": "I",
    "antofagasta": "II",
    "atacama": "III",
    "coquimbo": "IV",
    "valparaiso": "V", "valparaíso": "V",
    "ohiggins": "VI", "o'higgins": "VI", "libertador": "VI",
    "maule": "VII",
    "biobio": "VIII", "bíobío": "VIII", "bio bio": "VIII", "bío bío": "VIII",
    "araucania": "IX", "araucanía": "IX",
    "los lagos": "X",
    "aysen": "XI", "aysén": "XI",
    "magallanes": "XII",
    "metropolitana": "RM", "rm": "RM", "santiago": "RM",
    "los rios": "XIV", "los ríos": "XIV",
    "nuble": "XVI", "ñuble": "XVI",
}

KNOWN_ABBREVIATIONS = {"XV", "I", "II", "III", "IV", "V", "VI", "RM", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI"}

REGION_ORDER = {
    "XV": 0, "I": 1, "II": 2, "III": 3, "IV": 4,
    "V": 5, "VI": 6, "RM": 7, "VII": 8, "VIII": 9,
    "IX": 10, "X": 11, "XI": 12, "XII": 13, "XIV": 14, "XVI": 15,
}

RSH_PATTERNS = [
    re.compile(r"RSH\s*(?:m[aá]ximo|hasta|≤|<=)?\s*:?\s*(\d{1,2})\s*%", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*%\s*(?:de\s*)?RSH", re.IGNORECASE),
    re.compile(r"tramo\s*(?:del\s*)?(\d{1,2})\s*%", re.IGNORECASE),
    re.compile(r"(\d{1,2})\s*%\s*(?:m[aá]s\s*vulnerable)", re.IGNORECASE),
]

NEM_PATTERNS = [
    re.compile(r"NEM\s*(?:m[ií]nimo|desde|≥|>=)?\s*:?\s*([\d,.]+)", re.IGNORECASE),
    re.compile(r"prom(?:edio)?\s*(?:de\s*)?notas\s*(?:m[ií]nimo|desde|≥|>=)?\s*:?\s*([\d,.]+)", re.IGNORECASE),
    re.compile(r"nota\s*(?:m[ií]nima|de\s*corte)?\s*:?\s*([\d,.]+)", re.IGNORECASE),
    re.compile(r"([\d,.]+)\s*(?:de\s*)?NEM", re.IGNORECASE),
]

MONTO_PATTERNS = [
    re.compile(r"\$\s*([\d.,]+\s*(?:\w+\s*)*)", re.IGNORECASE),
    re.compile(r"monto\s*(?:m[aá]ximo|de)?\s*:?\s*\$?\s*([\d.,]+\s*(?:\w+\s*)*)", re.IGNORECASE),
]


ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def parse_date(raw: Optional[str]) -> str:
    if not raw or not raw.strip():
        return ""
    raw = raw.strip()

    iso_match = ISO_DATE_RE.search(raw)
    if iso_match:
        try:
            y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            dt = datetime(y, m, d)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    for pattern in DATE_FORMATS[1:]:
        match = pattern.search(raw)
        if match:
            try:
                parsed = dateutil.parser.parse(match.group(), dayfirst=True)
                if parsed:
                    return parsed.strftime("%Y-%m-%d")
            except (ValueError, dateutil.parser.ParserError):
                continue

    try:
        parsed = dateutil.parser.parse(raw, dayfirst=True, fuzzy=True)
        if parsed and parsed.year > 1900:
            return parsed.strftime("%Y-%m-%d")
    except (ValueError, dateutil.parser.ParserError):
        pass

    return ""


def extract_rsh(text: Optional[str]) -> str:
    if not text:
        return ""
    for pattern in RSH_PATTERNS:
        match = pattern.search(text)
        if match:
            val = int(match.group(1))
            if 0 <= val <= 100:
                return str(val)
    return ""


def extract_nem(text: Optional[str]) -> str:
    if not text:
        return ""
    for pattern in NEM_PATTERNS:
        match = pattern.search(text)
        if match:
            raw_val = match.group(1).replace(",", ".")
            try:
                val = float(raw_val)
                if 1.0 <= val <= 7.0:
                    return f"{val:.1f}"
            except ValueError:
                continue
    return ""


def extract_monto(text: Optional[str]) -> str:
    if not text:
        return ""
    for pattern in MONTO_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"${match.group(1).strip()}"
    return ""


def normalize_region(text: Optional[str]) -> str:
    if not text or not text.strip():
        return ""
    text_lower = text.strip().lower()

    if text_lower in {"nacional", "todas", "todas las regiones", "sin restriccion", "sin restricción"}:
        return ""

    found = set()
    for name, abbr in REGION_ABBR_MAP.items():
        if name in text_lower:
            found.add(abbr)

    upper = re.findall(r"\b(XV|XVI|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I|RM)\b", text.upper())
    found.update(upper)

    return ",".join(sorted(found, key=lambda x: REGION_ORDER.get(x, 999)))


def normalize_tipo_beca(raw: Optional[str]) -> str:
    if not raw or not raw.strip():
        return "Beca General"
    raw = raw.strip().title()
    mapping = {
        "Alimentacion": "Beca de Alimentación",
        "Alimentación": "Beca de Alimentación",
        "Arancel": "Beca de Arancel",
        "Aranceles": "Beca de Arancel",
        "Residencia": "Beca de Residencia",
        "Transporte": "Beca de Transporte",
        "Fotocopia": "Beca de Fotocopias",
        "Fotocopias": "Beca de Fotocopias",
        "Deportiva": "Beca Deportiva",
        "Deportes": "Beca Deportiva",
        "Excelencia": "Beca de Excelencia Académica",
        "Merito": "Beca de Mérito",
        "Investigacion": "Beca de Investigación",
        "Investigación": "Beca de Investigación",
        "Practica": "Beca de Práctica",
        "Titulacion": "Beca de Titulación",
        "Titulación": "Beca de Titulación",
        "Discapacidad": "Beca de Discapacidad",
        "Indigena": "Beca Indígena",
        "Indígena": "Beca Indígena",
        "Mantención": "Beca de Mantención",
        "Matricula": "Beca de Matrícula",
        "Matrícula": "Beca de Matrícula",
        "Nivelacion": "Beca de Nivelación Académica",
        "Nivelación": "Beca de Nivelación Académica",
    }
    for key, value in mapping.items():
        if key.lower() in raw.lower():
            return value
    return raw


def extract_institucion_from_url(url: Optional[str]) -> str:
    if not url:
        return ""
    domain_hints = {
        "duoc.cl": "DUOC UC",
        "usm.cl": "UTFSM",
        "pucv.cl": "PUCV",
        "uc.cl": "Pontificia Universidad Católica de Chile",
        "uchile.cl": "Universidad de Chile",
        "usach.cl": "USACH",
        "udec.cl": "Universidad de Concepción",
        "uach.cl": "Universidad Austral de Chile",
        "ufro.cl": "Universidad de La Frontera",
        "junaeb.cl": "JUNAEB",
        "mineduc.cl": "Mineduc",
        "becasycreditos.cl": "Mineduc",
    }
    for domain, name in domain_hints.items():
        if domain in url.lower():
            return name
    return ""


def truncate_description(text: Optional[str], max_chars: int = 500) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text
