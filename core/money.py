# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: limpieza y formato de importes monetarios.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Utilidades de limpieza y formato de importes."""
from __future__ import annotations

import re
import pandas as pd


def limpiar_dinero(valor) -> float | None:
    """Convierte cualquier representación de importe a float.

    Devuelve None (no 0.0) si el valor no es parseable, para no contaminar sumas.
    Soporta formato europeo (1.234,56 / 15.000), americano (1,234.56 / 15,000)
    y plano. Los importes deben ser positivos: cualquier valor ≤ 0 o con signo
    negativo se considera no válido a efectos del análisis.
    """
    if pd.isna(valor):
        return None
    bruto = str(valor).strip()
    if bruto.startswith('-'):
        return None
    texto = bruto.replace('€', '').replace('euros', '').replace('EUR', '').strip()
    texto = re.sub(r'[^\d.,]', '', texto)
    if not texto:
        return None

    try:
        if '.' in texto and ',' in texto:
            # Coexisten ambos separadores: decide por la posición del último
            if texto.rfind(',') > texto.rfind('.'):
                # Europeo: 1.234,56
                texto = texto.replace('.', '').replace(',', '.')
            else:
                # Americano: 1,234.56
                texto = texto.replace(',', '')
        elif ',' in texto:
            # Solo comas. 3 dígitos tras la última coma => separador de miles
            ultimos = texto.rsplit(',', 1)[1]
            if len(ultimos) == 3 and texto.count(',') >= 1 and len(texto) - len(ultimos) - 1 <= 3:
                texto = texto.replace(',', '')
            else:
                texto = texto.replace(',', '.')
        elif '.' in texto:
            # Solo puntos. Si hay varios o exactamente 3 dígitos tras el último
            # punto, lo tratamos como separador de miles europeo (15.000, 1.234.567).
            ultimos = texto.rsplit('.', 1)[1]
            if texto.count('.') > 1 or (len(ultimos) == 3 and len(texto) - len(ultimos) - 1 <= 3):
                texto = texto.replace('.', '')
            # Si hay 1 o 2 dígitos tras el punto, es decimal: dejar tal cual.

        resultado = float(texto)
        return resultado if resultado > 0 else None
    except ValueError:
        return None


def formatear_euros(valor: float) -> str:
    """Formatea un float como string de importe europeo: 1.234,56 €."""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
