"""
calculos/aplastamiento.py
=========================
Verificación al aplastamiento (compresión perpendicular a las fibras)
según CIRSOC 601-16.

No depende de Streamlit.
"""


def area_contacto_apoyo(b_mm: float, La_mm: float) -> float:
    """
    Área neta de contacto en el apoyo (mm²).

    Parámetros
    ----------
    b_mm  : ancho de la sección en contacto (mm)
    La_mm : longitud del apoyo (mm)
    """
    return b_mm * La_mm


def tension_aplastamiento(Vu_kN: float, A_ap_mm2: float) -> float:
    """
    Tensión de aplastamiento fc⊥ = R / A_contacto (N/mm²).

    La reacción R se aproxima con el cortante máximo Vu.
    """
    Vu_N = Vu_kN * 1000.0
    return Vu_N / A_ap_mm2


def resistencia_aplastamiento(Fcp: float, CD: float, CM: float, Ct: float = 1.0) -> float:
    """
    Resistencia modificada F'c⊥ = Fcp · CD · CM · Ct.
    """
    return Fcp * CD * CM * Ct


def verificar_aplastamiento(Vu_kN: float, A_ap_mm2: float, Fcp: float,
                             CD: float, CM: float, Ct: float = 1.0) -> dict:
    """
    Verifica el aplastamiento en el apoyo.

    Retorna dict con fcp_dem, Fcp_mod, ratio, verifica.
    """
    fcp_dem = tension_aplastamiento(Vu_kN, A_ap_mm2)
    Fcp_mod = resistencia_aplastamiento(Fcp, CD, CM, Ct)
    ratio   = fcp_dem / Fcp_mod if Fcp_mod > 0 else float("inf")
    return {
        "fcp_dem":  fcp_dem,
        "Fcp_mod":  Fcp_mod,
        "ratio":    ratio,
        "verifica": ratio <= 1.0,
    }
