"""
calculos/factores_mod.py
========================
Factores de modificación de resistencia según CIRSOC 601-16.

Referencia: Tablas 4.3-3 (madera aserrada) y 5.3-2 (madera laminada encolada)
No depende de Streamlit.
"""

import math


# ── Factor de humedad CM ────────────────────────────────────────────────────

def factores_CM(es_humedo: bool, es_laminada: bool, Fb: float = None, Fc: float = None) -> dict:
    """
    Devuelve los factores CM para cada propiedad.

    Parámetros
    ----------
    es_humedo   : bool  → True si condición húmeda (HRA ≥ 16%)
    es_laminada : bool  → True si es madera laminada encolada (MLE)
    Fb, Fc      : float → Valores del catálogo (para notas especiales de Tabla 4.3-3)

    Referencia: Tabla 4.3-3 (MA) y Tabla 5.3-2 (MLE)

    Retorna
    -------
    dict con claves: Fb, Fv, Fcp, Fc, Ft, E
    """
    if not es_humedo:
        return {"Fb": 1.0, "Fv": 1.0, "Fcp": 1.0, "Fc": 1.0, "Ft": 1.0, "E": 1.0}

    if es_laminada:
        # Tabla 5.3-2
        return {
            "Fb":  0.80,
            "Fv":  0.87,
            "Fcp": 0.53,
            "Fc":  0.73,
            "Ft":  0.80,
            "E":   0.83,
        }
    else:
        # Tabla 4.3-3
        cm = {
            "Fb":  0.85,
            "Fv":  0.97,
            "Fcp": 0.67,
            "Fc":  0.80,
            "Ft":  1.00,
            "E":   0.90,
        }
        # Notas especiales Tabla 4.3-3
        if Fb is not None and not math.isnan(Fb) and Fb <= 7.9:
            cm["Fb"] = 1.00
        if Fc is not None and not math.isnan(Fc) and Fc <= 5.2:
            cm["Fc"] = 1.00
        return cm


# ── Factor de tamaño CF (madera aserrada) ──────────────────────────────────

def factor_CF(d_mm: float) -> float:
    """
    Factor de tamaño CF para madera aserrada (CIRSOC 601, art. 4.3.6).

    CF = min( (150/d)^0.2 , 1.3 )
    """
    if d_mm <= 0:
        return 1.0
    return min((150.0 / d_mm) ** 0.2, 1.3)


# ── Factor de volumen CV (madera laminada encolada) ─────────────────────────

def factor_CV(d_mm: float, b_mm: float) -> float:
    """
    Factor de volumen CV para MLE (CIRSOC 601, art. 5.3.6).

    CV = min( (600/d)^0.1 + (150/b)^0.05 , 1.1 )
    """
    if d_mm <= 0 or b_mm <= 0:
        return 1.0
    return min((600.0 / d_mm) ** 0.1 + (150.0 / b_mm) ** 0.05, 1.1)


# ── Longitud efectiva y esbeltez lateral ───────────────────────────────────

def longitud_efectiva_Le(Lu_m: float, d_mm: float, tipo_apoyo: str) -> float:
    """
    Longitud efectiva de pandeo lateral Le (mm).

    Referencia: CIRSOC 601, Tabla 3.3.3
    """
    Lu_mm = Lu_m * 1000.0
    ratio_db = Lu_mm / d_mm if d_mm > 0 else 1.0
    tipo = (tipo_apoyo or "").lower()

    if "voladizo" in tipo:
        Le_mm = 1.33 * Lu_mm if ratio_db < 7.0 else 0.90 * Lu_mm + 3.0 * d_mm
    else:
        Le_mm = 2.06 * Lu_mm if ratio_db < 7.0 else 1.63 * Lu_mm + 3.0 * d_mm

    return Le_mm


def esbeltez_RB(Le_mm: float, d_mm: float, b_mm: float) -> float:
    """
    Relación de esbeltez lateral RB = sqrt(Le * d / b²).

    Referencia: CIRSOC 601, ec. 3.3.3
    """
    if b_mm <= 0:
        return float("nan")
    return math.sqrt(Le_mm * d_mm / b_mm ** 2)


def tension_critica_FbE(Emin: float, CM_E: float, RB: float) -> float:
    """
    Tensión crítica de pandeo lateral.

    F_bE = 1.2 * E'min / RB²
    E'min = Emin * CM_E   (Ct = 1 asumido)

    Referencia: CIRSOC 601, ec. 3.3.3
    """
    if RB is None or RB <= 0 or Emin is None or math.isnan(Emin):
        return float("nan")
    E_min_mod = Emin * CM_E
    return 1.2 * E_min_mod / (RB ** 2)


# ── Factor de estabilidad CL ────────────────────────────────────────────────

def factor_CL(FbE: float, Fb_estrella: float) -> float:
    """
    Factor de estabilidad lateral CL (ecuación de Ylinen para flexión).

    Referencia: CIRSOC 601, ec. 3.3.3

    Parámetros
    ----------
    FbE          : Tensión crítica de pandeo (N/mm²)
    Fb_estrella  : F*b = Fb · CD · CM · Ct · CF · CV · Cr  (sin CL)

    Retorna
    -------
    CL ∈ [0, 1]
    """
    if FbE is None or math.isnan(FbE) or Fb_estrella <= 0:
        return 1.0

    R = FbE / Fb_estrella
    term1 = (1.0 + R) / 1.9
    radicando = term1 ** 2 - R / 0.95

    if radicando <= 0:
        return 1.0

    CL = term1 - math.sqrt(radicando)
    return max(min(CL, 1.0), 0.0)
