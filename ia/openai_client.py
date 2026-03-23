"""
ia/openai_client.py
===================
Integración con la API de OpenAI para explicaciones con IA.

Centraliza toda la lógica de llamadas a OpenAI en un solo lugar.
No depende de Streamlit (solo usa os, json, requests).
"""

import os
import json
import time
import requests


def _extract_text(resp_json: dict) -> str:
    """Extrae el texto de la respuesta de la API de OpenAI."""
    output_text = resp_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts = []
    for item in resp_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    return "\n".join(parts).strip()


def llamar_openai(prompt: str, api_key: str, modelo: str = "gpt-4o",
                  max_intentos: int = 3) -> str:
    """
    Llama a la API de OpenAI y retorna el texto de respuesta.

    Parámetros
    ----------
    prompt      : texto del prompt
    api_key     : clave de API de OpenAI
    modelo      : modelo a usar (default gpt-4o)
    max_intentos: reintentos ante error 429 (rate limit)

    Retorna
    -------
    str con la respuesta

    Raises
    ------
    RuntimeError si no se puede obtener respuesta
    """
    if not api_key:
        raise RuntimeError("Falta OPENAI_API_KEY.")

    payload = {"model": modelo, "input": prompt, "store": False}
    data    = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url     = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    espera = 2
    for intento in range(max_intentos):
        try:
            r = requests.post(url, headers=headers, data=data, timeout=60)

            if r.status_code == 429:
                if intento == max_intentos - 1:
                    raise RuntimeError("Límite de consultas alcanzado. Esperá y reintentá.")
                time.sleep(espera)
                espera *= 2
                continue

            r.raise_for_status()
            return _extract_text(r.json())

        except requests.exceptions.Timeout:
            if intento == max_intentos - 1:
                raise RuntimeError("La consulta a la IA tardó demasiado.")
            time.sleep(espera)
            espera *= 2

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error al consultar OpenAI: {e}")

    raise RuntimeError("No se pudo obtener respuesta de la IA.")


def get_api_key(secrets=None) -> str:
    """
    Obtiene la API key de Streamlit secrets o de la variable de entorno.

    Uso en Streamlit:
        api_key = get_api_key(st.secrets)
    """
    if secrets is not None:
        key = secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    return os.environ.get("OPENAI_API_KEY", "")


def explicar_combinaciones(df_q, comb_gov, D, L, S, W, api_key: str) -> str:
    """
    Genera una explicación técnica de las combinaciones de carga con IA.
    """
    tabla_txt = df_q[["Combinación", "Fórmula", "q (kN/m)", "CD", "q_10 (kN/m)"]].to_csv(index=False)

    prompt = f"""
Sos un asistente técnico de ingeniería estructural especializado en diseño de vigas de madera según CIRSOC 601.

Tu tarea es explicar las combinaciones de carga y el rol del factor CD de forma breve, clara, técnica y práctica.
Usá SOLO los datos provistos. Respondé en español.
No uses LaTeX. Escribí las fórmulas en texto simple (ej: q10 = q / CD).
No repitas innecesariamente toda la tabla. Evitá lenguaje pedagógico genérico.
Escribí como una nota técnica breve.

Datos de entrada (kN/m):
D = {D:.3f}, L = {L:.3f}, S = {S:.3f}, W = {W:.3f}

Tabla de combinaciones (CSV):
{tabla_txt}

Combinación gobernante:
- Combinación: {comb_gov['Combinación']}
- Fórmula: {comb_gov['Fórmula']}
- q = {comb_gov['q (kN/m)']:.3f} kN/m
- CD = {comb_gov['CD']:.2f}
- q10 = {comb_gov['q_10 (kN/m)']:.3f} kN/m

Redactá la respuesta en exactamente 2 párrafos (sin títulos, sin viñetas, máximo 160 palabras):
Párrafo 1: qué significa dividir por CD y cómo interpretar q10.
Párrafo 2: por qué gobierna esa combinación, comparándola brevemente con las demás.
""".strip()

    return llamar_openai(prompt, api_key)
