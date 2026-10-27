"""Pruebas de los tickets. Por defecto prueban tickets.py; para probar la referencia:
    MODULO=soluciones pytest -v          (Windows PowerShell:  $env:MODULO="soluciones"; pytest -v)
"""
import importlib
import os

import pandas as pd
import pytest

from config import DIAS_SEMANA, ESTADOS_VALIDOS
from io_datos import cargar_csv

m = importlib.import_module(os.environ.get("MODULO", "tickets"))

REGLAS = ["paciente_documento_duplicado", "paciente_nacimiento_futuro", "paciente_sin_eps",
          "cita_estado_no_estandar", "cita_paciente_inexistente", "factura_valor_no_positivo"]


@pytest.fixture(scope="module")
def crudo():
    return cargar_csv()


@pytest.fixture(scope="module")
def limpio(crudo):
    return m.limpiar(crudo)


# ----------------------------- T01 / T02 -----------------------------
def test_t01_reporte_calidad(crudo):
    r = m.reporte_calidad(crudo)
    assert list(r.columns) == ["regla", "tabla", "registros_afectados", "total", "pct"]
    assert list(r["regla"]) == REGLAS
    assert (r["registros_afectados"] > 0).all()          # el dataset trae todos los problemas
    esperado = (r["registros_afectados"] / r["total"] * 100).round(2)
    pd.testing.assert_series_equal(r["pct"], esperado, check_names=False)


def test_t02_limpieza_deja_calidad_en_cero(limpio):
    assert (m.reporte_calidad(limpio)["registros_afectados"] == 0).all()


def test_t02_normaliza_tipos_y_texto(crudo, limpio):
    assert (crudo["cita"]["Estado"] != crudo["cita"]["Estado"].str.strip().str.upper()).any()  # entrada intacta
    assert set(limpio["cita"]["Estado"]) <= set(ESTADOS_VALIDOS)
    p = limpio["paciente"]
    assert (p["Nombres"] == p["Nombres"].str.strip().str.title()).all()
    assert pd.api.types.is_integer_dtype(p["IdEPS"])
    assert pd.api.types.is_integer_dtype(limpio["cita"]["IdPaciente"])
    assert 0 in set(limpio["eps"]["IdEPS"])


def test_t02_conserva_id_menor_y_remapea(crudo, limpio):
    p0 = crudo["paciente"]
    dup = p0[p0.duplicated(["TipoDocumento", "NumeroDocumento"], keep=False)]
    borrados = set()
    for _, g in dup.groupby(["TipoDocumento", "NumeroDocumento"]):
        borrados |= set(sorted(g["IdPaciente"])[1:])
    assert borrados.isdisjoint(set(limpio["paciente"]["IdPaciente"]))
    assert borrados.isdisjoint(set(limpio["cita"]["IdPaciente"]))      # se reasignaron
    assert borrados.isdisjoint(set(limpio["factura"]["IdPaciente"]))


# ----------------------------- T03 -----------------------------
def test_t03_citas_mes_especialidad(limpio):
    r = m.citas_por_mes_especialidad(limpio)
    assert list(r.columns) == ["especialidad", "mes", "citas_total", "atendidas", "canceladas",
                               "inasistentes", "tasa_inasistencia", "var_mensual_atendidas"]
    assert r["citas_total"].sum() == len(limpio["cita"])
    assert (r["citas_total"] == r["atendidas"] + r["canceladas"] + r["inasistentes"]).all()
    f = r.iloc[3]
    assert f["tasa_inasistencia"] == round(f["inasistentes"] / (f["atendidas"] + f["inasistentes"]) * 100, 1)
    assert r.drop_duplicates("especialidad")["var_mensual_atendidas"].isna().all()   # 1er mes de cada una
    assert r["mes"].iloc[0] == "2025-01"


# ----------------------------- T04 -----------------------------
def test_t04_facturacion_eps(limpio):
    r = m.facturacion_por_eps(limpio)
    assert list(r.columns) == ["eps", "mes", "total", "n_facturas", "ticket_prom", "pct_mes",
                               "var_mes_anterior", "acumulado"]
    assert r["total"].sum() == pytest.approx(limpio["factura"]["ValorTotal"].sum())
    assert r.groupby("mes")["pct_mes"].sum().between(99, 101).all()
    assert r.groupby("eps")["acumulado"].last().sum() == pytest.approx(r["total"].sum())


