"""Soluciones de referencia. ¡Intenta cada ticket en tickets.py antes de mirar aquí!"""
from pathlib import Path

import pandas as pd

from config import DIAS_SEMANA, EDAD_BINS, EDAD_LABELS, ESTADOS_VALIDOS, FECHA_REF


# ------------------------------- T01 -------------------------------
def reporte_calidad(t: dict) -> pd.DataFrame:
    p, c, f = t["paciente"], t["cita"], t["factura"]
    reglas = [
        ("paciente_documento_duplicado", "paciente", p.duplicated(["TipoDocumento", "NumeroDocumento"]).sum(), len(p)),
        ("paciente_nacimiento_futuro", "paciente", (p["FechaNacimiento"] > FECHA_REF).sum(), len(p)),
        ("paciente_sin_eps", "paciente", p["IdEPS"].isna().sum(), len(p)),
        ("cita_estado_no_estandar", "cita", (~c["Estado"].isin(ESTADOS_VALIDOS)).sum(), len(c)),
        ("cita_paciente_inexistente", "cita", (~c["IdPaciente"].isin(p["IdPaciente"])).sum(), len(c)),
        ("factura_valor_no_positivo", "factura", (f["ValorTotal"] <= 0).sum(), len(f)),
    ]
    r = pd.DataFrame(reglas, columns=["regla", "tabla", "registros_afectados", "total"])
    r["pct"] = (r["registros_afectados"] / r["total"] * 100).round(2)
    return r


# ------------------------------- T02 -------------------------------
def limpiar(t: dict) -> dict:
    p, c, f, eps = (t[k].copy() for k in ("paciente", "cita", "factura", "eps"))

    # texto
    for col in ("Nombres", "Apellidos"):
        p[col] = p[col].str.strip().str.title()
    c["Estado"] = c["Estado"].str.strip().str.upper()

    # duplicados: IdPaciente canónico = el menor de cada documento; se reasigna en cita y factura
    p = p.sort_values("IdPaciente")
    canonico = p.groupby(["TipoDocumento", "NumeroDocumento"])["IdPaciente"].transform("min")
    mapa = pd.Series(canonico.to_numpy(), index=p["IdPaciente"].to_numpy())
    p = p[p["IdPaciente"] == canonico]
    for df in (c, f):
        df["IdPaciente"] = df["IdPaciente"].map(mapa).fillna(df["IdPaciente"])

    # fechas futuras y EPS nula
    p.loc[p["FechaNacimiento"] > FECHA_REF, "FechaNacimiento"] = pd.NaT
    eps = pd.concat([eps, pd.DataFrame({"IdEPS": [0], "Nombre": ["SIN DATO"]})], ignore_index=True)
    p["IdEPS"] = p["IdEPS"].fillna(0).astype(int)

    # integridad referencial y valores inválidos
    c = c[c["IdPaciente"].isin(p["IdPaciente"])]
    f = f[f["IdPaciente"].isin(p["IdPaciente"]) & (f["ValorTotal"] > 0)]
    c, f = c.copy(), f.copy()
    c["IdPaciente"] = c["IdPaciente"].astype(int)
    f["IdPaciente"] = f["IdPaciente"].astype(int)

    return {**t, "paciente": p.reset_index(drop=True), "cita": c.reset_index(drop=True),
            "factura": f.reset_index(drop=True), "eps": eps}


# ------------------------------- helpers -------------------------------
def _cita_con_especialidad(t: dict) -> pd.DataFrame:
    return (t["cita"]
            .merge(t["medico"][["IdMedico", "IdEspecialidad"]], on="IdMedico")
            .merge(t["especialidad"].rename(columns={"Nombre": "especialidad"}), on="IdEspecialidad"))


