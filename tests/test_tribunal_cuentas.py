# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: consultas Tribunal de Cuentas con DuckDB.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

from __future__ import annotations

import subprocess

import pytest

from core.tribunal_cuentas import detalle_partidas_entidad, exportar_accdb_a_csv, listar_tablas_accdb, ranking_gasto_capitulo


def test_ranking_gasto_capitulo_acepta_codigos_numericos(tmp_path):
    economica = tmp_path / "tb_economica.csv"
    inventario = tmp_path / "tb_inventario.csv"
    economica.write_text(
        "idente,tipreig,cdcta,importer,imported,importel\n"
        "1,G,221,120000,130000,118000\n"
        "1,G,226,80000,85000,79000\n"
        "2,G,221,50000,52000,49000\n"
        "3,I,100,99999,99999,99999\n",
        encoding="utf-8",
    )
    inventario.write_text(
        "idente,nombreente,codbdgel\n"
        "1,Concello de Santiago,15078\n"
        "2,Concello de Ames,15002\n"
        "3,Entidad Ingreso,15000\n",
        encoding="utf-8",
    )

    ranking = ranking_gasto_capitulo(economica, inventario, capitulo=2, provincias=None)
    assert ranking.iloc[0]["entidad"] == "Concello de Santiago"
    assert ranking.iloc[0]["total_gastado"] == 200000
    assert ranking.iloc[1]["entidad"] == "Concello de Ames"

    detalle = detalle_partidas_entidad(economica, inventario, "%santiago%", capitulo=2)
    assert detalle["cuenta"].tolist() == ["221", "226"]


def test_listar_tablas_accdb_convierte_timeout_en_error_claro(monkeypatch, tmp_path):
    accdb = tmp_path / "Liquidaciones.accdb"
    accdb.write_bytes(b"fake")
    monkeypatch.setattr("core.tribunal_cuentas.mdbtools_disponible", lambda: True)

    def _run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", _run)
    with pytest.raises(RuntimeError, match="tardó demasiado"):
        listar_tablas_accdb(accdb, timeout=1)


def test_exportar_accdb_a_csv_elimina_parcial_si_mdb_export_falla(monkeypatch, tmp_path):
    accdb = tmp_path / "Liquidaciones.accdb"
    destino = tmp_path / "csv"
    accdb.write_bytes(b"fake")

    def _run(*args, **kwargs):
        stdout = kwargs.get("stdout")
        if stdout is not None:
            stdout.write("parcial")
        raise subprocess.CalledProcessError(2, args[0], stderr="tabla dañada")

    monkeypatch.setattr(subprocess, "run", _run)
    with pytest.raises(RuntimeError, match="tabla dañada"):
        exportar_accdb_a_csv(accdb, destino, tablas=["tb_economica"], timeout_tabla=1)

    assert not (destino / "tb_economica.csv").exists()
