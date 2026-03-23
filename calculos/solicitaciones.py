"""
calculos/solicitaciones.py
==========================
Solicitaciones internas (V, M) y flechas máximas para
carga distribuida uniforme (UDL) según condición de apoyo.

No depende de Streamlit.
"""

import numpy as np


# ── Integración numérica por trapecios ─────────────────────────────────────

def _cumtrapz(y, x):
    """Integral acumulada por trapecios (equivalente a scipy.integrate.cumtrapz)."""
    out = np.zeros_like(y, dtype=float)
    out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * (x[1:] - x[:-1]))
    return out


def _deflection_from_M(M, x, EI, enforce_yL=False, enforce_thetaL=False):
    """
    Integra y'' = M/(EI) por trapecios para obtener la flecha.

    Parámetros
    ----------
    M              : array de momentos (N·m)
    x              : array de posiciones (m)
    EI             : rigidez a flexión (N·m²)
    enforce_yL     : si True, impone y(L)=0
    enforce_thetaL : si True, impone theta(L)=0
    """
    y2    = M / EI
    theta = _cumtrapz(y2, x)
    theta = np.r_[0.0, theta][:len(x)]

    y = _cumtrapz(theta, x)
    y = np.r_[0.0, y][:len(x)]

    if enforce_thetaL:
        theta = theta - theta[-1] * (x / x[-1])
        y = _cumtrapz(theta, x)
        y = np.r_[0.0, y][:len(x)]

    if enforce_yL:
        y = y - y[-1] * (x / x[-1])

    return y


# ── Solicitaciones máximas por UDL ─────────────────────────────────────────

def solicitaciones_max_udl(L: float, q_kNm: float, E_Nmm2: float, I_mm4: float, tipo: str) -> dict:
    """
    Calcula V_max, M_max y flecha_max para carga uniforme q.

    Parámetros
    ----------
    L       : float  → Luz (m)
    q_kNm   : float  → Carga distribuida (kN/m), puede ser negativa
    E_Nmm2  : float  → Módulo de elasticidad (N/mm²)
    I_mm4   : float  → Momento de inercia (mm⁴)
    tipo    : str    → Condición de apoyo normalizada

    Retorna
    -------
    dict con:
        reactions       : dict con RA_kN, RB_kN, MA_kNm, MB_kNm
        Vmax_abs_kN     : float
        x_Vmax_m        : float
        Mpos_max_kNm    : float o None
        x_Mpos_m        : float o None
        Mneg_min_kNm    : float o None
        x_Mneg_m        : float o None
        fmax_mm         : float
        x_fmax_m        : float
    """
    out = {
        "reactions": {},
        "Vmax_abs_kN": None, "x_Vmax_m": None,
        "Mpos_max_kNm": None, "x_Mpos_m": None,
        "Mneg_min_kNm": None, "x_Mneg_m": None,
        "fmax_mm": None, "x_fmax_m": None,
    }

    # Unidades internas: N y m
    w  = float(q_kNm) * 1000.0   # kN/m → N/m
    EI = float(E_Nmm2) * 1e6 * float(I_mm4) * 1e-12   # N/mm² * mm⁴ → N·m²
    n  = 4001
    x  = np.linspace(0.0, L, n)
    t  = (tipo or "").lower()

    # 1) Simplemente apoyada
    if "simplemente" in t:
        RA = RB = w * L / 2.0
        out["reactions"] = {"RA_kN": RA/1e3, "RB_kN": RB/1e3, "MA_kNm": 0.0, "MB_kNm": 0.0}
        out["Vmax_abs_kN"]  = abs(w * L / 2.0) / 1e3;  out["x_Vmax_m"] = 0.0
        out["Mpos_max_kNm"] = (w * L**2 / 8.0) / 1e3;  out["x_Mpos_m"] = L / 2.0
        out["fmax_mm"]      = (5 * w * L**4 / (384.0 * EI)) * 1e3; out["x_fmax_m"] = L / 2.0
        return out

    # 2) Articulada–Continua (propped cantilever)
    if "propped" in t or "articulada" in t:
        RB = 3 * w * L / 8.0
        MA = -w * L**2 / 8.0
        VA = w * L - RB
        out["reactions"] = {"RA_kN": VA/1e3, "RB_kN": RB/1e3, "MA_kNm": MA/1e3, "MB_kNm": 0.0}
        out["Vmax_abs_kN"]  = max(abs(VA), abs(RB)) / 1e3;  out["x_Vmax_m"] = 0.0
        out["Mpos_max_kNm"] = (9.0/128.0 * w * L**2) / 1e3
        out["x_Mpos_m"]     = float(np.clip(VA / w, 0.0, L))
        out["Mneg_min_kNm"] = MA / 1e3;  out["x_Mneg_m"] = 0.0
        M = MA + VA * x - w * x**2 / 2.0
        y = _deflection_from_M(M, x, EI, enforce_yL=True)
        idx = int(np.argmax(np.abs(y)))
        out["fmax_mm"] = float(np.abs(y[idx]) * 1e3);  out["x_fmax_m"] = float(x[idx])
        return out

    # 3) Ambos empotrados (fixed-fixed)
    if "empotrado" in t or "continua" in t:
        MA = MB = -w * L**2 / 12.0
        RA = RB = w * L / 2.0
        out["reactions"] = {"RA_kN": RA/1e3, "RB_kN": RB/1e3, "MA_kNm": MA/1e3, "MB_kNm": MB/1e3}
        out["Vmax_abs_kN"]  = abs(w * L / 2.0) / 1e3;   out["x_Vmax_m"] = 0.0
        out["Mpos_max_kNm"] = (w * L**2 / 24.0) / 1e3;  out["x_Mpos_m"] = L / 2.0
        out["Mneg_min_kNm"] = MA / 1e3;                  out["x_Mneg_m"] = 0.0
        out["fmax_mm"]      = (w * L**4 / (384.0 * EI)) * 1e3; out["x_fmax_m"] = L / 2.0
        return out

    # 4) Voladizo (default)
    out["reactions"] = {"RA_kN": (w*L)/1e3, "RB_kN": 0.0, "MA_kNm": (-w*L**2/2.0)/1e3, "MB_kNm": 0.0}
    out["Vmax_abs_kN"]  = abs(w * L) / 1e3;      out["x_Vmax_m"] = 0.0
    out["Mneg_min_kNm"] = (-w * L**2 / 2.0)/1e3; out["x_Mneg_m"] = 0.0
    out["fmax_mm"]      = (w * L**4 / (8.0 * EI)) * 1e3; out["x_fmax_m"] = L
    return out
