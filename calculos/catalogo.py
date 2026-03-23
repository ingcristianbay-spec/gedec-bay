"""
calculos/catalogo.py
====================
Lectura y normalización del catálogo de maderas CIRSOC 601.

No depende de Streamlit.
"""

import pandas as pd
from io import BytesIO


def load_catalog(xlsx_path_or_buf) -> pd.DataFrame:
    """
    Lee el catálogo de maderas desde un archivo Excel.

    Acepta:
    - Ruta como string (ej: "datos/cirsoc601-maderas.xlsx")
    - Buffer (archivo subido con st.file_uploader)

    Retorna pd.DataFrame normalizado.
    """
    # Leer contenido una vez
    if hasattr(xlsx_path_or_buf, "getvalue"):
        contenido = xlsx_path_or_buf.getvalue()
    elif hasattr(xlsx_path_or_buf, "read"):
        try:
            xlsx_path_or_buf.seek(0)
        except Exception:
            pass
        contenido = xlsx_path_or_buf.read()
    else:
        contenido = None

    def _leer(**kwargs):
        if contenido is not None:
            return pd.read_excel(BytesIO(contenido), **kwargs)
        return pd.read_excel(xlsx_path_or_buf, **kwargs)

    # Buscar fila de encabezados
    raw     = _leer(header=None, dtype=str)
    hdr_row = None

    for i in range(min(40, len(raw))):
        ups = [str(x).strip().upper() for x in raw.iloc[i].tolist()]
        if "DESIGNACIÓN" in ups or "DESIGNACION" in ups:
            hdr_row = i
            break

    if hdr_row is None:
        df = _leer(header=0, decimal=",")
    else:
        df = _leer(header=hdr_row, decimal=",")

    df.columns = [str(c).strip() for c in df.columns]

    # Saltear fila de unidades si existe
    if len(df) > 0:
        primera = [str(v).strip().lower() for v in df.iloc[0].tolist()]
        if any(v in {"n/mm2", "n/mm²", "kg/m3"} for v in primera):
            df = df.iloc[1:].reset_index(drop=True)

    return _normalizar(df)


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas y convierte a numérico."""
    alias = {
        "DESIGNACION": "DESIGNACIÓN",
        "CLASE": "CLASIF",
        "GRADO": "CLASIF",
        "RHO": "p0.05",
        "RH0.05": "p0.05",
        "P0.05": "p0.05",
        "DESCRIPCION": "DESCRIPCIÓN",
    }

    nuevas = []
    for c in df.columns:
        ku = str(c).strip().upper()
        nuevas.append(alias.get(ku, str(c).strip().replace(",", ".")))
    df.columns = nuevas

    quiero = ["DESIGNACIÓN", "CLASIF", "DESCRIPCIÓN",
              "Fb", "Ft", "Fv", "FcP", "Fc", "E", "E0.05", "Emin", "p0.05"]
    presentes = [c for c in quiero if c in df.columns]
    df = df[presentes].copy()

    if "DESIGNACIÓN" in df.columns:
        df = df[df["DESIGNACIÓN"].astype(str).str.strip().ne("")].copy()

    texto = {"DESIGNACIÓN", "CLASIF", "DESCRIPCIÓN"}
    for c in [col for col in df.columns if col not in texto]:
        df[c] = (
            df[c].astype(str)
                 .str.replace("\u2212", "-", regex=False)
                 .str.replace(",", ".", regex=False)
        )
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.reset_index(drop=True)


def get_valor(fila: pd.Series, *nombres) -> float:
    """
    Extrae el primer valor numérico disponible entre los nombres dados.
    Retorna float('nan') si no encuentra ninguno.
    """
    for n in nombres:
        if n in fila.index and pd.notna(fila[n]):
            try:
                return float(fila[n])
            except Exception:
                pass
    return float("nan")
