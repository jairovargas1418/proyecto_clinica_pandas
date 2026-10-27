# %% [markdown]
# # Etapa 2 · Conocer los datos (sin tocar tickets)
# Ejecuta cada celda (bloque que empieza con `# %%`) con Shift+Enter.
# REGLA DEL JUEGO: antes de ejecutar, escribe en un papel qué crees que saldrá. Luego compara.

# %% 0. Cargar las tablas
import pandas as pd
from config import FECHA_REF
from io_datos import cargar_csv

t = cargar_csv()            # diccionario: nombre de tabla -> DataFrame
list(t.keys())

# %% 1. ¿Cuántas filas y columnas tiene cada tabla?
# shape = (filas, columnas)
{nombre: df.shape for nombre, df in t.items()}

# %% 2. TABLA PACIENTE: mira las primeras filas
p = t["paciente"]
p.head()

# %% 3. ¿Qué tipo de dato tiene cada columna?
# Pregunta: ¿FechaNacimiento es texto o fecha real? ¿Y NumeroDocumento?
p.dtypes

# %% 4. ¿Cuántos nulos hay por columna?
p.isna().sum()

# %% 5. Pacientes DUPLICADOS: mismo TipoDocumento + NumeroDocumento
# duplicated() marca True en la 2ª aparición en adelante (la 1ª queda False)
p.duplicated(["TipoDocumento", "NumeroDocumento"]).sum()

# %% 6. Mira un duplicado "en vivo", lado a lado
# keep=False marca TODAS las filas repetidas (la 1ª también), para verlas juntas
dup = p[p.duplicated(["TipoDocumento", "NumeroDocumento"], keep=False)]
dup = dup.sort_values(["NumeroDocumento", "IdPaciente"])
dup.head(6)
# Fíjate en: ¿qué cambia entre las dos filas? ¿qué se mantiene igual?

# %% 7. Fechas de nacimiento imposibles (posteriores a FECHA_REF)
(p["FechaNacimiento"] > FECHA_REF).sum()

# %% 7b. Míralas
p[p["FechaNacimiento"] > FECHA_REF].head(3)

# %% 8. TABLA CITA: primeras filas
c = t["cita"]
c.head()

# %% 9. Los ESTADOS de las citas
# value_counts() cuenta cuántas veces aparece cada valor
c["Estado"].value_counts()

# %% 10. ¿Cuántos estados DISTINTOS hay? (deberían ser 4)
c["Estado"].nunique()

# %% 11. Los espacios invisibles: repr() muestra las comillas y los espacios
c["Estado"].map(repr).value_counts()

# %% 12. RELACIONES entre tablas: ¿todas las citas tienen un paciente que exista?
# merge how="left" conserva TODAS las citas; indicator=True agrega la columna _merge
cruce = c.merge(p[["IdPaciente"]], on="IdPaciente", how="left", indicator=True)
cruce["_merge"].value_counts()
# 'both' = la cita encontró su paciente | 'left_only' = el paciente NO existe

# %% 12b. Mira esas citas "huérfanas"
cruce[cruce["_merge"] == "left_only"].head(3)

# %% 13. TABLA FACTURA: describe() resume una columna numérica
f = t["factura"]
f["ValorTotal"].describe()

# %% 13b. ¿Cuántas facturas tienen valor 0 o negativo?
(f["ValorTotal"] <= 0).sum()

# %% 14. Sigue a UN paciente por todas las tablas (el 811 aparece en la primera cita)
idp = 811
print("paciente:")
print(p[p["IdPaciente"] == idp].to_string(), "\n")
print("citas:");    print(c[c["IdPaciente"] == idp].to_string(), "\n")
print("facturas:"); print(f[f["IdPaciente"] == idp].to_string())

# %% [markdown]
# ## Mini-retos (resuélvelos tú, con las mismas herramientas de arriba)
# R1. ¿Cuántos pacientes hay por TipoDocumento?  (pista: value_counts)
# R2. ¿Cuántas citas hay por mes?                (pista: c["Fecha"].dt.month + value_counts + sort_index)
# R3. ¿Cuántas citas tiene cada IdMedico? ¿Cuál es el médico con más?  (pista: value_counts / groupby)

# %% R1


# %% R2


# %% R3

