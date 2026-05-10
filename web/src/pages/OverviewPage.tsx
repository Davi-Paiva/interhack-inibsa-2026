import type { ReactNode } from 'react';
import {
  ArrowDown,
  BellRing,
  BrainCircuit,
  CheckCircle2,
  Database,
  GitBranch,
  Layers3,
  LineChart,
  Network,
  RefreshCcw,
  ScanSearch,
  ShieldAlert,
  Sparkles,
  Target,
  Users,
  Workflow,
} from 'lucide-react';
import { Header } from '../components/layout/Header';
import { KPICard } from '../components/features/KPICard';
import { Badge } from '../components/ui/Badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/Card';
import { cn } from '../utils/helpers';

type Tone = 'blue' | 'emerald' | 'amber' | 'rose' | 'slate';

const toneStyles: Record<Tone, string> = {
  blue: 'border-blue-200 bg-blue-50 text-blue-700',
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  amber: 'border-amber-200 bg-amber-50 text-amber-700',
  rose: 'border-rose-200 bg-rose-50 text-rose-700',
  slate: 'border-slate-200 bg-slate-50 text-slate-700',
};

const heroPills = [
  '2 motores analíticos',
  'Alertas explicables',
  'Priorización global',
];

const topMetrics = [
  {
    title: 'Capas del sistema',
    value: '7',
    icon: <Layers3 className="h-4 w-4" />,
  },
  {
    title: 'Forecast comercial',
    value: 'RMSE 156.8',
    icon: <LineChart className="h-4 w-4" />,
  },
  {
    title: 'Riesgo técnico',
    value: 'AUC 0.619',
    icon: <ShieldAlert className="h-4 w-4" />,
  },
  {
    title: 'Tipos de alerta',
    value: '5',
    icon: <BellRing className="h-4 w-4" />,
  },
];

const navItems = [
  { href: '#arquitectura', label: 'Arquitectura' },
  { href: '#datos', label: 'Datos' },
  { href: '#comercial', label: 'Comercial' },
  { href: '#tecnico', label: 'Técnico' },
  { href: '#alertas', label: 'Alertas' },
  { href: '#explicabilidad', label: 'Explicabilidad' },
  { href: '#mejora', label: 'Mejora continua' },
];

const cleaningItems = [
  'Normalización de IDs, texto, fechas y números.',
  'Enriquecimiento de ventas con campañas, devoluciones y calendario.',
  'Outliers por IQR y eliminación de anomalías fuera de campaña.',
  'Métricas de calidad y drift entre histórico y daily.',
];

const featureItems = [
  'Cliente: revenue, pedidos, ticket, frecuencia, recencia y estabilidad.',
  'Producto: rolling sales 30d, growth, returns y customer count.',
  'Cliente-producto: growth 30d, recencia, frecuencia y campaign lift.',
  'Embeddings SVD: útiles en técnico, descartados en forecast comercial.',
];

const removedFeatures = [
  'client_features: first/last_order_date, return_orders_30d, orders_30d',
  'product_features: product_total_orders, current_sales_30d, previous_sales_30d',
  'client_product_features: first/last_order_date, current_sales_30d, previous_sales_30d',
];

const commercialRows: ReactNode[][] = [
  [
    'Segmentación',
    'KMeans',
    'Diferencia clientes leales, promiscuos y marginales.',
  ],
  [
    'Forecast 30 días',
    'LightGBM',
    'Predice demanda futura por cliente-producto.',
  ],
  [
    'Leakage + captura',
    'Scoring',
    'Detecta caída de consumo y prioriza oportunidad comercial.',
  ],
  [
    'Siguiente compra',
    'Timing + probabilidad',
    'Propone ventana de contacto accionable.',
  ],
];

const segmentCards = [
  {
    title: 'Leales',
    share: '12.8%',
    variant: 'high' as const,
    text: 'Pocos, muy activos y con alto valor.',
  },
  {
    title: 'Promiscuos',
    share: '65.6%',
    variant: 'medium' as const,
    text: 'La mayoría; actividad intermedia y más sensibles al churn.',
  },
  {
    title: 'Marginales',
    share: '21.6%',
    variant: 'low' as const,
    text: 'Bajo valor, baja frecuencia y alta recencia.',
  },
];

