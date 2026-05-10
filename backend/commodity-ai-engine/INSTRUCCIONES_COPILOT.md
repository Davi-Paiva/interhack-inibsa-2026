# INSTRUCCIONES PARA DESARROLLAR COMMODITY AI ENGINE

## Objetivo
Desarrollar los componentes del Commodity AI Engine reutilizando la feature engineering ya existente.

## Fuente oficial de esquema
- `backend/data_processing/inibsa_feature_tables.xlsx`

Si hay conflicto entre suposiciones y CSV/parquet legado, manda el Excel.

## Entradas obligatorias
Las features se consumen desde:
- `backend/processed_data/<mode>/`

Tablas esperadas:
- `clients.csv`
- `products.csv`
- `client_product_features.csv`
- `sales_enriched.csv`

## Donde trabajar
- Codigo: `backend/commodity-ai-engine/src/commodity_engine.py`
- Prompts: `backend/commodity-ai-engine/prompts/`

## Contrato de outputs por componente
Escribir en:
- `backend/commodity-ai-engine/output/<mode>/`

Archivos principales:
- `cluster_assignments.parquet`
- `cluster_profiles.parquet`
- `consumption_forecast.parquet`
- `metrics/cluster_metrics.json`
- `metrics/forecast_metrics.json`
- `metrics/forecast_backtest_predictions.parquet`

## Reglas de implementacion
- No rehacer feature engineering desde raw CSV para la operativa actual.
- El forecast real historico puede reconstruir snapshots desde `sales_enriched.csv` para backtesting.
- No eliminar outliers.
- Tratar campañas como contexto de negocio, no anomalía.
- Usar validación de esquema al inicio de cada componente.

## Checklist rapido
- Leido `backend/data_processing/inibsa_feature_tables.xlsx`
- Validada presencia de columnas en CSV/parquet legado
- Generados outputs por componente
- Sin NaN en columnas criticas de salida
