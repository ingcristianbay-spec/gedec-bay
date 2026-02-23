# app_streamlit_autocatalog.py
import os
import streamlit as st
import pandas as pd
import numpy as np
import math


# ------------------ CONFIG DE PÁGINA ------------------
st.set_page_config(
    page_title="Vigas de madera – CIRSOC 601",
    page_icon="🪵",
    layout="wide",                    # ahora usa todo el ancho
    initial_sidebar_state="collapsed" # opcional: oculta la barra lateral
)

# CSS para ajustar el ancho según el dispositivo
st.markdown("""
<style>
/* Escritorio grande */
@media (min-width: 1400px) {
  .block-container { max-width: 1400px; }
}

/* Laptops y tablets horizontales */
@media (min-width: 992px) and (max-width: 1399px) {
  .block-container { max-width: 1100px; }
}

/* Tablets verticales y móviles */
@media (max-width: 991px) {
  .block-container {
    max-width: 95vw;
    padding-left: 1rem;
    padding-right: 1rem;
  }
  h1 { line-height: 1.15; }
}
</style>
""", unsafe_allow_html=True)

st.title("Diseño de vigas de madera (CIRSOC 601)")


# ======================================================
# =========== UTILIDADES DE INTEGRACIÓN =================
# ======================================================
def _cumtrapz(y, x):
    out = np.zeros_like(y, dtype=float)
    out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * (x[1:] - x[:-1]))
    return out

def _deflection_from_M(M, x, EI, enforce_yL=False, enforce_thetaL=False):
    """
    Integra y'' = M/(E*I) por trapecios usando _cumtrapz (sin SciPy).
    """
    y2 = M / EI
    theta = _cumtrapz(y2, x)
    theta = np.r_[0.0, theta]
    theta = theta[:len(x)]

    y = _cumtrapz(theta, x)
    y = np.r_[0.0, y]
    y = y[:len(x)]

    if enforce_thetaL:
        # imponer theta(L)=0
        theta = theta - theta[-1] * (x / x[-1])
        y = _cumtrapz(theta, x)
        y = np.r_[0.0, y]
        y = y[:len(x)]

    if enforce_yL:
        # imponer y(L)=0
        y = y - y[-1] * (x / x[-1])

    return y

# ======================================================
# ========== ANÁLISIS UDL SEGÚN CONDICIÓN DE APOYO =====
# ======================================================
def solicitaciones_max_udl(L, qNpm, EPa, Im4, tipo):
    out = {
        "reactions": {},
        "Vmax_abs_kN": None, "x_Vmax_m": None,
        "Mpos_max_kNm": None, "x_Mpos_m": None,
        "Mneg_min_kNm": None, "x_Mneg_m": None,
        "fmax_mm": None, "x_fmax_m": None,
    }
    EI = EPa * Im4
    n = 4001
    x = np.linspace(0.0, L, n)
    w = qNpm

    # 1) Simplemente apoyada
    if "simplemente apoyada" in tipo:
        RA = RB = w * L / 2.0
        out["reactions"] = {"RA_kN": RA/1000, "RB_kN": RB/1000, "MA_kNm": 0.0, "MB_kNm": 0.0}
        out["Vmax_abs_kN"] = (w * L / 2.0) / 1000.0; out["x_Vmax_m"] = 0.0
        out["Mpos_max_kNm"] = (w * L**2 / 8.0) / 1000.0; out["x_Mpos_m"] = L/2.0
        out["Mneg_min_kNm"] = None; out["x_Mneg_m"] = None
        out["fmax_mm"] = (5 * w * L**4 / (384.0 * EI)) * 1000.0; out["x_fmax_m"] = L/2.0
        return out

    # 2) Articulada–Continua (propped cantilever)
    if "propped cantilever" in tipo:
        RB = 3 * w * L / 8.0
        MA = -w * L**2 / 8.0
        VA = w * L - RB
        out["reactions"] = {"RA_kN": VA/1000, "RB_kN": RB/1000, "MA_kNm": MA/1000, "MB_kNm": 0.0}

        Vmax_abs = max(abs(VA), abs(RB))
        out["Vmax_abs_kN"] = Vmax_abs / 1000.0
        out["x_Vmax_m"] = 0.0 if abs(VA) >= abs(RB) else L

        out["Mpos_max_kNm"] = (9.0/128.0 * w * L**2) / 1000.0
        out["x_Mpos_m"] = float(np.clip(VA / w, 0.0, L))
        out["Mneg_min_kNm"] = MA / 1000.0
        out["x_Mneg_m"] = 0.0

        # Flecha por integración numérica: y(0)=0, θ(0)=0, y(L)=0
        M = MA + VA * x - w * x**2 / 2.0
        y = _deflection_from_M(M, x, EI, enforce_yL=True, enforce_thetaL=False)
        idx = int(np.argmax(np.abs(y)))
        out["fmax_mm"] = float(np.abs(y[idx]) * 1000.0)
        out["x_fmax_m"] = float(x[idx])
        return out

    # 3) Ambos empotrados (fixed-fixed)
    if "ambos empotrados" in tipo:
        MA = MB = -w * L**2 / 12.0
        RA = RB = w * L / 2.0
        out["reactions"] = {"RA_kN": RA/1000, "RB_kN": RB/1000, "MA_kNm": MA/1000, "MB_kNm": MB/1000}
        out["Vmax_abs_kN"] = (w * L / 2.0) / 1000.0; out["x_Vmax_m"] = 0.0
        out["Mpos_max_kNm"] = (w * L**2 / 24.0) / 1000.0; out["x_Mpos_m"] = L/2.0
        out["Mneg_min_kNm"] = MA / 1000.0; out["x_Mneg_m"] = 0.0
        out["fmax_mm"] = (w * L**4 / (384.0 * EI)) * 1000.0; out["x_fmax_m"] = L/2.0
        return out

    # 4) Voladizo (empotramiento–libre)
    out["reactions"] = {"RA_kN": (w*L)/1000.0, "RB_kN": 0.0, "MA_kNm": (-w*L**2/2.0)/1000.0, "MB_kNm": 0.0}
    out["Vmax_abs_kN"] = (w * L) / 1000.0; out["x_Vmax_m"] = 0.0
    out["Mpos_max_kNm"] = None; out["x_Mpos_m"] = None
    out["Mneg_min_kNm"] = (-w * L**2 / 2.0) / 1000.0; out["x_Mneg_m"] = 0.0
    out["fmax_mm"] = (w * L**4 / (8.0 * EI)) * 1000.0; out["x_fmax_m"] = L
    return out

# ======================================================
# =========== LECTOR ROBUSTO DE CATÁLOGO ===============
# ======================================================
def load_catalog_anywhere(xlsx_path_or_buf):
    raw = pd.read_excel(xlsx_path_or_buf, header=None, dtype=str)
    hdr_row = None

    # Buscar fila de encabezados (DESIGNACIÓN / DESIGNACION)
    for i in range(min(40, len(raw))):
        ups = [str(x).strip().upper() for x in raw.iloc[i].tolist()]
        if "DESIGNACIÓN" in ups or "DESIGNACION" in ups:
            hdr_row = i
            break

    if hdr_row is None:
        # Tomar primera fila como encabezado
        df = pd.read_excel(xlsx_path_or_buf, header=0, decimal=",")
        df.columns = [str(c).strip() for c in df.columns]
        return _normalize_catalog(df)

    # Leer usando la fila detectada como encabezado
    df = pd.read_excel(xlsx_path_or_buf, header=hdr_row, decimal=",")
    df.columns = [str(c).strip() for c in df.columns]

    # Si la fila siguiente tiene unidades (N/mm2, kg/m3), la salteamos
    if len(df) > 0:
        first = [str(v).strip().lower() for v in df.iloc[0].tolist()]
        if any(v in {"n/mm2", "n/mm²", "kg/m3"} for v in first):
            df = df.iloc[1:].reset_index(drop=True)

    return _normalize_catalog(df)