const commercialMetrics: ReactNode[][] = [
  [
    'Clustering',
    'Silhouette 0.330',
    'Separación suficiente para negocio.',
  ],
  [
    'Forecast',
    'RMSE 156.8 vs 502.6 baseline',
    'Mejora fuerte frente al enfoque naive.',
  ],
  [
    'Leakage',
    'Precision@1% 42.4%',
    'Prioriza mejor que el scoring actual.',
  ],
  [
    'Siguiente compra',
    'Within 30d: 89.8%',
    'Muy útil para decidir cuándo contactar.',
  ],
];

const technicalRows: ReactNode[][] = [
  [
    'Ciclo esperado',
    'Heurística',
    'Estima cuándo debería recomprar esa relación.',
  ],
  [
    'Volume drift',
    'Reglas',
    'Detecta caída reciente de volumen.',
  ],
  [
    'Interval drift',
    'Ratio de inactividad',
    'Detecta alargamiento del ciclo de compra.',
  ],
  [
    'Peer drift',
    'Comparación con pares',
    'Compara contra clientes similares.',
  ],
  [
    'Risk scoring',
    'Scorer ponderado',
    'Combina señales y ajusta prioridad con gap de negocio.',
  ],
];

const technicalMetrics: ReactNode[][] = [
  [
    'Modelo seleccionado',
    'AUC 0.6191',
    'Peer weighting con embeddings, ligera mejora sobre baseline.',
  ],
  [
    'Top 5%',
    'Precision 0.7300',
    'Buena capacidad para priorizar relaciones más sensibles.',
  ],
  [
    'Cobertura',
    '10,939 relaciones',
    'Análisis masivo sobre histórico técnico.',
  ],
];

const alertRows: ReactNode[][] = [
  [
    'Leakage comercial',
    'Caída frente a demanda esperada.',
    'Equipo comercial.',
  ],
  [
    'Oportunidad de captura',
    'Score, prioridad y valor del cliente.',
    'KAM / inside sales.',
  ],
  [
    'Siguiente compra',
    'Probabilidad y ventana de contacto.',
    'Delegado comercial.',
  ],
  [
    'Riesgo técnico',
    'Inactividad, drift y gap potencial.',
    'Equipo técnico-comercial.',
  ],
  [
    'Cola global',
    'Score final, fecha y recomendación.',
    'Coordinación operativa.',
  ],
];

const explainabilityItems = [
  'Explica por qué salta una alerta.',
  'Muestra factores, métricas y trazabilidad.',
  'No recalcula el modelo: interpreta el output ya generado.',
  'Alimenta frontend, negocio y priorización global.',
];

const improvementRows: ReactNode[][] = [
  [
    'Feedback de alertas',
    'Validez, acción, resultado y causa raíz.',
    'Reducir falsos positivos y ajustar prioridad.',
  ],
  [
    'Reentrenamiento',
    'Offline y con comparación contra baseline.',
    'Solo se acepta si mejora métricas reales.',
  ],
  [
    'Future work',
    'Refinar cluster promiscuo y mejores labels.',
    'Más precisión y mejor semántica de negocio.',
  ],
];

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-6 space-y-4">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
        <p className="max-w-4xl text-sm leading-6 text-gray-600">{description}</p>
      </div>
      {children}
    </section>
  );
}

function Pill({ children, tone = 'slate' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium',
        toneStyles[tone]
      )}
    >
      {children}
    </span>
  );
}

function DiagramNode({
  title,
  description,
  icon,
  tone = 'slate',
}: {
  title: string;
  description: string;
  icon: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className={cn('rounded-xl border p-2', toneStyles[tone])}>{icon}</div>
        <div className="space-y-1">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <p className="text-sm leading-6 text-gray-600">{description}</p>
        </div>
      </div>
    </div>
  );
}

