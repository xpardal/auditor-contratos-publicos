# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: normalización de fechas PLACSP.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests de ingesta PLACSP."""
from __future__ import annotations

import pandas as pd

from core.constants import inferir_municipio
from core import placsp
from core.placsp import _normalizar_fecha_placsp, cargar_placsp, filtrar_por_organos, filtrar_por_texto_organismo


def test_normalizar_fecha_placsp_repara_anos_con_ceros_iniciales():
    assert _normalizar_fecha_placsp("0023-10-06", max_year=2026) == "2023-10-06"
    assert _normalizar_fecha_placsp("0024-05-20", max_year=2026) == "2024-05-20"


def test_normalizar_fecha_placsp_descarta_anos_implausibles():
    assert _normalizar_fecha_placsp("0274-07-31", max_year=2026) is None
    assert _normalizar_fecha_placsp("1902-01-18", max_year=2026) is None
    assert _normalizar_fecha_placsp("2004-02-21", max_year=2026) is None


def test_extrae_tipo_contrato_desde_typecode():
    from pathlib import Path
    from core.placsp import _extraer_contrato
    import xml.etree.ElementTree as ET

    sample = Path("sample/contratosMenoresPerfilesContratantes_2024")
    if not sample.is_dir():
        return
    archivos = sorted(sample.glob("*.atom"))[:5]
    tipos = set()
    for arch in archivos:
        for _, entry in ET.iterparse(arch, events=("end",)):
            if entry.tag == "{http://www.w3.org/2005/Atom}entry":
                fila = _extraer_contrato(entry)
                if fila and fila.get("Tipo_Contrato"):
                    tipos.add(fila["Tipo_Contrato"])
                entry.clear()
        if {"Servicios", "Suministros", "Obras"} <= tipos:
            break
    assert {"Servicios", "Suministros"} <= tipos
    assert "Servicios/Suministros" not in tipos


def test_cargar_placsp_recrea_cache_si_se_borro_durante_la_sesion(tmp_path, monkeypatch):
        carpeta = tmp_path / "placsp"
        carpeta.mkdir()
        (carpeta / "contratos.atom").write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
            xmlns:cbc="urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2"
            xmlns:cac="urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2">
    <entry>
        <title>Servicio de prueba</title>
        <summary>Órgano de Contratación: Concello de Proba; Importe: 14900,00</summary>
        <updated>2024-01-10T09:00:00Z</updated>
        <link href="https://contrataciondelestado.es/test" />
        <cac:ProcurementProject><cbc:TypeCode>2</cbc:TypeCode></cac:ProcurementProject>
        <cac:WinningParty><cbc:Name>ACME SL</cbc:Name></cac:WinningParty>
        <cbc:AwardDate>2024-01-10</cbc:AwardDate>
    </entry>
</feed>
""",
                encoding="utf-8",
        )
        cache_borrada = tmp_path / ".cache" / "anidada"
        monkeypatch.setattr(placsp, "CACHE_DIR", cache_borrada)
        assert not cache_borrada.exists()

        df = cargar_placsp(carpeta, batch_size=1)

        assert cache_borrada.exists()
        assert df["Adjudicatario"].tolist() == ["ACME SL"]
        assert df["Importe_euros"].tolist() == [14900.0]


def test_inferir_municipio_desde_organo_local():
    assert inferir_municipio("Alcaldía del Concello de Rois") == "Rois"
    assert inferir_municipio("Junta de Gobierno del Ayuntamiento de Cartagena") == "Cartagena"
    assert inferir_municipio("Órgano de Contratación de la Ciudad Autónoma de Ceuta") == "Ceuta"
    assert inferir_municipio("Servicio Murciano de Salud") is None


def test_filtrar_por_organos_tolera_acentos_y_nombres_compuestos():
    df = pd.DataFrame({
        "Organo": [
            "Alcaldía del Concello de Santiago de Compostela",
            "Alcaldía del Ayuntamiento de Santiago del Teide",
            "Presidencia de la Diputación Provincial de Valencia",
        ]
    })

    assert filtrar_por_organos(df, ["Santiago de Compostela"])["Organo"].tolist() == [
        "Alcaldía del Concello de Santiago de Compostela"
    ]
    assert filtrar_por_organos(df, ["Santiago Compostela"])["Organo"].tolist() == [
        "Alcaldía del Concello de Santiago de Compostela"
    ]
    assert filtrar_por_organos(df, ["València"])["Organo"].tolist() == [
        "Presidencia de la Diputación Provincial de Valencia"
    ]


def test_filtrar_por_texto_organismo_busca_en_organo_y_municipio():
    df = pd.DataFrame({
        "Organo": [
            "Junta de Gobierno Local",
            "Alcaldía del Ayuntamiento de Santiago del Teide",
            "Alcaldía del Concello de A Coruña",
        ],
        "Municipio": [
            "Santiago de Compostela",
            "Santiago del Teide",
            "A Coruña",
        ],
    })

    assert filtrar_por_texto_organismo(df, "Compostela")["Municipio"].tolist() == [
        "Santiago de Compostela"
    ]
    assert filtrar_por_texto_organismo(df, "Santiago Compostela")["Municipio"].tolist() == [
        "Santiago de Compostela"
    ]
    assert filtrar_por_texto_organismo(df, "coruna")["Municipio"].tolist() == [
        "A Coruña"
    ]