def _normalize_catalog(df):
    # --- aliases de encabezados
    rename_map = {
        "DESIGNACION": "DESIGNACIÓN",
        "CLASE": "CLASIF",
        "GRADO": "CLASIF",
        "RHO": "p0.05",
        "RH0.05": "p0.05",
        "P0.05": "p0.05",
        "DESCRIPCION": "DESCRIPCIÓN",
        "DESCRIPCIÓN": "DESCRIPCIÓN",
    }

    cols_norm = []
    for c in df.columns:
        k = str(c).strip()
        ku = k.upper()
        if ku in rename_map:
            cols_norm.append(rename_map[ku])
        elif ku in {"FB","FT","FV","FCP","FC","E","E0.05","E0,05","EMIN"}:
            cols_norm.append(k.replace(",", "."))  # por si viene con coma decimal
        else:
            cols_norm.append(k)

    df.columns = cols_norm

    # columnas que queremos conservar (incluye densidad p0.05)
    want = [
        "DESIGNACIÓN","CLASIF","DESCRIPCIÓN",
        "Fb","Ft","Fv","FcP","Fc","E","E0.05","Emin","p0.05"
    ]
    present = [c for c in want if c in df.columns]
    df = df[present].copy()

    if "DESIGNACIÓN" in df.columns:
        df = df[df["DESIGNACIÓN"].astype(str).str.strip().ne("")].copy()

    # No convertir a número las columnas de texto
    text_cols = {"DESIGNACIÓN","CLASIF","DESCRIPCIÓN"}
    numeric_cols = [c for c in df.columns if c not in text_cols]

    for c in numeric_cols:
        df[c] = (
            df[c].astype(str)
                 .str.replace("\u2212","-", regex=False)
                 .str.replace(",", ".", regex=False)
        )
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.reset_index(drop=True)



# ======================================================
# ============ CARGA DEL CATÁLOGO (AUTOMÁTICA) =========
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(BASE_DIR, "data", "cirsoc 601-maderas.xlsx")

df_maderas = None
if os.path.exists(CATALOG):
    with open(CATALOG, "rb") as f:
        df_maderas = load_catalog_anywhere(f)
    st.success(f"Catálogo de maderas cargado automáticamente: {os.path.basename(CATALOG)}")
else:
    st.warning("No se encontró el catálogo local. Podés cargar uno manualmente.")
    xlsx_file = st.file_uploader("Cargar Excel de maderas", type=["xlsx"])
    if xlsx_file:
        df_maderas = load_catalog_anywhere(xlsx_file)

# ======================================================
# ================= ENTRADAS DE CÁLCULO =================
# ======================================================

st.subheader("Entradas de cálculo")

# ---------------- GEOMETRÍA + APOYO + CM + Cr ----------------
st.markdown("### Geometría y condiciones de la viga")

# FILA 1: L, La, Le, Condición de apoyo
g1, g2, g3, g4, g5 = st.columns([0.8, 0.6, 0.6, 1.0, 0.6])

L_m   = g1.number_input("Luz L [m]", value=2.60, step=0.1, min_value=0.0, format="%.2f")
La_cm = g2.number_input("Apoyo La [cm]", value=10.0, step=1.0, min_value=0.0, format="%.2f")
st.caption("La se usa para verificar aplastamiento ⟂ fibras (compresión perpendicular) en apoyos.")
Lu_m  = g3.number_input("Distancia Lu [m]", value=1.30, step=0.10, min_value=0.0, format="%.2f")

apoyo = g4.selectbox(
    "Condición de apoyo",
    ["Simplemente apoyada", "Articulada–Continua", "Continua–Continua", "Voladizo"],
    index=0
)

Le_m_show = st.session_state.get("Le_m", None)
g5.text_input("Le calc [m]", f"{Le_m_show:.2f}" if Le_m_show is not None else "—", disabled=True)

# Normalizar condición de apoyo
tipo_apoyo_raw = apoyo.lower()
if "simplemente" in tipo_apoyo_raw:
    tipo_calc = "simplemente apoyada"
elif "articulada" in tipo_apoyo_raw:
    tipo_calc = "propped cantilever"
elif "continua" in tipo_apoyo_raw:
    tipo_calc = "ambos empotrados"
elif "voladizo" in tipo_apoyo_raw:
    tipo_calc = "voladizo"
else:
    tipo_calc = "simplemente apoyada"

st.session_state["tipo_apoyo"] = tipo_calc

# FILA 2: CM y Cr (más compactos)
c1, c2 = st.columns([1.0, 1.0])

condicion_servicio = c1.selectbox(
    "Condición de humedad (CM)",
    ["Estado seco (HRA < 16%)", "Estado húmedo"],
    index=0,
    key="cond_servicio"   # 👈 clave para recuperarlo después
)

# Cr
opcion_cr = c2.selectbox(
    "Distribución lateral de cargas (Cr)",
    ["Sin distribución lateral (Cr=1.0)", "Con distribución lateral (Cr=1.10)"],
    index=1
)

Cr_flex = 1.10 if "1.10" in opcion_cr else 1.0
st.session_state["Cr_flex"] = Cr_flex


# ---------------- CARGAS ----------------
st.markdown("### Cargas sobre la viga (en kN/m)")
# st.caption(" CIRSOC 601: D = carga permanente, L = uso, S = nieve, W = viento")

c4, c5, c6, c7 = st.columns([0.8, 0.8, 0.8, 0.8])
D_kN_m = c4.number_input("Carga permanente D [kN/m]", value=0.50, step=0.1, min_value=0.0)
L_kN_m = c5.number_input("Carga por uso L [kN/m]", value=1.20, step=0.1, min_value=0.0)
S_kN_m = c6.number_input("Carga por nieve S [kN/m]", value=0.20, step=0.1, min_value=0.0)
W_kN_m = c7.number_input("Carga por viento W [kN/m]", value=-0.20, step=0.01, min_value=-30.0)

# ======================================================
# ========== COMBINACIÓN DE CARGAS (CIRSOC 601) ========
# ======================================================

st.subheader("Cargas máxima de diseño con factores $C_D$ ")

# Asegurar presencia de variables
D = float(D_kN_m) if "D_kN_m" in locals() else 0.0
L = float(L_kN_m) if "L_kN_m" in locals() else 0.0
S = float(S_kN_m) if "S_kN_m" in locals() else 0.0
W = float(W_kN_m) if "W_kN_m" in locals() else 0.0

# CD fijos por norma (CIRSOC 601)
CD_dict = {
    "D": 0.90, 
    "D+L": 1.00,
    "D+S": 1.15,
    "D+L+S": 1.15,
    "D+W": 1.60,
}

# Definición de combinaciones
combos = [
    {"Combinación": "D / CD",           "Fórmula": "D",         "q (kN/m)": D,           "CD": CD_dict["D"]},
    {"Combinación": "(D + L + S) / CD", "Fórmula": "D + L + S", "q (kN/m)": D + L + S,   "CD": CD_dict["D+L+S"]},
    {"Combinación": "(D + L) / CD",     "Fórmula": "D + L",     "q (kN/m)": D + L,       "CD": CD_dict["D+L"]},
    {"Combinación": "(D + S) / CD",     "Fórmula": "D + S",     "q (kN/m)": D + S,       "CD": CD_dict["D+S"]},
    {"Combinación": "(D + W) / CD",     "Fórmula": "D + W",     "q (kN/m)": D + W,       "CD": CD_dict["D+W"]},
]


col_q10 = "Carga equivalente a 10 años (kN/m)"

# Calcular métricas por combinación
for c in combos:
    c["q (kN/m)"] = float(c["q (kN/m)"])
    c["CD"] = float(c["CD"])
    c[col_q10] = c["q (kN/m)"] / c["CD"]  # equivalente a 10 años

df_q = pd.DataFrame(
    combos,
    columns=["Combinación", "Fórmula", "q (kN/m)", "CD", col_q10]
)

# Identificar combinación gobernante (máxima carga equivalente a 10 años)
idx_gov = pd.to_numeric(df_q[col_q10], errors="coerce").idxmax()
comb_gov = df_q.loc[idx_gov]

