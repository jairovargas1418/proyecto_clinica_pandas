"""Genera datos SINTÉTICOS de una clínica materno-infantil (no hay pacientes reales).

Incluye problemas de calidad a propósito: pacientes duplicados, estados mal escritos,
fechas de nacimiento futuras, EPS nulas, citas con pacientes inexistentes y facturas <= 0.
"""
import numpy as np
import pandas as pd

from config import DATA_DIR, FECHA_REF

rng = np.random.default_rng(2026)
DATA_DIR.mkdir(exist_ok=True)

# ---------------- Catálogos ----------------
genero = pd.DataFrame({"IdGenero": [1, 2], "Nombre": ["Femenino", "Masculino"]})
eps = pd.DataFrame({"IdEPS": range(1, 7),
                    "Nombre": ["Sanitas", "Sura", "Nueva EPS", "Compensar", "Famisanar", "Particular"]})
esp_nombres = ["Pediatría", "Ginecología y Obstetricia", "Neonatología", "Cirugía Pediátrica", "Medicina General"]
especialidad = pd.DataFrame({"IdEspecialidad": range(1, 6), "Nombre": esp_nombres})
diag = [  # (IdEspecialidad, CIE10, descripción)
    (1, "J00", "Rinofaringitis aguda"), (1, "J03.9", "Amigdalitis aguda"), (1, "A09", "Gastroenteritis"),
    (1, "Z00.1", "Control de niño sano"), (1, "L20", "Dermatitis atópica"),
    (2, "Z34", "Supervisión de embarazo normal"), (2, "N76.0", "Vaginitis aguda"),
    (2, "N92.0", "Menstruación excesiva"), (2, "Z30", "Anticoncepción"),
    (3, "P59.9", "Ictericia neonatal"), (3, "P07.3", "Prematuridad"), (3, "Z00.1", "Control de niño sano"),
    (4, "K35", "Apendicitis aguda"), (4, "K40", "Hernia inguinal"), (4, "S06", "Trauma craneoencefálico"),
    (5, "I10", "Hipertensión esencial"), (5, "E66", "Obesidad"), (5, "J06.9", "Infección respiratoria aguda"),
]
diagnostico = pd.DataFrame(diag, columns=["_esp", "CodigoCIE10", "Descripcion"])
diagnostico.insert(0, "IdDiagnostico", range(1, len(diagnostico) + 1))

NOMBRES = ["Sofía", "Mateo", "Valentina", "Santiago", "Isabella", "Samuel", "Mariana", "Emmanuel", "Camila",
           "Juan", "Daniela", "Nicolás", "Laura", "Tomás", "Luciana", "Andrés", "Salomé", "Martín", "Paula", "Sebastián"]
APELLIDOS = ["García", "Rodríguez", "Martínez", "López", "Gómez", "Hernández", "Díaz", "Pérez", "Ramírez",
             "Torres", "Vargas", "Castro", "Rojas", "Moreno", "Jiménez", "Ortiz", "Cárdenas", "Suárez"]

# ---------------- Médicos ----------------
cuotas = [10, 8, 3, 4, 5]
medico = pd.DataFrame({
    "IdMedico": range(1, 31),
    "Documento": (10**9 + rng.choice(10**7, 30, replace=False)).astype(str),
    "Nombres": rng.choice(NOMBRES, 30), "Apellidos": [f"{a} {b}" for a, b in zip(rng.choice(APELLIDOS, 30), rng.choice(APELLIDOS, 30))],
    "IdEspecialidad": np.repeat(range(1, 6), cuotas),
})

# ---------------- Pacientes ----------------
n = 3000
es_ped = rng.random(n) < 0.65
edad = np.where(es_ped, np.minimum(rng.gamma(2.2, 3.0, n), 17.9), rng.uniform(18, 45, n))
edad[:150] = rng.uniform(0, 0.95, 150)             # un grupo de recién nacidos / lactantes
es_ped[:150] = True
nac = FECHA_REF - pd.to_timedelta((edad * 365.25).astype(int), unit="D")
genero_id = np.where(es_ped, rng.choice([1, 2], n), 1)   # adultas: mujeres (ginecología)
tipo = np.select([edad < 7, edad < 18], ["RC", "TI"], default="CC")
paciente = pd.DataFrame({
    "IdPaciente": range(1, n + 1), "TipoDocumento": tipo,
    "NumeroDocumento": (10**9 + rng.choice(10**7, n, replace=False)).astype(str),
    "Nombres": rng.choice(NOMBRES, n),
    "Apellidos": [f"{a} {b}" for a, b in zip(rng.choice(APELLIDOS, n), rng.choice(APELLIDOS, n))],
    "FechaNacimiento": nac, "IdGenero": genero_id,
    "IdEPS": rng.choice(eps["IdEPS"], n, p=[.22, .20, .25, .15, .10, .08]).astype(float),
    "IdCiudad": rng.choice([1, 2, 3, 4], n, p=[.7, .15, .1, .05]),
})
paciente.loc[rng.choice(n, 40, replace=False), "IdEPS"] = np.nan                       # EPS nula
fut = rng.choice(n, 15, replace=False)
paciente.loc[fut, "FechaNacimiento"] = FECHA_REF + pd.to_timedelta(rng.integers(30, 400, 15), unit="D")

