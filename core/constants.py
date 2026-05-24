# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: constantes legales, provincias de referencia y patrones regex.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Constantes legales y patrones regex compartidos por toda la app."""
from __future__ import annotations

import re

# -----------------------------------------------------------------------------
# Límites legales (Ley 9/2017 de Contratos del Sector Público, art. 118)
# -----------------------------------------------------------------------------
LIMITE_SERVICIOS = 15_000.0  # € — servicios y suministros
LIMITE_OBRAS = 40_000.0      # € — obras
LIMITE_MAXIMO = 50_000.0     # € — por encima ya NO es contrato menor

# Umbrales de alerta conservadores (% del límite legal)
UMBRAL_ALERTA_SERVICIOS = LIMITE_SERVICIOS * 0.90  # 13.500 €
UMBRAL_ALERTA_OBRAS = LIMITE_OBRAS * 0.90          # 36.000 €

# -----------------------------------------------------------------------------
# Patrones regex para escaneo forense de PDFs/CSVs sueltos
# -----------------------------------------------------------------------------
PATRONES = {
    "Emails":      r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "DNI/NIF":     r'\b\d{8}[-\s]?[A-Z]\b',
    "IBAN":        r'\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}(?:[\s]?\d{2})?\b',
    "Teléfonos":   r'\b(?:\+34|0034)?(?:6\d{2}|7\d{2}|9\d{2})[ -.]?\d{3}[ -.]?\d{3}\b',
    "Fechas":      r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    "Importes (€)": r'[0-9.,]+\s?(?:€|euros|EUR)',
}

# Provincias gallegas (códigos INE)
PROVINCIAS_GALICIA = ("15", "27", "32", "36")

# Códigos provinciales INE usados también como prefijo postal de dos dígitos.
PROVINCIAS_INE: dict[str, str] = {
    "01": "Álava",
    "02": "Albacete",
    "03": "Alicante",
    "04": "Almería",
    "05": "Ávila",
    "06": "Badajoz",
    "07": "Baleares",
    "08": "Barcelona",
    "09": "Burgos",
    "10": "Cáceres",
    "11": "Cádiz",
    "12": "Castellón",
    "13": "Ciudad Real",
    "14": "Córdoba",
    "15": "A Coruña",
    "16": "Cuenca",
    "17": "Girona",
    "18": "Granada",
    "19": "Guadalajara",
    "20": "Gipuzkoa",
    "21": "Huelva",
    "22": "Huesca",
    "23": "Jaén",
    "24": "León",
    "25": "Lleida",
    "26": "La Rioja",
    "27": "Lugo",
    "28": "Madrid",
    "29": "Málaga",
    "30": "Murcia",
    "31": "Navarra",
    "32": "Ourense",
    "33": "Asturias",
    "34": "Palencia",
    "35": "Las Palmas",
    "36": "Pontevedra",
    "37": "Salamanca",
    "38": "Santa Cruz de Tenerife",
    "39": "Cantabria",
    "40": "Segovia",
    "41": "Sevilla",
    "42": "Soria",
    "43": "Tarragona",
    "44": "Teruel",
    "45": "Toledo",
    "46": "Valencia",
    "47": "Valladolid",
    "48": "Bizkaia",
    "49": "Zamora",
    "50": "Zaragoza",
    "51": "Ceuta",
    "52": "Melilla",
}

