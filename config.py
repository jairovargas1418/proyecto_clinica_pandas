"""Configuración central del proyecto."""
import os
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SALIDAS_DIR = BASE_DIR / "salidas"

# Fecha de corte de los datos: así los resultados son reproducibles (no dependen de "hoy").
FECHA_REF = pd.Timestamp("2025-12-31")

ESTADOS_VALIDOS = ["PROGRAMADA", "ATENDIDA", "CANCELADA", "INASISTENTE"]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
EDAD_BINS = [0, 2, 6, 12, 18, 200]                       # intervalos [a, b)
EDAD_LABELS = ["0-1", "2-5", "6-11", "12-17", "18+"]


def crear_engine():
    """Engine de SQLAlchemy para SQL Server (autenticación de Windows).

    Define las variables de entorno SQLSERVER_HOST y SQLSERVER_DB antes de usarlo.
    Ajusta SQLSERVER_DRIVER según el driver ODBC instalado en tu equipo.
    """
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine

    servidor = os.environ["SQLSERVER_HOST"]
    base = os.environ["SQLSERVER_DB"]
    driver = os.environ.get("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
    odbc = (f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};"
            "Trusted_Connection=yes;TrustServerCertificate=yes")
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}", fast_executemany=True)
