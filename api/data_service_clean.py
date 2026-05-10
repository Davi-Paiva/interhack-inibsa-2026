"""Data service to load and transform ML pipeline outputs into API models."""

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from models import (
    Clinic, ClinicDetail, Signal, TimelineDataPoint, 
    Recommendation, KPI, OverviewStats, RiskLevel
)


class DataService:
    """Service to load ML pipeline outputs and transform them for API consumption."""
    
    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300
    
    def __init__(self, project_root: Path, mode: str = "historical"):
        self.project_root = Path(project_root).resolve()
        self.mode = mode
        self._cache = {}
        self._results_cache = {}
        self._cache_timestamps = {}
        
    # ========== Path Helpers ==========
    
    @property
    def global_queue_path(self) -> Path:
        return self.project_root / "backend" / "global_prioritization" / "output" / self.mode / "global_alert_queue.json"
    
    @property
    def global_queue_parquet_path(self) -> Path:
        return self.project_root / "backend" / "global_prioritization" / "output" / self.mode / "global_alert_queue.parquet"
    
    @property
    def processed_data_dir(self) -> Path:
        return self.project_root / "backend" / "processed_data" / self.mode
    
    @property
    def clients_path(self) -> Path:
        return self.processed_data_dir / "clients.csv"
    
    @property
    def products_path(self) -> Path:
        return self.processed_data_dir / "products.csv"
    
    @property
    def sales_path(self) -> Path:
        return self.processed_data_dir / "sales_enriched.csv"
    
    @property
    def explainability_dir(self) -> Path:
        return self.project_root / "backend" / "explainability_engine" / "output" / self.mode
    
    # ========== Data Loading ==========
    
    def load_global_queue(self) -> pd.DataFrame:
        """Load the global alert queue from JSON or parquet."""
        if 'global_queue' in self._cache:
            return self._cache['global_queue']
        
        # Try parquet first (more efficient)
        if self.global_queue_parquet_path.exists():
            df = pd.read_parquet(self.global_queue_parquet_path)
            # Parse JSON strings in columns if needed
            for col in ['source_variants', 'explanation_ids', 'source_row_keys']:
                if col in df.columns and df[col].dtype == 'object':
                    df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else x)
            # Ensure customer_id and product_id are strings for merging
            if 'customer_id' in df.columns:
                df['customer_id'] = df['customer_id'].astype(str)
            if 'product_id' in df.columns:
                df['product_id'] = df['product_id'].astype(str)
        # Fallback to JSON
        elif self.global_queue_path.exists():
            with open(self.global_queue_path, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Ensure customer_id and product_id are strings
            if 'customer_id' in df.columns:
                df['customer_id'] = df['customer_id'].astype(str)
            if 'product_id' in df.columns:
                df['product_id'] = df['product_id'].astype(str)
        else:
            # Return empty DataFrame with expected schema
            df = pd.DataFrame(columns=[
                'global_alert_id', 'customer_id', 'product_id', 'severity_label',
                'priority_label', 'global_priority_score', 'recommended_action',
                'process_on_date', 'source_engine', 'canonical_variant'
            ])
        
        self._cache['global_queue'] = df
        return df
    
    def load_clients(self) -> pd.DataFrame:
        """Load client master data."""
        if 'clients' in self._cache:
            return self._cache['clients']
        
        if self.clients_path.exists():
            df = pd.read_csv(self.clients_path)
            # Rename client_id to customer_id to match global queue
            if 'client_id' in df.columns:
                df['customer_id'] = df['client_id'].astype(str)
                df['customer_name'] = 'Cliente ' + df['customer_id']
            # Add customer_name if missing
            if 'customer_name' not in df.columns and 'customer_id' in df.columns:
                df['customer_name'] = 'Cliente ' + df['customer_id'].astype(str)
        else:
            df = pd.DataFrame(columns=['customer_id', 'customer_name', 'is_active_customer'])
        
        self._cache['clients'] = df
        return df
    
    def load_products(self) -> pd.DataFrame:
        """Load product master data."""
        if 'products' in self._cache:
            return self._cache['products']
        
        if self.products_path.exists():
            df = pd.read_csv(self.products_path)
            # Ensure product_id is string for merging
            if 'product_id' in df.columns:
                df['product_id'] = df['product_id'].astype(str)
            # Add product_name if missing
            if 'product_name' not in df.columns and 'product_id' in df.columns:
                df['product_name'] = 'Producto ' + df['product_id']
        else:
            df = pd.DataFrame(columns=['product_id', 'product_name', 'analytic_block'])
        
        self._cache['products'] = df
        return df
    
    def load_sales(self) -> pd.DataFrame:
        """Load sales history."""
        if 'sales' in self._cache:
            return self._cache['sales']
        
        if self.sales_path.exists():
            df = pd.read_csv(self.sales_path, low_memory=False)
            # Map column names to match expected schema
            if 'client_id' in df.columns:
                df['customer_id'] = df['client_id'].astype(str)
            if 'date' in df.columns:
                df['transaction_date'] = pd.to_datetime(df['date'])
            elif 'transaction_date' in df.columns:
                df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            if 'sales_value' in df.columns:
                df['revenue'] = df['sales_value']
        else:
            df = pd.DataFrame(columns=['customer_id', 'product_id', 'transaction_date', 'revenue'])
        
        self._cache['sales'] = df
        return df
    
    def load_explanations(self) -> pd.DataFrame:
        """Load explanation data."""
        if 'explanations' in self._cache:
            return self._cache['explanations']
        
        # Try to load all_explanations or combined commodity/technical
        all_explanations = self.explainability_dir / "all_explanations.parquet"
        commodity_explanations = self.explainability_dir / "commodity_explanations.parquet"
        technical_explanations = self.explainability_dir / "technical_explanations.parquet"
        
        frames = []
        for path in [all_explanations, commodity_explanations, technical_explanations]:
            if path.exists():
                frames.append(pd.read_parquet(path))
        
        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=['source_row_key', 'explanation_id', 'explanation_text', 'severity'])
        
        self._cache['explanations'] = df
        return df
    
    # ========== Transformation Methods ==========
    
    def _map_risk_level(self, severity_label: Optional[str]) -> RiskLevel:
        """Map severity labels to risk levels."""
        if not severity_label:
            return 'low'
        severity_lower = str(severity_label).lower()
        if 'critical' in severity_lower or 'critico' in severity_lower:
            return 'critical'
        elif 'high' in severity_lower or 'alto' in severity_lower:
            return 'high'
        elif 'medium' in severity_lower or 'medio' in severity_lower:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_inactivity_days(self, customer_id: str, sales_df: pd.DataFrame) -> int:
        """Calculate days since last order for a customer."""
        customer_sales = sales_df[sales_df['customer_id'] == customer_id]
        if customer_sales.empty or 'transaction_date' not in customer_sales.columns:
            return 365  # Default high value
        
        last_date = customer_sales['transaction_date'].max()
        if pd.isna(last_date):
            return 365
        
        today = pd.Timestamp.now()
        return (today - last_date).days
    
    def _calculate_potential_revenue(self, customer_id: str, sales_df: pd.DataFrame) -> float:
        """Estimate potential revenue based on historical patterns."""
        customer_sales = sales_df[sales_df['customer_id'] == customer_id]
        if customer_sales.empty or 'revenue' not in customer_sales.columns:
            return 0.0
        
        # Use 90-day average * 4 quarters as annual potential
        last_90_days = customer_sales[
            customer_sales['transaction_date'] >= (pd.Timestamp.now() - pd.Timedelta(days=90))
        ]
        if not last_90_days.empty:
            avg_90d = last_90_days['revenue'].mean()
            return avg_90d * 4
        
        # Fallback to historical average
        return customer_sales['revenue'].mean() * 12
    
    def _build_timeline(self, customer_id: str, product_id: str, sales_df: pd.DataFrame) -> list[TimelineDataPoint]:
        """Build sales timeline for a customer-product combination."""
        # Filter relevant sales
        mask = (sales_df['customer_id'] == customer_id) & (sales_df['product_id'] == product_id)
        relevant_sales = sales_df[mask].copy()
        
        if relevant_sales.empty:
            return []
        
        # Group by month
        relevant_sales['month'] = relevant_sales['transaction_date'].dt.to_period('M')
        monthly = relevant_sales.groupby('month').agg({
            'revenue': 'sum'
        }).reset_index()
        
        # Calculate rolling 3-month average
        monthly['rolling_sales'] = monthly['revenue'].rolling(window=3, min_periods=1).mean()
        monthly['date'] = monthly['month'].dt.to_timestamp().dt.strftime('%Y-%m-%d')
        
        timeline = []
        for _, row in monthly.iterrows():
            timeline.append(TimelineDataPoint(
                date=row['date'],
                sales=float(row['revenue']),
                rollingSales=float(row['rolling_sales']),
                campaignActive=False  # TODO: Link to campaign data if available
            ))
        
        return timeline[-16:]  # Last 16 months
    
    def _build_signals(self, alert_row: dict, explanations_df: pd.DataFrame) -> list[Signal]:
        """Build signal list from alert row and explanations."""
        signals = []
        
        # Get explanations linked to this alert
        source_row_keys = alert_row.get('source_row_keys', [])
        if isinstance(source_row_keys, str):
            try:
                source_row_keys = json.loads(source_row_keys)
            except:
                source_row_keys = []
        
        for key in source_row_keys:
            matching = explanations_df[explanations_df['source_row_key'] == key]
            for _, exp_row in matching.iterrows():
                signals.append(Signal(
                    id=exp_row.get('explanation_id', f"signal-{len(signals)}"),
                    name=exp_row.get('explanation_text', 'Unknown signal')[:100],
                    severity=self._map_risk_level(exp_row.get('severity')),
                    value=float(exp_row.get('value', 0.0)) if pd.notna(exp_row.get('value')) else 0.0,
                    threshold=float(exp_row.get('threshold', 0.0)) if pd.notna(exp_row.get('threshold')) else 0.0,
                    description=exp_row.get('explanation_text', ''),
                    category='behavior'  # TODO: Derive from explanation type
                ))
        
        # If no signals from explanations, create a generic one
        if not signals:
            signals.append(Signal(
                id='signal-generic',
                name='Risk detected by ML pipeline',
                severity=self._map_risk_level(alert_row.get('severity_label')),
                value=float(alert_row.get('global_priority_score', 0.0)),
                threshold=0.5,
                description=alert_row.get('recommended_action', 'Action required'),
                category='behavior'
            ))
        
        return signals
    
    def _build_recommendations(self, alert_row: dict, risk_level: RiskLevel) -> list[Recommendation]:
        """Build recommendations based on alert data and risk level."""
        recommendations = []
        
        action_text = alert_row.get('recommended_action', '')
        
        if risk_level in ['critical', 'high']:
            recommendations.append(Recommendation(
                id='rec-1',
                type='assign',
                priority='high',
                title='Asignar representante comercial',
                description=f'{action_text}. Contactar al cliente en las próximas 24-48 horas.',
                estimatedImpact='+25% retención'
            ))
            
            recommendations.append(Recommendation(
                id='rec-2',
                type='campaign',
                priority='high',
                title='Incluir en campaña específica',
                description='Ofrecer condiciones preferenciales para reactivar la relación comercial.',
                estimatedImpact='+15% conversión'
            ))
        
        recommendations.append(Recommendation(
            id='rec-3',
            type='followup',
            priority='medium' if risk_level in ['critical', 'high'] else 'low',
            title='Programar seguimiento',
            description='Agendar revisión de progreso en 2 semanas.',
            estimatedImpact='+10% engagement'
        ))
        
        return recommendations
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid based on TTL."""
        if cache_key not in self._cache_timestamps:
            return False
        age = time.time() - self._cache_timestamps[cache_key]
        return age < self.CACHE_TTL
    
    def clear_cache(self):
        """Clear all caches (useful for manual refresh)."""
        self._cache.clear()
        self._results_cache.clear()
        self._cache_timestamps.clear()
        # Clear lru_cache on instance methods
        self._get_customer_metrics.cache_clear()
    
    @lru_cache(maxsize=1000)
    def _get_customer_metrics(self, customer_id: str) -> tuple:
        """Cache customer metrics calculations (inactivity days, potential revenue)."""
        sales_df = self.load_sales()
        
        customer_sales = sales_df[sales_df['customer_id'] == customer_id]
        if customer_sales.empty:
            return (365, 0.0)  # inactivity_days, potential_revenue
        
        # Calculate inactivity days
        if 'transaction_date' in customer_sales.columns:
            last_date = customer_sales['transaction_date'].max()
            if pd.notna(last_date):
                inactivity_days = (pd.Timestamp.now() - last_date).days
            else:
                inactivity_days = 365
        else:
            inactivity_days = 365
        
        # Calculate potential revenue
        if 'revenue' in customer_sales.columns:
            # Use 90-day average * 4 quarters as annual potential
            last_90_days = customer_sales[
                customer_sales['transaction_date'] >= (pd.Timestamp.now() - pd.Timedelta(days=90))
            ]
            if not last_90_days.empty:
                avg_90d = last_90_days['revenue'].mean()
                potential_revenue = avg_90d * 4
            else:
                potential_revenue = customer_sales['revenue'].mean() * 12
        else:
            potential_revenue = 0.0
        
        return (inactivity_days, potential_revenue)
    
    # ========== Public API Methods ==========
    
    def get_all_clinics(self) -> list[Clinic]:
        """Get all clinics with risk assessment (cached). (cached)."""
        cache_key = f'clinic_detail_{clinic_id}'
        
        # Return cached result if valid
        if self._is_cache_valid(cache_key) and cache_key in self._results_cache:
            return self._results_cache[cache_key]
        
        cache_key = 'all_clinics'
        
        # Return cached result if valid
        if self._is_cache_valid(cache_key) and cache_key in self._results_cache:
            return self._results_cache[cache_key]
        
        queue_df = self.load_global_queue()
        clients_df = self.load_clients()
        products_df = self.load_products()
        
        if queue_df.empty:
            return []
        
        # Merge with client and product data
        enriched = queue_df.merge(
            clients_df, on='customer_id', how='left'
        ).merge(
            products_df, on='product_id', how='left'
        )
        
        clinics = []
        for _, row in enriched.iterrows():
            customer_id = row['customer_id']
            
            # Get cached metrics
            inactivity_days, potential_revenue = self._get_customer_metrics(customer_id)
            
            # Map to Clinic model
            clinic = Clinic(
                id=row.get('global_alert_id', f"clinic-{customer_id}"),
                name=row.get('customer_name', f'Cliente {customer_id}'),
                clientCode=customer_id,
                productFamily=row.get('analytic_block', 'Unknown'),
                riskScore=min(1.0, max(0.0, float(row.get('global_priority_score', 0.5)))),
                priorityScore=min(1.0, max(0.0, float(row.get('global_priority_score', 0.5)))),
                riskLevel=self._map_risk_level(row.get('severity_label')),
                potentialRevenue=potential_revenue,
                lastOrderDays=inactivity_days,
                inactivityRatio=min(1.0, inactivity_days / 180.0),  # Normalize to 6 months
                recommendedAction=row.get('recommended_action', 'Review'),
                signalCount=len(json.loads(row.get('source_row_keys', '[]'))) if isinstance(row.get('source_row_keys'), str) else 1,
                status='new'
            )
            clinics.append(clinic)
        
        # Cache the results
        self._results_cache[cache_key] = clinics
        self._cache_timestamps[cache_key] = time.time(in(1.0, inactivity_days / 180.0),  # Normalize to 6 months
                recommendedAction=row.get('recommended_action', 'Review'),
                signalCount=len(json.loads(row.get('source_row_keys', '[]'))) if isinstance(row.get('source_row_keys'), str) else 1,
                status='new'
            )
            clinics.append(clinic)
        
        return clinics
    
    def get_clinic_detail(self, clinic_id: str) -> Optional[ClinicDetail]:
        """Get detailed information for a specific clinic."""
        queue_df = self.load_global_queue()
        clients_df = self.load_clients()
        products_df = self.load_products()
        sales_df = self.load_sales()
        explanations_df = self.load_explanations()
        
        # Find the alert row
        alert_row = queue_df[queue_df['global_alert_id'] == clinic_id]
        if alert_row.empty:
            # Try matching by customer_id
            customer_id = clinic_id.replace('clinic-', '')
            alert_row = queue_df[queue_df['customer_id'] == customer_id]
            if alert_row.empty:
                return None
        
        alert_row = alert_row.iloc[0].to_dict()
        customer_id = alert_row['customer_id']
        product_id = alert_row['product_id']
        
        # Get base clinic data
        client_info = clients_df[clients_df['customer_id'] == customer_id]
        product_info = products_df[products_df['product_id'] == product_id]
        
        # Build all components
        timeline = self._build_timeline(customer_id, product_id, sales_df)
        signals = self._build_signals(alert_row, explanations_df)
        risk_level = self._map_risk_level(alert_row.get('severity_label'))
        recommendations = self._build_recommendations(alert_row, risk_level)
        
        # Use cached metrics
        inactivity_days, potential_revenue = self._get_customer_metrics(customer_id
        total_purchases = len(customer_sales)
        avg_order_value = customer_sales['revenue'].mean() if not customer_sales.empty else 0.0
        last_order_date = customer_sales['transaction_date'].max() if not customer_sales.empty else pd.NaT
        
        inactivity_days = self._calculate_inactivity_days(customer_id, sales_df)
        potential_revenue = self._calculate_potential_revenue(customer_id, sales_df)
        
        clinic_detail = ClinicDetail(
            id=alert_row.get('global_alert_id', f"clinic-{customer_id}"),
            name=client_info.iloc[0]['customer_name'] if not client_info.empty else f'Cliente {customer_id}',
            clientCode=customer_id,
            productFamily=product_info.iloc[0]['analytic_block'] if not product_info.empty else 'Unknown',
            riskScore=min(1.0, max(0.0, float(alert_row.get('global_priority_score', 0.5)))),
            priorityScore=min(1.0, max(0.0, float(alert_row.get('global_priority_score', 0.5)))),
            riskLevel=risk_level,
            potentialRevenue=potential_revenue,
            lastOrderDays=inactivity_days,
            inactivityRatio=min(1.0, inactivity_days / 180.0),
            recommendedAction=alert_row.get('recommended_action', 'Review'),
            signalCount=len(signals),
            status='new',
            signals=signals,
            timeline=timeline,
            recommendations=recommendations,
            totalPurchases=total_purchases,
            avgOrderValue=float(avg_order_value),
            lastOrderDate=last_order_date.strftime('%Y-%m-%d') if pd.notna(last_order_date) else 'N/A',
            campaignResponse=0.0  # TODO: Link to campaign response data
        )
        
        # Cache the result
        # Cache the result
        self._results_cache[cache_key] = clinic_detail
        self._cache_timestamps[cache_key] = time.time()
        
        return clinic_detail
    
    def get_kpis(self) -> list[KPI]:
        """Get summary KPIs for the dashboard (cached)."""
        cache_key = 'kpis'
        
        # Return cached result if valid
        if self._is_cache_valid(cache_key) and cache_key in self._results_cache:
            return self._results_cache[cache_key]
        
        clinics = self.get_all_clinics()
        
        if not clinics:
            return [
                KPI(label='At Risk Clinics', value=0, trend='stable'),
                KPI(label='Critical Clinics', value=0, trend='stable'),
                KPI(label='Revenue at Risk', value='€0', trend='stable'),
                KPI(label='Recovered This Month', value=0, trend='stable'),
            ]
        
        critical_count = sum(1 for c in clinics if c.riskLevel == 'critical')
        high_count = sum(1 for c in clinics if c.riskLevel == 'high')
        at_risk_count = critical_count + high_count
        
        revenue_at_risk = sum(c.potentialRevenue for c in clinics if c.riskLevel in ['critical', 'high'])
        
        kpis = [
            KPI(label='At Risk Clinics', value=float(at_risk_count), change=12, trend='up'),
            KPI(label='Critical Clinics', value=critical_count, change=5, trend='up'),
            KPI(label='Revenue at Risk', value=f'€{revenue_at_risk:,.0f}', change=8, trend='up'),
            KPI(label='Recovered This Month', value=3, change=2, trend='up'),
        ]
        
        # Cache the results
        self._results_cache[cache_key] = kpis
        self._cache_timestamps[cache_key] = time.time()
        
        return kpis
    
    def get_overview_stats(self) -> OverviewStats:
        """Get overview statistics for the dashboard (cached)."""
        cache_key = 'overview_stats'
        
        # Return cached result if valid
        if self._is_cache_valid(cache_key) and cache_key in self._results_cache:
            return self._results_cache[cache_key]
        
        clinics = self.get_all_clinics()
        
        if not clinics:
            return OverviewStats(
                totalClinics=0,
                atRiskClinics=0,
                criticalClinics=0,
                highRiskClinics=0,
                totalRevenueAtRisk=0.0,
                avgRiskScore=0.0,
                avgPriorityScore=0.0
            )
        
        critical_count = sum(1 for c in clinics if c.riskLevel == 'critical')
        high_count = sum(1 for c in clinics if c.riskLevel == 'high')
        at_risk_count = critical_count + high_count
        revenue_at_risk = sum(c.potentialRevenue for c in clinics if c.riskLevel in ['critical', 'high'])
        avg_risk = sum(c.riskScore for c in clinics) / len(clinics)
        avg_priority = sum(c.priorityScore for c in clinics) / len(clinics)
        
        stats = OverviewStats(
            totalClinics=len(clinics),
            atRiskClinics=at_risk_count,
            criticalClinics=critical_count,
            highRiskClinics=high_count,
            totalRevenueAtRisk=revenue_at_risk,
            avgRiskScore=avg_risk,
            avgPriorityScore=avg_priority
        )
        
        # Cache the result
        self._results_cache[cache_key] = stats
        self._cache_timestamps[cache_key] = time.time()
        
        return stats
