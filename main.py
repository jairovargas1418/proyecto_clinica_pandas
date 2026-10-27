"""Orquestador: carga -> calidad -> limpieza -> reportes -> Excel.

Uso:
    python main.py                       # usa TUS funciones (tickets.py) y los CSV de data/
    python main.py --modulo soluciones   # usa las soluciones de referencia
    python main.py --fuente sqlserver    # lee desde SQL Server (ver README)
"""
import argparse
import importlib
import logging

import pandas as pd

from config import SALIDAS_DIR
from io_datos import cargar_csv, cargar_sqlserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("clinica")


def ejecutar(nombre, fn, *args, **kwargs):
    """Corre un ticket; si aún no lo implementas, avisa y sigue con los demás."""
    try:
        r = fn(*args, **kwargs)
        detalle = f"{len(r):,} filas" if hasattr(r, "__len__") else str(r)
        log.info("OK  %-28s %s", nombre, detalle)
        return r
    except NotImplementedError:
        log.warning("PENDIENTE %s", nombre)
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modulo", default="tickets", choices=["tickets", "soluciones"])
    ap.add_argument("--fuente", default="csv", choices=["csv", "sqlserver"])
    ap.add_argument("--salida", default=str(SALIDAS_DIR / "reporte_clinica.xlsx"))
    args = ap.parse_args()
    m = importlib.import_module(args.modulo)

    if args.fuente == "csv":
        crudo = cargar_csv()
    else:
        from config import crear_engine
        crudo = cargar_sqlserver(crear_engine())
    log.info("Tablas cargadas: %s", {k: len(v) for k, v in crudo.items()})

    calidad_antes = ejecutar("T01 calidad (antes)", m.reporte_calidad, crudo)
    limpio = ejecutar("T02 limpieza", m.limpiar, crudo)
    if limpio is None:
        log.error("Sin T02 no se pueden calcular los demás reportes.")
        return
    calidad_despues = ejecutar("T01 calidad (después)", m.reporte_calidad, limpio)

    mapa = ejecutar("T06b mapa de calor", m.mapa_calor_horas, limpio)
    resultados = {
        "calidad_antes": calidad_antes,
        "calidad_despues": calidad_despues,
        "citas_mes_especialidad": ejecutar("T03 citas por mes", m.citas_por_mes_especialidad, limpio),
        "facturacion_eps": ejecutar("T04 facturación por EPS", m.facturacion_por_eps, limpio),
        "pacientes_grupo_etario": ejecutar("T05a grupo etario", m.pacientes_por_grupo_etario, limpio),
        "pacientes_recurrentes": ejecutar("T05b recurrentes", m.pacientes_recurrentes, limpio),
        "top_diagnosticos": ejecutar("T05c diagnósticos", m.top_diagnosticos, limpio),
        "ocupacion_medicos": ejecutar("T06a ocupación", m.ocupacion_agenda, limpio),
        "mapa_calor_horas": None if mapa is None else mapa.reset_index(),
    }
    resultados = {k: v for k, v in resultados.items() if isinstance(v, pd.DataFrame)}

    ruta = ejecutar("T07 exportar Excel", m.exportar_excel, resultados, args.salida)
    if ruta:
        log.info("Reporte listo: %s", ruta)


if __name__ == "__main__":
    main()
