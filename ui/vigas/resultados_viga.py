"""
ui/vigas/resultados_viga.py
============================
Muestra los resultados de todas las verificaciones de la viga.

Cada función recibe los resultados ya calculados (dicts)
y solo se encarga de mostrarlos en pantalla.
"""

import math
import streamlit as st
from ui.estilos import card_verificacion, resultado_ratio


# ── Helpers de display ────────────────────────────────────────────────────────

def _fila_verificacion(titulo: str, col_metrica_1, label_1: str, val_1: str,
                        col_metrica_2, label_2: str, val_2: str,
                        col_metrica_3, label_3: str, val_3: str,
                        col_resultado, label_ratio: str, res: dict,
                        col_detalle, detalle_fn):
    """Layout estándar de 6 columnas para cada verificación."""
    st.markdown(card_verificacion(titulo), unsafe_allow_html=True)

    col_metrica_1.metric(label_1, val_1)
    col_metrica_2.metric(label_2, val_2)
    col_metrica_3.metric(label_3, val_3)

    col_resultado.markdown(
        resultado_ratio(label_ratio, res["ratio"], res["verifica"]),
        unsafe_allow_html=True,
    )

    with col_detalle:
        with st.expander("Ver factores / detalles"):
            detalle_fn()


# ── Flexión ───────────────────────────────────────────────────────────────────

def mostrar_flexion(res_flex: dict, factores: dict):
    """
    Parámetros
    ----------
    res_flex : dict  → salida de calculos.flexion.verificar_flexion()
    factores : dict  → Fb, CD, CM, Ct, CF, CV, Cr, CL, Le_m, RB, FbE, etc.
    """
    st.markdown("## Verificaciones de la viga")

    c0, c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 2.2, 2.0])

    with c0:
        st.markdown(card_verificacion("DISEÑO A<br>FLEXIÓN"), unsafe_allow_html=True)

    c1.metric("Momento solicitante $M_u$", f"{factores['Mu_kNm']:.2f} kN·m")
    c2.metric("Tensión máxima $f_b$",       f"{res_flex['fb_dem']:.2f} N/mm²")
    c3.metric("Resistencia final $F'_b$",   f"{res_flex['Fb_mod']:.2f} N/mm²")

    with c4:
        st.markdown(
            resultado_ratio("Relación demanda/capacidad (f<sub>b</sub> / F′<sub>b</sub>)",
                            res_flex["ratio"], res_flex["verifica"]),
            unsafe_allow_html=True,
        )

    with c5:
        with st.expander("Ver factores aplicados a $F'_b$"):
            f = factores
            st.write(f"**Fb (catálogo):** {f['Fb']:.2f} N/mm²")
            st.write(f"**CD:** {f['CD']:.2f}")
            st.write(f"**CM:** {f['CM']:.2f}")
            st.write(f"**Ct:** {f.get('Ct', 1.0):.2f}")
            st.write(f"**Cr:** {f['Cr']:.2f}")
            if f.get("es_laminada"):
                st.write(f"**CV (volumen, MLE):** {f['CV']:.2f}")
            else:
                st.write(f"**CF (tamaño, MA):** {f['CF']:.2f}")
            st.write(f"**CL (pandeo lateral):** {f['CL']:.3f}")

            if f.get("seccion_circ"):
                st.info("Sección **circular**: no aplica pandeo lateral.")
            else:
                st.write(f"Le = **{f.get('Le_m', 0):.2f} m**")
                st.write(f"Lu/d = **{f.get('ratio_db', 0):.2f}**")
                st.write(f"RB = **{f.get('RB', 0):.2f}**")
                st.write(f"E'min modificado = **{f.get('E_min_mod', 0):.2f}** N/mm²")
                st.write(f"F_bE = **{f.get('FbE', 0):.2f}** N/mm²")


# ── Corte ─────────────────────────────────────────────────────────────────────

def mostrar_corte(res_corte: dict, factores: dict):
    c0, c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 2.2, 2.0])

    with c0:
        st.markdown(card_verificacion("DISEÑO<br>A CORTE"), unsafe_allow_html=True)

    c1.metric("Corte solicitante $V_u$",  f"{factores['Vu_kN']:.2f} kN")
    c2.metric("Tensión de corte $f_v$",   f"{res_corte['fv_dem']:.2f} N/mm²")
    c3.metric("Resistencia final $F'_v$", f"{res_corte['Fv_mod']:.2f} N/mm²")

    with c4:
        st.markdown(
            resultado_ratio("Relación demanda/capacidad (f<sub>v</sub> / F′<sub>v</sub>)",
                            res_corte["ratio"], res_corte["verifica"]),
            unsafe_allow_html=True,
        )

    with c5:
        with st.expander("Ver factores aplicados a $F'_v$"):
            f = factores
            st.write(f"**Fv (catálogo):** {f['Fv']:.2f} N/mm²")
            st.write(f"**CD:** {f['CD']:.2f}")
            st.write(f"**CM:** {f['CM_v']:.2f}")
            st.write(f"**Ct:** {f.get('Ct', 1.0):.2f}")


# ── Aplastamiento ─────────────────────────────────────────────────────────────

