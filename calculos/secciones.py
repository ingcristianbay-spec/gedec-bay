"""
calculos/secciones.py
=====================
Propiedades geométricas de secciones transversales.

CIRSOC 601 - Madera estructural
No depende de Streamlit. Solo recibe números, devuelve números.
"""

import math


def seccion_rectangular(b_mm: float, d_mm: float) -> dict:
    """
    Calcula las propiedades de una sección rectangular.

    Parámetros
    ----------
    b_mm : float  → Ancho (mm)
    d_mm : float  → Altura (mm)

    Retorna
    -------
    dict con:
        shape   : "rect"
        b_mm    : float
        d_mm    : float
        A_mm2   : área (mm²)
        W_mm3   : módulo resistente (mm³)
        I_mm4   : momento de inercia (mm⁴)
    """
    if b_mm <= 0 or d_mm <= 0:
        raise ValueError(f"Dimensiones inválidas: b={b_mm}, d={d_mm}")

    A = b_mm * d_mm
    W = b_mm * d_mm**2 / 6.0
    I = b_mm * d_mm**3 / 12.0

    return {
        "shape": "rect",
        "b_mm": b_mm,
        "d_mm": d_mm,
        "D_mm": None,
        "A_mm2": A,
        "W_mm3": W,
        "I_mm4": I,
    }


def seccion_circular(D_mm: float) -> dict:
    """
    Calcula las propiedades de una sección circular maciza.

    Parámetros
    ----------
    D_mm : float  → Diámetro (mm)

    Retorna
    -------
    dict con A_mm2, W_mm3, I_mm4
    """
    if D_mm <= 0:
        raise ValueError(f"Diámetro inválido: D={D_mm}")

    A = math.pi * D_mm**2 / 4.0
    W = math.pi * D_mm**3 / 32.0
    I = math.pi * D_mm**4 / 64.0

    return {
        "shape": "circ",
        "b_mm": None,
        "d_mm": None,
        "D_mm": D_mm,
        "A_mm2": A,
        "W_mm3": W,
        "I_mm4": I,
    }
