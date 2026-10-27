"""Carga de datos: CSV sintéticos o SQL Server. Ambos devuelven el mismo diccionario de DataFrames."""
import pandas as pd

from config import DATA_DIR

TABLAS = ["genero", "eps", "especialidad", "diagnostico", "medico",
          "paciente", "cita", "consulta", "factura"]

# Para usar SQL Server: ajusta estas consultas a los nombres reales de tus tablas/columnas.
# Lo importante es que cada DataFrame termine con las MISMAS columnas que los CSV de data/.
CONSULTAS_SQL = {t: f"SELECT * FROM dbo.{t.capitalize()}" for t in TABLAS}


def normalizar_tipos(t: dict) -> dict:
    """Fija los tipos de dato esperados (fechas reales, documentos como texto, hora 'HH:MM')."""
    t["paciente"]["FechaNacimiento"] = pd.to_datetime(t["paciente"]["FechaNacimiento"])
    t["paciente"]["NumeroDocumento"] = t["paciente"]["NumeroDocumento"].astype(str)
    t["cita"]["Fecha"] = pd.to_datetime(t["cita"]["Fecha"])
    t["cita"]["Hora"] = t["cita"]["Hora"].astype(str).str[:5]
    t["consulta"]["FechaConsulta"] = pd.to_datetime(t["consulta"]["FechaConsulta"])
    t["factura"]["Fecha"] = pd.to_datetime(t["factura"]["Fecha"])
    return t


def cargar_csv(carpeta=DATA_DIR) -> dict:
    t = {n: pd.read_csv(carpeta / f"{n}.csv", dtype={"NumeroDocumento": str, "Documento": str})
         for n in TABLAS}
    return normalizar_tipos(t)


def cargar_sqlserver(engine, consultas: dict = CONSULTAS_SQL) -> dict:
    t = {n: pd.read_sql(q, engine) for n, q in consultas.items()}
    return normalizar_tipos(t)


def cargar_a_staging(df: pd.DataFrame, tabla: str, engine, esquema: str = "stg") -> None:
    """Escribe un resultado en SQL Server (reemplaza la tabla). Ideal para que Power BI lo consuma."""
    df.to_sql(tabla, engine, schema=esquema, if_exists="replace", index=False, chunksize=1000)