def mostrar_aplastamiento(res_ap: dict, factores: dict):
    c0, c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 2.2, 2.0])

    with c0:
        st.markdown(card_verificacion("DISEÑO AL<br>APLASTAMIENTO"), unsafe_allow_html=True)

    c1.metric("Reacción $R$ (≈ $V_u$)",       f"{factores['Vu_kN']:.2f} kN")
    c2.metric("Tensión $f_{c⊥}$",             f"{res_ap['fcp_dem']:.2f} N/mm²")
    c3.metric("Resistencia final $F'_{c⊥}$",  f"{res_ap['Fcp_mod']:.2f} N/mm²")

    with c4:
        st.markdown(
            resultado_ratio("Relación demanda/capacidad (f<sub>c⊥</sub> / F′<sub>c⊥</sub>)",
                            res_ap["ratio"], res_ap["verifica"]),
            unsafe_allow_html=True,
        )

    with c5:
        with st.expander("Ver factores aplicados a $F'_{c⊥}$"):
            f = factores
            st.write(f"**Fcp (catálogo):** {f['Fcp']:.2f} N/mm²")
            st.write(f"**CD:** {f['CD']:.2f}")
            st.write(f"**CM:** {f['CM_cp']:.2f}")
            st.write(f"**b (ancho efectivo):** {f['b_ap_mm']:.1f} mm")
            st.write(f"**Lₐ:** {f['La_mm']:.1f} mm")
            st.write(f"**Área neta A:** {f['A_ap_mm2']:.0f} mm²")


# ── Deformaciones ─────────────────────────────────────────────────────────────

def mostrar_deformaciones(res_def: dict, L_m: float) -> float:
    """
    Retorna el valor de p_L_perm ingresado por el usuario.
    """
    c0, c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 2.2, 2.0])

    with c0:
        st.markdown(card_verificacion("VERIFICACIÓN DE<br>DEFORMACIONES"), unsafe_allow_html=True)

    with c1:
        p_L_perm = st.number_input(
            "%L permanente",
            min_value=0.0, max_value=100.0, value=30.0, step=5.0, format="%.0f",
            key="p_L_perm",
        ) / 100.0

    c2.metric("Flecha instantánea",  f"{res_def['di_inst_mm']:.2f} mm")
    c3.metric("Flecha (D + %L)",     f"{res_def['di_LD_mm']:.2f} mm")

    with c4:
        st.markdown(
            resultado_ratio("Control deformaciones",
                            res_def["ratio_ctrl"], res_def["verifica"]),
            unsafe_allow_html=True,
        )

    with c5:
        with st.expander("Ver más detalles"):
            r = res_def
            st.markdown(f"""
**Deformaciones por acción (mm):**
- Δ(D): **{r['di_D']:.2f}**  |  Δ(L): **{r['di_L']:.2f}**
- Δ(S): **{r['di_S']:.2f}**  |  Δ(W): **{r['di_W']:.2f}**

**Instantánea** (crítica: {r['crit_inst']}):
- Δi = {r['di_inst_mm']:.2f} mm  |  Límite L/360 = {r['lim_inst_mm']:.2f} mm  |  ratio = {r['ratio_inst']:.2f}

**Permanente:**
- Δperm = {r['df_perm_mm']:.2f} mm  |  Límite L/300 = {r['lim_perm_mm']:.2f} mm  |  ratio = {r['ratio_perm']:.2f}

**Control:** ratio_max = **{r['ratio_ctrl']:.2f}**
""")

    return p_L_perm


# ── Vibraciones ───────────────────────────────────────────────────────────────

def mostrar_vibraciones(res_vib: dict, tipo: str):
    c0, c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 2, 2.2, 2.0])

    with c0:
        st.markdown(card_verificacion("VERIFICACIÓN<br>POR VIBRACIONES"), unsafe_allow_html=True)

    with c1:
        n_vigas_m = st.number_input(
            "Vigas por metro",
            min_value=1.0, max_value=5.0, value=1.0, step=1.0, format="%.0f",
            key="n_vigas_por_m",
        )

    f0    = res_vib["f0_hz"]
    delta = res_vib["delta_1kN_mm"]

    c2.metric("Frecuencia f₀", f"{f0:.2f} Hz"    if not math.isnan(f0)    else "—")
    c3.metric("Δi (1 kN)",     f"{delta:.2f} mm" if not math.isnan(delta) else "—")

    with c4:
        st.markdown(
            resultado_ratio("Control vibraciones (f₀ y Δi)",
                            res_vib["r_max"], res_vib["verifica"]),
            unsafe_allow_html=True,
        )

    with c5:
        with st.expander("Ver más detalles"):
            r = res_vib
            st.write(f"Tipo de apoyo: {tipo}")
            st.markdown("**Límites (art. 3.2.3)**")
            st.write(f"- f₀ > {r['lim_f0_hz']:.2f} Hz")
            st.write(f"- Δi ≤ {r['lim_delta_mm']:.2f} mm")
            st.markdown("**Relaciones de verificación**")
            st.write(f"- r_f = {r['r_f']:.3f}")
            st.write(f"- r_Δ = {r['r_d']:.3f}")
            st.write(f"- r_max = **{r['r_max']:.3f}**")

    return n_vigas_m


