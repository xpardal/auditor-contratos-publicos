# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: ingesta streaming de feeds Atom de PLACSP y caché Parquet.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Ingesta de datos PLACSP (Plataforma de Contratación del Sector Público).

Lee archivos .atom (uno por día/lote, ~1100/año) en streaming con
xml.etree.iterparse para no cargarlos enteros en memoria, y persiste el
resultado consolidado en un Parquet por carpeta. La escritura del Parquet
también es incremental (lotes con `pyarrow.parquet.ParquetWriter`), por lo
que la huella de RAM se mantiene acotada incluso con millones de filas.

El identificador de carpeta es un hash del path absoluto + número de archivos,
de modo que si añades nuevos .atom el caché se invalida automáticamente.

Para consultar el Parquet sin volver a cargarlo entero a memoria se ofrece
:func:`consultar_placsp` (DuckDB con *predicate pushdown* sobre el Parquet)
y :func:`opciones_placsp` (valores únicos para los desplegables de la UI).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xml.etree.ElementTree as ET

from .constants import LIMITE_MAXIMO, inferir_geografia, inferir_municipio, inferir_tipo_entidad
from .money import limpiar_dinero

ATOM_NS = "{http://www.w3.org/2005/Atom}"
CBC_NS = "{urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2}"
CAC_NS = "{urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2}"

# Códigos PLACSP de tipo de contrato (TypeCode dentro de ProcurementProject).
# https://contrataciondelestado.es/codice (SyndicationContractCode)
PLACSP_TIPO_CONTRATO = {
    "1": "Suministros",
    "2": "Servicios",
    "3": "Obras",
    "7": "Concesión de servicios",
    "8": "Administrativo especial",
    "21": "Concesión de servicios",
    "22": "Concesión de obras",
    "31": "Concesión de obras",
    "32": "Concesión de servicios",
    "40": "Privado",
    "50": "Patrimonial",
}

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def _firma_carpeta(carpeta: Path, archivos: list[Path]) -> str:
    """Hash estable de la carpeta para invalidar caché si cambia el contenido."""
    h = hashlib.sha1()
    h.update(str(carpeta.resolve()).encode())
    h.update(f"|n={len(archivos)}".encode())
    # Incluimos tamaño total para detectar cambios sin leer cada archivo
    total_size = sum(a.stat().st_size for a in archivos[:50])  # muestra
    h.update(f"|s={total_size}".encode())
    # Versión del esquema: subir cuando cambien las columnas extraídas
    h.update(b"|schema=v6")
    return h.hexdigest()[:16]


def _texto(elemento: ET.Element | None) -> str | None:
    if elemento is None or elemento.text is None:
        return None
    return elemento.text.strip() or None


