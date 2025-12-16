import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

engine = create_engine('sqlite:///./test.db')
df = pd.read_sql("SELECT * FROM documentos", engine)

# Si tus datos generales por equipo están en la tabla, asegúrate de agregarlos en la importación:
for col in ["Grupo", "Cema", "Comeq", "Estado", "Ubicación", "SERVICIO", "SECRETARIA"]:
    if col not in df.columns:
        df[col] = None  # Evita errores si faltan por ahora

# Cálculo de estado
df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"], errors='coerce')
df["estado"] = df["fecha_vencimiento"].apply(
    lambda x: "Al día" if pd.isna(x) or (x.date() - datetime.now().date()).days > 3
    else ("Próximo" if 0 <= (x.date() - datetime.now().date()).days <= 3 else "Vencido")
)

st.title("Control Documental Local")

# FILTROS avanzados
cols_filtro = ["Grupo", "Cema", "Comeq", "Estado", "Ubicación", "SERVICIO", "SECRETARIA", "estado"]
filtros = {}
with st.expander("Filtros avanzados"):
    cols = st.columns(len(cols_filtro))
    for i, field in enumerate(cols_filtro):
        options = ["Todos"] + sorted(df[field].dropna().astype(str).unique())
        choice = cols[i].selectbox(f"Filtrar por {field}", options)
        filtros[field] = None if choice == "Todos" else choice

df_filtrado = df.copy()
for campo, valor in filtros.items():
    if valor not in (None, "Todos"):
        df_filtrado = df_filtrado[df_filtrado[campo].astype(str) == valor]

st.write(f"Total documentos filtrados: {len(df_filtrado)}")
st.dataframe(df_filtrado)

if st.button("Exportar filtrado a Excel"):
    df_filtrado.to_excel("documentos_filtrados.xlsx", index=False)
    st.success("¡Datos exportados!")