# Guardar para cálculos:
q_sinCD = float(comb_gov["q (kN/m)"])
CD_gov = float(comb_gov["CD"])
q_10 = float(comb_gov[col_q10])

st.session_state["q_design_kN_m"] = q_sinCD
st.session_state["CD_flexion"] = CD_gov

# Mostrar resumen
st.info(
    f"**Gobernante (10 años):** {comb_gov['Combinación']} → "
    f"q (sin CD) = {q_sinCD:.2f} kN/m, "
    f"CD = {CD_gov:.2f} ⇒ "
    f"carga eq. 10 años = **{q_10:.2f} kN/m**"
)

# Tabla dentro del expander
with st.expander("Ver detalle de combinaciones y $C_D$"):
    df_q_view = df_q[["Combinación", "CD", "q (kN/m)", col_q10]].copy()
    st.dataframe(
        df_q_view.style.format({
            "CD": "{:.2f}",
            "q (kN/m)": "{:.2f}",
            col_q10: "{:.2f}",
        }),
        use_container_width=True
    )


# ---------------- SECCIÓN ----------------
st.markdown("### Sección transversal")

# 5 columnas: [Tipo] [b/D] [d (si rect)] [W] [I]
c_tipo, c_bD, c_d, c_W, c_I = st.columns([1.2, 0.8, 0.8, 1.0, 1.0])

tipo_seccion = c_tipo.selectbox("Tipo de sección", ["Rectangular", "Circular"], index=0)

if tipo_seccion == "Rectangular":
    # Entradas
    b_mm = c_bD.number_input("Ancho b [mm]",  value=50.0,  step=1.0, min_value=1.0, format="%.0f")
    d_mm = c_d .number_input("Altura d [mm]", value=150.0, step=1.0, min_value=1.0, format="%.0f")

    # Cálculos rectangulares: W = b*d²/6 ; I = b*d³/12
    W_mm3 = b_mm * d_mm**2 / 6.0
    I_mm4 = b_mm * d_mm**3 / 12.0

    # Lecturas (mismo look que los inputs)
    c_W.text_input("Módulo resistente W [mm³]", f"{W_mm3:,.0f}", disabled=True)
    c_I.text_input("Momento de inercia I [mm⁴]", f"{I_mm4:,.0f}", disabled=True)

    # Guardar para el cálculo estructural
    seccion_geom = {"shape": "rect", "b_mm": b_mm, "d_mm": d_mm, "D_mm": None, "W_mm3": W_mm3, "I_mm4": I_mm4}

else:
    # Circular
    D_mm = c_bD.number_input("Diámetro D [mm]", value=150.0, step=1.0, min_value=1.0, format="%.0f")

    # Ocupamos la 3ra columna (c_d) con un espacio para alinear (opcional)
    c_d.markdown("&nbsp;", unsafe_allow_html=True)

    # Cálculos circulares: I = π D⁴ / 64 ; W = I / (D/2) = π D³ / 32
    I_mm4 = np.pi * (D_mm**4) / 64.0
    W_mm3 = np.pi * (D_mm**3) / 32.0

    c_W.text_input("Módulo resistente W [mm³]", f"{W_mm3:,.0f}", disabled=True)
    c_I.text_input("Momento de inercia I [mm⁴]", f"{I_mm4:,.0f}", disabled=True)

    seccion_geom = {"shape": "circ", "b_mm": None, "d_mm": None, "D_mm": D_mm, "W_mm3": W_mm3, "I_mm4": I_mm4}

# ======================================================
# ============ DATOS DE APOYO PARA APLASTAMIENTO ========
# ======================================================
La_mm = La_cm * 10.0  # cm -> mm

# Ancho de apoyo (en dirección perpendicular a la carga)
# Para rectangular: usamos b
# Para circular: aproximamos ancho = D (podés cambiarlo luego)
if seccion_geom["shape"] == "rect":
    b_ap_mm = float(seccion_geom["b_mm"])
else:
    b_ap_mm = float(seccion_geom["D_mm"])

A_ap_mm2 = b_ap_mm * La_mm  # área de apoyo aproximada

st.session_state["La_mm"] = La_mm
st.session_state["b_ap_mm"] = b_ap_mm
st.session_state["A_ap_mm2"] = A_ap_mm2


# ======================================================
# ===================== MATERIAL =======================
# ======================================================

st.subheader("Material (Designación – Clase/Grado)")
st.markdown("""
<style>
h3 {
    margin-top: 1.2rem !important;   /* mantiene espacio arriba */
    margin-bottom: -2rem !important; /* elimina espacio debajo */
}
</style>
""", unsafe_allow_html=True)
# ---- Estilo global: el select ocupa todo el ancho ----
st.markdown("""
<style>
#material-select div[data-baseweb="select"]{
  width:100% !important;
  min-width:520px;
  max-width:none !important;
}
</style>
""", unsafe_allow_html=True)

# ---- Estilos tarjeta derecha (valores) ----
st.markdown("""
<style>
.val-card{background:#eaf1ff;border:1px solid #cfe1ff;border-radius:12px;padding:16px 18px;box-sizing:border-box;}
.val-title{font-weight:700;letter-spacing:.2px;margin-bottom:10px;color:#0f1b2d;}
.val-grid{display:grid;grid-template-columns:repeat(3, 1fr);gap:12px 18px;}
.val-item{background:#f6f9ff;border:1px solid #dde9ff;border-radius:10px;padding:12px;}
.val-k{font-size:12.5px;color:#5b6b84;margin-bottom:2px;}
.val-v{font-size:16px;font-weight:600;color:#0f1b2d;line-height:1.1;}
@media (max-width:1300px){ .val-grid{grid-template-columns:repeat(2,1fr);} }
@media (max-width:900px){  .val-grid{grid-template-columns:1fr;} }
</style>
""", unsafe_allow_html=True)

# ---- Estilos cajita azul izquierda (descripción) ----
st.markdown("""
<style>
.mat-card-left{
  background:#eaf1ff; border:1px solid #cfe1ff; border-radius:12px;
  padding:12px 14px; margin-top:1px; box-sizing:border-box;
}
.mat-desc-left{
  font-size:14.5px; line-height:1.4; color:#1d2a44; text-align:justify;
}
</style>
""", unsafe_allow_html=True)

# ---- columnas: izquierda (selector+desc) / derecha (valores) ----
col_sel, col_vals = st.columns([1.25, 1.75])