# ------------------------------- T03 -------------------------------
def citas_por_mes_especialidad(t: dict) -> pd.DataFrame:
    d = _cita_con_especialidad(t)
    d["mes"] = d["Fecha"].dt.to_period("M").astype(str)
    r = (d.groupby(["especialidad", "mes"])["Estado"].value_counts().unstack(fill_value=0)
          .reindex(columns=ESTADOS_VALIDOS, fill_value=0)
          .rename(columns={"ATENDIDA": "atendidas", "CANCELADA": "canceladas", "INASISTENTE": "inasistentes"})
          .reset_index())
    r.columns.name = None
    r["citas_total"] = r[["PROGRAMADA", "atendidas", "canceladas", "inasistentes"]].sum(axis=1)
    r["tasa_inasistencia"] = (r["inasistentes"] / (r["atendidas"] + r["inasistentes"]) * 100).round(1)
    r = r.sort_values(["especialidad", "mes"])
    r["var_mensual_atendidas"] = (r.groupby("especialidad")["atendidas"].pct_change() * 100).round(1)
    return r[["especialidad", "mes", "citas_total", "atendidas", "canceladas", "inasistentes",
              "tasa_inasistencia", "var_mensual_atendidas"]].reset_index(drop=True)


# ------------------------------- T04 -------------------------------
def facturacion_por_eps(t: dict) -> pd.DataFrame:
    d = (t["factura"]
         .merge(t["paciente"][["IdPaciente", "IdEPS"]], on="IdPaciente")
         .merge(t["eps"].rename(columns={"Nombre": "eps"}), on="IdEPS"))
    d["mes"] = d["Fecha"].dt.to_period("M").astype(str)
    g = d.groupby(["eps", "mes"], as_index=False).agg(total=("ValorTotal", "sum"),
                                                      n_facturas=("IdFactura", "count"))
    g["ticket_prom"] = (g["total"] / g["n_facturas"]).round(0)
    g["pct_mes"] = (g["total"] / g.groupby("mes")["total"].transform("sum") * 100).round(1)
    g = g.sort_values(["eps", "mes"]).reset_index(drop=True)
    g["var_mes_anterior"] = (g.groupby("eps")["total"].pct_change() * 100).round(1)
    g["acumulado"] = g.groupby("eps")["total"].cumsum()
    return g[["eps", "mes", "total", "n_facturas", "ticket_prom", "pct_mes", "var_mes_anterior", "acumulado"]]


# ------------------------------- T05 -------------------------------
def pacientes_por_grupo_etario(t: dict) -> pd.DataFrame:
    p = t["paciente"].dropna(subset=["FechaNacimiento"]).merge(
        t["genero"].rename(columns={"Nombre": "genero"}), on="IdGenero")
    nac = p["FechaNacimiento"]
    cumple_pendiente = (nac.dt.month * 100 + nac.dt.day) > (FECHA_REF.month * 100 + FECHA_REF.day)
    p["edad"] = FECHA_REF.year - nac.dt.year - cumple_pendiente.astype(int)
    p["grupo_etario"] = pd.cut(p["edad"], bins=EDAD_BINS, labels=EDAD_LABELS, right=False)
    return (p.groupby(["grupo_etario", "genero"], observed=True).size()
             .rename("pacientes").reset_index())


def pacientes_recurrentes(t: dict, min_citas: int = 3, dias: int = 90) -> pd.DataFrame:
    c = t["cita"].query("Estado == 'ATENDIDA'").sort_values(["IdPaciente", "Fecha"]).copy()
    hace_k = c.groupby("IdPaciente")["Fecha"].shift(min_citas - 1)   # fecha de la cita k-1 posiciones atrás
    c["span"] = (c["Fecha"] - hace_k).dt.days
    ids = c.loc[c["span"] <= dias, "IdPaciente"].unique()
    total = c.groupby("IdPaciente").size().rename("citas_atendidas")
    r = (total.loc[ids].reset_index()
         .merge(t["paciente"][["IdPaciente", "TipoDocumento", "NumeroDocumento"]], on="IdPaciente")
         .sort_values(["citas_atendidas", "IdPaciente"], ascending=[False, True]))
    return r[["IdPaciente", "TipoDocumento", "NumeroDocumento", "citas_atendidas"]].reset_index(drop=True)


