# Sistema de Retención de Clientes

Sistema para identificar señales de pérdida de clientes en productos técnicos.

## Uso

```bash
cd backend
python3 customer_retention/src/run_churn_analysis.py
```

## Estructura
- **Input**: `backend/raw_data/` (sales.csv, clients.csv, products.csv, potential.csv)
- **Output**: `backend/customer_retention/output/` (alerts_output.json, customer_risk_analysis.csv)

## Funcionalidad

**Detecta**:
- Cuándo un cliente debería volver a comprar (IPT - Inter-Purchase Time)
- Señales de abandono: caída frecuencia/volumen, desaparición, retrasos
- Distingue uso sistemático (regular) vs puntual (ocasional)

**Clasifica Riesgo**:
- 🔴 ROJO: Retraso crítico >3σ, caída >50% → Contacto URGENTE (7d)
- 🟠 NARANJA: Retraso >2σ, caída 30-50% → Contacto PROACTIVO (15d)
- 🟡 AMARILLO: Retraso 1-2σ → SEGUIMIENTO (30d)
- 🟢 VERDE: Normal → Mantenimiento rutinario

## Código

```python
from customer_retention import ChurnDetector, RiskLevel

detector = ChurnDetector()
detector.load_data('raw_data/sales.csv', 'raw_data/clients.csv', 
                   'raw_data/products.csv', 'raw_data/potential.csv')

df_features = detector.calculate_customer_features()
df_anomalies = detector.detect_anomalies(df_features)
df_risk = detector.classify_risk(df_anomalies)
df_risk = detector.calculate_churn_probability(df_risk)

alerts = detector.generate_alerts(df_risk, min_risk_level=RiskLevel.YELLOW)
detector.export_alerts_to_json(alerts, 'output/alerts.json')
```

## Personalización

```python
ChurnDetector(
    systematic_cv_threshold=0.3,   # Variabilidad baja = sistemático
    occasional_cv_threshold=0.5,   # Variabilidad alta = puntual
    systematic_freq_threshold=6    # Min 6 compras/año = sistemático
)
```
