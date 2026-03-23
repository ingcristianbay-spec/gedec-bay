"""
ui/vigas/entrada_geometria.py
==============================
Inputs de geometría, condición de apoyo y factores CM/Cr.

Retorna un dict con todos los valores ingresados por el usuario.
"""

import streamlit as st


# Mapeo de etiquetas UI → código interno
_TIPO_MAP = {
    "simplemente": "simplemente apoyada",
    "articulada":  "propped cantilever",
    "continua":    "ambos empotrados",
    "voladizo":    "voladizo",
}


def panel_geometria() -> dict:
    """
    Muestra los inputs de geometría y condición de apoyo.

    Retorna
    -------
    dict con:
        tipo_calc       : str  → condición de apoyo normalizada
        L_m             : float → luz (m)
        La_cm           : float → longitud apoyo (cm)
        Lu_m            : float → distancia no arriostrada (m)
        es_humedo       : bool
        Cr_flex         : float → factor Cr
    """
    st.markdown("## Geometría y condiciones de la viga")

    g0, g1, g2, g3, g4, g5, g6 = st.columns(
        [1.0, 0.65, 0.65, 0.75, 0.70, 1.15, 1.25]
    )

    apoyo = g0.selectbox(
        "Condición de apoyo",
        ["Simplemente apoyada", "Articulada–Continua", "Continua–Continua", "Voladizo"],
        index=0,
    )

    L_m   = g1.number_input("Luz L [m]",      value=2.60, step=0.1,  min_value=0.0, format="%.2f")
    La_cm = g2.number_input("Apoyo La [cm]",   value=10.0, step=1.0,  min_value=0.1, format="%.2f")
    Lu_m  = g3.number_input("Distancia Lu [m]", value=1.30, step=0.10, min_value=0.0, format="%.2f")

    # Le calculado (solo lectura — se actualiza desde session_state)
    Le_m_show = st.session_state.get("Le_m", None)
    g4.text_input(
        "Le calc [m]",
        f"{Le_m_show:.2f}" if Le_m_show is not None else "—",
        disabled=True,
    )

    cond_serv = g5.selectbox(
        "Condición de humedad (CM)",
        ["Estado seco (HRA < 16%)", "Estado húmedo"],
        index=0,
        key="cond_servicio",
    )

    opcion_cr = g6.selectbox(
        "Distribución lateral (Cr)",
        ["Sin distribución lateral (Cr=1.0)", "Con distribución lateral (Cr=1.10)"],
        index=1,
    )

    # Normalizar tipo de apoyo
    tipo_raw  = apoyo.lower()
    tipo_calc = "simplemente apoyada"
    for clave, valor in _TIPO_MAP.items():
        if clave in tipo_raw:
            tipo_calc = valor
            break

    es_humedo = "húmed" in cond_serv.lower() or "humed" in cond_serv.lower()
    Cr_flex   = 1.10 if "1.10" in opcion_cr else 1.0

    # Guardar en session_state para que otros módulos puedan leerlo
    st.session_state["tipo_apoyo"] = tipo_calc
    st.session_state["Cr_flex"]    = Cr_flex

    return {
        "tipo_calc": tipo_calc,
        "L_m":       L_m,
        "La_cm":     La_cm,
        "Lu_m":      Lu_m,
        "es_humedo": es_humedo,
        "Cr_flex":   Cr_flex,
    }