# -----------------------------------------------------------------------------
# Mapa provincia → comunidad autónoma (50 provincias + Ceuta y Melilla).
# Sirve para enriquecer datos PLACSP/Tribunal con geografía cuando no viene
# explícita. Las claves se comparan en minúsculas contra el nombre del órgano.
# -----------------------------------------------------------------------------
PROVINCIAS_CCAA: dict[str, str] = {
    # Andalucía
    "Almería": "Andalucía", "Cádiz": "Andalucía", "Córdoba": "Andalucía",
    "Granada": "Andalucía", "Huelva": "Andalucía", "Jaén": "Andalucía",
    "Málaga": "Andalucía", "Sevilla": "Andalucía",
    # Aragón
    "Huesca": "Aragón", "Teruel": "Aragón", "Zaragoza": "Aragón",
    # Asturias
    "Asturias": "Asturias",
    # Baleares
    "Baleares": "Islas Baleares", "Illes Balears": "Islas Baleares",
    # Canarias
    "Las Palmas": "Canarias", "Santa Cruz de Tenerife": "Canarias",
    "Tenerife": "Canarias", "Gran Canaria": "Canarias",
    # Cantabria
    "Cantabria": "Cantabria",
    # Castilla-La Mancha
    "Albacete": "Castilla-La Mancha", "Ciudad Real": "Castilla-La Mancha",
    "Cuenca": "Castilla-La Mancha", "Guadalajara": "Castilla-La Mancha",
    "Toledo": "Castilla-La Mancha",
    # Castilla y León
    "Ávila": "Castilla y León", "Burgos": "Castilla y León",
    "León": "Castilla y León", "Palencia": "Castilla y León",
    "Salamanca": "Castilla y León", "Segovia": "Castilla y León",
    "Soria": "Castilla y León", "Valladolid": "Castilla y León",
    "Zamora": "Castilla y León",
    # Cataluña
    "Barcelona": "Cataluña", "Girona": "Cataluña", "Gerona": "Cataluña",
    "Lleida": "Cataluña", "Lérida": "Cataluña", "Tarragona": "Cataluña",
    # C. Valenciana
    "Alicante": "Comunidad Valenciana", "Alacant": "Comunidad Valenciana",
    "Castellón": "Comunidad Valenciana", "Castelló": "Comunidad Valenciana",
    "Valencia": "Comunidad Valenciana", "València": "Comunidad Valenciana",
    # Extremadura
    "Badajoz": "Extremadura", "Cáceres": "Extremadura",
    # Galicia
    "A Coruña": "Galicia", "La Coruña": "Galicia", "Coruña": "Galicia",
    "Lugo": "Galicia", "Ourense": "Galicia", "Orense": "Galicia",
    "Pontevedra": "Galicia",
    # Madrid
    "Madrid": "Comunidad de Madrid",
    # Murcia
    "Murcia": "Región de Murcia",
    # Navarra
    "Navarra": "Navarra", "Nafarroa": "Navarra",
    # País Vasco
    "Álava": "País Vasco", "Araba": "País Vasco",
    "Gipuzkoa": "País Vasco", "Guipúzcoa": "País Vasco",
    "Bizkaia": "País Vasco", "Vizcaya": "País Vasco",
    # La Rioja
    "La Rioja": "La Rioja", "Rioja": "La Rioja",
    # Ciudades autónomas
    "Ceuta": "Ceuta", "Melilla": "Melilla",
}

# Tipos de entidad contratante por palabra clave (orden = prioridad)
TIPOS_ENTIDAD: tuple[tuple[str, str], ...] = (
    ("Diputación Foral", "Diputación foral"),
    ("Foru Aldundia", "Diputación foral"),
    ("Diputación", "Diputación provincial"),
    ("Cabildo", "Cabildo insular"),
    ("Consell Insular", "Consell insular"),
    ("Mancomunidad", "Mancomunidad"),
    ("Comarca", "Comarca"),
    ("Consorcio", "Consorcio"),
    ("Ayuntamiento", "Ayuntamiento"),
    ("Concello", "Ayuntamiento"),
    ("Concejo", "Ayuntamiento"),
    ("Udala", "Ayuntamiento"),
    ("Alcaldía", "Ayuntamiento"),
    ("Universidad", "Universidad"),
    ("Universidade", "Universidad"),
    ("Hospital", "Hospital / Sanidad"),
    ("Servicio de Salud", "Sanidad autonómica"),
    ("Servizo Galego de Saúde", "Sanidad autonómica"),
    ("Ministerio", "Administración General del Estado"),
    ("Subdelegación del Gobierno", "Administración General del Estado"),
    ("Delegación del Gobierno", "Administración General del Estado"),
    ("Agencia Estatal", "Administración General del Estado"),
    ("Junta de", "Comunidad autónoma"),
    ("Generalitat", "Comunidad autónoma"),
    ("Xunta de Galicia", "Comunidad autónoma"),
    ("Gobierno de", "Comunidad autónoma"),
    ("Govern", "Comunidad autónoma"),
    ("Comunidad de Madrid", "Comunidad autónoma"),
    ("Eusko Jaurlaritza", "Comunidad autónoma"),
)

