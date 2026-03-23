"""
ui/encabezado.py
================
Encabezado institucional de la aplicación.

Uso en app.py:
    from ui.encabezado import mostrar_encabezado
    mostrar_encabezado()
"""

import streamlit as st


def mostrar_encabezado(
    logo_path: str = "utn_logo.png",
    version: str = "v1.0.0",
    fecha: str = "20/03/2026",
):
    """
    Muestra el encabezado institucional con logo, título e info del grupo.
    """
    with st.container(key="header_card"):
        col_logo, col_titulo, col_info = st.columns(
            [0.9, 4.6, 1.8], vertical_alignment="center"
        )

        with col_logo:
            try:
                st.image(logo_path, width=70)
            except Exception:
                st.markdown("🪵")

        with col_titulo:
            st.markdown(
                """
                <div style="text-align:center;">
                    <h1 style="margin:0; font-size:2.15rem; line-height:1.15;">
                        Diseño de Vigas de Madera (CIRSOC 601)
                    </h1>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_info:
            st.markdown(
                f"""
                <div style="font-size:15px; line-height:1.7;">
                    <b>GEDEC</b> Grupo de Estudio de Estructuras Civiles<br>
                    <b>FRSR-UTN</b> Regional San Rafael<br>
                    <b>Desarrollador:</b> Dr. Ing. Cristian Bay<br>
                    <b>Versión:</b> {version}<br>
                    <b>Actualización:</b> {fecha}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr>", unsafe_allow_html=True)

    
