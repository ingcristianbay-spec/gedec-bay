"""
ui/vigas/entrada_seccion.py
============================
Inputs de sección transversal y material (catálogo de maderas).
"""

import math
import numpy as np
import pandas as pd
import streamlit as st

from calculos.secciones import seccion_rectangular, seccion_circular
from calculos.catalogo  import get_valor
from calculos.factores_mod import factores_CM


def _fmt(val, dec=2, suf=""):
    """Formatea un número con separador de miles y comas decimales (es-AR)."""
    if pd.isna(val):
        return f"—{(' ' + suf) if suf else ''}"
    s = f"{val:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{(' ' + suf) if suf else ''}"


def panel_seccion(df_maderas: pd.DataFrame, es_humedo: bool) -> dict:
    """
    Muestra los inputs de sección y material.

    Parámetros
    ----------
    df_maderas : pd.DataFrame → catálogo de maderas ya cargado
    es_humedo  : bool         → condición de servicio (viene de panel_geometria)

    Retorna
    -------
    dict con:
        seccion     : dict (shape, b_mm, d_mm, D_mm, A_mm2, W_mm3, I_mm4)
        fila        : pd.Series → fila del catálogo seleccionada
        es_laminada : bool
        Fb, Fv, Fcp, Fc, Ft, E, Emin, rho : float
        CM          : dict → factores CM por propiedad
        La_mm       : float
        b_ap_mm     : float
        A_ap_mm2    : float
    """
    st.markdown("## Sección transversal y material")

    c_tipo, c_bD, c_d, c_W_col, c_I_col, c_mat, c_props = st.columns(
        [1.2, 0.8, 0.8, 1.0, 1.0, 1.8, 1.0]
    )

    tipo_sec = c_tipo.selectbox("Tipo de sección", ["Rectangular", "Circular"], index=0)

    # ── Material ──────────────────────────────────────────────────────────────
    opciones = (
        df_maderas["DESIGNACIÓN"].astype(str) + " – " + df_maderas["CLASIF"].astype(str)
    ).tolist()
    choice = c_mat.selectbox("Material", opciones, index=0)

    # ── Geometría ─────────────────────────────────────────────────────────────
    if tipo_sec == "Rectangular":
        b_mm = c_bD.number_input("Ancho b [mm]",  value=50.0,  step=1.0, min_value=1.0, format="%.0f")
        d_mm = c_d.number_input( "Altura d [mm]", value=150.0, step=1.0, min_value=1.0, format="%.0f")
        seccion = seccion_rectangular(b_mm, d_mm)
    else:
        D_mm = c_bD.number_input("Diámetro D [mm]", value=150.0, step=1.0, min_value=1.0, format="%.0f")
        c_d.markdown("&nbsp;", unsafe_allow_html=True)
        seccion = seccion_circular(D_mm)

    c_W_col.text_input("Módulo resistente W [mm³]", f"{seccion['W_mm3']:,.0f}", disabled=True)
    c_I_col.text_input("Momento de inercia I [mm⁴]", f"{seccion['I_mm4']:,.0f}", disabled=True)

    # ── Resolver fila del catálogo ─────────────────────────────────────────────
    designacion, clasif = choice.split(" – ", 1)
    designacion = designacion.strip()
    clasif      = clasif.strip()

    mask = (
        df_maderas["DESIGNACIÓN"].astype(str).str.strip() == designacion
    ) & (
        df_maderas["CLASIF"].astype(str).str.strip() == clasif
    )

    if not mask.any():
        st.error(f"No se encontró en el catálogo: {designacion} – {clasif}")
        st.stop()

    fila = df_maderas.loc[mask].iloc[0]

    es_laminada = "grado" in str(fila.get("CLASIF", "")).lower()

    # ── Propiedades mecánicas ──────────────────────────────────────────────────
    Fb   = get_valor(fila, "Fb",  "fb")
    Fv   = get_valor(fila, "Fv",  "fv")
    Fcp  = get_valor(fila, "FcP", "Fcp", "fcp")
    Fc   = get_valor(fila, "Fc",  "fc")
    Ft   = get_valor(fila, "Ft",  "ft")
    E    = get_valor(fila, "E",   "e")
    Emin = get_valor(fila, "Emin", "EMIN", "E_min")
    rho  = get_valor(fila, "p0.05", "rho0.05", "rho", "densidad")

    # ── Factores CM ────────────────────────────────────────────────────────────
    CM = factores_CM(es_humedo, es_laminada, Fb=Fb, Fc=Fc)

    # Guardar en session_state
    st.session_state["madera_es_laminada"] = es_laminada
    st.session_state["CM_Fb_base"]  = CM["Fb"]
    st.session_state["CM_Fv_base"]  = CM["Fv"]
    st.session_state["CM_Fcp_base"] = CM["Fcp"]
    st.session_state["CM_Fc_base"]  = CM["Fc"]
    st.session_state["CM_Ft_base"]  = CM["Ft"]
    st.session_state["CM_E_base"]   = CM["E"]

    # ── Área de apoyo ──────────────────────────────────────────────────────────
    La_mm   = float(st.session_state.get("La_mm", 100.0))   # viene de geometría
    b_ap_mm = float(seccion["b_mm"] or seccion["D_mm"])
    A_ap    = b_ap_mm * La_mm

    st.session_state["La_mm"]    = La_mm
    st.session_state["b_ap_mm"]  = b_ap_mm
    st.session_state["A_ap_mm2"] = A_ap

    # ── Panel de propiedades ───────────────────────────────────────────────────
    with c_props:
        with st.expander("Propiedades del material ", expanded=False):
            st.markdown(
                f"""
                <div style="font-size:12.5px; line-height:1.25;">
                  <div style="font-weight:700; margin-bottom:6px;">{designacion} – {clasif}</div>
                  <div><b>Fb</b>   = resistencia a <b>flexión</b>     → {_fmt(Fb,   2, 'N/mm²')}</div>
                  <div><b>Fv</b>   = resistencia a <b>corte</b> ∥    → {_fmt(Fv,   2, 'N/mm²')}</div>
                  <div><b>Fcp</b>  = resistencia a <b>comp.</b> ⟂    → {_fmt(Fcp,  2, 'N/mm²')}</div>
                  <div style="margin-top:6px;">
                  <b>E</b>    = módulo elasticidad (prom.) → {_fmt(E,    0, 'N/mm²')}</div>
                  <div><b>Emin</b> = módulo elasticidad (mín.) → {_fmt(Emin, 0, 'N/mm²')}</div>
                  <div><b>ρ</b>    = densidad              → {_fmt(rho,  0, 'kg/m³')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    return {
        "seccion":     seccion,
        "fila":        fila,
        "es_laminada": es_laminada,
        "Fb": Fb, "Fv": Fv, "Fcp": Fcp,
        "Fc": Fc, "Ft": Ft,
        "E":  E,  "Emin": Emin, "rho": rho,
        "CM":       CM,
        "La_mm":    La_mm,
        "b_ap_mm":  b_ap_mm,
        "A_ap_mm2": A_ap,
    }
