# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: consultas DuckDB y conversión de liquidaciones del Tribunal de Cuentas.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Ingesta de datos del Tribunal de Cuentas (liquidaciones de entes locales).

Dos vías:
1. Si tienes el .accdb original (Liquidaciones2024.accdb): lo convierte
   a CSVs por tabla usando `mdbtools` (brew install mdbtools).
2. Si ya tienes los CSVs `tb_economica.csv` (1,19 M filas) y `tb_inventario.csv`
   los consulta con DuckDB SIN cargarlos en memoria.

DuckDB permite hacer joins, filtros y agregaciones sobre CSVs gigantes
en segundos, perfecto para el caso "millones de presupuestos locales"
que demanda el periodismo de datos sobre gasto público.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import duckdb
import pandas as pd

from .constants import PROVINCIAS_GALICIA

# -----------------------------------------------------------------------------
# Conversión .accdb → CSVs (requiere mdbtools)
# -----------------------------------------------------------------------------

def mdbtools_disponible() -> bool:
    return shutil.which("mdb-tables") is not None and shutil.which("mdb-export") is not None


def _error_mdbtools(comando: list[str], exc: subprocess.CalledProcessError | subprocess.TimeoutExpired) -> str:
    nombre = Path(comando[0]).name
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"{nombre} tardó demasiado y se canceló para evitar bloquear la aplicación."
    stderr = (exc.stderr or "").strip()
    detalle = f": {stderr}" if stderr else ""
    return f"{nombre} terminó con código {exc.returncode}{detalle}"


def listar_tablas_accdb(accdb: str | Path, *, timeout: int = 60) -> list[str]:
    """Devuelve las tablas de una base Access .accdb."""
    if not mdbtools_disponible():
        raise RuntimeError(
            "mdbtools no está instalado. Instálalo con:  brew install mdbtools"
        )
    comando = ["mdb-tables", "-1", str(accdb)]
    try:
        resultado = subprocess.run(
            comando,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(_error_mdbtools(comando, exc)) from exc
    out = resultado.stdout
    return [t.strip() for t in out.splitlines() if t.strip()]


def exportar_accdb_a_csv(
    accdb: str | Path,
    destino: str | Path,
    *,
    tablas: list[str] | None = None,
    progreso=None,
    timeout_listado: int = 60,
    timeout_tabla: int = 300,
) -> list[Path]:
    """Exporta tablas de un .accdb a CSV individuales en `destino`.

    Si `tablas` es None, exporta todas. Devuelve la lista de CSVs creados.
    Si se pasa `progreso`, se invoca antes y después de exportar cada tabla
    como ``progreso(i, total, nombre_tabla, estado)``. Por compatibilidad,
    también acepta callbacks antiguos de tres argumentos.
    """
    accdb = Path(accdb)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if tablas is None:
        tablas = listar_tablas_accdb(accdb, timeout=timeout_listado)

    creados: list[Path] = []
    total = len(tablas)

    def _notificar(i: int, tabla: str, estado: str) -> None:
        if progreso is None:
            return
        try:
            progreso(i, total, tabla, estado)
        except TypeError:
            try:
                progreso(i, total, tabla)
            except Exception:
                pass
        except Exception:
            pass

    for i, tabla in enumerate(tablas, start=1):
        _notificar(i, tabla, "inicio")
        salida = destino / f"{tabla}.csv"
        with salida.open("w", encoding="utf-8") as f:
            comando = ["mdb-export", str(accdb), tabla]
            try:
                subprocess.run(
                    comando,
                    check=True,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_tabla,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                salida.unlink(missing_ok=True)
                raise RuntimeError(f"No se pudo exportar la tabla '{tabla}': {_error_mdbtools(comando, exc)}") from exc
        creados.append(salida)
        _notificar(i, tabla, "fin")
    return creados


# -----------------------------------------------------------------------------
# Consulta DuckDB sobre los CSVs ya extraídos
# -----------------------------------------------------------------------------

def _conn(economica_csv: Path, inventario_csv: Path) -> duckdb.DuckDBPyConnection:
    """Crea una conexión DuckDB que lee los CSV directamente (sin importarlos)."""
    con = duckdb.connect(database=":memory:")
    con.execute(f"""
        CREATE OR REPLACE VIEW econ AS
        SELECT * FROM read_csv_auto('{economica_csv}', HEADER=TRUE);
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW inv AS
        SELECT * FROM read_csv_auto('{inventario_csv}', HEADER=TRUE);
    """)
    return con


def ranking_gasto_capitulo(
    economica_csv: str | Path,
    inventario_csv: str | Path,
    *,
    capitulo: int = 2,
    provincias: tuple[str, ...] | None = PROVINCIAS_GALICIA,
    top: int | None = None,
) -> pd.DataFrame:
    """Devuelve el ranking de gasto por entidad en un capítulo presupuestario.

    Por defecto: Capítulo 2 (gastos corrientes en bienes y servicios) en
    provincias gallegas. Pon provincias=None para toda España.
    Funciona en segundos sobre el CSV de 1,19 M filas gracias a DuckDB.
    """
    economica_csv = Path(economica_csv).resolve()
    inventario_csv = Path(inventario_csv).resolve()
    con = _conn(economica_csv, inventario_csv)

    filtro_prov = ""
    if provincias:
        provs = ", ".join(f"'{p}'" for p in provincias)
        filtro_prov = f"AND substring(trim(CAST(i.codbdgel AS VARCHAR)), 1, 2) IN ({provs})"

    sql = f"""
        SELECT
                        trim(CAST(i.nombreente AS VARCHAR)) AS entidad,
            SUM(TRY_CAST(e.importer AS DOUBLE)) AS total_gastado,
            COUNT(*)                         AS num_partidas
        FROM econ e
        JOIN inv i ON e.idente = i.idente
        WHERE e.tipreig = 'G'
                    AND trim(CAST(e.cdcta AS VARCHAR)) LIKE '{capitulo}%'
          {filtro_prov}
        GROUP BY entidad
        ORDER BY total_gastado DESC NULLS LAST
        {f'LIMIT {int(top)}' if top else ''}
    """
    return con.execute(sql).fetchdf()


def detalle_partidas_entidad(
    economica_csv: str | Path,
    inventario_csv: str | Path,
    entidad_like: str,
    *,
    capitulo: int | None = None,
) -> pd.DataFrame:
    """Devuelve todas las partidas de gasto/ingreso de una entidad concreta.

    `entidad_like` admite wildcards SQL (% _).
    """
    economica_csv = Path(economica_csv).resolve()
    inventario_csv = Path(inventario_csv).resolve()
    con = _conn(economica_csv, inventario_csv)

    filtro_cap = f"AND trim(CAST(e.cdcta AS VARCHAR)) LIKE '{capitulo}%'" if capitulo is not None else ""
    sql = f"""
        SELECT
            trim(CAST(i.nombreente AS VARCHAR)) AS entidad,
            e.tipreig,
            trim(CAST(e.cdcta AS VARCHAR)) AS cuenta,
            TRY_CAST(e.imported AS DOUBLE) AS previsto,
            TRY_CAST(e.importer AS DOUBLE) AS reconocido,
            TRY_CAST(e.importel AS DOUBLE) AS liquidado
        FROM econ e
        JOIN inv i ON e.idente = i.idente
        WHERE LOWER(trim(CAST(i.nombreente AS VARCHAR))) LIKE LOWER('{entidad_like}')
        {filtro_cap}
        ORDER BY reconocido DESC NULLS LAST
    """
    return con.execute(sql).fetchdf()
