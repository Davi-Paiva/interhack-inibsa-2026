# COMMODITY AI ENGINE - INICIO

## Estado actual
- El contrato de columnas sigue definido por `backend/data_processing/inibsa_feature_tables.xlsx`.
- El engine ya no depende de `backend/processed_data/<mode>/features/`.
- La fuente operativa actual son los CSV en `backend/processed_data/<mode>/`.

## Flujo correcto
1. `data_processing` limpia y publica datos
2. `feature_engineering` materializa:
   - `clients.csv`
   - `products.csv`
   - `client_product_features.csv`
3. `commodity-ai-engine` consume esas tablas y `sales_enriched.csv`
4. los outputs se escriben en `backend/commodity-ai-engine/output/<mode>/`

## Regla clave
Antes de cada componente:
- validar esquema CSV/parquet legado contra Excel
- si hay conflicto, prevalece el Excel

## Outputs principales
- `cluster_assignments.parquet`
- `cluster_profiles.parquet`
- `consumption_forecast.parquet`
- `metrics/cluster_metrics.json`
- `metrics/forecast_metrics.json`
- `metrics/forecast_backtest_predictions.parquet`

## Checklist minimo
- Excel leido
- tablas CSV localizadas
- outputs generados por componente
- validaciones basicas superadas
