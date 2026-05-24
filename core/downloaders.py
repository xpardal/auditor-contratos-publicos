# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: descargas reproducibles, extracción segura y manifiestos de procedencia.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Descarga reproducible de fuentes oficiales.

Este modulo separa la obtencion de datos de la ingesta/analisis. La app puede
descargar fuentes oficiales a disco, guardar un manifiesto de trazabilidad y
despues reutilizar los loaders locales ya existentes.
"""
from __future__ import annotations

import json
import re
import shutil
import ssl
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import certifi


DEFAULT_PLACSP_MENORES_URL = (
    "https://contrataciondelestado.es/sindicacion/sindicacion_1143/"
    "contratosMenoresPerfilesContratantes.atom"
)

ATOM_NS = "{http://www.w3.org/2005/Atom}"
USER_AGENT = "TFG-Auditor-Contratos/1.0 (+https://contrataciondelestado.es)"


@dataclass
class DescargaResultado:
    fuente: str
    destino: Path
    descargados: list[Path] = field(default_factory=list)
    omitidos: list[Path] = field(default_factory=list)
    extraidos: list[Path] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    manifest_path: Path | None = None
    ultimo_url: str | None = None

    @property
    def total_archivos(self) -> int:
        return len(self.descargados) + len(self.omitidos)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slug(texto: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", texto).strip("_").lower() or "fuente"


def _request(url: str) -> Request:
    return Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml, application/xml, text/xml, */*",
        },
    )


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _nombre_desde_url(url: str, fallback: str) -> str:
    nombre = Path(unquote(urlparse(url).path)).name
    if not nombre or nombre in {".", "/"}:
        nombre = fallback
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", nombre)


def _descargar_bytes(url: str, *, timeout: int) -> tuple[bytes, str]:
    with urlopen(_request(url), timeout=timeout, context=_ssl_context()) as response:
        return response.read(), response.geturl()


def _descargar_stream(url: str, salida: Path, *, timeout: int) -> str:
    tmp = salida.with_name(f"{salida.name}.tmp")
    try:
        with urlopen(_request(url), timeout=timeout, context=_ssl_context()) as response, tmp.open("wb") as fh:
            shutil.copyfileobj(response, fh, length=1024 * 1024)
            final_url = response.geturl()
        tmp.replace(salida)
        return final_url
    finally:
        if tmp.exists():
            tmp.unlink()


def _siguiente_atom(contenido: bytes, base_url: str) -> str | None:
    try:
        root = ET.fromstring(contenido)
    except ET.ParseError:
        return None
    for link in root.findall(f"{ATOM_NS}link"):
        if link.attrib.get("rel") == "next" and link.attrib.get("href"):
            return urljoin(base_url, link.attrib["href"])
    return None


def _guardar_manifest(resultado: DescargaResultado, urls: list[str]) -> Path:
    manifest_dir = resultado.destino / "_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(resultado.fuente)}.json"
    payload = {
        "fecha_utc": _now_iso(),
        "fuente": resultado.fuente,
        "destino": str(resultado.destino),
        "urls_visitadas": urls,
        "ultimo_url": resultado.ultimo_url,
        "descargados": [str(p) for p in resultado.descargados],
        "omitidos": [str(p) for p in resultado.omitidos],
        "extraidos": [str(p) for p in resultado.extraidos],
        "errores": resultado.errores,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    resultado.manifest_path = path
    return path


def descargar_placsp_menores(
    destino: str | Path,
    *,
    url_inicial: str = DEFAULT_PLACSP_MENORES_URL,
    max_archivos: int = 30,
    sobrescribir: bool = False,
    timeout: int = 60,
    progreso=None,
) -> DescargaResultado:
    """Descarga paginas Atom paginadas de contratos menores de PLACSP.

    Sigue el enlace `<link rel="next">` de cada feed, guarda cada pagina como
    `.atom` y deja un manifiesto JSON con las URLs visitadas. `max_archivos`
    evita descargas accidentales de cientos/miles de paginas.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    resultado = DescargaResultado(fuente="PLACSP contratos menores", destino=destino)

    url = url_inicial.strip()
    visitadas: list[str] = []
    vistas: set[str] = set()

    for i in range(max(1, int(max_archivos))):
        if not url or url in vistas:
            break
        vistas.add(url)
        visitadas.append(url)
        resultado.ultimo_url = url

        try:
            contenido, final_url = _descargar_bytes(url, timeout=timeout)
        except Exception as exc:
            resultado.errores.append(f"{url}: {exc}")
            break

        nombre = _nombre_desde_url(final_url or url, f"placsp_menores_{i + 1:04d}.atom")
        if not nombre.lower().endswith((".atom", ".xml")):
            nombre = f"{Path(nombre).stem or f'placsp_menores_{i + 1:04d}'}.atom"
        salida = destino / nombre

        if salida.exists() and not sobrescribir:
            resultado.omitidos.append(salida)
        else:
            salida.write_bytes(contenido)
            resultado.descargados.append(salida)

        if progreso:
            progreso(i + 1, max_archivos, url)

        url = _siguiente_atom(contenido, final_url or url)

    _guardar_manifest(resultado, visitadas)
    return resultado


def _extraer_zip_seguro(zip_path: Path, destino: Path) -> list[Path]:
    destino_resuelto = destino.resolve()
    extraidos: list[Path] = []
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (destino / member.filename).resolve()
            try:
                target.relative_to(destino_resuelto)
            except ValueError:
                raise RuntimeError(f"Ruta insegura dentro del ZIP: {member.filename}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            extraidos.append(target)
    return extraidos


def descargar_url_directa(
    url: str,
    destino: str | Path,
    *,
    nombre_archivo: str | None = None,
    sobrescribir: bool = False,
    descomprimir_zip: bool = True,
    timeout: int = 180,
) -> DescargaResultado:
    """Descarga cualquier URL directa oficial a disco.

    Sirve para ficheros `.accdb`, `.csv`, `.xlsx` o `.zip` publicados por una
    fuente oficial. No automatiza formularios ni sesiones; exige una URL directa
    para mantener la trazabilidad y evitar scraping frágil.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    resultado = DescargaResultado(fuente="URL directa oficial", destino=destino, ultimo_url=url)

    nombre = (nombre_archivo or "").strip() or _nombre_desde_url(url, "fuente_descargada")
    salida = destino / nombre

    try:
        if salida.exists() and not sobrescribir:
            resultado.omitidos.append(salida)
        else:
            resultado.ultimo_url = _descargar_stream(url.strip(), salida, timeout=timeout)
            resultado.descargados.append(salida)

        if descomprimir_zip and salida.suffix.lower() == ".zip" and salida.exists():
            resultado.extraidos = _extraer_zip_seguro(salida, destino / salida.stem)
    except Exception as exc:
        resultado.errores.append(f"{url}: {exc}")

    _guardar_manifest(resultado, [url])
    return resultado