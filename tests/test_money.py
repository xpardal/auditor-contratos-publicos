# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: normalización y formato de importes monetarios.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests de utilidades monetarias."""
from __future__ import annotations

import pytest

from core.money import formatear_euros, limpiar_dinero


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("1.234,56 €", 1234.56),
        ("1,234.56", 1234.56),
        ("15000", 15000.0),
        ("15.000", 15000.0),
        ("18.150,00 EUR", 18150.0),
        ("  47.500 €  ", 47500.0),
        ("750 euros", 750.0),
    ],
)
def test_limpiar_dinero_formatos(entrada, esperado):
    assert limpiar_dinero(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize("entrada", [None, "", "abc", "—", "0", "0,00", "-100"])
def test_limpiar_dinero_invalido_devuelve_none(entrada):
    assert limpiar_dinero(entrada) is None


def test_formatear_euros_estilo_europeo():
    assert formatear_euros(1234567.89) == "1.234.567,89 €"
    assert formatear_euros(0.5) == "0,50 €"


def test_formatear_euros_none():
    assert formatear_euros(None) == "—"
