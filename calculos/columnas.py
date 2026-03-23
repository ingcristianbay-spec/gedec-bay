"""
calculos/columnas.py
====================
Verificación de columnas a compresión según CIRSOC 601-16, art. 3.3.

ESTADO: esqueleto listo para implementar.

Referencia: CIRSOC 601-16, arts. 3.3.1 a 3.3.4
"""

import math


def factor_CP(Fc: float, FcE: float, c: float = 0.8) -> float:
    """
    Factor de estabilidad de columna CP (ecuación de Ylinen).

    Referencia: CIRSOC 601-16, ec. 3.3.1

    Parámetros
    ----------
    Fc  : resistencia característica a compresión ∥ (N/mm²)
    FcE : tensión crítica de pandeo (N/mm²)
    c   : coeficiente de forma:
          0.8 para madera aserrada
          0.9 para madera laminada encolada (MLE)

    Retorna
    -------
    CP ∈ [0, 1]
    """
    if Fc <= 0 or FcE <= 0:
        return 0.0

    R     = FcE / Fc
    term1 = (1.0 + R) / (2.0 * c)
    radicando = term1**2 - R / c

    if radicando <= 0:
        return 1.0

    CP = term1 - math.sqrt(radicando)
    return max(min(CP, 1.0), 0.0)


def tension_critica_FcE(E_min_mod: float, Le_d: float) -> float:
    """
    Tensión crítica de pandeo de columna.

    FcE = 0.822 · E'min / (Le/d)²

    Referencia: CIRSOC 601-16, ec. 3.3.2

    Parámetros
    ----------
    E_min_mod : E'min modificado por CM y Ct (N/mm²)
    Le_d      : relación de esbeltez Le/d (adimensional)
    """
    if Le_d <= 0:
        return float("nan")
    return 0.822 * E_min_mod / (Le_d**2)


def longitud_efectiva_columna(L_m: float, condicion: str) -> float:
    """
    Longitud efectiva de pandeo Le (m) según condición de vinculación.

    Parámetros
    ----------
    L_m       : longitud libre de la columna (m)
    condicion : "ambos articulados"   → Le = 1.0 · L
                "empotrado-libre"     → Le = 2.0 · L   (voladizo)
                "empotrado-articulado"→ Le = 0.7 · L
                "ambos empotrados"    → Le = 0.5 · L

    Referencia: CIRSOC 601-16, Tabla 3.3-1
    """
    factores = {
        "ambos articulados":    1.0,
        "empotrado-libre":      2.0,
        "empotrado-articulado": 0.7,
        "ambos empotrados":     0.5,
    }
    k = factores.get(condicion.lower(), 1.0)
    return k * L_m


def verificar_columna(
    Pu_kN: float,
    seccion: dict,
    Fc: float,
    Emin: float,
    CD: float,
    CM: float,
    Ct: float = 1.0,
    CF: float = 1.0,
    Le_d: float = None,
    c: float = 0.8,
) -> dict:
    """
    Verificación de columna a compresión pura.

    Parámetros
    ----------
    Pu_kN   : carga axial de compresión (kN)
    seccion : dict con A_mm2
    Fc      : resistencia característica a compresión ∥ (N/mm²)
    Emin    : módulo de elasticidad mínimo (N/mm²)
    CD, CM, Ct, CF : factores de modificación
    Le_d    : relación de esbeltez Le/d (si None, no se aplica CP)
    c       : coeficiente de forma (0.8 MA, 0.9 MLE)

    Retorna
    -------
    dict con fc_dem, Fc_mod, CP, ratio, verifica
    """
    Pu_N   = Pu_kN * 1000.0
    A_mm2  = float(seccion["A_mm2"])
    fc_dem = Pu_N / A_mm2   # N/mm²

    # F*c (sin CP)
    Fc_estrella = Fc * CD * CM * Ct * CF

    # Factor CP
    if Le_d is not None and Le_d > 0 and not math.isnan(Emin):
        E_min_mod = Emin * CM * Ct
        FcE = tension_critica_FcE(E_min_mod, Le_d)
        CP  = factor_CP(Fc_estrella, FcE, c)
    else:
        CP  = 1.0
        FcE = float("nan")

    Fc_mod = Fc_estrella * CP
    ratio  = fc_dem / Fc_mod if Fc_mod > 0 else float("inf")

    return {
        "fc_dem":     fc_dem,
        "Fc_mod":     Fc_mod,
        "Fc_estrella": Fc_estrella,
        "CP":          CP,
        "FcE":         FcE,
        "ratio":       ratio,
        "verifica":    ratio <= 1.0,
    }
