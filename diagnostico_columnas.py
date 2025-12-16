import pandas as pd

EXCEL_PATH = r"C:\Users\misanchez\Documents\CONTROL DOCUMENTAL\Control Documental Actualizado Noviembre 2024.xlsx"

# Lee sin encabezado y muestra las primeras 20 filas crudas
df_preview = pd.read_excel(EXCEL_PATH, header=None)
print(df_preview.head(20).to_string())