function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: ReactNode[][];
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-4 py-3 text-left font-semibold text-gray-700">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`} className="align-top">
              {row.map((cell, cellIndex) => (
                <td key={`cell-${rowIndex}-${cellIndex}`} className="px-4 py-3 text-gray-600">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OverviewPage() {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Header
        title="Resumen"
        subtitle="Visión rápida del backend para una demo de 2 minutos"
      />

      <main className="flex-1 overflow-y-auto bg-gray-50">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
          <Card className="overflow-hidden border-blue-200 bg-gradient-to-br from-white via-blue-50 to-white">
            <CardContent className="p-6">
              <div className="grid gap-6 lg:grid-cols-[1.5fr_0.85fr]">
                <div className="space-y-5">
                  <div className="flex flex-wrap gap-2">
                    {heroPills.map((pill, index) => (
                      <Pill
                        key={pill}
                        tone={index === 0 ? 'blue' : index === 1 ? 'emerald' : 'amber'}
                      >
                        {pill}
                      </Pill>
                    ))}
                  </div>

                  <div className="space-y-2">
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                      Convertimos datos comerciales en alertas accionables y explicables
                    </h1>
                    <p className="max-w-3xl text-sm leading-7 text-gray-600">
                      El sistema limpia datos, genera features, ejecuta un motor comercial y un
                      motor técnico, explica cada alerta y consolida una cola global priorizada.
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {navItems.map((item) => (
                      <a
                        key={item.href}
                        href={item.href}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-blue-200 hover:text-blue-700"
                      >
                        {item.label}
                      </a>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    Idea clave
                  </div>
                  <div className="space-y-3 text-sm leading-6 text-gray-600">
                    <p>Unificamos predicción, riesgo y oportunidad en una sola cola.</p>
                    <p>Los embeddings se evaluaron: útiles en técnico, no en forecast comercial.</p>
                    <p>La explicabilidad hace que cada alerta sea interpretable y accionable.</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {topMetrics.map((metric) => (
              <KPICard
                key={metric.title}
                title={metric.title}
                value={metric.value}
                icon={metric.icon}
              />
            ))}
          </div>

          <Section
            id="arquitectura"
            title="Arquitectura"
            description="Pipeline end-to-end desde CSV raw hasta cola global priorizada."
          >
            <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Pipeline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-2xl border border-gray-200 bg-gray-50 p-5">
                    <div className="flex flex-col gap-3">
                      <DiagramNode
                        title="Datos raw"
                        description="Sales, clients, products, campaigns y potential."
                        icon={<Database className="h-5 w-5" />}
                      />
                      <div className="flex justify-center text-gray-400">
                        <ArrowDown className="h-5 w-5" />
                      </div>
                      <DiagramNode
                        title="Data processing"
                        description="Limpieza, validación y enriquecimiento."
                        icon={<ScanSearch className="h-5 w-5" />}
                        tone="blue"
                      />
                      <div className="flex justify-center text-gray-400">
                        <ArrowDown className="h-5 w-5" />
                      </div>
                      <DiagramNode
                        title="Feature engineering"
                        description="Features cliente, producto y cliente-producto."
                        icon={<Sparkles className="h-5 w-5" />}
                        tone="emerald"
                      />
                      <div className="flex justify-center text-gray-400">
                        <GitBranch className="h-5 w-5" />
                      </div>
                      <div className="grid gap-4 md:grid-cols-2">
                        <DiagramNode
                          title="Motor comercial"
                          description="Segmentación, forecast, leakage y captura."
                          icon={<LineChart className="h-5 w-5" />}
                          tone="amber"
                        />
                        <DiagramNode
                          title="Motor técnico"
                          description="Inactividad, drift y riesgo de abandono."
                          icon={<ShieldAlert className="h-5 w-5" />}
                          tone="rose"
                        />
                      </div>
                      <div className="flex justify-center text-gray-400">
                        <Workflow className="h-5 w-5" />
                      </div>
                      <DiagramNode
                        title="Explicabilidad + cola global"
                        description="Razones, score final, fecha y recomendación."
                        icon={<Network className="h-5 w-5" />}
                        tone="emerald"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Qué entrega cada capa</CardTitle>
                </CardHeader>
                <CardContent>
                  <DataTable
                    columns={['Capa', 'Output']}
                    rows={[
                      ['Data processing', 'sales_enriched + tablas limpias'],
                      ['Feature engineering', 'clients, products, client_product_features'],
                      ['Motor comercial', 'forecast, leakage, captura, next purchase'],
                      ['Motor técnico', 'technical_risk_assessments'],
                      ['Explicabilidad', 'explanations en JSON y parquet'],
                      ['Cola global', 'ranking final y recomendación'],
                    ]}
                  />
                </CardContent>
              </Card>
            </div>
          </Section>

          <Section
            id="datos"
            title="Procesamiento de datos"
            description="Qué hacemos antes de modelar."
          >
            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-1">
                <CardHeader>
                  <CardTitle className="text-xl">Cleaning</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {cleaningItems.map((item) => (
                    <div
                      key={item}
                      className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600"
                    >
                      {item}
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="lg:col-span-1">
                <CardHeader>
                  <CardTitle className="text-xl">Feature engineering</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {featureItems.map((item) => (
                    <div
                      key={item}
                      className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600"
                    >
                      {item}
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="lg:col-span-1">
                <CardHeader>
                  <CardTitle className="text-xl">Features no aplicadas</CardTitle>
                  <CardDescription>
                    Variables intermedias que no forman parte del contrato final.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {removedFeatures.map((item) => (
                    <div
                      key={item}
                      className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600"
                    >
                      {item}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </Section>

          <Section
            id="comercial"
            title="Módulo comercial"
            description="Predice demanda, detecta pérdidas de consumo y propone la mejor acción comercial."
          >
            <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Modelos utilizados</CardTitle>
                </CardHeader>
                <CardContent>
                  <DataTable columns={['Bloque', 'Modelo', 'Rol']} rows={commercialRows} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Tipos de cliente</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {segmentCards.map((segment) => (
                    <div key={segment.title} className="rounded-2xl border border-gray-200 p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">{segment.title}</h3>
                        <Badge variant={segment.variant}>{segment.share}</Badge>
                      </div>
                      <p className="text-sm leading-6 text-gray-600">{segment.text}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Métricas clave</CardTitle>
              </CardHeader>
              <CardContent>
                <DataTable
                  columns={['Componente', 'Métrica', 'Lectura']}
                  rows={commercialMetrics}
                />
              </CardContent>
            </Card>
          </Section>

          <Section
            id="tecnico"
            title="Módulo técnico"
            description="Detecta relaciones cliente-producto en riesgo antes de que se conviertan en abandono real."
          >
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Modelos utilizados</CardTitle>
                </CardHeader>
                <CardContent>
                  <DataTable columns={['Bloque', 'Tipo', 'Rol']} rows={technicalRows} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Métricas clave</CardTitle>
                </CardHeader>
                <CardContent>
                  <DataTable
                    columns={['Bloque', 'Métrica', 'Lectura']}
                    rows={technicalMetrics}
                  />
                </CardContent>
              </Card>
            </div>
          </Section>

          <Section
            id="alertas"
            title="Alertas y cola global"
            description="Los dos motores desembocan en una sola cola priorizada para negocio."
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-xl">Tipos de alerta</CardTitle>
              </CardHeader>
              <CardContent>
                <DataTable
                  columns={['Alerta', 'Qué informa', 'Destinatario']}
                  rows={alertRows}
                />
              </CardContent>
            </Card>
          </Section>

          <Section
            id="explicabilidad"
            title="Explicabilidad"
            description="Convertimos un score en una explicación útil para negocio."
          >
            <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Cómo funciona</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <DiagramNode
                    title="Lee outputs"
                    description="Consume los artefactos de ambos motores."
                    icon={<Database className="h-5 w-5" />}
                  />
                  <DiagramNode
                    title="Genera explicación"
                    description="Resume por qué salta la alerta."
                    icon={<BrainCircuit className="h-5 w-5" />}
                    tone="blue"
                  />
                  <DiagramNode
                    title="Añade trazabilidad"
                    description="Factores, métricas y decision trace."
                    icon={<Target className="h-5 w-5" />}
                    tone="emerald"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Qué aporta</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {explainabilityItems.map((item) => (
                    <div
                      key={item}
                      className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600"
                    >
                      {item}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </Section>

          <Section
            id="mejora"
            title="Mejora continua"
            description="Cerramos el loop con feedback de alertas y futuras iteraciones."
          >
            <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Bucle de aprendizaje</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <DiagramNode
                    title="Alerta"
                    description="Llega con score y recomendación."
                    icon={<BellRing className="h-5 w-5" />}
                    tone="blue"
                  />
                  <div className="flex justify-center text-gray-400">
                    <ArrowDown className="h-5 w-5" />
                  </div>
                  <DiagramNode
                    title="Feedback"
                    description="Validez, acción, outcome y causa raíz."
                    icon={<Users className="h-5 w-5" />}
                    tone="emerald"
                  />
                  <div className="flex justify-center text-gray-400">
                    <ArrowDown className="h-5 w-5" />
                  </div>
                  <DiagramNode
                    title="Reentrenamiento"
                    description="Solo si mejora frente al baseline."
                    icon={<RefreshCcw className="h-5 w-5" />}
                    tone="amber"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">Siguientes pasos</CardTitle>
                </CardHeader>
                <CardContent>
                  <DataTable
                    columns={['Palanca', 'Qué hacemos', 'Impacto esperado']}
                    rows={improvementRows}
                  />
                </CardContent>
              </Card>
            </div>
          </Section>
        </div>
      </main>
    </div>
  );
}
