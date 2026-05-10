import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { RiskBadge } from '../components/features/RiskBadge';
import { formatCurrency } from '../utils/helpers';
import { getClinics } from '../utils/api';
import { ArrowUpDown, Filter, ChevronRight } from 'lucide-react';
import type { Clinic, RiskLevel } from '../types';

type SortField = 'name' | 'riskScore' | 'priorityScore' | 'potentialRevenue' | 'lastOrderDays';
type SortDirection = 'asc' | 'desc';

export function PriorityQueuePage() {
  const navigate = useNavigate();
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('priorityScore');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

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

  // Filter and sort logic
  const filteredAndSortedClinics = clinics
    .filter(clinic => {
      const matchesSearch = clinic.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           clinic.clientCode.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesRisk = riskFilter === 'all' || clinic.riskLevel === riskFilter;
      return matchesSearch && matchesRisk;
    })
    .sort((a, b) => {
      const multiplier = sortDirection === 'asc' ? 1 : -1;
      if (sortField === 'name') {
        return multiplier * a.name.localeCompare(b.name);
      }
      return multiplier * ((a[sortField] as number) - (b[sortField] as number));
    });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => (
    <ArrowUpDown
      className={`h-4 w-4 inline ml-1 ${
        sortField === field ? 'text-primary' : 'text-gray-500'
      }`}
    />
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        title="Priority Queue"
        subtitle="Cola de priorización comercial"
      />

      <main className="flex-1 overflow-y-auto bg-gray-50 p-6">
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-gray-500">Cargando clínicas...</p>
          </div>
        )}

        {error && (
          <Card className="mb-6 p-4 bg-red-50 border-red-200">
            <p className="text-red-700">Error: {error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Reintentar
            </button>
          </Card>
        )}

        {!loading && !error && (
          <>
        {/* Filters */}
        <Card className="mb-6 p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Input
                type="search"
                placeholder="Buscar por nombre o código de cliente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium">Nivel de Riesgo:</span>
              <div className="flex gap-2">
                <Button
                  variant={riskFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRiskFilter('all')}
                >
                  Todos
                </Button>
                <Button
                  variant={riskFilter === 'critical' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRiskFilter('critical')}
                >
                  Crítico
                </Button>
                <Button
                  variant={riskFilter === 'high' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRiskFilter('high')}
                >
                  Alto
                </Button>
                <Button
                  variant={riskFilter === 'medium' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setRiskFilter('medium')}
                >
                  Medio
                </Button>
              </div>
            </div>
          </div>
        </Card>

        {/* Results count */}
        <div className="mb-4 text-sm text-gray-500">
          Mostrando {filteredAndSortedClinics.length} de {clinics.length} clínicas
        </div>

        {/* Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th
                    className="p-4 text-left text-sm font-medium cursor-pointer hover:bg-gray-200"
                    onClick={() => handleSort('name')}
                  >
                    Clínica
                    <SortIcon field="name" />
                  </th>
                  <th className="p-4 text-left text-sm font-medium">
                    Familia de Producto
                  </th>
                  <th
                    className="p-4 text-left text-sm font-medium cursor-pointer hover:bg-gray-200"
                    onClick={() => handleSort('potentialRevenue')}
                  >
                    Revenue Potencial
                    <SortIcon field="potentialRevenue" />
                  </th>
                  <th
                    className="p-4 text-left text-sm font-medium cursor-pointer hover:bg-gray-200"
                    onClick={() => handleSort('lastOrderDays')}
                  >
                    Último Pedido
                    <SortIcon field="lastOrderDays" />
                  </th>
                  <th className="p-4 text-left text-sm font-medium">
                    Acción Recomendada
                  </th>
                  <th className="p-4 text-left text-sm font-medium">
                    Nivel
                  </th>
                  <th className="p-4"></th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedClinics.map((clinic) => (
                  <tr
                    key={clinic.id}
                    className="border-b hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/clinics/${clinic.id}`)}
                  >
                    <td className="p-4">
                      <div>
                        <p className="font-medium text-gray-900">{clinic.name}</p>
                        <p className="text-sm text-gray-500">{clinic.clientCode}</p>
                      </div>
                    </td>
                    <td className="p-4">
                      <Badge variant="outline">{clinic.productFamily}</Badge>
                    </td>
                    <td className="p-4 font-medium">
                      {formatCurrency(clinic.potentialRevenue)}
                    </td>
                    <td className="p-4">
                      <span className="text-sm">{clinic.lastOrderDays} días</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-gray-600">
                        {clinic.recommendedAction}
                      </span>
                    </td>
                    <td className="p-4">
                      <RiskBadge level={clinic.riskLevel} />
                    </td>
                    <td className="p-4">
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {filteredAndSortedClinics.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No se encontraron clínicas con los filtros aplicados
          </div>
        )}
        </>
        )}
      </main>
    </div>
  );
}
