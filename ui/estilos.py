"""
ui/estilos.py
=============
Todo el CSS de la aplicación en un solo lugar.

Uso en app.py:
    from ui.estilos import aplicar_estilos
    aplicar_estilos()
"""

import streamlit as st


def aplicar_estilos():
    """Inyecta el CSS global de la aplicación."""
    st.markdown("""
<style>
/* ========== Layout general ========== */
section.main > div.block-container {
    padding-top: 0.2rem;
    padding-bottom: 1rem;
}

@media (min-width: 1400px) {
    section.main > div.block-container { max-width: 1400px; }
}
@media (min-width: 992px) and (max-width: 1399px) {
    section.main > div.block-container { max-width: 1100px; }
}
@media (max-width: 991px) {
    section.main > div.block-container {
        max-width: 95vw;
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

/* ========== Espaciado ========== */
div[data-testid="stVerticalBlock"] > div {
    padding-top: 0.50rem !important;
    padding-bottom: 0.10rem !important;
}
div[data-testid="stWidgetLabel"] {
    margin-top: 0.12rem !important;
    margin-bottom: 0.12rem !important;
}
div[data-testid="stWidgetLabel"] p {
    margin: 0 !important;
    line-height: 1.15 !important;
}

/* ========== Títulos ========== */
h1 { font-size: 2.2rem !important; margin: 0.35rem 0 0.25rem 0 !important; line-height: 1.10 !important; }
h2 { font-size: 1.5rem !important; margin: 0.45rem 0 0.25rem 0 !important; line-height: 1.12 !important; }
h3 { font-size: 1.30rem !important; margin: 0.30rem 0 0.18rem 0 !important; line-height: 1.15 !important; }

/* ========== Encabezado institucional ========== */
.st-key-header_card {
    background-color: #f1f3f5;
    border: 1px solid #d9d9d9;
    border-radius: 14px;
    padding: 18px 20px 10px 20px;
    margin-bottom: 12px;
}
.st-key-header_card hr {
    height: 1px;
    background-color: #c8c8c8;
    border: none;
    margin-top: 10px;
    margin-bottom: 0px;
}

/* ========== Alerts ========== */
div[data-testid="stAlert"] { margin: 0.25rem 0 0.35rem 0 !important; }

/* ========== Texto ========== */
html, body { font-size: 15px; }

/* ========== Métricas ========== */
div[data-testid="stMetricValue"] { font-size: 1.6rem !important; line-height: 1.1 !important; }
div[data-testid="stMetricLabel"] { font-size: 0.95rem !important; }

/* ========== Inputs deshabilitados ========== */
input:disabled {
    -webkit-text-fill-color: #111 !important;
    color: #111 !important;
    opacity: 1 !important;
}
div[data-testid="stTextInput"] label p {
    color: #111 !important;
    opacity: 1 !important;
}

/* ========== Tooltip ========== */
.help-tip {
    cursor: help;
    font-weight: 700;
    margin-left: 6px;
}
</style>
""", unsafe_allow_html=True)


def card_verificacion(titulo: str) -> str:
    """
    HTML para la tarjeta de título de cada verificación.
    Uso: st.markdown(card_verificacion("DISEÑO A FLEXIÓN"), unsafe_allow_html=True)
    """
    return f"""
    <div style="
        padding:10px 10px;
        border-radius:10px;
        border:1px solid rgba(0,0,0,0.12);
        background:rgba(0,0,0,0.02);
        font-weight:800;
        text-align:center;">
        {titulo}
    </div>
    """


def resultado_ratio(label: str, ratio: float, verifica: bool) -> str:
    """
    HTML para mostrar relación demanda/capacidad con color verde/rojo.
    """
    color  = "#198754" if verifica else "#dc3545"
    texto  = "VERIFICA" if verifica else "NO VERIFICA"
    return f"""
    <div style="font-size: 0.8rem; color: rgb(49,51,63); margin-bottom: 0.25rem;">{label}</div>
    <div style="font-size: 1.6rem; font-weight: 600; color:{color};">
        {ratio:.2f} — {texto}
    </div>
    """
