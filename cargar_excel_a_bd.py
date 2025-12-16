import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
from models import Equipo, Documento

EXCEL_PATH = r"C:\Users\misanchez\Documents\CONTROL DOCUMENTAL\Control Documental Actualizado Noviembre 2024 reporte.xlsx"

# Mapeo: tipo documento -> columnas desde / hasta en el Excel
COLUMNAS_VIGENCIAS = {
    '030. SOAT (Seguro Obligatorio Contra Accidentes de Transito)': {
        'desde': '030. SOAT (Seguro Obligatorio Contra Accidentes de Transito).1',
        'hasta': '030. SOAT (Seguro Obligatorio Contra Accidentes de Transito).2',
    },
    '035. Todo Riesgo': {
        'desde': '035. Todo Riesgo.1',
        'hasta': '035. Todo Riesgo.2',
    },
    '037. Revision Tecnomecanica y de Gases': {
        'desde': '037. Revision Tecnomecanica y de Gases.1',
        'hasta': '037. Revision Tecnomecanica y de Gases.2',
    },
    '040. Responsabilidad Civil Contractual': {
        'desde': '040. Responsabilidad Civil Contractual.1',
        'hasta': '040. Responsabilidad Civil Contractual.2',
    },
    '045. Responsabilidad Civil Extracontractual': {
        'desde': '045. Responsabilidad Civil Extracontractual.1',
        'hasta': '045. Responsabilidad Civil Extracontractual.2',
    },
    '047. Tarjeta de Operación': {
        'desde': '047. Tarjeta de Operación.1',
        'hasta': '047. Tarjeta de Operación.2',
    },
    '050. Extracto de Contrato': {
        'desde': '050. Extracto de Contrato.1',
        'hasta': '050. Extracto de Contrato.2',
    },
    '055. Revision Preventiva ': {
        'desde': '055. Revision Preventiva .1',
        'hasta': '055. Revision Preventiva .2',
    },
}

def excel_a_date(valor):
    """Convierte '2025-12-20 00:00:00' o NaN a date."""
    if pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None

def cargar():
    df = pd.read_excel(EXCEL_PATH)

    db: Session = SessionLocal()

    try:
        for _, row in df.iterrows():
            grupo = row.get('Grupo')
            cema = row.get('Cema')
            comeq = row.get('Comeq')

            # Crear o reutilizar Equipo
            equipo = db.query(Equipo).filter_by(grupo=grupo, cema=cema, comeq=comeq).first()
            if not equipo:
                equipo = Equipo(
                    grupo=grupo,
                    cema=cema,
                    comeq=comeq,
                    estado=row.get('Estado')
                )
                db.add(equipo)
                db.flush()  # obtener equipo.id

            # Crear un Documento por cada tipo, con vigencia_desde / vigencia_hasta
            for tipo_doc, cols in COLUMNAS_VIGENCIAS.items():
                valor_desde = row.get(cols['desde'])
                valor_hasta = row.get(cols['hasta'])

                fecha_desde = excel_a_date(valor_desde)
                fecha_hasta = excel_a_date(valor_hasta)

                # Si al menos una de las fechas existe, se crea el registro
                if fecha_desde or fecha_hasta:
                    doc = Documento(
                        equipo_id=equipo.id,
                        tipo_documento=tipo_doc,
                        vigencia_desde=fecha_desde,
                        vigencia_hasta=fecha_hasta,
                    )
                    db.add(doc)

        db.commit()
        print("Datos cargados en test.db")
    finally:
        db.close()

if __name__ == "__main__":
    cargar()