# Palabras clave que identifican CCAA por sí mismas (sin provincia explícita)
CCAA_DIRECTAS: tuple[tuple[str, str], ...] = (
    ("Xunta de Galicia", "Galicia"),
    ("Junta de Andalucía", "Andalucía"),
    ("Junta de Castilla y León", "Castilla y León"),
    ("Junta de Comunidades de Castilla-La Mancha", "Castilla-La Mancha"),
    ("Junta de Castilla-La Mancha", "Castilla-La Mancha"),
    ("Junta de Extremadura", "Extremadura"),
    ("Generalitat de Catalunya", "Cataluña"),
    ("Generalitat Valenciana", "Comunidad Valenciana"),
    ("Govern de les Illes Balears", "Islas Baleares"),
    ("Gobierno de Canarias", "Canarias"),
    ("Gobierno Vasco", "País Vasco"),
    ("Eusko Jaurlaritza", "País Vasco"),
    ("Gobierno de Aragón", "Aragón"),
    ("Gobierno del Principado de Asturias", "Asturias"),
    ("Gobierno de Cantabria", "Cantabria"),
    ("Gobierno de Navarra", "Navarra"),
    ("Gobierno de La Rioja", "La Rioja"),
    ("Comunidad de Madrid", "Comunidad de Madrid"),
    ("Región de Murcia", "Región de Murcia"),
)

PATRONES_MUNICIPIO: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:Ayuntamiento|Concello|Concejo|Ajuntament|Ajuntamento|Udala|Alcald[ií]a)\s+"
        r"(?:del|de|da|do|d'|l')?\s*([^,;()\-/]+(?:\s+[^,;()\-/]+){0,5})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Municipio|Entidad Local Menor)\s+(?:del|de|da|do)?\s*"
        r"([^,;()\-/]+(?:\s+[^,;()\-/]+){0,5})",
        re.IGNORECASE,
    ),
)

CCAA_CENTROIDES: dict[str, tuple[float, float]] = {
    "Andalucía": (37.40, -4.60),
    "Aragón": (41.60, -0.90),
    "Asturias": (43.35, -5.85),
    "Canarias": (28.30, -15.60),
    "Cantabria": (43.18, -3.99),
    "Castilla-La Mancha": (39.50, -3.00),
    "Castilla y León": (41.65, -4.72),
    "Cataluña": (41.80, 1.80),
    "Ceuta": (35.89, -5.32),
    "Comunidad Valenciana": (39.50, -0.75),
    "Comunidad de Madrid": (40.42, -3.70),
    "Extremadura": (39.00, -6.00),
    "Galicia": (42.80, -8.00),
    "Islas Baleares": (39.57, 2.65),
    "La Rioja": (42.30, -2.45),
    "Melilla": (35.29, -2.94),
    "Navarra": (42.80, -1.65),
    "País Vasco": (43.00, -2.60),
    "Región de Murcia": (37.99, -1.13),
}

