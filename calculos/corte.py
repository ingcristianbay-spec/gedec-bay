"""
calculos/corte.py
=================
Verificación a corte según CIRSOC 601-16, art. 3.2.2.

No depende de Streamlit.
"""

import math


def tension_corte_demandada(Vu_kN: float, seccion: dict) -> float:
    """
    Tensión de corte demandada fv (N/mm²).

    Para sección rectangular: fv = 3V / (2·b·d)   (CIRSOC 601, art. 3.2.2)
    Para sección circular:    fv = 4V / (3·A)

    Parámetros
    ----------
    Vu_kN   : Cortante máximo (kN)
    seccion : dict con shape, b_mm, d_mm o D_mm

    Retorna
    -------
    fv en N/mm²
    """
    Vu_N = Vu_kN * 1000.0

    if seccion["shape"] == "rect":
        b = float(seccion["b_mm"])
        d = float(seccion["d_mm"])
        return 1.5 * Vu_N / (b * d)
    else:
        D  = float(seccion["D_mm"])
        A  = math.pi * D**2 / 4.0
        return (4.0 / 3.0) * Vu_N / A


def resistencia_corte(Fv: float, CD: float, CM: float, Ct: float = 1.0) -> float:
    """
    Resistencia modificada a corte F'v = Fv · CD · CM · Ct.
    """
    return Fv * CD * CM * Ct


def verificar_corte(Vu_kN: float, seccion: dict, Fv: float, CD: float, CM: float, Ct: float = 1.0) -> dict:
    """
    Verifica la sección a corte.

    Retorna dict con fv_dem, Fv_mod, ratio, verifica.
    """
    fv_dem = tension_corte_demandada(Vu_kN, seccion)
    Fv_mod = resistencia_corte(Fv, CD, CM, Ct)
    ratio  = fv_dem / Fv_mod if Fv_mod > 0 else float("inf")
    return {
        "fv_dem":  fv_dem,
        "Fv_mod":  Fv_mod,
        "ratio":   ratio,
        "verifica": ratio <= 1.0,
    }
