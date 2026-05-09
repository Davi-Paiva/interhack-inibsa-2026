# COMMODITY AI ENGINE - INICIO

## Estado actual correcto
- La feature engineering se considera existente y reutilizable.
- El contrato de columnas se define en:
  - backend/data_processing/inibsa_feature_tables.xlsx
- Los prompts de implementacion estan en:
  - backend/commodity-ai-engine/prompts/

## Flujo correcto
1. cleaning + features en data_processing
2. parquet en backend/processed_data/<mode>/features/
3. componentes commodity consumen esas tablas
4. outputs de commodity en backend/commodity-ai-engine/output/<mode>/

## Estructura util
- backend/commodity-ai-engine/src/commodity_engine.py
- backend/commodity-ai-engine/prompts/README.md
- backend/commodity-ai-engine/prompts/PROMPT_1_KMEANS_CLUSTERING.md
- backend/commodity-ai-engine/prompts/PROMPT_2_CONSUMPTION_FORECAST.md
- backend/commodity-ai-engine/prompts/PROMPT_3_DEMAND_LEAKAGE.md
- backend/commodity-ai-engine/prompts/PROMPT_4_CAPTURE_SCORING.md
- backend/commodity-ai-engine/prompts/PROMPT_5_NEXT_PURCHASE.md

## Orden de ejecucion recomendado
1. Prompt 1: clustering
2. Prompt 2: consumption forecast
3. Prompt 3: demand leakage
4. Prompt 4: capture scoring
5. Prompt 5: next purchase

## Regla clave
Antes de cada componente:
- validar esquema parquet contra Excel
- si hay conflicto, prevalece el Excel

## Contract de outputs
- cluster_assignments.parquet
- cluster_profiles.parquet
- consumption_forecast.parquet
- demand_leakage_signals.parquet
- capture_opportunities.parquet
- next_purchase_predictions.parquet

Ruta:
- backend/commodity-ai-engine/output/<mode>/

## Lo que no se debe hacer
- no rehacer feature engineering desde raw csv
- no eliminar outliers
- no tratar campanas como anomalias

## Checklist minimo
- Excel leido
- tablas parquet localizadas
- prompts ejecutados en orden
- outputs generados por componente
- validaciones basicas superadas
