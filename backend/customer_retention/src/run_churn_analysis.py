"""
Script de ejemplo para ejecutar el detector de abandono de clientes
"""

import sys
import os

# Asegurar que el directorio backend esté en el path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(script_dir))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from customer_retention.src.churn_detector import ChurnDetector, RiskLevel
import pandas as pd


def run_analysis():
    """Ejecuta el análisis completo de riesgo de abandono"""
    
    print("=" * 60)
    print("ANÁLISIS DE RIESGO DE ABANDONO - PRODUCTOS TÉCNICOS")
    print("=" * 60)
    
    # Inicializar detector
    detector = ChurnDetector(
        systematic_cv_threshold=0.3,    # Baja variabilidad = sistemático
        occasional_cv_threshold=0.5,    # Alta variabilidad = puntual
        systematic_freq_threshold=6     # Mínimo 6 compras/año = sistemático
    )

    # Determinar rutas correctas según directorio de ejecución
    # El script puede ejecutarse desde backend/ o desde backend/anomaly_detection/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)  # Subir a backend/
    
    # Rutas absolutas a los archivos de datos
    data_dir = os.path.join(backend_dir, '../raw_data')
    output_dir = os.path.join(script_dir, '../output')  # Dentro de anomaly_detection/
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n1️⃣  CARGANDO DATOS...")
    print(f"   📂 Directorio de datos: {data_dir}")
    
    detector.load_data(
        sales_path=os.path.join(data_dir, 'sales.csv'),
        clients_path=os.path.join(data_dir, 'clients.csv'),
        products_path=os.path.join(data_dir, 'products.csv'),
        potential_path=os.path.join(data_dir, 'potential.csv')
    )
    
    # Calcular features
    print("\n2️⃣  CALCULANDO FEATURES POR CLIENTE-FAMILIA...")
    df_features = detector.calculate_customer_features()
    print(f"   → {len(df_features)} combinaciones cliente-familia analizadas")
    print(f"   → Tipos de uso: {df_features['usage_type'].value_counts().to_dict()}")
    
    # Detectar anomalías
    print("\n3️⃣  DETECTANDO ANOMALÍAS...")
    df_anomalies = detector.detect_anomalies(df_features)
    
    print(f"   → Caída de frecuencia: {df_anomalies['anomaly_frequency_drop'].sum()}")
    print(f"   → Caída de volumen: {df_anomalies['anomaly_volume_drop'].sum()}")
    print(f"   → Desaparición total: {df_anomalies['anomaly_total_disappearance'].sum()}")
    print(f"   → Retraso significativo: {df_anomalies['anomaly_significant_delay'].sum()}")
    
    # Clasificar riesgo
    print("\n4️⃣  CLASIFICANDO NIVEL DE RIESGO...")
    df_risk = detector.classify_risk(df_anomalies)
    
    # Calcular probabilidad de abandono
    df_risk = detector.calculate_churn_probability(df_risk)
    
    risk_distribution = df_risk['risk_level'].value_counts().to_dict()
    print(f"   → Distribución de riesgo:")
    for level in ['ROJO', 'NARANJA', 'AMARILLO', 'VERDE']:
        count = risk_distribution.get(level, 0)
        pct = (count / len(df_risk) * 100) if len(df_risk) > 0 else 0
        print(f"      • {level}: {count} ({pct:.1f}%)")
    
    # Generar alertas (solo amarillo y superior)
    print("\n5️⃣  GENERANDO ALERTAS...")
    alerts = detector.generate_alerts(df_risk, min_risk_level=RiskLevel.YELLOW)
    
    # Estadísticas
    stats = detector.get_summary_stats(alerts)
    print(f"\n   📊 ESTADÍSTICAS:")
    print(f"      • Total de alertas: {stats['total_alerts']}")
    print(f"      • Clientes únicos en riesgo: {stats['total_clients_at_risk']}")
    print(f"      • Alertas alta prioridad (rojo/naranja): {stats['high_priority']}")
    print(f"      • Probabilidad media de abandono: {stats['avg_churn_probability']:.1%}")
    
    # Mostrar top 5 alertas de mayor riesgo
    print("\n6️⃣  TOP 5 ALERTAS DE MAYOR RIESGO:")
    print("-" * 60)
    
    top_alerts = sorted(alerts, key=lambda x: (x.priority, -x.churn_probability))[:5]
    
    for i, alert in enumerate(top_alerts, 1):
        print(f"\n   {i}. Cliente: {alert.client_id} | Familia: {alert.family}")
        print(f"      Riesgo: {alert.risk_level.value} | Prioridad: {alert.priority}")
        print(f"      Probabilidad abandono: {alert.churn_probability:.1%}")
        print(f"      {alert.explanation}")
        print(f"      ➜ ACCIÓN: {alert.recommended_action}")
    
    # Exportar resultados
    print("\n7️⃣  EXPORTANDO RESULTADOS...")
    print(f"   📂 Directorio de salida: {output_dir}")
    
    # Alertas en JSON
    alerts_path = os.path.join(output_dir, 'alerts_output.json')
    detector.export_alerts_to_json(alerts, alerts_path)
    
    # Análisis completo en CSV
    risk_path = os.path.join(output_dir, 'customer_risk_analysis.csv')
    df_risk.to_csv(risk_path, index=False)
    print(f"   ✓ Análisis de riesgo: {risk_path}")
    
    # Resumen ejecutivo
    summary_df = df_risk.groupby(['risk_level', 'family']).agg({
        'client_id': 'count',
        'churn_probability': 'mean',
        'days_since_last_purchase': 'mean',
        'volume_change_3m_vs_6m': 'mean'
    }).round(2)
    summary_df.columns = ['num_clients', 'avg_churn_prob', 'avg_days_since_last', 'avg_volume_change_pct']
    summary_path = os.path.join(output_dir, 'summary_by_risk_family.csv')
    summary_df.to_csv(summary_path)
    print(f"   ✓ Resumen ejecutivo: {summary_path}")
    
    print("\n" + "=" * 60)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 60)
    
    return detector, df_risk, alerts