# ===== IZQUIERDA: SELECTOR + DESCRIPCIÓN =====
with col_sel:
    st.markdown("""
    <style>
    /* 🔹 Subir el cuadro select para alinearlo con la tarjeta derecha */
    #material-select {
        margin-top: -10px;  /* antes estaba sin margen, ahora sube 10px */
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div id="material-select">', unsafe_allow_html=True)
    opciones = (df_maderas["DESIGNACIÓN"].astype(str) + " – " + df_maderas["CLASIF"].astype(str)).tolist()
    choice = st.selectbox(
        "Madera / Clase",
        opciones,
        index=0,
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # choice tiene forma "DESIGNACIÓN – CLASIF"
    designacion, clasif = choice.split(" – ", 1)
    designacion = designacion.strip()
    clasif = clasif.strip()

    # Filtro por DESIGNACIÓN + CLASIF  → distingue CLASE 1 / 2 / 3
    mask = (
        df_maderas["DESIGNACIÓN"].astype(str).str.strip() == designacion
    ) & (
        df_maderas["CLASIF"].astype(str).str.strip() == clasif
    )

    if not mask.any():
        st.error(f"No se encontró en el catálogo la combinación: {designacion} – {clasif}")
        st.stop()

    fila = df_maderas.loc[mask].iloc[0]

    # Detectar si la madera es laminada (grado) o aserrada (clase)
    clasif_text = str(fila.get("CLASIF", ""))
    es_laminada = "grado" in clasif_text.lower()
    st.session_state["madera_es_laminada"] = es_laminada
    
    # ===== Calcular CM (CIRSOC 601: Tablas 4.3-3 y 5.3-2) =====
    cond_serv = st.session_state.get("cond_servicio", "Estado seco (HRA < 16%)")
    es_humedo = "húmed" in cond_serv.lower() or "humed" in cond_serv.lower()

    if es_humedo:
        if es_laminada:
            # Madera laminada encolada (MLE) — Tabla 5.3-2
            CM_Fb_base  = 0.80
            CM_Fv_base  = 0.87
            CM_Fcp_base = 0.53   # compresión ⟂ fibras (Fc┴)
            CM_Fc_base  = 0.73   # compresión ∥ fibras (Fc)
            CM_Ft_base  = 0.80
            CM_E_base   = 0.83   # E, E0.05 y Emin
        else:
            # Madera aserrada (MA) — Tabla 4.3-3
            CM_Fb_base  = 0.85
            CM_Fv_base  = 0.97
            CM_Fcp_base = 0.67   # compresión ⟂ fibras (Fc┴)
            CM_Fc_base  = 0.80   # compresión ∥ fibras (Fc)
            CM_Ft_base  = 1.00
            CM_E_base   = 0.90   # E, E0.05 y Emin

            # Notas de Tabla 4.3-3 (MA):
            # (1) Para Fb ≤ 7.9 N/mm² ⇒ CM(Fb)=1.0
            # (2) Para Fc ≤ 5.2 N/mm² ⇒ CM(Fc)=1.0
            try:
                Fb_cat = float(fila.get("Fb", np.nan))
                if not np.isnan(Fb_cat) and Fb_cat <= 7.9:
                    CM_Fb_base = 1.00
            except Exception:
                pass

            try:
                Fc_cat = float(fila.get("Fc", np.nan))
                if not np.isnan(Fc_cat) and Fc_cat <= 5.2:
                    CM_Fc_base = 1.00
            except Exception:
                pass
    else:
        CM_Fb_base  = 1.00
        CM_Fv_base  = 1.00
        CM_Fcp_base = 1.00
        CM_Fc_base  = 1.00
        CM_Ft_base  = 1.00
        CM_E_base   = 1.00

    # Guardar para usar en cada verificación
    st.session_state["CM_Fb_base"]  = CM_Fb_base
    st.session_state["CM_Fv_base"]  = CM_Fv_base
    st.session_state["CM_Fcp_base"] = CM_Fcp_base
    st.session_state["CM_Fc_base"]  = CM_Fc_base
    st.session_state["CM_Ft_base"]  = CM_Ft_base
    st.session_state["CM_E_base"]   = CM_E_base

    # Descripción (caja azul, debajo del select)
    desc = ""
    if "DESCRIPCIÓN" in fila.index and pd.notna(fila["DESCRIPCIÓN"]):
        desc = str(fila["DESCRIPCIÓN"]).strip()
    if desc:
        st.markdown(f"""
        <div class="mat-card-left">
          <div class="mat-desc-left">{desc}</div>
        </div>
        """, unsafe_allow_html=True)


# ===== Helpers =====
def get_val(row, *names):
    for n in names:
        if n in row.index and pd.notna(row[n]):
            try:
                return float(row[n])
            except Exception:
                pass
    return float("nan")

def fmt(val, dec=2, suf=""):
    if pd.isna(val):
        return f"—{(' ' + suf) if suf else ''}"
    s = f"{val:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{(' ' + suf) if suf else ''}"

# ===== Valores desde la fila seleccionada =====
Fb   = get_val(fila, "Fb", "fb")
Fv   = get_val(fila, "Fv", "fv")
Fcp  = get_val(fila, "FcP", "Fcp", "fcp")
E    = get_val(fila, "E", "e")                 # SOLO E
E005 = get_val(fila, "E0.05", "E0,05")         # SOLO E0.05
Emin = get_val(fila, "Emin", "EMIN", "E_min")  # SOLO Emin
rho  = get_val(fila, "p0.05", "rho0.05", "ρ0.05", "rho", "densidad")

# ===== DERECHA: TARJETA (solo valores) =====
with col_vals:
    html = f"""
    <div class="val-card">
      <div class="val-title">VALORES DE REFERENCIA</div>
      <div class="val-grid">
        <div class="val-item"><div class="val-k">Fb — Flexión</div><div class="val-v">{fmt(Fb,2,'N/mm²')}</div></div>
        <div class="val-item"><div class="val-k">Fv — Corte paralelo</div><div class="val-v">{fmt(Fv,2,'N/mm²')}</div></div>
        <div class="val-item"><div class="val-k">Fcp — Compresión ⟂ fibras</div><div class="val-v">{fmt(Fcp,2,'N/mm²')}</div></div>
        <div class="val-item"><div class="val-k">E — Módulo de elasticidad</div><div class="val-v">{fmt(E,0,'N/mm²')}</div></div>
        <div class="val-item"><div class="val-k">Emin — Módulo mínimo</div><div class="val-v">{fmt(Emin,0,'N/mm²')}</div></div>
        <div class="val-item"><div class="val-k">ρ — Peso específico</div><div class="val-v">{fmt(rho,0,'kg/m³')}</div></div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    

# ======================================================
# =============== DISEÑO A FLEXIÓN DE LA VIGA ==========
# ======================================================
st.markdown("## Diseño a flexión de la viga")

q_d = st.session_state.get("q_design_kN_m", None)

if q_d is None:
    st.warning("Primero definí la carga de diseño $q_d$ en el bloque de combinaciones.")
    st.stop()

# Módulo resistente de la sección (mm³)
W_mm3 = seccion_geom.get("W_mm3", None)
if W_mm3 is None:
    st.error("No se pudo obtener el módulo resistente W de la sección. Revisá la geometría.")
    st.stop()

if pd.isna(Fb):
    st.error("La resistencia a flexión Fb no está definida para esta madera en el catálogo.")
    st.stop()

# Luz en m
L = float(L_m)

# Usamos el valor absoluto de q_d (por si alguna combinación da negativo)
q_abs = abs(q_d)

# Tipo de apoyo normalizado
tipo = st.session_state.get("tipo_apoyo", "simplemente apoyada").lower()


# ================== FACTORES BÁSICOS ==================
es_laminada = st.session_state.get("madera_es_laminada", False)

# Geometría para factores (mm)
if seccion_geom["shape"] == "rect":
    d_mm = seccion_geom["d_mm"]
    b_mm = seccion_geom["b_mm"]
else:  # circular: usamos d = b = D
    d_mm = seccion_geom["D_mm"]
    b_mm = seccion_geom["D_mm"]

CM      = st.session_state.get("CM_Fb_base", 1.0)     # humedad
CD_flex = st.session_state.get("CD_flexion", 1.0)     # desde combinaciones
Ct      = 1.0
Cr      = st.session_state.get("Cr_flex", 1.0)        # distribución lateral
Cc      = 1.0                                         # viga sin curvatura (por ahora 1)
CF      = 1.0
CV      = 1.0

# ======================================================
# = Le, R_B y F_bE (inestabilidad lateral en flexión) ==
# ======================================================
FbE       = None
RB        = None
Le_m_calc = None

# st.markdown("### Inestabilidad lateral y factor CL")

if seccion_geom["shape"] == "circ":
    # Para sección circular no corresponde verificar pandeo lateral
    st.warning("La sección es **circular** ⇒ no corresponde verificar pandeo lateral ni $F_{bE}$.")
else:
    # Longitud no arriostrada Lu (en mm) ingresada por el usuario
    Lu_mm = Lu_m * 1000.0

    # Relación de esbeltez lateral (Lu/d)
    ratio_db = Lu_mm / d_mm if d_mm > 0 else 1.0

    # Esquema de apoyo
    tipo_apoyo = tipo  # ya lo tenemos en minúsculas

    # ---- Cálculo de Le según tus reglas ----
    if "voladizo" in tipo_apoyo:
        if ratio_db < 7.0:
            Le_mm = 1.33 * Lu_mm
        else:
            Le_mm = 0.90 * Lu_mm + 3.0 * d_mm
    else:
        if ratio_db < 7.0:
            Le_mm = 2.06 * Lu_mm
        else:
            Le_mm = 1.63 * Lu_mm + 3.0 * d_mm

    # Le en metros para mostrar
    Le_m_calc = Le_mm / 1000.0

    # Relación de esbeltez lateral R_B
    RB = (Le_mm * d_mm / (b_mm ** 2)) ** 0.5 if b_mm > 0 else None

    # ---- Cálculo de F_bE ----
    if RB is None or RB == 0:
        FbE = None
        st.error("No se pudo calcular $F_{bE}$ porque $R_B$ no está definido.")
    else:
        # Emin del catálogo (N/mm²): usar el valor ya normalizado (get_val) en vez de acceder directo a la fila
        try:
            Emin_loc = float(Emin)  # Emin ya viene de tu extracción previa con get_val(...)
        except (TypeError, ValueError):
            FbE = None
            st.error("No se pudo calcular $F_{bE}$: $E_{min}$ no está disponible o no es numérico en el catálogo.")
            st.stop()
    
        Ct_E = 1.0
        CM_E = st.session_state.get("CM_E_base", 1.0)
    
        # E'min = Emin * Ct * CM
        E_min_mod = Emin_loc * Ct_E * CM_E
    
        # F_bE = 1.2 * E'min / R_B²
        FbE = 1.2 * E_min_mod / (RB ** 2)

    # Guardar para posible uso posterior
    st.session_state["Le_mm"] = Le_mm
    st.session_state["Le_m"] = Le_m_calc
    st.session_state["RB"] = RB
    st.session_state["FbE"] = FbE

# ================== F*b (sin CL) ==================
# CF / CV según tipo de madera
if es_laminada:
    # Madera laminada → usamos CV, CF = 1
    CV = (600.0 / d_mm)**0.1 + (150.0 / b_mm)**0.05
    CV = min(CV, 1.1)
else:
    # Madera aserrada → usamos CF, CV = 1
    CF = (150.0 / d_mm)**0.2
    CF = min(CF, 1.3)

# F*b = Fb · CD · CM · Ct · CF · CV · Cr
Fb_base = Fb * CD_flex * CM * Ct * CF * CV * Cr

# ================== Cálculo de CL ==================
if FbE is not None and Fb_base > 0:
    R = FbE / Fb_base  # FbE / F*b

    term1 = (1.0 + R) / 1.9
    radicando = term1**2 - R / 0.95

    if radicando > 0:
        CL = term1 - math.sqrt(radicando)
        CL = max(min(CL, 1.0), 0.0)
    else:
        CL = 1.0
else:
    CL = 1.0

st.session_state["CL_flex"] = CL

# Resistencia final a flexión
Fb_mod = Fb_base * CL

# ================== VERIFICACIÓN A FLEXIÓN ==================

# ========= SOLICITACIONES UDL (reutilizable) =========
qNpm = q_abs * 1000.0
udl = solicitaciones_max_udl(L, qNpm, EPa=1.0, Im4=1.0, tipo=tipo)
st.session_state["udl"] = udl

Mpos = udl.get("Mpos_max_kNm") or 0.0
Mneg = udl.get("Mneg_min_kNm") or 0.0
Mu_kNm = max(abs(Mpos), abs(Mneg))
st.session_state["Mu_kNm"] = float(Mu_kNm)

# Momento solicitante en N·mm
Mu_Nmm = Mu_kNm * 1e6  # kN·m → N·mm

# Momento resistente en N·mm (si después querés mostrarlo)
Mr_Nmm = Fb_mod * W_mm3

# Tensión máxima por flexión f_b (N/mm²)
f_b = Mu_Nmm / W_mm3

# Relación demanda/capacidad
ratio = f_b / Fb_mod if Fb_mod > 0 else float("inf")

# Evaluación
verifica = ratio <= 1.0
color = "green" if verifica else "red"
texto = "VERIFICA" if verifica else "NO VERIFICA"

# Cuatro columnas
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Momento solicitante $M_u$", f"{Mu_kNm:.2f} kN·m")

with c2:
    st.metric("Tensión máxima $f_b$", f"{f_b:.2f} N/mm²")

with c3:
    st.metric("Resistencia final $F'_b$", f"{Fb_mod:.2f} N/mm²")

with c4:
    st.markdown(
        f"""
        <div style="
            font-size: 0.8rem;
            color: rgb(49, 51, 63);
            margin-bottom: 0.25rem;
        ">
            Relación demanda/capacidad (f<sub>b</sub> / F′<sub>b</sub>)
        </div>
        <div style="font-size: 1.6rem; font-weight: 600; color:{color};">
            {ratio:.2f} — {texto}
        </div>
        """,
        unsafe_allow_html=True
    )
    
with c5:
    with st.expander("Ver factores aplicados a $F'_b$"):
        st.write(f"**Fb (catálogo):** {Fb:.2f} N/mm²")
        st.write(f"**CD (flexión):** {CD_flex:.2f}")
        st.write(f"**CM (humedad):** {CM:.2f}")
        st.write(f"**Ct (temperatura):** {Ct:.2f}")
        st.write(f"**Cr (distribución lateral):** {Cr:.2f}")
        if es_laminada:
            st.write(f"**CV (volumen, laminada):** {CV:.2f}")
        else:
            st.write(f"**CF (tamaño, aserrada):** {CF:.2f}")
        st.write("Factor de estabilidad lateral y CL")    
        st.write(f"**CL (pandeo lateral):** {CL:.3f}")
        st.write(f"Longitud efectiva: Le = **{Le_m_calc:.2f} m**  \n")
        st.write(f"Relación Lu/d: **{ratio_db:.2f}**  \n")
        st.write(f"Esbeltez lateral: RB = **{RB:.2f}**  \n")
        st.write(f"Módulo de elasticidad para pandeo: E'min (modificado): **{E_min_mod:.2f}** N/mm²  \n")
        st.write(f"Tensión crítica de pandeo: F_bE: **{FbE:.2f}** N/mm²")
        
        
        
        
        
    
# ======================================================
# =============== DISEÑO A CORTE DE LA VIGA ============
# ======================================================
st.markdown("## Diseño a corte (paralelo a las fibras)")

if pd.isna(Fv):
    st.error("La resistencia al corte Fv no está definida para esta madera en el catálogo.")
    st.stop()

q_d = st.session_state.get("q_design_kN_m", None)
if q_d is None:
    st.warning("Primero definí la carga de diseño $q_d$ en el bloque de combinaciones.")
    st.stop()

# Luz y carga (usamos valor absoluto por consistencia con flexión)
L = float(L_m)
q_abs = abs(float(q_d))

# Tipo de apoyo normalizado
tipo = st.session_state.get("tipo_apoyo", "simplemente apoyada").lower()


# Tensión de corte demandada fv (N/mm²)
# ========= TOMAR VU DESDE ANÁLISIS UDL (obligatorio) =========
udl = st.session_state.get("udl", None)
if udl is None or udl.get("Vmax_abs_kN", None) is None:
    st.error(
        "No se encontró $V_u$ del bloque 'ANÁLISIS UDL SEGÚN CONDICIÓN DE APOYO'. "
        "Primero ejecutá ese análisis (flexión) para que se guarde 'udl' en session_state."
    )
    st.stop()

Vu_kN = float(udl["Vmax_abs_kN"])
st.session_state["Vu_kN"] = Vu_kN

Vu_N = Vu_kN * 1000.0  # kN → N

if seccion_geom["shape"] == "rect":
    # CIRSOC 601 (art. 3.2.2): fv = 3V / (2 b d)  (equivalente: 1.5 V / (b d))
    fv_dem = 1.5 * Vu_N / (b_mm * d_mm)
else:
    # Sección circular maciza: τmax = 4V/(3A)
    A_mm2 = np.pi * (seccion_geom["D_mm"] ** 2) / 4.0
    fv_dem = (4.0 / 3.0) * Vu_N / A_mm2

st.session_state["fv_dem"] = float(fv_dem)

# Resistencia de diseño ajustada: F'v = Fv · CD · CM · Ct  (Manual CIRSOC 601)
CD_corte = st.session_state.get("CD_flexion", 1.0)
CM_v     = st.session_state.get("CM_Fv_base", 1.0)
Ct_v     = 1.0

Fv_mod = Fv * CD_corte * CM_v * Ct_v
st.session_state["Fv_mod"] = float(Fv_mod)

# Relación demanda/capacidad
ratio_v = fv_dem / Fv_mod if Fv_mod > 0 else float("inf")
verifica_v = ratio_v <= 1.0
color_v = "green" if verifica_v else "red"
texto_v = "VERIFICA" if verifica_v else "NO VERIFICA"

# Resultados
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Corte solicitante $V_u$", f"{Vu_kN:.2f} kN")

with c2:
    st.metric("Tensión de corte $f_v$", f"{fv_dem:.2f} N/mm²")

with c3:
    st.metric("Resistencia final $F'_v$", f"{Fv_mod:.2f} N/mm²")

with c4:
    st.markdown(
        f'''
        <div style="
            font-size: 0.8rem;
            color: rgb(49, 51, 63);
            margin-bottom: 0.25rem;
        ">
            Relación demanda/capacidad (f<sub>v</sub> / F′<sub>v</sub>)
        </div>
        <div style="font-size: 1.6rem; font-weight: 600; color:{color_v};">
            {ratio_v:.2f} — {texto_v}
        </div>
        ''',
        unsafe_allow_html=True
    )

with c5:
    with st.expander("Ver factores aplicados a $F'_v$"):
        st.write(f"**Fv (catálogo):** {Fv:.2f} N/mm²")
        st.write(f"**CD (corte):** {CD_corte:.2f}")
        st.write(f"**CM (corte):** {CM_v:.2f}")
        st.write(f"**Ct (temperatura):** {Ct_v:.2f}")

# ======================================================
# ====== DISEÑO AL APLASTAMIENTO (Fc⊥) EN APOYOS ========
# ======================================================
st.markdown("## Diseño al aplastamiento (compresión ⟂ a las fibras)")

# 1) Validaciones
if pd.isna(Fcp):
    st.error("La resistencia a compresión perpendicular (Fcp / Fc⊥) no está definida para esta madera en el catálogo.")
    st.stop()

# Tomar Vu desde ANÁLISIS UDL (obligatorio)
udl = st.session_state.get("udl", None)
if udl is None or udl.get("Vmax_abs_kN", None) is None:
    st.error(
        "No se encontró $V_u$ del bloque 'ANÁLISIS UDL SEGÚN CONDICIÓN DE APOYO'. "
        "Primero ejecutá el análisis (flexión) para que se guarde 'udl' en session_state."
    )
    st.stop()

Vu_kN = float(udl["Vmax_abs_kN"])
Vu_N  = Vu_kN * 1000.0  # kN → N
st.session_state["Vu_kN"] = Vu_kN

# Área neta de apoyo (ya la calculás antes)
A_ap_mm2 = st.session_state.get("A_ap_mm2", None)
La_mm    = st.session_state.get("La_mm", None)
b_ap_mm  = st.session_state.get("b_ap_mm", None)

if A_ap_mm2 is None or float(A_ap_mm2) <= 0:
    st.error("No se pudo obtener el área neta de apoyo $A$ (A_ap_mm2). Revisá La y la geometría.")
    st.stop()

# 2) Tensión demandada: f_c⊥ = R / A_contacto (Manual: reacción o Vmax distribuido en área neta)
fcp_dem = Vu_N / float(A_ap_mm2)  # N/mm²
st.session_state["fcp_dem"] = float(fcp_dem)

# 3) Resistencia ajustada: F'c⊥ = Fc⊥ · CD · CM · Ct
CD_cp = st.session_state.get("CD_flexion", 1.0)
CM_cp = st.session_state.get("CM_Fcp_base", 1.0)
Ct_cp = 1.0

Fcp_mod = Fcp * CD_cp * CM_cp * Ct_cp
st.session_state["Fcp_mod"] = float(Fcp_mod)

# 4) Verificación
ratio_cp = fcp_dem / Fcp_mod if Fcp_mod > 0 else float("inf")
verifica_cp = ratio_cp <= 1.0
color_cp = "green" if verifica_cp else "red"
texto_cp = "VERIFICA" if verifica_cp else "NO VERIFICA"

# 5) Resultados (mismo layout que CORTE)
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Reacción/Apoyo $R$ (≈ $V_u$)", f"{Vu_kN:.2f} kN")

with c2:
    st.metric("Tensión $f_{c\\perp}$", f"{fcp_dem:.2f} N/mm²")

with c3:
    st.metric("Resistencia final $F'_{c\\perp}$", f"{Fcp_mod:.2f} N/mm²")

with c4:
    st.markdown(
        f'''
        <div style="
            font-size: 0.8rem;
            color: rgb(49, 51, 63);
            margin-bottom: 0.25rem;
        ">
            Relación demanda/capacidad (f<sub>c⊥</sub> / F′<sub>c⊥</sub>)
        </div>
        <div style="font-size: 1.6rem; font-weight: 600; color:{color_cp};">
            {ratio_cp:.2f} — {texto_cp}
        </div>
        ''',
        unsafe_allow_html=True
    )

with c5:
    with st.expander("Ver factores aplicados a $F'_{c\\perp}$"):
        st.write(f"**Fc⊥ (catálogo):** {Fcp:.2f} N/mm²")
        st.write(f"**CD:** {CD_cp:.2f}")
        st.write(f"**CM (humedad):** {CM_cp:.2f}")
        st.write(f"**Ct (temperatura):** {Ct_cp:.2f}")

        # Datos del contacto dentro del expander (no como métrica)
        if (La_mm is not None) and (b_ap_mm is not None):
            st.write(f"**b (ancho efectivo):** {float(b_ap_mm):.1f} mm")
            st.write(f"**Lₐ (longitud apoyo):** {float(La_mm):.1f} mm")
        st.write(f"**Área neta A:** {float(A_ap_mm2):.0f} mm²")

# ======================================================
# ========== VERIFICACIÓN DE DEFORMACIONES (FLECHAS) ====
# ======================================================

# Tooltip (hover) en el título
st.markdown("""
<style>
.help-tip {
  cursor: help;
  font-weight: 700;
  margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)

tooltip_txt = (
    "Ayuda: para deformaciones se usa E medio (ajustado por CM y Ct). "
    "Contraflecha asumida = 0 mm. "
    "Kcr fijo = 1.50."
)

st.markdown(
    f'## Verificación de deformaciones (flechas) <span class="help-tip" title="{tooltip_txt}"></span>',
    unsafe_allow_html=True
)

# Chequeos mínimos
if E is None or pd.isna(E):
    st.error("No se puede verificar deformaciones: el módulo E no está definido en el catálogo.")
    st.stop()

if "I_mm4" not in locals() or I_mm4 is None or I_mm4 <= 0:
    st.error("No se puede verificar deformaciones: el momento de inercia I no está definido o es inválido.")
    st.stop()

# Recuperar cargas (kN/m)
D  = float(D_kN_m) if "D_kN_m" in locals() else float(st.session_state.get("D_kN_m", 0.0))
Lq = float(L_kN_m) if "L_kN_m" in locals() else float(st.session_state.get("L_kN_m", 0.0))
S  = float(S_kN_m) if "S_kN_m" in locals() else float(st.session_state.get("S_kN_m", 0.0))
W  = float(W_kN_m) if "W_kN_m" in locals() else float(st.session_state.get("W_kN_m", 0.0))

# Luz y apoyo
L_m_loc  = float(L_m)
L_mm_loc = L_m_loc * 1000.0
tipo     = st.session_state.get("tipo_apoyo", "simplemente apoyada").lower()

# E' = E medio * CM * Ct  (para deformaciones: NO usar CD)
CM_E = float(st.session_state.get("CM_E_base", 1.0))
Ct_E = 1.0
E_def = float(E) * CM_E * Ct_E  # N/mm² (SIEMPRE E medio)

def deflex_udl_mm(q_kN_m: float) -> float:
    """
    Flecha máxima (mm) por carga UDL q [kN/m].
    Usa solicitaciones_max_udl(L, qNpm, EPa, Im4, tipo).
    Devuelve el valor (mm) con el signo de q.
    """
    q = float(q_kN_m)
    if abs(q) < 1e-12:
        return 0.0

    sgn = 1.0 if q >= 0 else -1.0

    # Conversión de unidades para tu solver:
    qNpm = abs(q) * 1000.0          # kN/m -> N/m
    EPa  = float(E_def) * 1e6       # N/mm² -> Pa
    Im4  = float(I_mm4) * 1e-12     # mm⁴ -> m⁴

    sol = solicitaciones_max_udl(
        L=L_m_loc,
        qNpm=qNpm,
        EPa=EPa,
        Im4=Im4,
        tipo=tipo
    )

    fmm = float(sol.get("fmax_mm", 0.0))  # mm (abs)
    return sgn * abs(fmm)

# ------------------------------------------------------
# RESULTADOS EN 5 COLUMNAS (misma fisonomía que vibración)
# ------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    # % de sobrecarga viva considerada permanente para flecha final
    p_L_perm = st.number_input(
        "%L permanente",
        min_value=0.0, max_value=100.0, value=30.0, step=5.0, format="%.0f",
        key="p_L_perm"
    ) / 100.0

# Flechas instantáneas por acción (mm)
di_D = deflex_udl_mm(D)
di_L = deflex_udl_mm(Lq)
di_S = deflex_udl_mm(S)
di_W = deflex_udl_mm(W)

# ---- 1) Flecha instantánea (variables): Δi(V) = max[Δ(L)+Δ(S), Δ(W)]
di_sum_LS = di_L + di_S
di_V = di_sum_LS if abs(di_sum_LS) >= abs(di_W) else di_W
crit_inst = "ΣLi (L+S)" if abs(di_sum_LS) >= abs(di_W) else "W"

di_inst_mm = abs(di_V)

# Límites (van al desplegable)
lim_inst = L_mm_loc / 360.0
lim_perm = L_mm_loc / 300.0

ratio_inst = di_inst_mm / lim_inst if lim_inst > 0 else float("inf")
ok_inst = ratio_inst <= 1.0

# ---- 2) Flecha para carga LD: D + p%·L  (esto va en columna 3)
di_LD = di_D + p_L_perm * di_L
di_LD_mm = abs(di_LD)

# ---- 3) Flecha permanente (final) Δperm = Kcr·Δ(LD) + Δ(CD)  (contraflecha=0)
Kcr = 1.50  # fijo
contraflecha_mm = 0.0  # asumida

# CD: (1-p%)·L + S   (W NO se incluye en final)
di_CD = (1.0 - p_L_perm) * di_L + di_S

df_perm = Kcr * di_LD + di_CD - contraflecha_mm
df_perm_mm = abs(df_perm)

ratio_perm = df_perm_mm / lim_perm if lim_perm > 0 else float("inf")
ok_perm = ratio_perm <= 1.0

# Control gobernante
ratio_ctrl = max(ratio_inst, ratio_perm)
ok_total = ok_inst and ok_perm

color_def = "#198754" if ok_total else "#dc3545"
texto_def = "VERIFICA" if ok_total else "NO VERIFICA"

# Detalle (con límites dentro del desplegable)
detalle_md = f"""
**Deformaciones por acción (mm):**
- Δ(D): **{di_D:.2f}**
- Δ(L): **{di_L:.2f}**
- Δ(S): **{di_S:.2f}**
- Δ(W): **{di_W:.2f}**

**Instantánea:** Δi(V)=max[Δ(L)+Δ(S), Δ(W)]
- Δ(L+S): {di_sum_LS:.2f}  |  Δ(W): {di_W:.2f}
- Adoptada: {di_V:.2f} (crítica: {crit_inst})
- Límite: L/360 = {lim_inst:.2f}
- ratio_inst = {ratio_inst:.2f}

**Carga LD (D + %L):**
- %L permanente = {p_L_perm*100:.0f} %
- Δ(LD) = Δ(D) + %·Δ(L) = {di_LD:.2f}

**Permanente:** Δperm = Kcr·Δ(LD) + Δ(CD)  (contraflecha = 0)
- Kcr = {Kcr:.2f}
- Δ(CD) = (1-%)·Δ(L) + Δ(S) = {di_CD:.2f}
- Δperm = {df_perm:.2f}
- Límite: L/300 = {lim_perm:.2f}
- ratio_perm = {ratio_perm:.2f}

**Control:**
- ratio_ctrl = max(ratio_inst, ratio_perm) = **{ratio_ctrl:.2f}**
"""

with c2:
    st.metric("Flecha instantánea", f"{di_inst_mm:.2f} mm")

with c3:
    st.metric("Flecha (D + %L)", f"{di_LD_mm:.2f} mm")

with c4:
    st.markdown(
        f'''
        <div style="
            font-size: 0.8rem;
            color: rgb(49, 51, 63);
            margin-bottom: 0.25rem;
        ">
            Control deformaciones (máx. instantánea y permanente)
        </div>
        <div style="font-size: 1.6rem; font-weight: 600; color:{color_def};">
            {ratio_ctrl:.2f} — {texto_def}
        </div>
        ''',
        unsafe_allow_html=True
    )

with c5:
    with st.expander("Detalles", expanded=False):
        st.markdown(detalle_md)
            
# ======================================================
# ========== VIBRACIONES POR TRÁNSITO HUMANO (3.2.3) ===
# ======================================================

def beta1_primer_modo(tipo_apoyo: str) -> float:
    """
    Parámetro modal β1 (1er modo) para viga Euler-Bernoulli.
    Nota: para 'continua' sin modelar vanos, conviene usar 'simplemente apoyada' (conservador)
          o permitir que el usuario elija una aproximación.
    """
    t = (tipo_apoyo or "").lower()
    if "voladizo" in t:
        return 1.875104068711961  # empotramiento-libre
    if "ambos empotrados" in t or "fixed-fixed" in t:
        return 4.730040744862704  # empotramiento-empotramiento
    if "propped cantilever" in t:
        return 3.926602312047919  # empotramiento-articulación
    # default: simplemente apoyada
    return math.pi


def frecuencia_natural_hz(L_m: float, EPa: float, Im4: float, wNpm_masa: float, tipo_apoyo: str) -> float:
    """
    f0 = (β1^2 / (2π)) * sqrt( EI / (m * L^4) )
    - wNpm_masa: carga lineal equivalente para masa (N/m). Se convierte a m= w/g (kg/m).
    """
    if L_m <= 0 or EPa <= 0 or Im4 <= 0:
        return float("nan")
    g = 9.81
    w_eff = abs(float(wNpm_masa))
    m_kgpm = w_eff / g  # kg/m
    if m_kgpm <= 0:
        return float("nan")

    beta = beta1_primer_modo(tipo_apoyo)
    return (beta**2) / (2.0 * math.pi) * math.sqrt((EPa * Im4) / (m_kgpm * (L_m**4)))


def flecha_puntual_mm_FE(L_m: float, EPa: float, Im4: float, P_N: float, xP_m: float, tipo_apoyo: str,
                         n_el: int = 80) -> float:
    """
    Flecha (mm) por carga puntual P en xP usando un FE 1D de viga E-B (2 dof/nodo: w, theta).
    Devuelve |w| en el nodo más cercano a xP (para centro del vano o extremo libre).
    """
    if L_m <= 0 or EPa <= 0 or Im4 <= 0 or n_el < 2:
        return float("nan")

    n_nodes = n_el + 1
    x = np.linspace(0.0, L_m, n_nodes)
    Le = L_m / n_el
    EI = EPa * Im4

    # Matriz de rigidez elemental (Euler-Bernoulli)
    k = (EI / (Le**3)) * np.array([
        [12,    6*Le,  -12,    6*Le],
        [6*Le,  4*Le**2, -6*Le,  2*Le**2],
        [-12,  -6*Le,   12,   -6*Le],
        [6*Le,  2*Le**2, -6*Le,  4*Le**2],
    ], dtype=float)

    ndof = 2 * n_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    F = np.zeros(ndof, dtype=float)

    # Ensamble global
    for e in range(n_el):
        dofs = [2*e, 2*e+1, 2*(e+1), 2*(e+1)+1]
        K[np.ix_(dofs, dofs)] += k

    # Carga puntual al nodo más cercano
    idxP = int(np.argmin(np.abs(x - float(xP_m))))
    F[2*idxP] += -float(P_N)  # hacia abajo

    # Condiciones de borde
    t = (tipo_apoyo or "").lower()
    fixed_dofs = []

    if "voladizo" in t:
        # empotramiento en x=0
        fixed_dofs += [0, 1]  # w0=0, theta0=0
    elif "ambos empotrados" in t or "fixed-fixed" in t:
        fixed_dofs += [0, 1, 2*(n_nodes-1), 2*(n_nodes-1)+1]
    elif "propped cantilever" in t:
        # empotramiento en x=0 + apoyo simple en x=L (w(L)=0)
        fixed_dofs += [0, 1, 2*(n_nodes-1)]
    else:
        # simplemente apoyada: w(0)=0 y w(L)=0 (rotaciones libres)
        fixed_dofs += [0, 2*(n_nodes-1)]

    fixed_dofs = sorted(set(fixed_dofs))
    free_dofs = np.array([i for i in range(ndof) if i not in fixed_dofs], dtype=int)

    # Resolver
    Kff = K[np.ix_(free_dofs, free_dofs)]
    Ff = F[free_dofs]

    try:
        uf = np.linalg.solve(Kff, Ff)
    except np.linalg.LinAlgError:
        return float("nan")

    u = np.zeros(ndof, dtype=float)
    u[free_dofs] = uf

    w_at_load_m = u[2*idxP]
    return abs(w_at_load_m) * 1000.0  # mm


# ------------------ UI / CÁLCULO ------------------
st.markdown("## Verificación de vibraciones inducidas por el tránsito humano (art. 3.2.3)")

# Chequeos mínimos (reusa los de deformaciones)
if E_def is None or pd.isna(E_def):
    st.error("No se puede verificar vibraciones: E' (E_def) no está definido.")
    st.stop()
if I_mm4 is None or I_mm4 <= 0:
    st.error("No se puede verificar vibraciones: I no está definido o es inválido.")
    st.stop()

# p_L_perm: mismo porcentaje usado en deformaciones (debe existir en tu app)
try:
    p_L_perm_loc = float(p_L_perm)
except Exception:
    p_L_perm_loc = 0.0

# Helper: muestra "Lím: ..." con texto negro y flecha verde/roja
def lim_texto(texto: str, ok: bool):
    flecha = "↑" if ok else "↓"
    c = "#198754" if ok else "#dc3545"  # color solo para la flecha
    st.markdown(
        f"<span style='color:{c}; font-weight:700'>{flecha}</span>"
        f"<span style='color:#000000;'> {texto}</span>",
        unsafe_allow_html=True
    )

# Unidades base
EPa_vib = float(E_def) * 1e6       # N/mm² -> Pa
Im4_vib = float(I_mm4) * 1e-12     # mm⁴ -> m⁴
L_vib   = float(L_m_loc)

# ------------------ INPUT + SALIDA EN 5 COLUMNAS ------------------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    n_vigas_m = st.number_input(
        "Vigas por metro",
        min_value=1.0, max_value=5.0,
        value=1.0, step=1.0,
        format="%.0f",
        key="n_vigas_por_m"
    )

# Límites
lim_f0_hz = 8.0  # recomendación del art. 3.2.3
lim_delta_mm = 7.5 / (L_vib ** 1.2) if L_vib > 0 else float("nan")

# Masa: D + p_L_perm * L  (kN/m)
w_mass_kNpm = abs(float(D) + p_L_perm_loc * float(Lq))
w_mass_Npm  = w_mass_kNpm * 1000.0  # N/m

# Frecuencia (Hz) con D + p_L_perm*L
f0 = frecuencia_natural_hz(L_vib, EPa_vib, Im4_vib, w_mass_Npm, tipo)

# Flecha por 1 kN repartido entre las vigas en 1 m
P_total_N  = 1000.0  # 1 kN
P_por_viga = P_total_N / float(n_vigas_m)

xP = L_vib if "voladizo" in (tipo or "").lower() else L_vib / 2.0
delta_1kN_mm = flecha_puntual_mm_FE(L_vib, EPa_vib, Im4_vib, P_por_viga, xP, tipo)

# Chequeos individuales
ok_f0 = (not math.isnan(f0)) and (f0 > lim_f0_hz)
ok_delta = (not math.isnan(delta_1kN_mm)) and (not math.isnan(lim_delta_mm)) and (delta_1kN_mm <= lim_delta_mm)

# Relación crítica (como en deformaciones)
# - frecuencia: r_f = f_lim / f0  (si f0 baja, r_f sube)
# - flecha:     r_d = Δ / Δ_lim  (si Δ sube, r_d sube)
r_f = (lim_f0_hz / f0) if (not math.isnan(f0) and f0 > 0) else float("inf")
r_d = (delta_1kN_mm / lim_delta_mm) if (not math.isnan(delta_1kN_mm) and lim_delta_mm > 0) else float("inf")
r_max = max(r_f, r_d)

ok_vib = (r_max <= 1.0)

# ---- Col 2: Frecuencia (st.metric, sin límites abajo)
with col2:
    if not math.isnan(f0):
        st.metric("Frecuencia f₀ (D + %L)", f"{f0:.2f} Hz")
    else:
        st.metric("Frecuencia f₀ (D + %L)", "—")

# ---- Col 3: Δi (st.metric, sin límites abajo)
with col3:
    if not math.isnan(delta_1kN_mm):
        st.metric("Δi (1 kN)", f"{delta_1kN_mm:.2f} mm")
    else:
        st.metric("Δi (1 kN)", "—")

# ---- Col 4: “Control …” estilo deformaciones (relación + texto)
with col4:
    color_vib = "#198754" if ok_vib else "#dc3545"
    texto_vib = "VERIFICA" if ok_vib else "NO VERIFICA"

    st.markdown(
        f'''
        <div style="
            font-size: 0.8rem;
            color: rgb(49, 51, 63);
            margin-bottom: 0.25rem;
        ">
            Control vibraciones (f₀ y Δi)
        </div>
        <div style="font-size: 1.6rem; font-weight: 600; color:{color_vib};">
            {r_max:.2f} — {texto_vib}
        </div>
        ''',
        unsafe_allow_html=True
    )

# ---- Col 5: Detalles (incluye límites y relaciones)
with col5:
    with st.expander("Detalles", expanded=False):
        st.write(f"Tipo de apoyo: {tipo}")
        st.write(f"Combinación masa: D + p_L_perm·L = {w_mass_kNpm:.3f} kN/m  (p_L_perm={p_L_perm_loc:.3f})")
        st.write(f"Vigas por metro: {n_vigas_m:.0f}  →  P por viga: {P_por_viga:.1f} N (1kN/{n_vigas_m:.0f})")
        st.write(f"Posición carga 1kN: x = {xP:.3f} m")

        st.markdown("**Límites (art. 3.2.3)**")
        st.write(f"- Frecuencia recomendada: f₀ > {lim_f0_hz:.2f} Hz")
        st.write(f"- Flecha por 1 kN: Δi ≤ {lim_delta_mm:.2f} mm  (L = {L_vib:.3f} m)")

        st.markdown("**Relaciones de verificación**")
        st.write(f"- r_f = f_lim / f₀ = {r_f:.3f}")
        st.write(f"- r_Δ = Δi / Δ_lim = {r_d:.3f}")
        st.write(f"- r_max = max(r_f, r_Δ) = {r_max:.3f}  →  {'VERIFICA' if ok_vib else 'NO VERIFICA'}")