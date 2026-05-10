import { useState, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatCurrency } from '../utils/helpers';
import { getClinics } from '../utils/api';
import type { Clinic } from '../types';
import { useNavigate } from 'react-router-dom';
import { Building2, TrendingUp } from 'lucide-react';

export function ClinicsPage() {
  const navigate = useNavigate();
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadClinics = async () => {
      try {
        setLoading(true);
        const data = await getClinics({ limit: 1000 });
        setClinics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading clinics');
      } finally {
        setLoading(false);
      }
    };
    loadClinics();
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        title="Clinics"
        subtitle="Directorio de clínicas monitoreadas"
      />

      <main className="flex-1 overflow-y-auto bg-background p-6">
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-gray-500">Cargando clínicas...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-12">
            <p className="text-red-500 mb-4">Error: {error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {clinics.map((clinic) => (
            <Card
              key={clinic.id}
              className="cursor-pointer hover:shadow-lg transition-all"
              onClick={() => navigate(`/clinics/${clinic.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{clinic.name}</CardTitle>
                      <p className="text-sm text-gray-500 mt-1">
                        {clinic.clientCode}
                      </p>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Familia</span>
                    <Badge variant="outline">{clinic.productFamily}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Riesgo</span>
                    <Badge variant={clinic.riskLevel}>
                      {(clinic.riskScore * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Revenue en Riesgo</span>
                    <span className="text-sm font-semibold">
                      {formatCurrency(clinic.potentialRevenue)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t">
                    <span className="text-xs text-gray-500">
                      {clinic.lastOrderDays} días sin pedido
                    </span>
                    <span className="text-xs text-gray-500">
                      {clinic.signalCount} señales
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        )}
      </main>
    </div>
  );
}
