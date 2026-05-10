import { useState, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { KPICard } from '../components/features/KPICard';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatCurrency } from '../utils/helpers';
import { getClinics, getKPIs } from '../utils/api';
import type { Clinic, KPI } from '../types';
import { 
  AlertCircle, 
  TrendingUp, 
  DollarSign, 
  Users,
  Package,
  CheckCircle
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function OverviewPage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [kpis, setKPIs] = useState<KPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [clinicsData, kpisData] = await Promise.all([
          getClinics({ limit: 1000 }),
          getKPIs()
        ]);
        setClinics(clinicsData);
        setKPIs(kpisData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading data');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col h-screen overflow-hidden">
        <Header title="Overview" subtitle="Vista general del estado comercial" />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-gray-500">Cargando datos...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-screen overflow-hidden">
        <Header title="Overview" subtitle="Vista general del estado comercial" />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 mb-4">Error: {error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
            >
              Reintentar
            </button>
          </div>
        </main>
      </div>
    );
  }

  // Product family breakdown
  const productFamilyData = clinics.reduce((acc, clinic) => {
    const existing = acc.find(item => item.name === clinic.productFamily);
    if (existing) {
      existing.count++;
      existing.revenue += clinic.potentialRevenue;
    } else {
      acc.push({
        name: clinic.productFamily,
        count: 1,
        revenue: clinic.potentialRevenue,
      });
    }
    return acc;
  }, [] as Array<{ name: string; count: number; revenue: number }>);

  // Top 5 critical clinics
  const topCriticalClinics = clinics
    .filter(c => c.riskLevel === 'critical' || c.riskLevel === 'high')
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 5);

  // Extract KPI values
  const kpiAtRisk = kpis.find(k => k.label === 'At Risk Clinics');
  const kpiCritical = kpis.find(k => k.label === 'Critical Clinics');
  const kpiRevenue = kpis.find(k => k.label === 'Revenue at Risk');
  const kpiRecovered = kpis.find(k => k.label === 'Recovered This Month');

  const totalAtRisk = typeof kpiAtRisk?.value === 'number' ? kpiAtRisk.value : 0;
  const criticalClinics = typeof kpiCritical?.value === 'number' ? kpiCritical.value : 0;
  const recoveredLastMonth = typeof kpiRecovered?.value === 'number' ? kpiRecovered.value : 0;
  const avgRiskScore = clinics.length > 0 ? clinics.reduce((sum, c) => sum + c.riskScore, 0) / clinics.length : 0;
  const activeInterventions = clinics.filter(c => c.status === 'contacted').length;

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header 
        title="Overview" 
        subtitle="Vista general del estado comercial"
      />
      
      <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
        {/* KPIs */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          <KPICard
            title="Clínicas en Riesgo"
            value={totalAtRisk}
            icon={<AlertCircle className="h-4 w-4" />}
            trend={kpiAtRisk?.trend || 'up'}
            change={kpiAtRisk?.change || 0}
          />
          <KPICard
            title="Riesgo Crítico"
            value={criticalClinics}
            icon={<AlertCircle className="h-4 w-4 text-red-600" />}
            trend={kpiCritical?.trend || 'up'}
            change={kpiCritical?.change || 0}
          />
          <KPICard
            title="Revenue en Riesgo"
            value={kpiRevenue?.value || '€0'}
            icon={<DollarSign className="h-4 w-4" />}
            trend={kpiRevenue?.trend || 'up'}
            change={kpiRevenue?.change || 0}
          />
          <KPICard
            title="Recuperadas (30d)"
            value={recoveredLastMonth}
            icon={<CheckCircle className="h-4 w-4 text-green-600" />}
            trend={kpiRecovered?.trend || 'down'}
            change={kpiRecovered?.change || 0}
          />
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Top Critical Clinics */}
          <Card>
            <CardHeader>
              <CardTitle>Clínicas de Mayor Prioridad</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topCriticalClinics.map((clinic) => (
                  <div
                    key={clinic.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{clinic.name}</p>
                      <p className="text-sm text-gray-500">
                        {clinic.productFamily} • {clinic.lastOrderDays} días sin pedido
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right mr-2">
                        <p className="text-sm font-semibold text-gray-900">{formatCurrency(clinic.potentialRevenue)}</p>
                        <p className="text-xs text-gray-500">
                          Riesgo: {(clinic.riskScore * 100).toFixed(0)}%
                        </p>
                      </div>
                      <Badge variant={clinic.riskLevel}>
                        {clinic.riskLevel === 'critical' ? 'Crítico' : 'Alto'}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Product Family Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Distribución por Familia de Producto</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={productFamilyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value: number) => formatCurrency(value)}
                    labelStyle={{ color: '#000' }}
                  />
                  <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {productFamilyData.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">{item.name}</span>
                    <span className="font-medium text-gray-900">{item.count} clínicas</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Stats */}
        <div className="grid gap-4 md:grid-cols-3 mt-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Promedio de Riesgo
              </CardTitle>
                <TrendingUp className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {(avgRiskScore * 100).toFixed(1)}%
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Puntuación media de riesgo
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Intervenciones Activas
              </CardTitle>
                <Users className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {activeInterventions}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Casos en seguimiento comercial
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Familias de Producto
              </CardTitle>
                <Package className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {productFamilyData.length}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Líneas con riesgo detectado
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
