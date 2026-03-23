"""
ui/vigas/entrada_cargas.py
==========================
Inputs de cargas D, L, S, W y panel de combinaciones CIRSOC 601.
"""

import streamlit as st
from calculos.combinaciones_carga import calcular_combinaciones, combinacion_gobernante


def panel_cargas() -> dict:
    """
    Muestra los inputs de carga y la tabla de combinaciones.

    Retorna
    -------
    dict con:
        D, L, S, W     : float  (kN/m)
        q_sinCD        : float  → carga de diseño (kN/m), combinación gobernante
        CD_gov         : float  → CD de la combinación gobernante
        df_q           : pd.DataFrame → tabla de combinaciones
        comb_gov       : pd.Series → fila gobernante
    """
    st.markdown("## Cargas y combinaciones")

    c4, c5, c6, c7, c8, c9, c10 = st.columns([0.9] * 7)

    D = c4.number_input("Carga permanente D [kN/m]", value=0.50, step=0.1, min_value=0.0)
    L = c5.number_input("Carga por uso L [kN/m]",    value=1.20, step=0.1, min_value=0.0)
    S = c6.number_input("Carga por nieve S [kN/m]",  value=0.20, step=0.1, min_value=0.0)
    W = c7.number_input("Carga por viento W [kN/m]", value=-0.20, step=0.01, min_value=-30.0)

    # Calcular combinaciones
    df_q     = calcular_combinaciones(D, L, S, W)
    comb_gov = combinacion_gobernante(df_q)
    q_sinCD  = float(comb_gov["q (kN/m)"])
    CD_gov   = float(comb_gov["CD"])

    # Guardar en session_state
    st.session_state["q_design_kN_m"] = q_sinCD
    st.session_state["CD_flexion"]    = CD_gov

    # Resumen compacto
    with c8:
        st.text_input(
            "Carga de diseño [kN/m]",
            value=f"{q_sinCD:.2f}".replace(".", ","),
            disabled=True,
        )

    with c9:
        st.text_input(
            "Combinación gobernante",
            value=f"{comb_gov['Combinación']} | CD={CD_gov:.2f}",
            disabled=True,
        )

    with c10:
        with st.expander("Ver detalle de combinaciones y $C_D$"):
            df_view = df_q[["Combinación", "CD", "q (kN/m)", "q_10 (kN/m)"]].copy()
            st.dataframe(
                df_view.style.format({
                    "CD":          "{:.2f}",
                    "q (kN/m)":    "{:.2f}",
                    "q_10 (kN/m)": "{:.2f}",
                }),
                use_container_width=True,
            )

    return {
        "D": D, "L": L, "S": S, "W": W,
        "q_sinCD":  q_sinCD,
        "CD_gov":   CD_gov,
        "df_q":     df_q,
        "comb_gov": comb_gov,
    }
