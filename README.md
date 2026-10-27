# Proyecto: analítica de una clínica con pandas

Practica **todo lo visto (Niveles 1-5)** resolviendo las mismas solicitudes que llegan a un área de datos
de una clínica (gerencia, calidad, facturación, agenda), pero en Python en lugar de SQL.

> Los datos son **sintéticos** (una clínica materno-infantil inventada). Traen errores a propósito:
> duplicados, estados mal escritos, fechas imposibles, EPS nulas, citas huérfanas y facturas <= 0.

## 1. Preparación
```bash
pip install -r requirements.txt
python generar_datos.py        # (ya hay CSV en data/; úsalo para regenerarlos)
pytest -v                      # al inicio TODO falla: es normal, ese es tu tablero de avance
```

## 2. Cómo trabajar
1. Abre `tickets.py`. Cada función es una **solicitud** de un área, con su especificación en el docstring.
2. Implementa un ticket, corre `pytest -v -k t03` (por ejemplo) hasta que quede en verde.
3. Cuando termines (o te atasques de verdad), compara con `soluciones.py`.
4. `python main.py` ejecuta el pipeline completo con TUS funciones y genera `salidas/reporte_clinica.xlsx`
   (los tickets pendientes se saltan con una advertencia). `--modulo soluciones` usa la referencia.

Para probar la referencia: `MODULO=soluciones pytest -v` (PowerShell: `$env:MODULO="soluciones"; pytest -v`).

## 3. Los tickets

| Ticket | Solicitud | Conceptos pandas |
|---|---|---|
| T01 | Reporte de calidad de datos | `duplicated`, `isna`, `isin`, comparación de fechas, DataFrame de reglas |
| T02 | Estandarizar y limpiar | `str.strip/title/upper`, `groupby().transform`, `map`, `concat`, integridad referencial, tipos |
| T03 | Citas por mes y especialidad (+ tasa de inasistencia) | `merge`, `to_period`, `value_counts().unstack`, `pct_change` por grupo |
| T04 | Facturación por EPS | `agg` nombrada, `transform`, participación %, `cumsum` |
| T05a | Pacientes por grupo etario y género | edad calculada, `pd.cut`, `groupby(observed=)` |
| T05b | Pacientes recurrentes (>=3 citas en 90 días) | `sort_values`, `groupby().shift`, diferencias de fechas |
| T05c | Top diagnósticos por especialidad | cadena de `merge`, `rank` por grupo |
| T06a | Ocupación de médicos | `agg`, `nunique`, ratios |
| T06b | Mapa de calor día x hora | `pd.Categorical` ordenada, `pivot_table` |
| T07 | Entrega en Excel presentable | `ExcelWriter` + xlsxwriter (formato, filtros, anchos) |

Retos extra cuando termines: tipos `category` y memoria, `chunksize`, logging en cada ticket,
type hints completos, y comparar cada resultado con su equivalente en SQL (T03 y T04 son un buen par).

## 4. Pasar de los CSV a SQL Server
1. Define variables de entorno: `SQLSERVER_HOST`, `SQLSERVER_DB` (y `SQLSERVER_DRIVER` si no usas ODBC 17).
2. En `io_datos.py` ajusta `CONSULTAS_SQL` a tus tablas reales. Cada DataFrame debe quedar con las
   **mismas columnas** que los CSV de `data/` (renombra/une en el SELECT o en pandas).
3. `python main.py --fuente sqlserver --modulo tickets`
4. `cargar_a_staging(df, "rpt_facturacion_eps", engine)` deja un resultado en un esquema `stg` para Power BI.

Regla práctica: **SQL para filtrar y reducir en el servidor; pandas para limpiar, combinar fuentes
(SQL + Excel), calcular métricas complejas y automatizar entregas.** Evita traer tablas enormes completas.

## 5. Privacidad
Los datos de pacientes son datos sensibles de salud. Con datos reales: trabaja solo en equipos y redes
autorizados por la clínica, no los subas a repositorios, chats ni servicios externos, y anonimiza o
seudonimiza documentos y nombres para las prácticas. Confirma la política interna de tu clínica.
