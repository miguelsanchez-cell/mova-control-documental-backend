import pandas as pd

EXCEL_PATH = r"C:\Users\misanchez\Documents\CONTROL DOCUMENTAL\Control Documental Actualizado Noviembre 2024 reporte.xlsx"

df = pd.read_excel(EXCEL_PATH)
print(df.columns.tolist())
