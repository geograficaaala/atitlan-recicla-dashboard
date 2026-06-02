import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="ADALA Dashboard", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_processed" / "atitlan_recicla"

INDICADORES_PATH = DATA_DIR / "institucional_indicadores.csv"
TOTAL_MES_PATH = DATA_DIR / "total_mes.csv"
ZONA_MES_PATH = DATA_DIR / "zona_mes.csv"
MATERIALES_PATH = DATA_DIR / "materiales_resumen_mes.csv"


@st.cache_data
def load_data():
    indicadores = pd.read_csv(INDICADORES_PATH)
    total_mes = pd.read_csv(TOTAL_MES_PATH)
    zona_mes = pd.read_csv(ZONA_MES_PATH)
    materiales = pd.read_csv(MATERIALES_PATH)

    indicadores["mes_num"] = pd.to_numeric(indicadores["mes_num"], errors="coerce")
    indicadores["anio"] = pd.to_numeric(indicadores["anio"], errors="coerce")

    total_mes["mes_num"] = pd.to_numeric(total_mes["mes_num"], errors="coerce")
    total_mes["anio"] = pd.to_numeric(total_mes["anio"], errors="coerce")

    zona_mes["mes_num"] = pd.to_numeric(zona_mes["mes_num"], errors="coerce")
    zona_mes["anio"] = pd.to_numeric(zona_mes["anio"], errors="coerce")

    materiales["mes_num"] = pd.to_numeric(materiales["mes_num"], errors="coerce")
    materiales["anio"] = pd.to_numeric(materiales["anio"], errors="coerce")

    return indicadores, total_mes, zona_mes, materiales


def fmt_number(value, unidad=""):
    if pd.isna(value):
        return "—"
    if unidad == "proporción":
        return f"{value:.1%}"
    if unidad in {"GTQ", "GTQ/día"}:
        return f"Q {value:,.2f}"
    return f"{value:,.2f} {unidad}".strip()


indicadores, total_mes, zona_mes, materiales = load_data()

st.title("Dashboard institucional ADALA")
st.subheader("Piloto: Atitlán Recicla")

if indicadores.empty:
    st.error("No hay datos procesados para mostrar.")
    st.stop()

programa_nombre = indicadores["programa_nombre"].dropna().iloc[0]
st.caption(f"Programa cargado: {programa_nombre}")

latest_row = (
    indicadores.sort_values(["anio", "mes_num"])
    .dropna(subset=["mes_num"])
    .tail(1)
)

if latest_row.empty:
    st.error("No se pudo identificar el último período.")
    st.stop()

latest_anio = int(latest_row.iloc[0]["anio"])
latest_mes_num = int(latest_row.iloc[0]["mes_num"])
latest_mes = latest_row.iloc[0]["mes"]

st.markdown(f"### Último período disponible: {latest_mes} {latest_anio}")

latest_indicadores = indicadores[
    (indicadores["anio"] == latest_anio) &
    (indicadores["mes_num"] == latest_mes_num)
].copy()

kpi_ids = [
    "materiales_generales",
    "pet",
    "vidrio",
    "ingreso_bruto_total",
]

kpi_cols = st.columns(len(kpi_ids))

for col_ui, indicador_id in zip(kpi_cols, kpi_ids):
    row = latest_indicadores[latest_indicadores["indicador_id"] == indicador_id]
    if row.empty:
        col_ui.metric(indicador_id, "—")
        continue

    row = row.iloc[0]
    valor = row["valor"]
    meta = row["meta_mensual"]
    unidad = row["unidad"]

    delta = None
    if pd.notna(meta):
        if unidad == "proporción":
            delta = f"{(valor - meta):.1%}"
        else:
            delta = f"{valor - meta:,.2f}"

    col_ui.metric(
        label=row["indicador_nombre"],
        value=fmt_number(valor, unidad),
        delta=delta,
    )

st.markdown("### Evolución mensual")

indicador_opciones = indicadores[["indicador_id", "indicador_nombre"]].drop_duplicates()
indicador_map = dict(zip(indicador_opciones["indicador_nombre"], indicador_opciones["indicador_id"]))

indicador_nombre_sel = st.selectbox(
    "Selecciona un indicador",
    options=sorted(indicador_map.keys())
)
indicador_id_sel = indicador_map[indicador_nombre_sel]

serie = indicadores[indicadores["indicador_id"] == indicador_id_sel].copy()
serie = serie.sort_values(["anio", "mes_num"])
serie["periodo"] = serie["mes"] + " " + serie["anio"].astype(int).astype(str)
serie_chart = serie[["periodo", "valor", "meta_mensual"]].set_index("periodo")

st.line_chart(serie_chart)

st.markdown("### Resumen mensual consolidado")
tabla_total = total_mes.sort_values(["anio", "mes_num"]).copy()
st.dataframe(tabla_total, use_container_width=True)

st.markdown("### Resumen por zona")
zona_sel = st.selectbox(
    "Filtrar zona",
    options=["Todas"] + sorted(zona_mes["zona"].dropna().unique().tolist())
)

tabla_zona = zona_mes.copy()
if zona_sel != "Todas":
    tabla_zona = tabla_zona[tabla_zona["zona"] == zona_sel]

tabla_zona = tabla_zona.sort_values(["anio", "mes_num", "zona"])
st.dataframe(tabla_zona, use_container_width=True)

st.markdown("### Materiales por mes")
materiales_mes = (
    materiales.groupby(["anio", "mes_num", "mes", "material"], dropna=False)["cantidad"]
    .sum()
    .reset_index()
    .sort_values(["anio", "mes_num", "material"])
)

material_sel = st.selectbox(
    "Filtrar material",
    options=["Todos"] + sorted(materiales_mes["material"].dropna().unique().tolist())
)

tabla_materiales = materiales_mes.copy()
if material_sel != "Todos":
    tabla_materiales = tabla_materiales[tabla_materiales["material"] == material_sel]

st.dataframe(tabla_materiales, use_container_width=True)
