from dataclasses import dataclass, field


@dataclass
class BecaItem:
    nombre: str = ""
    institucion: str = ""
    tipo_beca: str = ""
    monto: str = ""
    fecha_inicio: str = ""
    fecha_cierre: str = ""
    rsh_maximo: str = ""
    nem_minimo: str = ""
    regiones: str = ""
    descripcion: str = ""
    url: str = ""

    scraped_at: str = field(default="", repr=False)
