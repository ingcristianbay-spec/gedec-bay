"""
app.py
======
Archivo principal de la aplicación CIRSOC 601.

Para ejecutar:
    streamlit run app.py

Este archivo es el "director de orquesta":
- No hace cálculos (eso lo hace calculos/)
- No genera pantallas directamente (eso lo hace ui/)
- Solo conecta los datos entre módulos
"""

import os
import math
import pandas as pd
import streamlit as st
from datetime import date

# ── Configuración de página (DEBE ser el primer comando st.*) ──────────────
st.set_page_config(
    page_title="Vigas de madera – CIRSOC 601",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports de módulos propios ─────────────────────────────────────────────
from ui.estilos       import aplicar_estilos
from ui.encabezado    import mostrar_encabezado

from ui.vigas.entrada_geometria import panel_geometria
from ui.vigas.entrada_cargas    import panel_cargas
from ui.vigas.entrada_seccion   import panel_seccion
from ui.vigas.resultados_viga   import (
    mostrar_flexion, mostrar_corte, mostrar_aplastamiento,
    mostrar_deformaciones, mostrar_vibraciones,
)

from calculos.catalogo      import load_catalog
from calculos.secciones     import seccion_rectangular, seccion_circular
from calculos.factores_mod  import (
    factor_CF, factor_CV,
    longitud_efectiva_Le, esbeltez_RB, tension_critica_FbE, factor_CL,
)
from calculos.solicitaciones import solicitaciones_max_udl
from calculos.flexion        import resistencia_flexion, verificar_flexion
from calculos.corte          import verificar_corte
from calculos.aplastamiento  import verificar_aplastamiento
from calculos.deformaciones  import verificar_deformaciones
from calculos.vibraciones    import verificar_vibraciones


# ===========================================================================
# 1. ESTILOS Y ENCABEZADO
# ===========================================================================
aplicar_estilos()
mostrar_encabezado(version="v1.0.0", fecha=date.today().strftime("%d/%m/%Y"))

with st.sidebar:
    st.markdown("### 📚 Documentos de referencia")
    st.markdown("""
- [CIRSOC 601-16 (Norma completa)](http://www.inti.gob.ar/assets/uploads/files/cirsoc/aprobados%20en%202016/CIRSOC601-completo.pdf)
- [Suplementos CIRSOC 601 (2020)](http://www.inti.gob.ar/assets/uploads/files/cirsoc/vigencia-2013/area600/Suplementos-del-CIRSOC-601-2020.pdf)
- [Manual CIRSOC 601](http://www.inti.gob.ar/assets/uploads/files/cirsoc/aprobados%20en%202016/manual601-completo.pdf)
- [Guía CIRSOC Madera](http://www.inti.gob.ar/assets/uploads/files/cirsoc/aprobados%20en%202016/guia-CIRSOCMADERA-24ABRIL_compressed.pdf)
- [Documento TVM 2017](https://www.inti.gob.ar/assets/uploads/files/cirsoc/01-En-vigencia-legal-a-partir-de-2013/600/tvm2017.pdf)
- [Guía Didáctica de Clasificación Estructural](https://www.inti.gob.ar/assets/uploads/files/cirsoc/01-En-vigencia-legal-a-partir-de-2013/600/Guia-Didactica-Clasificacion-Estructural-Madera.pdf)
""")
    st.markdown("---")
    st.markdown("### ⚠️ Aviso")
    st.caption(
        "Esta herramienta es de apoyo al predimensionado y verificación. "
        "Los resultados no reemplazan el criterio profesional ni la consulta "
        "completa de la normativa vigente (CIRSOC 601-16). "
        "El proyectista es responsable de verificar de forma independiente "
        "todos los cálculos antes de su aplicación."
    )


    
# ===========================================================================
# 2. CARGA DEL CATÁLOGO DE MADERAS
# ===========================================================================
CATALOG_PATH = os.path.join("datos", "cirsoc 601-maderas.xlsx")
df_maderas = None

if os.path.exists(CATALOG_PATH):
    df_maderas = load_catalog(CATALOG_PATH)
else:
    st.warning("No se encontró el catálogo local. Podés cargar uno manualmente.")
    xlsx_file = st.file_uploader("Cargar Excel de maderas", type=["xlsx"])
    if xlsx_file:
        df_maderas = load_catalog(xlsx_file)

if df_maderas is None:
    st.error("No se pudo cargar el catálogo de maderas. Cargá un Excel válido para continuar.")
    st.stop()

cols_requeridas = {"DESIGNACIÓN", "CLASIF", "Fb", "E"}
faltan = cols_requeridas - set(df_maderas.columns)
if faltan:
    st.error("Faltan columnas obligatorias en el catálogo: " + ", ".join(sorted(faltan)))
    st.stop()


# ===========================================================================
# 3. INPUTS DEL USUARIO
# ===========================================================================

# ── Geometría y condiciones ────────────────────────────────────────────────
geo = panel_geometria()
tipo   = geo["tipo_calc"]
L_m    = geo["L_m"]
La_cm  = geo["La_cm"]
Lu_m   = geo["Lu_m"]
La_mm  = La_cm * 10.0

# Guardar La_mm para que entrada_seccion pueda leerlo
st.session_state["La_mm"] = La_mm

# ── Cargas ─────────────────────────────────────────────────────────────────
cargas = panel_cargas()
D, L_q, S, W = cargas["D"], cargas["L"], cargas["S"], cargas["W"]
q_sinCD = cargas["q_sinCD"]
CD_gov  = cargas["CD_gov"]
df_q    = cargas["df_q"]
comb_gov = cargas["comb_gov"]

# ── Sección y material ─────────────────────────────────────────────────────
mat = panel_seccion(df_maderas, es_humedo=geo["es_humedo"])
seccion     = mat["seccion"]
es_laminada = mat["es_laminada"]
Fb, Fv, Fcp = mat["Fb"], mat["Fv"], mat["Fcp"]
E,  Emin    = mat["E"],  mat["Emin"]
CM          = mat["CM"]
A_ap_mm2    = mat["A_ap_mm2"]
b_ap_mm     = mat["b_ap_mm"]

# Validaciones básicas antes de calcular
if pd.isna(Fb):
    st.error("Fb no definido en el catálogo para esta madera.")
    st.stop()
if La_mm <= 0 or A_ap_mm2 <= 0:
    st.error("La longitud de apoyo La debe ser > 0.")
    st.stop()

# Dimensiones de la sección
if seccion["shape"] == "rect":
    b_mm = seccion["b_mm"]
    d_mm = seccion["d_mm"]
else:
    b_mm = d_mm = seccion["D_mm"]

W_mm3 = seccion["W_mm3"]
I_mm4 = seccion["I_mm4"]


# ===========================================================================
# 4. CÁLCULOS ESTRUCTURALES
# ===========================================================================

# ── Solicitaciones (V y M) ─────────────────────────────────────────────────
q_abs = abs(q_sinCD)
udl   = solicitaciones_max_udl(L_m, q_abs, E, I_mm4, tipo)

Mu_kNm = max(abs(udl.get("Mpos_max_kNm") or 0.0),
             abs(udl.get("Mneg_min_kNm") or 0.0))
Vu_kN  = float(udl.get("Vmax_abs_kN", 0.0))

# ── Factores de modificación para flexión ─────────────────────────────────
Ct = 1.0
Cr = geo["Cr_flex"]
CF = 1.0
CV = 1.0

if seccion["shape"] == "circ":
    seccion_circ = True
    CL    = 1.0
    FbE   = None
    RB    = None
    Le_m  = None
    ratio_db = None
    E_min_mod = None
    if seccion["shape"] == "circ":
        st.warning("Sección **circular** ⇒ no se verifica pandeo lateral.")
else:
    seccion_circ = False

    if es_laminada:
        CV = factor_CV(d_mm, b_mm)
    else:
        CF = factor_CF(d_mm)

    Le_mm    = longitud_efectiva_Le(Lu_m, d_mm, tipo)
    Le_m     = Le_mm / 1000.0
    RB       = esbeltez_RB(Le_mm, d_mm, b_mm)
    ratio_db = (Lu_m * 1000.0) / d_mm if d_mm > 0 else 0.0

    E_min_mod = Emin * CM["E"] if not math.isnan(Emin) else float("nan")
    FbE       = tension_critica_FbE(Emin, CM["E"], RB)

    # Guardar Le en session_state para mostrarlo en el input
    st.session_state["Le_m"] = Le_m

    # F*b (sin CL) para calcular CL
    Fb_estrella = Fb * CD_gov * CM["Fb"] * Ct * CF * CV * Cr
    CL = factor_CL(FbE, Fb_estrella)

# ── Resistencia y verificación a flexión ──────────────────────────────────
res_resist = resistencia_flexion(Fb, CD_gov, CM["Fb"], Ct, CF, CV, Cr, CL)
res_flex   = verificar_flexion(Mu_kNm, W_mm3, res_resist["Fb_mod"])
res_flex["ratio"] = res_flex["ratio"]   # alias para consistencia

# ── Verificación a corte ───────────────────────────────────────────────────
res_corte = verificar_corte(Vu_kN, seccion, Fv, CD_gov, CM["Fv"], Ct)

# ── Verificación al aplastamiento ──────────────────────────────────────────
res_ap = verificar_aplastamiento(Vu_kN, A_ap_mm2, Fcp, CD_gov, CM["Fcp"], Ct)

# ── Deformaciones: necesitamos el input %L → calculamos después del widget ─
# (se calculan después de mostrar el input en mostrar_deformaciones)
E_def = float(E) * CM["E"] * Ct   # E' para deformaciones (sin CD)


# ===========================================================================
# 5. MOSTRAR RESULTADOS
# ===========================================================================

# Factores para el panel de detalles de flexión
factores_flex = {
    "Fb": Fb, "CD": CD_gov, "CM": CM["Fb"], "Ct": Ct,
    "CF": CF, "CV": CV, "Cr": Cr, "CL": CL,
    "Mu_kNm": Mu_kNm,
    "es_laminada": es_laminada,
    "seccion_circ": seccion_circ,
    "Le_m": Le_m, "ratio_db": ratio_db,
    "RB": RB, "FbE": FbE, "E_min_mod": E_min_mod,
}
mostrar_flexion(res_flex, factores_flex)

factores_corte = {"Fv": Fv, "CD": CD_gov, "CM_v": CM["Fv"], "Ct": Ct, "Vu_kN": Vu_kN}
mostrar_corte(res_corte, factores_corte)

factores_ap = {
    "Fcp": Fcp, "CD": CD_gov, "CM_cp": CM["Fcp"],
    "Vu_kN": Vu_kN, "b_ap_mm": b_ap_mm, "La_mm": La_mm, "A_ap_mm2": A_ap_mm2,
}
mostrar_aplastamiento(res_ap, factores_ap)

# Deformaciones: el input %L está dentro del widget, se re-calcula al cambiar
p_L_perm = mostrar_deformaciones.__wrapped__ if hasattr(mostrar_deformaciones, "__wrapped__") else None

# Calculamos deformaciones con el valor actual de session_state
p_L_perm_val = st.session_state.get("p_L_perm", 30.0) / 100.0

res_def = verificar_deformaciones(
    D=D, L=L_q, S=S, W=W,
    p_L_perm=p_L_perm_val,
    L_m=L_m, E_Nmm2=E_def, I_mm4=I_mm4, tipo=tipo,
)
mostrar_deformaciones(res_def, L_m)

# Vibraciones: el input n_vigas está dentro del widget
n_vigas_val  = st.session_state.get("n_vigas_por_m", 1.0)
w_masa_kNm   = abs(D + p_L_perm_val * L_q)

res_vib = verificar_vibraciones(
    L_m=L_m, E_Nmm2=E_def, I_mm4=I_mm4,
    w_masa_kNm=w_masa_kNm,
    n_vigas=n_vigas_val,
    tipo=tipo,
)
mostrar_vibraciones(res_vib, tipo)


