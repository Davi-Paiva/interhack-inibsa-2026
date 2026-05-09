# Feature Engineering Module Guide

Este documento explica qué hace cada archivo del módulo `backend/feature_engineering` y qué se espera obtener del fichero `removed_extra_features.txt`.

## Objetivo del módulo

Este módulo transforma los datos ya limpiados por `backend/data_processing` en tablas de features listas para:

- validación de señales
- clustering futuro
- análisis de comportamiento
- dashboards de explicación
- consumo posterior por el Commodity AI Engine

El flujo esperado es:

`RAW -> DATA CLEANING -> FEATURE ENGINEERING -> COMMODITY AI ENGINE -> TECHNICAL PRODUCT ENGINE`

## Qué hace cada archivo

### [README.md](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/README.md)

Documento corto de uso del módulo.

Explica:

- el alcance funcional
- los inputs esperados
- los outputs generados
- cómo ejecutar el pipeline
- qué visualizaciones existen

### [MODULE_GUIDE.md](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/MODULE_GUIDE.md)

Esta guía.

Sirve como documentación interna para entender:

- qué hace cada archivo
- cómo se conectan entre sí
- qué significa el `.txt` de features eliminadas

### [config.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/config.py)

Define la configuración base del módulo.

Contiene:

- rutas de entrada y salida
- modo de ejecución (`historical` o `daily`)
- carpeta de features
- carpeta de métricas
- dataset fuente preferido (`sales_enriched.parquet`)

Su responsabilidad es únicamente centralizar configuración, no hacer cálculos.

### [utils.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/utils.py)

Agrupa utilidades pequeñas compartidas por el módulo.

Contiene:

- creación de carpetas
- lectura de parquet
- escritura de parquet
- escritura de JSON
- resolución del engine de parquet

Su objetivo es evitar repetir lógica técnica en otros archivos.

### [features.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/features.py)

Es el núcleo del módulo.

Se encarga de:

- cargar y normalizar la fuente de features
- enriquecer el input con contexto de clientes y productos si falta
- construir señales comportamentales
- estabilizar variables ruidosas
- alinear la salida con el contrato del Excel
- escribir las tablas finales
- generar el `.txt` de columnas temporales o extras eliminadas

Tablas principales que construye:

- `client_features`
- `product_features`
- `client_product_features`

También contiene helpers para:

- clipping
- filtrado por percentiles
- limpieza de `NaN`
- limpieza de `inf`
- limpieza orientada a visualización con `clean_feature_for_plot()`

### [run_features.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/run_features.py)

Es la capa de orquestación.

Se encarga de:

- leer argumentos CLI
- configurar logging
- lanzar el flujo histórico
- dejar preparado el placeholder de modo diario
- guardar outputs
- guardar métricas
- imprimir un resumen de ejecución

Es el archivo que se ejecuta directamente:

```bash
python3 backend/feature_engineering/run_features.py --mode historical
```

### [metrics/metrics.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/metrics/metrics.py)

Gestiona validación y monitorización ligera de features.

Calcula, por tabla:

- missing ratio
- null ratio
- infinite values ratio
- duplicate ratio
- resúmenes de distribución
- cobertura de rolling features
- cobertura de campaign features
- customer coverage
- product coverage
- sparsity ratio

Guarda JSONs en:

- `backend/processed_data/historical/features/metrics/`

### [plots/plots.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/plots/plots.py)

Contiene la lógica de visualización.

Se encarga de:

- leer las tablas de features
- aplicar filtros reutilizables
- limpiar señales para plots
- construir figuras Plotly
- seleccionar tablas de preview para el dashboard

No debería contener lógica de generación de features.

### [plots/dashboard.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/feature_engineering/plots/dashboard.py)

Es la UI mínima en Streamlit.

Se encarga de:

- cargar las tablas históricas
- mostrar navegación lateral
- aplicar filtros simples
- renderizar gráficos
- mostrar una previsualización de datos

