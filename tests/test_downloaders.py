# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: descargas reproducibles, navegación Atom y extracción ZIP segura.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests del módulo de descargas (sin red)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from core.downloaders import (
    _extraer_zip_seguro,
    _nombre_desde_url,
    _siguiente_atom,
    descargar_placsp_menores,
    descargar_url_directa,
)


ATOM_SAMPLE = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <title>Test</title>
  <link rel='self' href='https://ej.org/feed_1.atom'/>
  <link rel='next' href='https://ej.org/feed_2.atom'/>
  <entry><title>e1</title></entry>
</feed>"""


def test_siguiente_atom_devuelve_url_next():
    url = _siguiente_atom(ATOM_SAMPLE, "https://ej.org/feed_1.atom")
    assert url == "https://ej.org/feed_2.atom"


def test_siguiente_atom_relativo_se_resuelve():
    contenido = ATOM_SAMPLE.replace(
        b"https://ej.org/feed_2.atom", b"feed_2.atom"
    )
    url = _siguiente_atom(contenido, "https://ej.org/sub/feed_1.atom")
    assert url == "https://ej.org/sub/feed_2.atom"


def test_siguiente_atom_sin_next_devuelve_none():
    contenido = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'><title>x</title></feed>"""
    assert _siguiente_atom(contenido, "https://ej.org/") is None


def test_nombre_desde_url_sanea_caracteres():
    n = _nombre_desde_url("https://ej.org/algo%20extra%C3%B1o.atom", "fallback.atom")
    assert n.endswith(".atom")
    assert " " not in n


def test_descargar_placsp_offline_registra_error_y_manifest(tmp_path, monkeypatch):
    """Sin red: el downloader debe registrar el error y guardar manifiesto."""
    def _fake_descargar(url, *, timeout):
        raise RuntimeError("offline")

    monkeypatch.setattr("core.downloaders._descargar_bytes", _fake_descargar)
    res = descargar_placsp_menores(tmp_path / "placsp", max_archivos=1)
    assert res.errores
    assert res.manifest_path is not None and res.manifest_path.exists()
    payload = json.loads(res.manifest_path.read_text(encoding="utf-8"))
    assert payload["fuente"] == "PLACSP contratos menores"
    assert payload["errores"]


def test_extraer_zip_seguro_rechaza_path_traversal(tmp_path):
    zip_path = tmp_path / "malicioso.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escape.txt", "no")
    with pytest.raises(RuntimeError):
        _extraer_zip_seguro(zip_path, tmp_path / "salida")


def test_descargar_url_directa_offline_no_revienta(tmp_path, monkeypatch):
    def _fake_stream(url, salida, *, timeout):
        raise RuntimeError("offline")

    monkeypatch.setattr("core.downloaders._descargar_stream", _fake_stream)
    res = descargar_url_directa(
        "https://ej.org/datos.csv",
        tmp_path / "destino",
        sobrescribir=True,
    )
    assert res.errores
    assert res.manifest_path and res.manifest_path.exists()
