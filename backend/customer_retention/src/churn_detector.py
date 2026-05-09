"""
Sistema de Detección de Riesgo de Abandono de Clientes
Productos Técnicos - INIBSA
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Niveles de riesgo de abandono"""
    GREEN = "VERDE"      # Normal
    YELLOW = "AMARILLO"  # Vigilancia
    ORANGE = "NARANJA"   # Riesgo Medio
    RED = "ROJO"         # Riesgo Alto


class UsageType(Enum):
    """Tipo de uso del producto"""
    SYSTEMATIC = "SISTEMATICO"  # Compra regular
    OCCASIONAL = "PUNTUAL"      # Compra ocasional
    MIXED = "MIXTO"             # Comportamiento mixto


@dataclass
class Alert:
    """Estructura de una alerta de riesgo"""
    alert_id: str
    client_id: str
    family: str
    risk_level: RiskLevel
    priority: int
    days_since_last_purchase: int
    expected_days: float
    delay_days: float
    churn_probability: float
    volume_change_pct: float
    explanation: str
    recommended_action: str
    action_window_days: int
    

class ChurnDetector:
    """
    Detector de riesgo de abandono de clientes
    """
    
    def __init__(self, 
                 systematic_cv_threshold: float = 0.3,
                 occasional_cv_threshold: float = 0.5,
                 systematic_freq_threshold: int = 6):
        """
        Args:
            systematic_cv_threshold: Coeficiente de variación para uso sistemático
            occasional_cv_threshold: Coeficiente de variación para uso puntual
            systematic_freq_threshold: Mínimo de compras anuales para sistemático
        """
        self.systematic_cv_threshold = systematic_cv_threshold
        self.occasional_cv_threshold = occasional_cv_threshold
        self.systematic_freq_threshold = systematic_freq_threshold
        
    def load_data(self, 
                  sales_path: str, 
                  clients_path: str, 
                  products_path: str,
                  potential_path: str) -> None:
        """Carga los datasets necesarios"""
        
        # Cargar datos
        self.sales = pd.read_csv(sales_path, low_memory=False)
        self.clients = pd.read_csv(clients_path)
        self.products = pd.read_csv(products_path)
        self.potential = pd.read_csv(potential_path)
        
        # Limpiar columna de valores (quitar formato europeo)
        self.sales['Valores'] = self.sales['Valores'].str.replace('.', '', regex=False)
        self.sales['Valores'] = self.sales['Valores'].str.replace(',', '.', regex=False)
        self.sales['Valores'] = pd.to_numeric(self.sales['Valores'], errors='coerce')
        
        # Convertir fechas
        self.sales['Fecha'] = pd.to_datetime(self.sales['Fecha'], format='%m/%d/%Y')
        
        # Filtrar solo productos técnicos
        technical_products = self.products[
            self.products['Bloque analítico'] == 'Productos Técnicos'
        ]['Id.Prod'].unique()
        
        self.sales_technical = self.sales[
            self.sales['Id. Producto'].isin(technical_products)
        ].copy()
        
        # Merge con información de productos para obtener familia
        self.sales_technical = self.sales_technical.merge(
            self.products[['Id.Prod', 'Familia']],
            left_on='Id. Producto',
            right_on='Id.Prod',
            how='left'
        )
        
        print(f"✓ Datos cargados: {len(self.sales_technical)} transacciones de productos técnicos")
        print(f"✓ Clientes únicos: {self.sales_technical['Id. Cliente'].nunique()}")
        print(f"✓ Familias de productos: {self.sales_technical['Familia'].nunique()}")
        
    def calculate_customer_features(self, reference_date: datetime = None) -> pd.DataFrame:
        """
        Calcula features por cliente-familia
        
        Args:
            reference_date: Fecha de referencia para cálculos (default: hoy)
            
        Returns:
            DataFrame con features calculadas
        """
        if reference_date is None:
            reference_date = datetime.now()
            
        features_list = []
        
        # Agrupar por cliente y familia
        grouped = self.sales_technical.groupby(['Id. Cliente', 'Familia'])
        
        for (client_id, family), group in grouped:
            # Ordenar por fecha
            group = group.sort_values('Fecha')
            
            # Features básicas
            n_purchases = len(group)
            if n_purchases < 2:
                continue  # Necesitamos al menos 2 compras para calcular IPT
                
            # Fechas
            first_purchase = group['Fecha'].min()
            last_purchase = group['Fecha'].max()
            days_since_last = (reference_date - last_purchase).days
            
            # Inter-Purchase Time (IPT)
            purchase_dates = group['Fecha'].values
            ipts = np.diff(purchase_dates).astype('timedelta64[D]').astype(int)
            
            if len(ipts) > 0:
                mean_ipt = np.mean(ipts)
                median_ipt = np.median(ipts)
                std_ipt = np.std(ipts) if len(ipts) > 1 else 0
                cv_ipt = std_ipt / mean_ipt if mean_ipt > 0 else 0
            else:
                mean_ipt = median_ipt = std_ipt = cv_ipt = 0
                
            # Volumen y valor
            total_units = abs(group['Unidades'].sum())
            total_value = abs(group['Valores'].sum())
            avg_units_per_purchase = total_units / n_purchases
            avg_value_per_purchase = total_value / n_purchases
            
            # Tendencias (últimos 3 vs 6 meses)
            date_3m_ago = reference_date - timedelta(days=90)
            date_6m_ago = reference_date - timedelta(days=180)
            
            recent_3m = group[group['Fecha'] >= date_3m_ago]
            recent_6m = group[group['Fecha'] >= date_6m_ago]
            
            units_3m = abs(recent_3m['Unidades'].sum()) if len(recent_3m) > 0 else 0
            units_6m = abs(recent_6m['Unidades'].sum()) if len(recent_6m) > 0 else 0
            
            # Clasificación de tipo de uso
            usage_type = self._classify_usage_type(cv_ipt, n_purchases, 
                                                   (last_purchase - first_purchase).days)
            
            # Calcular fecha esperada de próxima compra
            expected_next_purchase_days = mean_ipt
            expected_next_purchase_date = last_purchase + timedelta(days=expected_next_purchase_days)
            delay_days = (reference_date - expected_next_purchase_date).days
            
            features = {
                'client_id': client_id,
                'family': family,
                'n_purchases': n_purchases,
                'first_purchase_date': first_purchase,
                'last_purchase_date': last_purchase,
                'days_since_last_purchase': days_since_last,
                'mean_ipt': mean_ipt,
                'median_ipt': median_ipt,
                'std_ipt': std_ipt,
                'cv_ipt': cv_ipt,
                'total_units': total_units,
                'total_value': total_value,
                'avg_units_per_purchase': avg_units_per_purchase,
                'avg_value_per_purchase': avg_value_per_purchase,
                'units_3m': units_3m,
                'units_6m': units_6m,
                'usage_type': usage_type.value,
                'expected_next_purchase_date': expected_next_purchase_date,
                'expected_next_purchase_days': expected_next_purchase_days,
                'delay_days': delay_days
            }
            
            features_list.append(features)
            
        df_features = pd.DataFrame(features_list)
        
        # Calcular cambio de volumen
        df_features['volume_change_3m_vs_6m'] = (
            (df_features['units_3m'] - (df_features['units_6m'] - df_features['units_3m'])) /
            (df_features['units_6m'] - df_features['units_3m'] + 1e-6)
        ) * 100
        
        return df_features
    
    def _classify_usage_type(self, cv_ipt: float, n_purchases: int, total_days: int) -> UsageType:
        """
        Clasifica el tipo de uso basado en coeficiente de variación y frecuencia
        """
        # Evitar división por cero si todas las compras son el mismo día
        if total_days == 0:
            # Solo 1 compra o todas el mismo día -> insuficiente información
            return UsageType.OCCASIONAL
        
        if total_days < 365:
            # Si no tenemos un año completo, usar número absoluto de compras
            freq_anual_estimated = (n_purchases / total_days) * 365
        else:
            freq_anual_estimated = (n_purchases / total_days) * 365
            
        if cv_ipt < self.systematic_cv_threshold and freq_anual_estimated >= self.systematic_freq_threshold:
            return UsageType.SYSTEMATIC
        elif cv_ipt > self.occasional_cv_threshold or freq_anual_estimated < 4:
            return UsageType.OCCASIONAL
        else:
            return UsageType.MIXED
    
    def detect_anomalies(self, df_features: pd.DataFrame) -> pd.DataFrame:
        """
        Detecta anomalías en patrones de compra
        
        Returns:
            DataFrame con flags de anomalías
        """
        df = df_features.copy()
        
        # 1. Caída de Frecuencia
        df['anomaly_frequency_drop'] = df['days_since_last_purchase'] > (1.5 * df['mean_ipt'])
        
        # 2. Caída de Volumen (comparar últimos 3m con periodo anterior)
        df['anomaly_volume_drop'] = df['volume_change_3m_vs_6m'] < -30
        
        # 3. Desaparición Total (sin compra por mucho tiempo)
        df['anomaly_total_disappearance'] = (
            df['days_since_last_purchase'] > (2 * df['mean_ipt'] + 30)
        )
        
        # 4. Retraso significativo
        df['anomaly_significant_delay'] = df['delay_days'] > (2 * df['std_ipt'])
        
        # Contador de anomalías
        anomaly_cols = [col for col in df.columns if col.startswith('anomaly_')]
        df['total_anomalies'] = df[anomaly_cols].sum(axis=1)
        
        return df
    
    def classify_risk(self, df_anomalies: pd.DataFrame) -> pd.DataFrame:
        """
        Clasifica el nivel de riesgo de cada cliente-familia
        """
        df = df_anomalies.copy()
        
        def _determine_risk(row):
            """Determina el nivel de riesgo basado en múltiples factores"""
            
            # Factores de riesgo
            delay_std_ratio = row['delay_days'] / (row['std_ipt'] + 1) if row['std_ipt'] > 0 else 0
            volume_change = row['volume_change_3m_vs_6m']
            total_anomalies = row['total_anomalies']
            usage_type = row['usage_type']
            
            # ROJO: Riesgo Alto
            if (row['anomaly_total_disappearance'] or 
                delay_std_ratio > 3 or 
                (volume_change < -50 and usage_type == 'SISTEMATICO')):
                return RiskLevel.RED.value, 1  # Prioridad 1
            
            # NARANJA: Riesgo Medio
            elif (delay_std_ratio > 2 or 
                  (30 <= abs(volume_change) <= 50 and usage_type == 'SISTEMATICO') or
                  total_anomalies >= 2):
                return RiskLevel.ORANGE.value, 2
            
            # AMARILLO: Vigilancia
            elif (1 <= delay_std_ratio <= 2 or 
                  total_anomalies == 1 or
                  (usage_type == 'PUNTUAL' and row['days_since_last_purchase'] > row['mean_ipt'])):
                return RiskLevel.YELLOW.value, 3
            
            # VERDE: Normal
            else:
                return RiskLevel.GREEN.value, 4
        
        df[['risk_level', 'priority']] = df.apply(
            lambda row: pd.Series(_determine_risk(row)), 
            axis=1
        )
        
        return df
    
    def calculate_churn_probability(self, df_risk: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula probabilidad de abandono usando una función simple
        (en producción, esto sería un modelo ML entrenado)
        """
        df = df_risk.copy()
        
        def _calc_probability(row):
            """Calcula probabilidad simplificada basada en factores clave"""
            prob = 0.0
            
            # Factor 1: Retraso
            if row['delay_days'] > 0:
                delay_factor = min(row['delay_days'] / (row['mean_ipt'] + 1), 1.0)
                prob += delay_factor * 0.4
            
            # Factor 2: Cambio de volumen
            if row['volume_change_3m_vs_6m'] < 0:
                volume_factor = min(abs(row['volume_change_3m_vs_6m']) / 100, 1.0)
                prob += volume_factor * 0.3
            
            # Factor 3: Anomalías
            anomaly_factor = min(row['total_anomalies'] / 4, 1.0)
            prob += anomaly_factor * 0.3
            
            return min(prob, 0.99)
        
        df['churn_probability'] = df.apply(_calc_probability, axis=1)
        
        return df
    
    def generate_alerts(self, df_risk: pd.DataFrame, 
                       min_risk_level: RiskLevel = RiskLevel.YELLOW) -> List[Alert]:
        """
        Genera alertas accionables para clientes en riesgo
        
        Args:
            df_risk: DataFrame con clasificación de riesgo
            min_risk_level: Nivel mínimo de riesgo para generar alerta
            
        Returns:
            Lista de alertas
        """
        # Filtrar por nivel mínimo de riesgo
        risk_order = {
            RiskLevel.RED.value: 1,
            RiskLevel.ORANGE.value: 2,
            RiskLevel.YELLOW.value: 3,
            RiskLevel.GREEN.value: 4
        }
        
        df_filtered = df_risk[
            df_risk['risk_level'].map(risk_order) <= risk_order[min_risk_level.value]
        ].copy()
        
        alerts = []
        
        for idx, row in df_filtered.iterrows():
            # Generar ID de alerta
            alert_id = f"ALR-{datetime.now().strftime('%Y%m%d')}-{idx:04d}"
            
            # Generar explicación
            explanation = self._generate_explanation(row)
            
            # Generar acción recomendada
            action, action_window = self._generate_action(row)
            
            alert = Alert(
                alert_id=alert_id,
                client_id=row['client_id'],
                family=row['family'],
                risk_level=RiskLevel(row['risk_level']),
                priority=int(row['priority']),
                days_since_last_purchase=int(row['days_since_last_purchase']),
                expected_days=float(row['expected_next_purchase_days']),
                delay_days=float(row['delay_days']),
                churn_probability=float(row['churn_probability']),
                volume_change_pct=float(row['volume_change_3m_vs_6m']),
                explanation=explanation,
                recommended_action=action,
                action_window_days=action_window
            )
            
            alerts.append(alert)
        
        return alerts
    
    def _generate_explanation(self, row: pd.Series) -> str:
        """Genera explicación en lenguaje natural"""
        parts = []
        
        # Tipo de cliente
        if row['usage_type'] == 'SISTEMATICO':
            parts.append(f"Cliente con compra sistemática (cada {row['mean_ipt']:.0f} días)")
        else:
            parts.append(f"Cliente con compra puntual (intervalo variable ~{row['mean_ipt']:.0f} días)")
        
        # Tiempo sin comprar
        parts.append(f"lleva {row['days_since_last_purchase']:.0f} días sin comprar")
        
        # Retraso
        if row['delay_days'] > 0:
            parts.append(f"con {row['delay_days']:.0f} días de retraso respecto a lo esperado")
        
        # Cambio de volumen
        if row['volume_change_3m_vs_6m'] < -10:
            parts.append(f"Volumen ha caído {abs(row['volume_change_3m_vs_6m']):.0f}% en últimos 3 meses")
        
        # Anomalías
        if row['total_anomalies'] > 0:
            parts.append(f"Patrón anómalo detectado ({row['total_anomalies']:.0f} señales)")
        
        return ". ".join(parts) + "."
    
    def _generate_action(self, row: pd.Series) -> Tuple[str, int]:
        """Genera acción recomendada y ventana de tiempo"""
        risk = row['risk_level']
        
        if risk == RiskLevel.RED.value:
            action = "CONTACTO URGENTE: Cliente en riesgo crítico de pérdida. Contactar inmediatamente para entender situación y ofrecer solución personalizada."
            window = 7
        elif risk == RiskLevel.ORANGE.value:
            action = "CONTACTO PROACTIVO: Cliente estable mostrando señales de cambio. Contactar para entender necesidades actuales y ofrecer revisión de productos."
            window = 15
        elif risk == RiskLevel.YELLOW.value:
            action = "SEGUIMIENTO: Monitorear evolución. Considerar contacto informativo sobre novedades o promociones específicas."
            window = 30
        else:
            action = "MANTENIMIENTO: Cliente en situación normal. Mantener seguimiento rutinario."
            window = 60
        
        return action, window
    
    def export_alerts_to_json(self, alerts: List[Alert], output_path: str) -> None:
        """Exporta alertas a JSON"""
        import json
        
        alerts_dict = [
            {
                'alert_id': alert.alert_id,
                'fecha_generacion': datetime.now().strftime('%Y-%m-%d'),
                'nivel_riesgo': alert.risk_level.value,
                'prioridad': alert.priority,
                'cliente': {
                    'id': str(alert.client_id)
                },
                'producto': {
                    'familia': alert.family
                },
                'metricas': {
                    'dias_desde_ultima_compra': alert.days_since_last_purchase,
                    'dias_esperados': round(alert.expected_days, 1),
                    'retraso_dias': round(alert.delay_days, 1),
                    'probabilidad_abandono': round(alert.churn_probability, 2),
                    'caida_volumen_pct': round(alert.volume_change_pct, 1)
                },
                'explicacion': alert.explanation,
                'accion_recomendada': {
                    'mensaje': alert.recommended_action,
                    'ventana_accion_dias': alert.action_window_days
                }
            }
            for alert in alerts
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(alerts_dict, f, ensure_ascii=False, indent=2)
        
        print(f"✓ {len(alerts)} alertas exportadas a {output_path}")
    
    def get_summary_stats(self, alerts: List[Alert]) -> Dict:
        """Genera estadísticas resumidas de las alertas"""
        from collections import Counter
        
        risk_counts = Counter(alert.risk_level.value for alert in alerts)
        
        return {
            'total_alerts': len(alerts),
            'by_risk_level': dict(risk_counts),
            'high_priority': sum(1 for alert in alerts if alert.priority <= 2),
            'avg_churn_probability': np.mean([alert.churn_probability for alert in alerts]),
            'total_clients_at_risk': len(set(alert.client_id for alert in alerts))
        }


def main():
    """Ejemplo de uso"""
    
    # Inicializar detector
    detector = ChurnDetector()
    
    # Cargar datos
    detector.load_data(
        sales_path='data/raw/sales.csv',
        clients_path='data/raw/clients.csv',
        products_path='data/raw/products.csv',
        potential_path='data/raw/potential.csv'
    )
    
    # Calcular features
    print("\n📊 Calculando features...")
    df_features = detector.calculate_customer_features()
    print(f"✓ Features calculadas para {len(df_features)} cliente-familia combinaciones")
    
    # Detectar anomalías
    print("\n🔍 Detectando anomalías...")
    df_anomalies = detector.detect_anomalies(df_features)
    print(f"✓ Anomalías detectadas: {df_anomalies['total_anomalies'].sum():.0f}")
    
    # Clasificar riesgo
    print("\n⚠️  Clasificando riesgo...")
    df_risk = detector.classify_risk(df_anomalies)
    
    # Calcular probabilidad de abandono
    df_risk = detector.calculate_churn_probability(df_risk)
    
    # Generar alertas
    print("\n🚨 Generando alertas...")
    alerts = detector.generate_alerts(df_risk, min_risk_level=RiskLevel.YELLOW)
    
    # Resumen
    stats = detector.get_summary_stats(alerts)
    print(f"\n📈 RESUMEN:")
    print(f"  Total alertas: {stats['total_alerts']}")
    print(f"  Clientes en riesgo: {stats['total_clients_at_risk']}")
    print(f"  Alta prioridad: {stats['high_priority']}")
    print(f"  Por nivel de riesgo: {stats['by_risk_level']}")
    print(f"  Probabilidad media abandono: {stats['avg_churn_probability']:.1%}")
    
    # Exportar
    detector.export_alerts_to_json(alerts, 'data/anomaly_detection/alerts_output.json')
    
    # Exportar DataFrame de riesgo
    df_risk.to_csv('data/anomaly_detection/customer_risk_analysis.csv', index=False)
    print(f"✓ Análisis completo exportado a data/anomaly_detection/")
    
    return detector, df_risk, alerts


if __name__ == "__main__":
    detector, df_risk, alerts = main()
