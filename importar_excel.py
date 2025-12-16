import pandas as pd
import numpy as np
from sqlalchemy import create_engine

EXCEL_PATH = r"C:\Users\misanchez\Documents\CONTROL DOCUMENTAL\Control Documental Actualizado Noviembre 2024.xlsx"
DB_PATH = "sqlite:///./test.db"

df_raw = pd.read_excel(EXCEL_PATH, header=None)
df_raw.columns = df_raw.iloc[0]
df = df_raw[1:].reset_index(drop=True)
df = df.loc[:, ~df.columns.isnull()]
df = df.loc[:, df.columns != 'nan']
df = df.loc[:, df.columns != np.nan]
df = df.loc[:, ~df.columns.duplicated()]

CAMPOS_GENERALES = ['Grupo', 'Cema', 'Comeq', 'Estado']

# ------------ Nuevo bloque inteligente de pivote ---------------
TIPOS_DOCUMENTO = [
    '030. SOAT (Seguro Obligatorio Contra Accidentes de Transito)',
    '035. Todo Riesgo',
    '037. Revision Tecnomecanica y de Gases',
    '040. Responsabilidad Civil Contractual',
    '045. Responsabilidad Civil Extracontractual',
    '047. Tarjeta de Operación',
    '050. Extracto de Contrato',
    '055. Revision Preventiva '
]
SUBCAMPOS = ['Fecha Expedicion', 'Vigencia Desde', 'Vigencia Hasta']

registros = []
for idx, row in df.iterrows():
    generales = {campo: row.get(campo, "") for campo in CAMPOS_GENERALES}
    for tipo in TIPOS_DOCUMENTO:
        for i, subcampo in enumerate(SUBCAMPOS):
            columna = tipo
            # Buscar desplazamiento de filas, ya que tras los títulos tienes "Fecha Expedicion", "Vigencia Desde", etc.
            try:
                # La primera fila es el título del documento (omitimos)
                valor = row.get(tipo, None)
                # El siguiente registro (idx+1) tiene los subcampos, así que iteramos por fila, no por subcolumna
                if pd.notna(valor) and str(valor).strip() == subcampo:
                    valor_sub = row.get(tipo, None)
                else:
                    valor_sub = row.get(tipo, None)

                # Aquí el código debe ajustarse según cómo se organizan esos subcampos
                # En tu archivo, seguro tienes: Título de columna, luego las tres subetiquetas, luego los valores
                # Si los subcampos son columnas, deberías renombrar así:
                col_name = f"{tipo} {subcampo}"
                valor = row.get(col_name, None)
                if pd.notna(valor) and str(valor).strip() != "":
                    reg = {
                        "equipo_id": idx + 1,
                        "tipo_documento": tipo,
                        "subcampo": subcampo,
                        "valor": valor,
                    }
                    reg.update(generales)
                    registros.append(reg)
            except Exception as ex:
                continue

if not registros:
    # Alternativa: detectar si los subcampos vienen en columnas tipo "xxxxxx Fecha Expedicion"
    columnas_full = df.columns.tolist()
    registros = []
    for idx, row in df.iterrows():
        generales = {campo: row.get(campo, "") for campo in CAMPOS_GENERALES}
        for tipo in TIPOS_DOCUMENTO:
            d = {}
            for subcampo in SUBCAMPOS:
                col_full = f"{tipo} {subcampo}"
                valor = row.get(col_full, None)
                d[subcampo] = valor
            if any((d[s] is not None and str(d[s]).strip() != '') for s in SUBCAMPOS):
                reg = {
                    "equipo_id": idx + 1,
                    "tipo_documento": tipo,
                    "fecha_expedicion": d.get("Fecha Expedicion", None),
                    "vigencia_desde": d.get("Vigencia Desde", None),
                    "vigencia_hasta": d.get("Vigencia Hasta", None),
                }
                reg.update(generales)
                registros.append(reg)

df_final = pd.DataFrame(registros)
print("Estructura tabular/nueva:", df_final.head(10))

# SQLite
try:
    engine = create_engine(DB_PATH)
    df_final.to_sql("documentos", engine, if_exists="replace", index=False)
    print("¡Documentos correctos importados a la base!")
except Exception as e:
    raise RuntimeError(f"Error exportando a base SQLite: {e}")

# Exporta a excel listo para gestión/alertas
df_final.to_excel("Control-Documentos-Tabular-Normalizado.xlsx", index=False)
print("¡Exportación Excel lista como Control-Documentos-Tabular-Normalizado.xlsx!")







