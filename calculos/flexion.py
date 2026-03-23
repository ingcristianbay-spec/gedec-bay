"""
calculos/flexion.py
===================
Verificación a flexión según CIRSOC 601-16, art. 3.2.1.

No depende de Streamlit.
"""


def resistencia_flexion(
    Fb: float,
    CD: float,
    CM: float,
    Ct: float = 1.0,
    CF: float = 1.0,
    CV: float = 1.0,
    Cr: float = 1.0,
    CL: float = 1.0,
) -> dict:
    """
    Calcula la resistencia modificada a flexión F'b.

    F*b  = Fb · CD · CM · Ct · CF · CV · Cr   (sin CL)
    F'b  = F*b · CL

    Retorna dict con Fb_estrella y Fb_mod.
    """
    Fb_estrella = Fb * CD * CM * Ct * CF * CV * Cr
    Fb_mod      = Fb_estrella * CL
    return {"Fb_estrella": Fb_estrella, "Fb_mod": Fb_mod}


def verificar_flexion(Mu_kNm: float, W_mm3: float, Fb_mod: float) -> dict:
    """
    Verifica la sección a flexión.

    Parámetros
    ----------
    Mu_kNm  : Momento solicitante máximo (kN·m)
    W_mm3   : Módulo resistente de la sección (mm³)
    Fb_mod  : Resistencia modificada F'b (N/mm²)

    Retorna
    -------
    dict con fb (tensión demandada), ratio, verifica
    """
    Mu_Nmm = Mu_kNm * 1e6          # kN·m → N·mm
    fb     = Mu_Nmm / W_mm3        # N/mm²
    ratio  = fb / Fb_mod if Fb_mod > 0 else float("inf")
    return {
        "fb_dem":    fb,
        "Fb_mod":    Fb_mod,
        "ratio":     ratio,
        "verifica":  ratio <= 1.0,
    }
