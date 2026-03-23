"""
calculos/vibraciones.py
=======================
Verificación de vibraciones por tránsito humano según CIRSOC 601-16, art. 3.2.3.

No depende de Streamlit.
"""

import math
import numpy as np


def beta1_primer_modo(tipo_apoyo: str) -> float:
    """Parámetro modal β1 del primer modo (Euler-Bernoulli)."""
    t = (tipo_apoyo or "").lower()
    if "voladizo" in t:
        return 1.875104068711961
    if "empotrado" in t or "fixed" in t:
        return 4.730040744862704
    if "propped" in t:
        return 3.926602312047919
    return math.pi   # simplemente apoyada (default)


def frecuencia_natural_hz(L_m: float, E_Nmm2: float, I_mm4: float,
                           w_kNm: float, tipo: str) -> float:
    """
    Frecuencia natural del primer modo (Hz).

    f0 = (β1²/2π) · sqrt( EI / (m·L⁴) )

    Parámetros
    ----------
    w_kNm : carga lineal para masa (kN/m) — típicamente D + p%·L
    """
    if L_m <= 0 or E_Nmm2 <= 0 or I_mm4 <= 0:
        return float("nan")

    EPa  = float(E_Nmm2) * 1e6       # N/mm² → Pa
    Im4  = float(I_mm4)  * 1e-12     # mm⁴   → m⁴
    g    = 9.81
    m    = abs(float(w_kNm)) * 1000.0 / g   # kg/m

    if m <= 0:
        return float("nan")

    beta = beta1_primer_modo(tipo)
    return (beta**2) / (2.0 * math.pi) * math.sqrt((EPa * Im4) / (m * L_m**4))


def flecha_1kN_FE(L_m: float, E_Nmm2: float, I_mm4: float,
                   n_vigas: float, tipo: str, n_el: int = 80) -> float:
    """
    Flecha (mm) bajo carga puntual de 1 kN distribuida entre n_vigas,
    calculada con elementos finitos de viga Euler-Bernoulli.

    Referencia: CIRSOC 601-16, art. 3.2.3
    """
    if L_m <= 0 or E_Nmm2 <= 0 or I_mm4 <= 0 or n_el < 2:
        return float("nan")

    EPa = float(E_Nmm2) * 1e6
    Im4 = float(I_mm4)  * 1e-12
    EI  = EPa * Im4

    n_nodes = n_el + 1
    x  = np.linspace(0.0, L_m, n_nodes)
    Le = L_m / n_el

    k = (EI / Le**3) * np.array([
        [12,     6*Le,   -12,    6*Le   ],
        [6*Le,   4*Le**2, -6*Le, 2*Le**2],
        [-12,   -6*Le,    12,   -6*Le   ],
        [6*Le,   2*Le**2, -6*Le, 4*Le**2],
    ], dtype=float)

    ndof = 2 * n_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    F = np.zeros(ndof, dtype=float)

    for e in range(n_el):
        dofs = [2*e, 2*e+1, 2*(e+1), 2*(e+1)+1]
        K[np.ix_(dofs, dofs)] += k

    t   = (tipo or "").lower()
    xP  = L_m if "voladizo" in t else L_m / 2.0
    P   = 1000.0 / float(n_vigas)   # N
    idP = int(np.argmin(np.abs(x - xP)))
    F[2*idP] -= P

    # Condiciones de borde
    if "voladizo" in t:
        fixed = [0, 1]
    elif "empotrado" in t:
        fixed = [0, 1, 2*(n_nodes-1), 2*(n_nodes-1)+1]
    elif "propped" in t:
        fixed = [0, 1, 2*(n_nodes-1)]
    else:
        fixed = [0, 2*(n_nodes-1)]

    free = np.array([i for i in range(ndof) if i not in fixed], dtype=int)
    try:
        uf = np.linalg.solve(K[np.ix_(free, free)], F[free])
    except np.linalg.LinAlgError:
        return float("nan")

    u = np.zeros(ndof)
    u[free] = uf
    return abs(u[2*idP]) * 1000.0   # m → mm


def verificar_vibraciones(
    L_m: float, E_Nmm2: float, I_mm4: float,
    w_masa_kNm: float, n_vigas: float, tipo: str,
    lim_f0_hz: float = 8.0,
) -> dict:
    """
    Verifica vibraciones según CIRSOC 601-16, art. 3.2.3.

    Retorna dict con f0, delta_1kN, lim_f0, lim_delta, ratios, verifica.
    """
    f0          = frecuencia_natural_hz(L_m, E_Nmm2, I_mm4, w_masa_kNm, tipo)
    delta_1kN   = flecha_1kN_FE(L_m, E_Nmm2, I_mm4, n_vigas, tipo)
    lim_delta   = 7.5 / (L_m ** 1.2) if L_m > 0 else float("nan")

    r_f = (lim_f0_hz / f0)    if (not math.isnan(f0)      and f0 > 0)      else float("inf")
    r_d = (delta_1kN / lim_delta) if (not math.isnan(delta_1kN) and lim_delta > 0) else float("inf")
    r_max = max(r_f, r_d)

    return {
        "f0_hz":         f0,
        "delta_1kN_mm":  delta_1kN,
        "lim_f0_hz":     lim_f0_hz,
        "lim_delta_mm":  lim_delta,
        "r_f":           r_f,
        "r_d":           r_d,
        "r_max":         r_max,
        "verifica":      r_max <= 1.0,
    }