No debería contener business logic compleja.

## Qué outputs se esperan

Después de ejecutar `data_processing` y `feature_engineering`, el resultado esperado en este módulo es:

- `backend/processed_data/historical/features/client_features.parquet`
- `backend/processed_data/historical/features/product_features.parquet`
- `backend/processed_data/historical/features/client_product_features.parquet`
- `backend/processed_data/historical/features/clients.parquet`
- `backend/processed_data/historical/features/products.parquet`
- `backend/processed_data/historical/features/removed_extra_features.txt`
- `backend/processed_data/historical/features/metrics/*.json`

## Qué significa `removed_extra_features.txt`

### Fichero

[removed_extra_features.txt](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/processed_data/historical/features/removed_extra_features.txt)

### Objetivo

Este fichero deja trazabilidad de columnas que:

- se calculan internamente para poder derivar features finales
- o aparecen como columnas extra respecto al contrato del Excel
- y por tanto no deben permanecer en la tabla final entregada

No significa que esas variables sean incorrectas.

Significa que:

- se usan como soporte intermedio
- no forman parte del output final acordado
- se eliminan antes de guardar el parquet definitivo

## Qué espero encontrar dentro del `.txt`

El `.txt` debe listar por tabla qué columnas se han descartado del resultado final.

Formato esperado:

```text
Removed extra or temporary features compared with Excel contract:

[client_features]
- columna_1
- columna_2

[product_features]
- columna_3

[client_product_features]
- columna_4
```

## Explicación de cada variable del `.txt`

### En `client_features`

- `first_order_date`
  Fecha de primera compra del cliente. Se usa para calcular frecuencia y antigüedad operativa.
- `last_order_date`
  Fecha de última compra del cliente. Se usa para `days_since_last_order` e `is_active_customer`.
- `return_orders_30d`
  Número de pedidos con devolución en la ventana de 30 días. Se usa para derivar `return_rate_30d`.
- `orders_30d`
  Número total de pedidos en 30 días. Se usa como denominador de `return_rate_30d`.
- `daily_revenue_mean_30d`
  Media de revenue diario en 30 días. Se usa para calcular estabilidad.
- `daily_revenue_std_30d`
  Desviación estándar de revenue diario en 30 días. Se usa para `coefficient_variation_30d`.

### En `product_features`

- `product_total_orders`
  Total de pedidos del producto. Se usa para derivar `product_frequency`.
- `first_order_date`
  Primera fecha observada del producto. Se usa para frecuencia temporal.
- `last_order_date`
  Última fecha observada del producto. Se usa para actividad reciente.
- `current_sales_30d`
  Ventana actual de ventas a 30 días. Se usa para calcular crecimiento.
- `previous_sales_30d`
  Ventana anterior de ventas a 30 días. Se usa como baseline de crecimiento.

### En `client_product_features`

- `first_order_date`
  Primera compra observada de la relación cliente-producto.
- `last_order_date`
  Última compra observada de la relación cliente-producto.
- `current_sales_30d`
  Ventana actual de ventas de esa relación a 30 días.
- `previous_sales_30d`
  Ventana anterior de ventas de esa relación a 30 días.

## Qué no debería aparecer en el `.txt`

No deberían aparecer:

- columnas del contrato final del Excel
- columnas que sí forman parte de la entrega final acordada
- columnas necesarias para dashboards si también son parte del contrato final

Excepción permitida actualmente:

- `customer_frequency_log1p`
- `is_active_customer`

Estas dos variables pueden existir aunque no estén en el Excel, porque se han mantenido expresamente para visualización y segmentación futura.

## Resumen práctico

- `features.py` calcula y recorta señales
- `run_features.py` orquesta la ejecución
- `metrics.py` valida la calidad
- `plots.py` prepara y dibuja
- `dashboard.py` expone la exploración visual
- `removed_extra_features.txt` documenta qué columnas intermedias se usaron pero no llegaron al resultado final