dup = paciente.sample(60, random_state=3).copy()                                       # duplicados "sucios"
dup["IdPaciente"] = range(n + 1, n + 61)
dup["Nombres"] = [f" {x.upper()} " if i % 2 else x.lower() for i, x in enumerate(dup["Nombres"])]
paciente_ids_base = paciente["IdPaciente"].to_numpy()
paciente = pd.concat([paciente, dup], ignore_index=True)

# ---------------- Citas ----------------
pool = {  # pacientes elegibles por especialidad (según edad / género)
    1: paciente_ids_base[(edad >= 1) & (edad < 18)], 2: paciente_ids_base[(edad >= 18)],
    3: paciente_ids_base[edad < 1], 4: paciente_ids_base[(edad >= 1) & (edad < 18)],
    5: paciente_ids_base[(edad >= 12)],
}
nac_base = pd.Series(nac, index=paciente_ids_base)
peso_pac = pd.Series(rng.gamma(0.8, 1.0, n), index=paciente_ids_base)   # algunos pacientes vienen mucho más
m = 22000
esp_cita = rng.choice([1, 2, 3, 4, 5], m, p=[.38, .30, .08, .09, .15])
filas = []
for e in range(1, 6):
    k = (esp_cita == e).sum()
    ids = pool[e]
    pac = rng.choice(ids, k, p=(peso_pac[ids] / peso_pac[ids].sum()).to_numpy())
    meds = medico.loc[medico["IdEspecialidad"] == e, "IdMedico"].to_numpy()
    filas.append(pd.DataFrame({"IdPaciente": pac, "IdMedico": rng.choice(meds, k), "_esp": e}))
cita = pd.concat(filas, ignore_index=True).sample(frac=1, random_state=5).reset_index(drop=True)

fecha = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, m), unit="D")
fecha = pd.Series(fecha).where(lambda s: s.values >= nac_base.loc[cita["IdPaciente"]].values,
                               nac_base.loc[cita["IdPaciente"]].values)         # nunca antes de nacer
fecha = fecha.clip(upper=FECHA_REF)
fecha = fecha + pd.to_timedelta((fecha.dt.dayofweek == 6).astype(int), unit="D")  # sin domingos
cita["Fecha"] = fecha.dt.normalize().to_numpy()
horas = rng.choice([7, 8, 9, 10, 11, 14, 15, 16, 17], m, p=[.08, .17, .17, .14, .09, .10, .10, .09, .06])
cita["Hora"] = [f"{h:02d}:{mi:02d}" for h, mi in zip(horas, rng.choice([0, 20, 40], m))]
cita["IdConsultorio"] = rng.integers(1, 13, m)
cita["Estado"] = rng.choice(["ATENDIDA", "CANCELADA", "INASISTENTE"], m, p=[.72, .13, .15])
cita.insert(0, "IdCita", range(1, m + 1))
cita = cita[cita["Fecha"].dt.dayofweek != 6].reset_index(drop=True)

limpio_estado = cita["Estado"].copy()
sucias = rng.choice(len(cita), 400, replace=False)                                      # estados sucios
for i, idx in enumerate(sucias):
    v = cita.at[idx, "Estado"]
    cita.at[idx, "Estado"] = [v.lower(), v.title(), v + " ", " " + v][i % 4]
falsos = rng.choice(len(cita), 120, replace=False)
cita.loc[falsos, "IdPaciente"] = rng.integers(99000, 99999, 120)                        # pacientes inexistentes

# ---------------- Consultas y facturas (solo citas atendidas con paciente real) ----------------
ok = (limpio_estado == "ATENDIDA").to_numpy() & ~cita.index.isin(falsos)
at = cita[ok]
consulta = pd.DataFrame({"IdConsulta": range(1, len(at) + 1), "FechaConsulta": at["Fecha"].to_numpy(),
                         "IdCita": at["IdCita"].to_numpy()})
ids_dx = []
for e in at["_esp"]:
    d = diagnostico.loc[diagnostico["_esp"] == e, "IdDiagnostico"].to_numpy()
    w = rng.dirichlet(np.ones(len(d)) * 0.7)
    ids_dx.append(rng.choice(d, p=w))
consulta["IdDiagnostico"] = ids_dx
consulta["Sintomas"] = "Sin dato"

base = {1: 85_000, 2: 120_000, 3: 180_000, 4: 450_000, 5: 70_000}
valor = at["_esp"].map(base).to_numpy() * rng.lognormal(0, 0.25, len(at))
factura = pd.DataFrame({
    "IdFactura": range(1, len(at) + 1),
    "Fecha": np.minimum(at["Fecha"] + pd.to_timedelta(rng.integers(0, 20, len(at)), unit="D"), FECHA_REF),
    "ValorTotal": (np.round(valor, -2)), "IdPaciente": at["IdPaciente"].to_numpy(),
})
factura = factura.reset_index(drop=True)
factura.loc[rng.choice(len(factura), 25, replace=False), "ValorTotal"] = rng.choice([0, -50_000], 25)

diagnostico = diagnostico.drop(columns="_esp")
cita = cita.drop(columns="_esp")

for nombre, d in {"genero": genero, "eps": eps, "especialidad": especialidad, "diagnostico": diagnostico,
                  "medico": medico, "paciente": paciente, "cita": cita, "consulta": consulta,
                  "factura": factura}.items():
    d.to_csv(DATA_DIR / f"{nombre}.csv", index=False)
    print(f"{nombre:13s} {len(d):>6,} filas")