def top_diagnosticos(t: dict, n: int = 3) -> pd.DataFrame:
    d = (t["consulta"].merge(t["cita"][["IdCita", "IdMedico"]], on="IdCita")
         .merge(t["medico"][["IdMedico", "IdEspecialidad"]], on="IdMedico")
         .merge(t["especialidad"].rename(columns={"Nombre": "especialidad"}), on="IdEspecialidad")
         .merge(t["diagnostico"], on="IdDiagnostico"))
    g = (d.groupby(["especialidad", "CodigoCIE10", "Descripcion"]).size()
          .rename("consultas").reset_index())
    g["rank"] = g.groupby("especialidad")["consultas"].rank(method="first", ascending=False).astype(int)
    return g[g["rank"] <= n].sort_values(["especialidad", "rank"]).reset_index(drop=True)


# ------------------------------- T06 -------------------------------
def ocupacion_agenda(t: dict, cupos_dia: int = 16) -> pd.DataFrame:
    c = t["cita"].query("Estado == 'ATENDIDA'")
    por_dia = c.groupby(["IdMedico", "Fecha"]).size().rename("n").reset_index()
    r = (por_dia.groupby("IdMedico")
         .agg(dias_con_agenda=("Fecha", "nunique"), citas_atendidas=("n", "sum"))
         .reset_index())
    r["promedio_citas_dia"] = r["citas_atendidas"] / r["dias_con_agenda"]
    r["ocupacion_pct"] = (r["promedio_citas_dia"] / cupos_dia * 100).round(1)
    r["promedio_citas_dia"] = r["promedio_citas_dia"].round(2)
    med = t["medico"].assign(medico=lambda m: m["Nombres"].str.strip() + " " + m["Apellidos"].str.strip())
    r = (r.merge(med[["IdMedico", "medico", "IdEspecialidad"]], on="IdMedico")
          .merge(t["especialidad"].rename(columns={"Nombre": "especialidad"}), on="IdEspecialidad"))
    return (r[["IdMedico", "medico", "especialidad", "dias_con_agenda", "citas_atendidas",
               "promedio_citas_dia", "ocupacion_pct"]]
            .sort_values("ocupacion_pct", ascending=False).reset_index(drop=True))


def mapa_calor_horas(t: dict) -> pd.DataFrame:
    c = t["cita"].query("Estado != 'CANCELADA'").copy()
    c["hora"] = pd.to_datetime(c["Hora"], format="%H:%M").dt.hour
    c["dia"] = pd.Categorical(c["Fecha"].dt.dayofweek.map(dict(enumerate(DIAS_SEMANA))),
                              categories=DIAS_SEMANA, ordered=True)
    m = c.pivot_table(index="dia", columns="hora", values="IdCita", aggfunc="count",
                      fill_value=0, observed=False)
    m.columns.name = None
    return m


# ------------------------------- T07 -------------------------------
def exportar_excel(resultados: dict, ruta) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    resumen = pd.DataFrame({"hoja": list(resultados), "filas": [len(df) for df in resultados.values()]})
    hojas = {"Resumen": resumen, **{k[:31]: v for k, v in resultados.items()}}

    with pd.ExcelWriter(ruta, engine="xlsxwriter") as xw:
        fmt_enc = xw.book.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78", "border": 1})
        fmt_dec = xw.book.add_format({"num_format": "#,##0.00"})
        for nombre, df in hojas.items():
            df.to_excel(xw, sheet_name=nombre, index=False)
            ws = xw.sheets[nombre]
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), fmt_enc)
                largo = df[col].astype(str).str.len().max() if len(df) else 0
                ancho = min(max(len(str(col)), 0 if pd.isna(largo) else largo) + 2, 45)
                ws.set_column(j, j, ancho, fmt_dec if pd.api.types.is_float_dtype(df[col]) else None)
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
    return ruta