def _normalizar_fecha_placsp(
    valor: str | None,
    *,
    min_year: int = 2010,
    max_year: int | None = None,
) -> str | None:
    if not valor:
        return None
    max_year = max_year or datetime.now().year + 1
    match = re.match(r"^(\d{1,4})-(\d{1,2})-(\d{1,2})", str(valor).strip())
    if not match:
        return None

    year_text, month_text, day_text = match.groups()
    year = int(year_text)
    if len(year_text) == 4 and year_text.startswith("00"):
        year = 2000 + int(year_text[-2:])

    if not (min_year <= year <= max_year):
        return None

    try:
        return datetime(year, int(month_text), int(day_text)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _extraer_contrato(entry: ET.Element) -> dict | None:
    """Extrae los campos relevantes de una <entry> Atom de PLACSP."""
    # Resumen (tiene órgano + importe en texto plano, fallback fiable)
    summary = _texto(entry.find(f"{ATOM_NS}summary"))
    organo = None
    importe = None
    if summary:
        m_org = re.search(r'(?:Órgano de Contratación|Órgano Contratante):\s*(.*?)(?:;|$)', summary)
        if m_org:
            organo = m_org.group(1).strip()
        m_imp = re.search(r'Importe:\s*([\d.,]+)', summary)
        if m_imp:
            importe = limpiar_dinero(m_imp.group(1))

    # Concepto = title de la entry (no el del feed)
    concepto = _texto(entry.find(f"{ATOM_NS}title")) or "Sin concepto"

    # Importe sin IVA — busca recursivamente
    if importe is None:
        for el in entry.iter(f"{CBC_NS}TaxExclusiveAmount"):
            importe = limpiar_dinero(el.text)
            if importe is not None:
                break

    if importe is None or importe > LIMITE_MAXIMO:
        return None  # Filtro de seguridad: solo contratos menores

    # Adjudicatario
    adjudicatario = None
    for winning in entry.iter(f"{CAC_NS}WinningParty"):
        for name in winning.iter(f"{CBC_NS}Name"):
            adjudicatario = _texto(name)
            if adjudicatario:
                break
        if adjudicatario:
            break

    # Tipo de contrato (TypeCode dentro de ProcurementProject)
    tipo_contrato = "Otros"
    for proj in entry.iter(f"{CAC_NS}ProcurementProject"):
        for tc in proj.findall(f"{CBC_NS}TypeCode"):
            valor = (tc.text or "").strip()
            if valor:
                tipo_contrato = PLACSP_TIPO_CONTRATO.get(valor, f"Tipo {valor}")
                break
        if tipo_contrato != "Otros":
            break
    if tipo_contrato == "Otros":
        for el in entry.iter(f"{CBC_NS}ContractTypeCode"):
            if (el.text or "").strip() in ("3", "WORKS", "works"):
                tipo_contrato = "Obras"
                break

    # Fecha de adjudicación → año fiscal
    fecha_str = None
    for el in entry.iter(f"{CBC_NS}AwardDate"):
        fecha_str = _normalizar_fecha_placsp(_texto(el))
        if fecha_str:
            break
    if not fecha_str:
        upd = _texto(entry.find(f"{ATOM_NS}updated"))
        fecha_str = _normalizar_fecha_placsp(upd)

    año_fiscal = None
    if fecha_str:
        año_fiscal = int(fecha_str[:4])

    if not organo:
        # Fallback: primer Name dentro de ContractingParty
        for cp in entry.iter(f"{CAC_NS}ContractingParty"):
            for name in cp.iter(f"{CBC_NS}Name"):
                organo = _texto(name)
                if organo:
                    break
            if organo:
                break

    if not organo:
        return None

    # Enlace al expediente PLACSP (id Atom suele ser una URL del perfil)
    link_expediente = None
    for link in entry.iter(f"{ATOM_NS}link"):
        href = link.attrib.get("href")
        if href and href.startswith("http"):
            link_expediente = href
            break
    if not link_expediente:
        link_expediente = _texto(entry.find(f"{ATOM_NS}id"))
        if link_expediente and not link_expediente.startswith("http"):
            link_expediente = None

    # Código CPV (vocabulario europeo de objeto del contrato)
    cpv = None
    for el in entry.iter(f"{CBC_NS}ItemClassificationCode"):
        valor = _texto(el)
        if valor and valor.isdigit() and len(valor) >= 4:
            cpv = valor
            break

    provincia, ccaa = inferir_geografia(organo)
    municipio = inferir_municipio(organo)
    tipo_entidad = inferir_tipo_entidad(organo)

    return {
        "Organo": organo,
        "Tipo_Entidad": tipo_entidad,
        "Provincia": provincia,
        "CCAA": ccaa,
        "Municipio": municipio,
        "Tipo_Contrato": tipo_contrato,
        "Concepto": concepto,
        "CPV": cpv,
        "Adjudicatario": adjudicatario or "No consta",
        "_Adjudicatario_Radar": adjudicatario,  # None = excluido del radar
        "Fecha": fecha_str[:10] if fecha_str else None,
        "Año_Fiscal": año_fiscal,
        "Importe_euros": importe,
        "Link_Expediente": link_expediente,
    }


def _iter_entries(path: Path) -> Iterator[ET.Element]:
    """Itera entries de un .atom liberando memoria conforme avanza."""
    try:
        for _, elem in ET.iterparse(path, events=("end",)):
            if elem.tag == f"{ATOM_NS}entry":
                yield elem
                elem.clear()
    except ET.ParseError:
        return


def cargar_placsp(
    carpeta: str | Path,
    *,
    progreso=None,
    forzar: bool = False,
    batch_size: int = 5_000,
) -> pd.DataFrame:
    """Carga TODOS los contratos menores de una carpeta de archivos .atom.

    Cachea el resultado en Parquet escribiendo por lotes (`batch_size` filas)
    para que la huella de memoria permanezca acotada incluso con millones de
    contratos. Si la carpeta no cambia, la segunda llamada es prácticamente
    instantánea (devuelve el Parquet ya generado).

    Parameters
    ----------
    carpeta : ruta a la carpeta con archivos .atom o .xml de PLACSP.
    progreso : callable opcional progreso(i, total) para barra de Streamlit.
    forzar : si True, ignora caché y reprocesa.
    batch_size : nº de filas por bloque al escribir el Parquet incremental.

    Returns
    -------
    pd.DataFrame
        DataFrame con todos los contratos. Para volúmenes muy grandes
        recomendamos usar :func:`ingestar_placsp_a_parquet` +
        :func:`consultar_placsp` en lugar de cargar todo en RAM.
    """
    parquet_path = ingestar_placsp_a_parquet(
        carpeta, progreso=progreso, forzar=forzar, batch_size=batch_size
    )
    if parquet_path is None or not parquet_path.exists():
        return pd.DataFrame()
    return pd.read_parquet(parquet_path)


def ingestar_placsp_a_parquet(
    carpeta: str | Path,
    *,
    progreso=None,
    forzar: bool = False,
    batch_size: int = 5_000,
) -> Path | None:
    """Ingesta streaming de la carpeta y persiste el Parquet sin saturar RAM.

    Devuelve la ruta del Parquet generado o ``None`` si la carpeta está
    vacía. El Parquet siempre se escribe en :data:`CACHE_DIR` con nombre
    derivado de la firma de la carpeta.
    """
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta: {carpeta}")

    archivos = sorted(list(carpeta.glob("*.atom")) + list(carpeta.glob("*.xml")))
    if not archivos:
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    firma = _firma_carpeta(carpeta, archivos)
    cache_path = CACHE_DIR / f"placsp_{firma}.parquet"

    if cache_path.exists() and not forzar:
        return cache_path

    # Escritor incremental: arranca con el primer lote no vacío para fijar el schema.
    writer: pq.ParquetWriter | None = None
    buffer: list[dict[str, Any]] = []
    total_filas = 0
    total = len(archivos)

    def _flush() -> None:
        nonlocal writer, buffer
        if not buffer:
            return
        tabla = pa.Table.from_pylist(buffer, schema=_PLACSP_SCHEMA)
        if writer is None:
            writer = pq.ParquetWriter(
                cache_path, _PLACSP_SCHEMA, compression="snappy"
            )
        writer.write_table(tabla)
        buffer.clear()

    try:
        for i, arch in enumerate(archivos):
            for entry in _iter_entries(arch):
                fila = _extraer_contrato(entry)
                if fila:
                    buffer.append(_fila_para_parquet(fila))
                    total_filas += 1
                    if len(buffer) >= batch_size:
                        _flush()
            if progreso:
                progreso(i + 1, total)
        _flush()
    finally:
        if writer is not None:
            writer.close()

    if total_filas == 0:
        # Sin filas válidas; eliminamos cualquier rastro vacío.
        if cache_path.exists():
            cache_path.unlink(missing_ok=True)
        return None

    return cache_path


def _quitar_acentos(texto: str) -> str:
    """Devuelve `texto` en minúsculas y sin diacríticos para comparar nombres."""
    import unicodedata
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", sin_acentos).strip()


def _terminos_busqueda(palabras: Iterable[str] | str) -> list[str]:
    if isinstance(palabras, str):
        candidatos = re.split(r"[,;\n]+", palabras)
    else:
        candidatos = palabras
    return [_quitar_acentos(p.strip()) for p in candidatos if p and p.strip()]


def _mascara_busqueda_tolerante(texto: pd.Series, terminos: Iterable[str]) -> pd.Series:
    texto_norm = texto.fillna("").astype(str).map(_quitar_acentos)
    mask = pd.Series(False, index=texto.index)
    for termino in terminos:
        tokens = [token for token in termino.split() if token]
        mask_termino = texto_norm.str.contains(re.escape(termino), na=False)
        if len(tokens) > 1:
            mask_tokens = pd.Series(True, index=texto.index)
            for token in tokens:
                mask_tokens &= texto_norm.str.contains(re.escape(token), na=False)
            mask_termino |= mask_tokens
        mask |= mask_termino
    return mask


def filtrar_por_organos(df: pd.DataFrame, palabras: Iterable[str]) -> pd.DataFrame:
    """Filtra el DataFrame por coincidencia tolerante en el nombre del órgano.

    La comparación es insensible a mayúsculas y a acentos/diacríticos para
    cubrir variantes como "València"/"Valencia" o "A Coruña"/"A Coruna".
    """
    palabras_norm = _terminos_busqueda(palabras)
    if not palabras_norm or df.empty:
        return df
    mask = _mascara_busqueda_tolerante(df["Organo"], palabras_norm)
    return df[mask].copy()


def filtrar_por_texto_organismo(df: pd.DataFrame, busqueda: str) -> pd.DataFrame:
    """Filtra por texto libre en órgano y municipio, tolerando acentos y huecos.

    Permite localizar ayuntamientos por el nombre completo o por fragmentos:
    "Santiago de Compostela", "Santiago Compostela" o "Compostela".
    """
    terminos = _terminos_busqueda(busqueda)
    if not terminos or df.empty:
        return df

    columnas = [col for col in ("Organo", "Municipio") if col in df.columns]
    if not columnas:
        return df.iloc[0:0].copy()

    texto = df[columnas[0]].fillna("").astype(str)
    for columna in columnas[1:]:
        texto = texto + " " + df[columna].fillna("").astype(str)
    mask = _mascara_busqueda_tolerante(texto, terminos)
    return df[mask].copy()


# -----------------------------------------------------------------------------
# Esquema Parquet y consultas DuckDB sobre el caché ya generado
# -----------------------------------------------------------------------------

_PLACSP_SCHEMA = pa.schema([
    pa.field("Organo", pa.string()),
    pa.field("Tipo_Entidad", pa.string()),
    pa.field("Provincia", pa.string()),
    pa.field("CCAA", pa.string()),
    pa.field("Municipio", pa.string()),
    pa.field("Tipo_Contrato", pa.string()),
    pa.field("Concepto", pa.string()),
    pa.field("CPV", pa.string()),
    pa.field("Adjudicatario", pa.string()),
    pa.field("_Adjudicatario_Radar", pa.string()),
    pa.field("Fecha", pa.string()),
    pa.field("Año_Fiscal", pa.int32()),
    pa.field("Importe_euros", pa.float64()),
    pa.field("Link_Expediente", pa.string()),
])


def _fila_para_parquet(fila: dict) -> dict:
    """Asegura tipos compatibles con :data:`_PLACSP_SCHEMA`."""
    fila = {nombre: fila.get(nombre) for nombre in _PLACSP_SCHEMA.names}
    año = fila.get("Año_Fiscal")
    if año is not None:
        try:
            fila["Año_Fiscal"] = int(año)
        except (TypeError, ValueError):
            fila["Año_Fiscal"] = None
    importe = fila.get("Importe_euros")
    if importe is not None:
        try:
            fila["Importe_euros"] = float(importe)
        except (TypeError, ValueError):
            fila["Importe_euros"] = None
    return fila


@dataclass
class MetadatosPLACSP:
    parquet_path: Path
    total_contratos: int
    organos: int
    adjudicatarios: int
    importe_total: float
    rango_fechas: tuple[str | None, str | None]
    ccaa: int


def metadatos_placsp(parquet_path: str | Path) -> MetadatosPLACSP:
    """Resumen rápido (DuckDB) sin cargar el Parquet entero a RAM."""
    parquet_path = Path(parquet_path)
    con = duckdb.connect(database=":memory:")
    fila = con.execute(
        f"""
        SELECT
            COUNT(*)                                AS total_contratos,
            COUNT(DISTINCT Organo)                  AS organos,
            COUNT(DISTINCT Adjudicatario)           AS adjudicatarios,
            COALESCE(SUM(Importe_euros), 0)         AS importe_total,
            MIN(Fecha)                              AS fecha_min,
            MAX(Fecha)                              AS fecha_max,
            COUNT(DISTINCT CCAA)                    AS ccaa
        FROM read_parquet('{parquet_path.as_posix()}')
        """
    ).fetchone()
    return MetadatosPLACSP(
        parquet_path=parquet_path,
        total_contratos=int(fila[0] or 0),
        organos=int(fila[1] or 0),
        adjudicatarios=int(fila[2] or 0),
        importe_total=float(fila[3] or 0.0),
        rango_fechas=(fila[4], fila[5]),
        ccaa=int(fila[6] or 0),
    )


def opciones_placsp(
    parquet_path: str | Path,
    columna: str,
    *,
    where: Mapping[str, Iterable[str]] | None = None,
    limite: int = 5_000,
) -> list[str]:
    """Devuelve los valores únicos de una columna del Parquet (para desplegables).

    `where` permite encadenar selecciones jerárquicas (p. ej. provincias
    sólo de una CCAA seleccionada).
    """
    parquet_path = Path(parquet_path)
    con = duckdb.connect(database=":memory:")
    where_sql, params = _construir_where(where or {})
    where_clauses = [f"{columna} IS NOT NULL"]
    if where_sql:
        where_clauses.append(where_sql)
    sql = (
        f"SELECT DISTINCT {columna} AS v "
        f"FROM read_parquet('{parquet_path.as_posix()}') "
        f"WHERE {' AND '.join(where_clauses)} "
        f"ORDER BY v LIMIT {int(limite)}"
    )
    valores = con.execute(sql, params).fetchall()
    return [str(v[0]) for v in valores if v[0] is not None]


def consultar_placsp(
    parquet_path: str | Path,
    *,
    ccaa: Iterable[str] | None = None,
    provincias: Iterable[str] | None = None,
    municipios: Iterable[str] | None = None,
    tipos_entidad: Iterable[str] | None = None,
    organos: Iterable[str] | None = None,
    años: Iterable[int] | None = None,
    tipos_contrato: Iterable[str] | None = None,
    contiene_adjudicatario: str | None = None,
    contiene_concepto: str | None = None,
    contiene_organo: Iterable[str] | None = None,
    importe_min: float | None = None,
    importe_max: float | None = None,
    limite: int | None = 250_000,
) -> pd.DataFrame:
    """Filtra el Parquet PLACSP con DuckDB y devuelve un DataFrame.

    DuckDB lee el Parquet con *predicate pushdown*, por lo que sólo carga
    las filas que cumplen los filtros. Esto permite trabajar cómodamente
    sobre Parquets de millones de contratos en un portátil.
    """
    parquet_path = Path(parquet_path)
    con = duckdb.connect(database=":memory:")

    clauses: list[str] = []
    params: list[Any] = []

    def _add_in(col: str, valores: Iterable[str] | Iterable[int] | None) -> None:
        if not valores:
            return
        valores = list(valores)
        if not valores:
            return
        marcadores = ", ".join(["?"] * len(valores))
        clauses.append(f"{col} IN ({marcadores})")
        params.extend(valores)

    _add_in("CCAA", ccaa)
    _add_in("Provincia", provincias)
    _add_in("Municipio", municipios)
    _add_in("Tipo_Entidad", tipos_entidad)
    _add_in("Organo", organos)
    _add_in("Año_Fiscal", años)
    _add_in("Tipo_Contrato", tipos_contrato)

    if contiene_adjudicatario:
        clauses.append("LOWER(Adjudicatario) LIKE ?")
        params.append(f"%{contiene_adjudicatario.lower()}%")
    if contiene_concepto:
        clauses.append("LOWER(Concepto) LIKE ?")
        params.append(f"%{contiene_concepto.lower()}%")
    if contiene_organo:
        sub = []
        for palabra in contiene_organo:
            palabra = (palabra or "").strip()
            if not palabra:
                continue
            sub.append("LOWER(Organo) LIKE ?")
            params.append(f"%{palabra.lower()}%")
        if sub:
            clauses.append("(" + " OR ".join(sub) + ")")
    if importe_min is not None:
        clauses.append("Importe_euros >= ?")
        params.append(float(importe_min))
    if importe_max is not None:
        clauses.append("Importe_euros <= ?")
        params.append(float(importe_max))

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    limit_sql = f" LIMIT {int(limite)}" if limite else ""
    sql = (
        f"SELECT * FROM read_parquet('{parquet_path.as_posix()}'){where_sql}{limit_sql}"
    )
    return con.execute(sql, params).fetchdf()


def _construir_where(filtros: Mapping[str, Iterable[str]]) -> tuple[str, list[Any]]:
    """Helper para `opciones_placsp`: construye el WHERE sin el filtro propio."""
    clauses: list[str] = []
    params: list[Any] = []
    for col, valores in filtros.items():
        valores = [v for v in (valores or []) if v]
        if not valores:
            continue
        marcadores = ", ".join(["?"] * len(valores))
        clauses.append(f"{col} IN ({marcadores})")
        params.extend(valores)
    return " AND ".join(clauses), params
