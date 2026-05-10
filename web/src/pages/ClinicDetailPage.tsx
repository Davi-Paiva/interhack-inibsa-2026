import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { RiskBadge } from '../components/features/RiskBadge';
import { formatCurrency, formatDate, formatPercent } from '../utils/helpers';
import { getClinicDetail } from '../utils/api';
import type { ClinicDetail } from '../types';
import {
  ArrowLeft,
  Building2,
  TrendingDown,
  Activity,
  Target,
  AlertTriangle,
  CheckCircle2,
  Phone,
  Mail,
  Calendar,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

export function ClinicDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [clinic, setClinic] = useState<ClinicDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadClinic = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const data = await getClinicDetail(id);
        setClinic(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading clinic');
      } finally {
        setLoading(false);
      }
    };
    loadClinic();
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col h-screen">
        <Header title="Cargando..." />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-gray-500">Cargando detalles de la clínica...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-screen">
        <Header title="Error" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 mb-4">Error: {error}</p>
            <Button onClick={() => navigate('/priority-queue')}>
              Volver a Priority Queue
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!clinic) {
    return (
      <div className="flex flex-col h-screen">
        <Header title="Clínica no encontrada" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">
              No se encontró información para esta clínica
            </p>
            <Button onClick={() => navigate('/priority-queue')}>
              Volver a Priority Queue
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        title={clinic.name}
        subtitle={`${clinic.clientCode} • ${clinic.productFamily}`}
      />

      <main className="flex-1 overflow-y-auto bg-background p-6">
        {/* Back button */}
        <Button
          variant="ghost"
          className="mb-4"
          onClick={() => navigate('/priority-queue')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver a Priority Queue
        </Button>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Riesgo</CardTitle>
              <AlertTriangle className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(clinic.riskScore * 100).toFixed(0)}%
              </div>
              <div className="mt-2">
                <RiskBadge level={clinic.riskLevel} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Prioridad</CardTitle>
              <Target className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(clinic.priorityScore * 100).toFixed(0)}%
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Score de intervención
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Revenue Potencial</CardTitle>
              <TrendingDown className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(clinic.potentialRevenue)}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                En riesgo (12 meses)
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Ratio Inactividad</CardTitle>
              <Activity className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatPercent(clinic.inactivityRatio)}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {clinic.lastOrderDays} días sin pedido
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Sales Timeline */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Evolución de Ventas</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={clinic.timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => new Date(value).toLocaleDateString('es-ES', { month: 'short' })}
                  />
                  <YAxis tickFormatter={(value) => `${value / 1000}k`} />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    labelFormatter={(label) => formatDate(label)}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="sales"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.6}
                    name="Ventas"
                  />
                  <Line
                    type="monotone"
                    dataKey="rollingSales"
                    stroke="#10b981"
                    strokeWidth={2}
                    name="Media Móvil"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
              <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Compras Totales</p>
                  <p className="text-lg font-semibold">{clinic.totalPurchases}</p>
                </div>
                <div>
                  <p className="text-gray-500">Valor Medio Pedido</p>
                  <p className="text-lg font-semibold">{formatCurrency(clinic.avgOrderValue)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Último Pedido</p>
                  <p className="text-lg font-semibold">{formatDate(clinic.lastOrderDate)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Signal Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Señales de Riesgo Detectadas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {clinic.signals.map((signal) => (
                  <div
                    key={signal.id}
                    className="p-4 rounded-lg border hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium">{signal.name}</h4>
                        <p className="text-sm text-gray-500 mt-1">
                          {signal.description}
                        </p>
                      </div>
                      <RiskBadge level={signal.severity} />
                    </div>
                    <div className="flex items-center gap-4 mt-3">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>Valor</span>
                          <span>Umbral: {formatPercent(signal.threshold)}</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              signal.value >= 0.8
                                ? 'bg-red-500'
                                : signal.value >= 0.6
                                ? 'bg-orange-500'
                                : 'bg-yellow-500'
                            }`}
                            style={{ width: `${signal.value * 100}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold">{formatPercent(signal.value)}</p>
                      </div>
                    </div>
                    <div className="mt-2">
                      <Badge variant="outline" className="text-xs">
                        {signal.category}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recommended Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Acciones Recomendadas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {clinic.recommendations.map((rec) => {
                  const Icon =
                    rec.type === 'assign'
                      ? Building2
                      : rec.type === 'campaign'
                      ? Mail
                      : rec.type === 'followup'
                      ? Phone
                      : Calendar;

                  const priorityColor =
                    rec.priority === 'high'
                      ? 'border-red-200 bg-red-50'
                      : rec.priority === 'medium'
                      ? 'border-yellow-200 bg-yellow-50'
                      : 'border-blue-200 bg-blue-50';

                  return (
                    <div
                      key={rec.id}
                      className={`p-4 rounded-lg border ${priorityColor} transition-all hover:shadow-md`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg bg-white">
                          <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium">{rec.title}</h4>
                            <Badge
                              variant={
                                rec.priority === 'high'
                                  ? 'critical'
                                  : rec.priority === 'medium'
                                  ? 'medium'
                                  : 'low'
                              }
                              className="text-xs"
                            >
                              {rec.priority}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-500 mb-2">
                            {rec.description}
                          </p>
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                            <span className="text-xs font-medium text-green-700">
                              Impacto estimado: {rec.estimatedImpact}
                            </span>
                          </div>
                        </div>
                      </div>
                      <Button size="sm" className="w-full mt-3">
                        Ejecutar Acción
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Info */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Información Adicional</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-gray-500">Señales Activas</p>
                <p className="text-2xl font-bold">{clinic.signalCount}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Respuesta a Campañas</p>
                <p className="text-2xl font-bold">{formatPercent(clinic.campaignResponse)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Estado</p>
                <Badge variant={clinic.status === 'recovered' ? 'low' : 'outline'} className="mt-2">
                  {clinic.status === 'new' && 'Nuevo'}
                  {clinic.status === 'contacted' && 'Contactado'}
                  {clinic.status === 'recovered' && 'Recuperado'}
                  {clinic.status === 'lost' && 'Perdido'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">Acción Sugerida</p>
                <p className="text-sm font-medium mt-2">{clinic.recommendedAction}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
