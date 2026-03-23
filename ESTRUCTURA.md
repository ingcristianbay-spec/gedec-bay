# Estructura del Proyecto CIRSOC 601

## ¿Cómo está organizado?

```
cirsoc601/
│
├── app.py                      ← Archivo principal (el que arranca Streamlit)
│
├── calculos/                   ← SOLO matemática / ingeniería (sin Streamlit)
│   ├── __init__.py             ← Le dice a Python que esta carpeta es un módulo
│   ├── secciones.py            ← Propiedades geométricas (W, I, A)
│   ├── combinaciones_carga.py  ← Combinaciones CIRSOC y CD
│   ├── factores_mod.py         ← CM, Ct, CF, CV, Cr, CL, etc.
│   ├── solicitaciones.py       ← V, M, flechas según condición de apoyo
│   ├── flexion.py              ← Verificación a flexión (art. 3.2.1)
│   ├── corte.py                ← Verificación a corte (art. 3.2.2)
│   ├── aplastamiento.py        ← Verificación aplastamiento Fc⊥
│   ├── deformaciones.py        ← Verificación flechas (art. 3.2.2)
│   └── vibraciones.py          ← Verificación vibraciones (art. 3.2.3)
│
├── ui/                         ← SOLO pantallas Streamlit (sin cálculos)
│   ├── __init__.py
│   ├── estilos.py              ← Todo el CSS
│   ├── encabezado.py           ← Logo + título + info institucional
│   └── vigas/
│       ├── __init__.py
│       ├── entrada_geometria.py    ← Inputs de geometría y apoyo
│       ├── entrada_cargas.py       ← Inputs D, L, S, W
│       ├── entrada_seccion.py      ← Selector sección + material
│       └── resultados_viga.py      ← Muestra resultados de todas las verificaciones
│
├── datos/
│   └── cirsoc 601-maderas.xlsx ← Catálogo de maderas (se copia acá)
│
└── ia/
    ├── __init__.py
    └── openai_client.py        ← Llamadas a la API de OpenAI
```

## La regla de oro

**`calculos/`** → No sabe que existe Streamlit. Recibe números, devuelve números.

**`ui/`** → No hace cálculos. Llama a `calculos/`, muestra resultados.

**`app.py`** → Orquesta todo. Es el director, no el actor.

## ¿Por qué así?

Si mañana querés agregar **columnas**, creás:
- `calculos/columnas.py`  ← las ecuaciones
- `ui/columnas/`          ← la pantalla

Sin tocar nada de vigas.

Si mañana querés cambiar el CSS, solo tocás `ui/estilos.py`.

Si mañana querés testear que `flexion.py` da bien los resultados, podés hacerlo
sin levantar Streamlit.