# ----------------------------- T05 -----------------------------
def test_t05a_grupo_etario(limpio):
    r = m.pacientes_por_grupo_etario(limpio)
    assert list(r.columns) == ["grupo_etario", "genero", "pacientes"]
    assert r["pacientes"].sum() == limpio["paciente"]["FechaNacimiento"].notna().sum()
    assert set(r["genero"]) == {"Femenino", "Masculino"}
    assert set(r["grupo_etario"].astype(str)) <= {"0-1", "2-5", "6-11", "12-17", "18+"}


def test_t05b_recurrentes(limpio):
    r = m.pacientes_recurrentes(limpio, min_citas=3, dias=90)
    assert list(r.columns) == ["IdPaciente", "TipoDocumento", "NumeroDocumento", "citas_atendidas"]
    assert r["citas_atendidas"].is_monotonic_decreasing
    fechas = (limpio["cita"].query("Estado == 'ATENDIDA'").groupby("IdPaciente")["Fecha"]
              .apply(lambda s: sorted(s)))

    def cumple(fs):
        return any((fs[i + 2] - fs[i]).days <= 90 for i in range(len(fs) - 2))

    incluidos = set(r["IdPaciente"])
    assert all(cumple(fechas[pid]) for pid in r["IdPaciente"].head(40))
    assert not any(cumple(fechas[pid]) for pid in [p for p in fechas.index if p not in incluidos][:300])


def test_t05c_top_diagnosticos(limpio):
    r = m.top_diagnosticos(limpio, n=3)
    assert list(r.columns) == ["especialidad", "CodigoCIE10", "Descripcion", "consultas", "rank"]
    assert r.groupby("especialidad").size().eq(3).all()
    assert (r.groupby("especialidad")["consultas"].diff().dropna() <= 0).all()
    assert r.groupby("especialidad")["rank"].apply(list).apply(lambda x: x == [1, 2, 3]).all()


# ----------------------------- T06 -----------------------------
def test_t06a_ocupacion(limpio):
    r = m.ocupacion_agenda(limpio, cupos_dia=16)
    assert list(r.columns) == ["IdMedico", "medico", "especialidad", "dias_con_agenda",
                               "citas_atendidas", "promedio_citas_dia", "ocupacion_pct"]
    assert r["citas_atendidas"].sum() == (limpio["cita"]["Estado"] == "ATENDIDA").sum()
    f = r.iloc[0]
    assert f["ocupacion_pct"] == round(f["citas_atendidas"] / f["dias_con_agenda"] / 16 * 100, 1)
    assert r["ocupacion_pct"].is_monotonic_decreasing


def test_t06b_mapa_calor(limpio):
    r = m.mapa_calor_horas(limpio)
    assert list(r.index) == DIAS_SEMANA
    assert list(r.columns) == sorted(r.columns)
    assert int(r.to_numpy().sum()) == (limpio["cita"]["Estado"] != "CANCELADA").sum()
    assert r.loc["Domingo"].sum() == 0


# ----------------------------- T07 -----------------------------
def test_t07_excel(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    res = {"uno": pd.DataFrame({"a": [1, 2], "b": [1.5, 2.5]}), "dos": pd.DataFrame({"x": ["p", "q", "r"]})}
    ruta = m.exportar_excel(res, tmp_path / "sub" / "r.xlsx")
    wb = openpyxl.load_workbook(ruta)
    assert wb.sheetnames == ["Resumen", "uno", "dos"]
    for nombre in ("uno", "dos"):
        ws = wb[nombre]
        assert ws.freeze_panes == "A2"
        assert ws["A1"].font.bold
        assert ws.auto_filter.ref
    resumen = pd.read_excel(ruta, sheet_name="Resumen")
    assert dict(zip(resumen["hoja"], resumen["filas"])) == {"uno": 2, "dos": 3}