def analyze_specific_client(client_id, df_risk):
    """Analiza un cliente específico en detalle"""
    
    client_data = df_risk[df_risk['client_id'] == client_id]
    
    if len(client_data) == 0:
        print(f"❌ Cliente {client_id} no encontrado en el análisis")
        return
    
    print(f"\n{'=' * 60}")
    print(f"ANÁLISIS DETALLADO - CLIENTE {client_id}")
    print(f"{'=' * 60}")
    
    for idx, row in client_data.iterrows():
        print(f"\n📦 Familia: {row['family']}")
        print(f"   Tipo de uso: {row['usage_type']}")
        print(f"   Nivel de riesgo: {row['risk_level']} (Prioridad {row['priority']})")
        print(f"   Probabilidad de abandono: {row['churn_probability']:.1%}")
        print(f"\n   📊 Métricas:")
        print(f"      • Número de compras: {row['n_purchases']}")
        print(f"      • Primera compra: {row['first_purchase_date'].strftime('%Y-%m-%d')}")
        print(f"      • Última compra: {row['last_purchase_date'].strftime('%Y-%m-%d')}")
        print(f"      • Días desde última compra: {row['days_since_last_purchase']}")
        print(f"      • Intervalo medio entre compras: {row['mean_ipt']:.1f} días")
        print(f"      • Retraso actual: {row['delay_days']:.1f} días")
        print(f"      • Cambio de volumen (3m): {row['volume_change_3m_vs_6m']:.1f}%")
        print(f"      • Valor total histórico: €{row['total_value']:.2f}")
        
        print(f"\n   🚨 Anomalías detectadas: {row['total_anomalies']}")
        if row['anomaly_frequency_drop']:
            print(f"      • ⚠️  Caída de frecuencia")
        if row['anomaly_volume_drop']:
            print(f"      • ⚠️  Caída de volumen")
        if row['anomaly_total_disappearance']:
            print(f"      • ⚠️  Riesgo de desaparición total")
        if row['anomaly_significant_delay']:
            print(f"      • ⚠️  Retraso significativo")


if __name__ == "__main__":
    # Ejecutar análisis completo
    detector, df_risk, alerts = run_analysis()
    
    # Ejemplo: analizar un cliente específico
    # Si quieres ver detalles de un cliente, descomenta y ajusta el ID:
    # analyze_specific_client('1000078762', df_risk)
    output_dir = os.path.join(backend_dir, 'anomaly_detection', 'data')
    print("\n💡 PRÓXIMOS PASOS:")
    print(f"   1. Revisar {os.path.join(output_dir, 'alerts_output.json')}")
    print("   2. Priorizar contacto con clientes en riesgo ROJO/NARANJA")
    print("   3. Ajustar thresholds según feedback del equipo comercial")
    print("   4. Implementar pipeline automático (diario/semanal)")
