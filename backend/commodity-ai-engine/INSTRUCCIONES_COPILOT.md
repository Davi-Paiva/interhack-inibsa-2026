# INSTRUCCIONES PARA DESARROLLAR COMMODITY AI ENGINE

## Objetivo
Desarrollar los 5 componentes del Commodity AI Engine reutilizando la feature engineering ya existente en el proyecto.

## Fuente oficial de esquema
Antes de implementar cualquier componente, leer y validar contra:
- backend/data_processing/inibsa_feature_tables.xlsx

Si hay conflicto entre suposiciones y parquet, manda el Excel.

## Entradas obligatorias
Las features se consumen desde:
- backend/processed_data/<mode>/features/

Tablas esperadas:
- client_features.parquet
- product_features.parquet
- client_product_features.parquet

Mode soportado:
- historical
- daily

## Donde trabajar
- Codigo: backend/commodity-ai-engine/src/commodity_engine.py
- Prompts: backend/commodity-ai-engine/prompts/

Usar estos prompts en orden:
1. PROMPT_1_KMEANS_CLUSTERING.md
2. PROMPT_2_CONSUMPTION_FORECAST.md
3. PROMPT_3_DEMAND_LEAKAGE.md
4. PROMPT_4_CAPTURE_SCORING.md
5. PROMPT_5_NEXT_PURCHASE.md

## Como usar Copilot
### Opcion recomendada (por componente)
1. Abre el prompt del componente.
2. Copia todo el prompt.
3. Pegalo en Copilot Chat.
4. Pide implementacion del componente en src/commodity_engine.py.
5. Repite con el siguiente prompt.

## Contrato de outputs por componente
Escribir en:
- backend/commodity-ai-engine/output/<mode>/

Archivos:
- cluster_assignments.parquet
- cluster_profiles.parquet
- consumption_forecast.parquet
- demand_leakage_signals.parquet
- capture_opportunities.parquet
- next_purchase_predictions.parquet

## Reglas de implementacion
- No rehacer feature engineering desde raw CSV.
- No eliminar outliers.
- Tratar campanas como contexto de negocio, no anomalia.
- Usar validacion de esquema al inicio de cada componente.
- Codigo modular, funciones cortas, logging claro.

## Checklist rapido
- Leido backend/data_processing/inibsa_feature_tables.xlsx
- Validada presencia de columnas en parquet
- Ejecutados prompts 1 a 5 en orden
- Generados outputs por componente
- Sin NaN en columnas criticas de salida
- Scores/probabilidades en rangos validos

## Comando base
```bash
cd backend/commodity-ai-engine
pip install -r requirements.txt
```

## Referencias
- backend/commodity-ai-engine/prompts/README.md
- backend/commodity-ai-engine/prompts/PROMPT_1_KMEANS_CLUSTERING.md
- backend/commodity-ai-engine/prompts/PROMPT_2_CONSUMPTION_FORECAST.md
- backend/commodity-ai-engine/prompts/PROMPT_3_DEMAND_LEAKAGE.md
- backend/commodity-ai-engine/prompts/PROMPT_4_CAPTURE_SCORING.md
- backend/commodity-ai-engine/prompts/PROMPT_5_NEXT_PURCHASE.md