PROVINCIA_CENTROIDES: dict[str, tuple[float, float]] = {
    "A Coruña": (43.36, -8.41), "La Coruña": (43.36, -8.41), "Coruña": (43.36, -8.41),
    "Alacant": (38.35, -0.49), "Albacete": (38.99, -1.86), "Alicante": (38.35, -0.49),
    "Almería": (36.84, -2.46), "Araba": (42.85, -2.67), "Asturias": (43.36, -5.84),
    "Álava": (42.85, -2.67), "Ávila": (40.66, -4.70), "Badajoz": (38.88, -6.97),
    "Baleares": (39.57, 2.65), "Barcelona": (41.39, 2.17), "Bizkaia": (43.26, -2.93),
    "Burgos": (42.34, -3.70), "Cáceres": (39.47, -6.37), "Cádiz": (36.53, -6.29),
    "Cantabria": (43.46, -3.81), "Castelló": (39.99, -0.04), "Castellón": (39.99, -0.04),
    "Ceuta": (35.89, -5.32), "Ciudad Real": (38.98, -3.93), "Córdoba": (37.88, -4.78),
    "Cuenca": (40.07, -2.14), "Gerona": (41.98, 2.82), "Gipuzkoa": (43.32, -1.98),
    "Girona": (41.98, 2.82), "Gran Canaria": (28.12, -15.43), "Granada": (37.18, -3.60),
    "Guadalajara": (40.63, -3.17), "Guipúzcoa": (43.32, -1.98), "Huelva": (37.26, -6.94),
    "Huesca": (42.14, -0.41), "Illes Balears": (39.57, 2.65), "Jaén": (37.78, -3.79),
    "La Rioja": (42.47, -2.45), "Las Palmas": (28.12, -15.43), "León": (42.60, -5.57),
    "Lleida": (41.62, 0.62), "Lérida": (41.62, 0.62), "Lugo": (43.01, -7.56),
    "Madrid": (40.42, -3.70), "Málaga": (36.72, -4.42), "Melilla": (35.29, -2.94),
    "Murcia": (37.99, -1.13), "Navarra": (42.82, -1.64), "Nafarroa": (42.82, -1.64),
    "Orense": (42.34, -7.86), "Ourense": (42.34, -7.86), "Palencia": (42.01, -4.53),
    "Pontevedra": (42.43, -8.64), "Rioja": (42.47, -2.45), "Salamanca": (40.97, -5.66),
    "Santa Cruz de Tenerife": (28.47, -16.25), "Segovia": (40.95, -4.12), "Sevilla": (37.39, -5.99),
    "Soria": (41.76, -2.47), "Tarragona": (41.12, 1.24), "Tenerife": (28.47, -16.25),
    "Teruel": (40.34, -1.11), "Toledo": (39.86, -4.03), "Valencia": (39.47, -0.38),
    "València": (39.47, -0.38), "Valladolid": (41.65, -4.72), "Vizcaya": (43.26, -2.93),
    "Zamora": (41.50, -5.75), "Zaragoza": (41.65, -0.89),
}


def inferir_municipio(nombre_organo: str | None) -> str | None:
    """Intenta extraer el municipio cuando el órgano local lo declara en su nombre."""
    if not nombre_organo:
        return None
    texto = re.sub(r"\s+", " ", str(nombre_organo)).strip()
    bajo = texto.lower()
    if "ciudad autónoma de ceuta" in bajo:
        return "Ceuta"
    if "ciudad autónoma de melilla" in bajo:
        return "Melilla"
    for patron in PATRONES_MUNICIPIO:
        match = patron.search(texto)
        if not match:
            continue
        municipio = match.group(1).strip(" .:;,_")
        municipio = re.sub(r"^(?:el|la|l)\s+", "", municipio, flags=re.IGNORECASE)
        municipio = re.sub(
            r"^(?:Ayuntamiento|Concello|Concejo|Ajuntament|Ajuntamento|Udala)\s+(?:del|de|da|do|d'|l')?\s*",
            "",
            municipio,
            flags=re.IGNORECASE,
        ).strip()
        municipio = re.sub(r"\s+(?:S\.A\.|S\.L\.|NIF|CIF)\b.*$", "", municipio, flags=re.IGNORECASE).strip()
        if 2 <= len(municipio) <= 80:
            return municipio
    return None


def inferir_geografia(nombre_organo: str | None) -> tuple[str | None, str | None]:
    """Devuelve (provincia, CCAA) inferidas del nombre del órgano contratante.

    Heurística pensada para PLACSP/Tribunal: primero patrones explícitos de
    CCAA, luego búsqueda de provincia como subcadena (la coincidencia más
    larga gana). Devuelve `None` cuando no hay evidencia, para no inventar.
    """
    if not nombre_organo:
        return (None, None)
    bajo = str(nombre_organo).lower()
    for clave, ccaa in CCAA_DIRECTAS:
        if clave.lower() in bajo:
            return (None, ccaa)
    mejor_provincia: str | None = None
    mejor_long = 0
    for provincia in PROVINCIAS_CCAA:
        clave = provincia.lower()
        if clave in bajo and len(clave) > mejor_long:
            mejor_provincia = provincia
            mejor_long = len(clave)
    if mejor_provincia:
        return (mejor_provincia, PROVINCIAS_CCAA[mejor_provincia])
    return (None, None)


def inferir_tipo_entidad(nombre_organo: str | None) -> str | None:
    """Devuelve el tipo de entidad inferido del nombre del órgano."""
    if not nombre_organo:
        return None
    bajo = str(nombre_organo).lower()
    for clave, etiqueta in TIPOS_ENTIDAD:
        if clave.lower() in bajo:
            return etiqueta
    return None
