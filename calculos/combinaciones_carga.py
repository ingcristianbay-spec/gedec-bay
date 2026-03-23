"""
calculos/combinaciones_carga.py
================================
Combinaciones de carga y factor CD según CIRSOC 601.

Referencia: CIRSOC 601-16, Tabla 2.3.2 y art. 2.3.3
No depende de Streamlit.
"""

import pandas as pd


# ── Factores CD por combinación (CIRSOC 601, Tabla 2.3.2) ──────────────────
CD_POR_COMBINACION = {
    "D":       0.90,
    "D+L":     1.00,
    "D+S":     1.15,
    "D+L+S":   1.15,
    "D+W":     1.60,
}


def calcular_combinaciones(D: float, L: float, S: float, W: float) -> pd.DataFrame:
    """
    Calcula todas las combinaciones de carga y retorna un DataFrame.

    Parámetros
    ----------
    D, L, S, W : float  → Cargas características (kN/m)

    Retorna
    -------
    pd.DataFrame con columnas:
        Combinación | Fórmula | q (kN/m) | CD | q_10 (kN/m)

    Nota: q_10 = q / CD  es la "carga equivalente a 10 años"
    """
    combos = [
        {"Combinación": "D / CD",           "Fórmula": "D",         "q (kN/m)": D,         "CD": CD_POR_COMBINACION["D"]},
        {"Combinación": "(D + L + S) / CD", "Fórmula": "D + L + S", "q (kN/m)": D + L + S, "CD": CD_POR_COMBINACION["D+L+S"]},
        {"Combinación": "(D + L) / CD",     "Fórmula": "D + L",     "q (kN/m)": D + L,     "CD": CD_POR_COMBINACION["D+L"]},
        {"Combinación": "(D + S) / CD",     "Fórmula": "D + S",     "q (kN/m)": D + S,     "CD": CD_POR_COMBINACION["D+S"]},
        {"Combinación": "(D + W) / CD",     "Fórmula": "D + W",     "q (kN/m)": D + W,     "CD": CD_POR_COMBINACION["D+W"]},
    ]

    for c in combos:
        c["q (kN/m)"] = float(c["q (kN/m)"])
        c["CD"]       = float(c["CD"])
        c["q_10 (kN/m)"] = c["q (kN/m)"] / c["CD"]

    return pd.DataFrame(combos, columns=["Combinación", "Fórmula", "q (kN/m)", "CD", "q_10 (kN/m)"])


def combinacion_gobernante(df: pd.DataFrame) -> pd.Series:
    """
    Retorna la fila del DataFrame con la mayor carga equivalente a 10 años.
    Es la combinación que gobierna el diseño.
    """
    idx = pd.to_numeric(df["q_10 (kN/m)"], errors="coerce").idxmax()
    return df.loc[idx]
