"""
calculos/deformaciones.py
=========================
Verificación de deformaciones (flechas) según CIRSOC 601-16, art. 3.2.2.

No depende de Streamlit.
"""

from calculos.solicitaciones import solicitaciones_max_udl


def flecha_udl(q_kNm: float, L_m: float, E_Nmm2: float, I_mm4: float, tipo: str) -> float:
    """
    Flecha máxima (mm) para carga distribuida q (kN/m).
    Devuelve valor con signo de q.
    """
    q = float(q_kNm)
    if abs(q) < 1e-12:
        return 0.0

    sgn = 1.0 if q >= 0 else -1.0
    sol = solicitaciones_max_udl(L_m, abs(q), E_Nmm2, I_mm4, tipo)
    fmm = float(sol.get("fmax_mm", 0.0))
    return sgn * abs(fmm)


def verificar_deformaciones(
    D: float, L: float, S: float, W: float,
    p_L_perm: float,
    L_m: float, E_Nmm2: float, I_mm4: float, tipo: str,
    Kcr: float = 1.5,
    contraflecha_mm: float = 0.0,
) -> dict:
    """
    Verifica deformaciones según CIRSOC 601-16.

    Parámetros
    ----------
    D, L, S, W    : cargas características (kN/m)
    p_L_perm      : fracción de L considerada permanente (0–1), ej: 0.30
    L_m           : luz (m)
    E_Nmm2        : módulo E modificado (N/mm²)
    I_mm4         : momento de inercia (mm⁴)
    tipo          : condición de apoyo normalizada
    Kcr           : factor de fluencia (default 1.5, CIRSOC 601)
    contraflecha  : contraflecha inicial (mm), default 0

    Retorna
    -------
    dict con:
        di_D, di_L, di_S, di_W      : flechas instantáneas por acción (mm)
        di_inst_mm                  : flecha instantánea variables (max[L+S, W])
        crit_inst                   : qué combinación gobierna la instantánea
        di_LD_mm                    : flecha por carga LD (D + p%·L)
        df_perm_mm                  : flecha permanente final
        lim_inst_mm                 : límite L/360
        lim_perm_mm                 : límite L/300
        ratio_inst, ratio_perm      : relaciones demanda/capacidad
        ratio_ctrl                  : máximo de ambas
        ok_inst, ok_perm, verifica  : bool
    """
    L_mm = L_m * 1000.0

    def _f(q): return flecha_udl(q, L_m, E_Nmm2, I_mm4, tipo)

    di_D = _f(D)
    di_L = _f(L)
    di_S = _f(S)
    di_W = _f(W)

    # Flecha instantánea de variables: max( |L+S|, |W| )
    di_sum_LS = di_L + di_S
    if abs(di_sum_LS) >= abs(di_W):
        di_V      = di_sum_LS
        crit_inst = "L+S"
    else:
        di_V      = di_W
        crit_inst = "W"

    di_inst_mm = abs(di_V)

    # Flecha por carga LD: D + p%·L
    di_LD     = di_D + p_L_perm * di_L
    di_LD_mm  = abs(di_LD)

    # Flecha permanente: Kcr·LD + CD - contraflecha
    # CD = (1-p%)·L + S  (W no se incluye en la permanente)
    di_CD      = (1.0 - p_L_perm) * di_L + di_S
    df_perm    = Kcr * di_LD + di_CD - contraflecha_mm
    df_perm_mm = abs(df_perm)

    # Límites
    lim_inst_mm = L_mm / 360.0
    lim_perm_mm = L_mm / 300.0

    ratio_inst = di_inst_mm / lim_inst_mm if lim_inst_mm > 0 else float("inf")
    ratio_perm = df_perm_mm / lim_perm_mm if lim_perm_mm > 0 else float("inf")
    ratio_ctrl = max(ratio_inst, ratio_perm)

    ok_inst = ratio_inst <= 1.0
    ok_perm = ratio_perm <= 1.0

    return {
        "di_D": di_D, "di_L": di_L, "di_S": di_S, "di_W": di_W,
        "di_inst_mm": di_inst_mm,
        "crit_inst": crit_inst,
        "di_LD_mm": di_LD_mm,
        "df_perm_mm": df_perm_mm,
        "lim_inst_mm": lim_inst_mm,
        "lim_perm_mm": lim_perm_mm,
        "ratio_inst": ratio_inst,
        "ratio_perm": ratio_perm,
        "ratio_ctrl": ratio_ctrl,
        "ok_inst": ok_inst,
        "ok_perm": ok_perm,
        "verifica": ok_inst and ok_perm,
    }
