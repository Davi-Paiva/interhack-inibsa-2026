import type { Clinic, ClinicDetail, Signal, TimelineDataPoint, Recommendation } from '../types';

// Generate timeline data
const generateTimeline = (clinicId: string): TimelineDataPoint[] => {
  const data: TimelineDataPoint[] = [];
  const startDate = new Date('2024-01-01');
  
  for (let i = 0; i < 16; i++) {
    const date = new Date(startDate);
    date.setMonth(startDate.getMonth() + i);
    
    // Simulate declining sales for high-risk clinics
    const baselineSales = clinicId.includes('high') ? 15000 : 25000;
    const decline = clinicId.includes('high') ? i * 1200 : i * 300;
    const variation = Math.random() * 3000;
    
    data.push({
      date: date.toISOString().split('T')[0],
      sales: Math.max(0, baselineSales - decline + variation),
      rollingSales: Math.max(0, baselineSales - decline * 0.7),
      campaignActive: i === 6 || i === 12
    });
  }
  
  return data;
};

// Mock clinics data
export const mockClinics: Clinic[] = [
  {
    id: 'clinic-001',
    name: 'Clínica Dental San Rafael',
    clientCode: 'CLI-001',
    productFamily: 'Implantología',
    riskScore: 0.89,
    priorityScore: 0.92,
    riskLevel: 'critical',
    potentialRevenue: 45000,
    lastOrderDays: 87,
    inactivityRatio: 0.76,
    recommendedAction: 'Intervención urgente',
    signalCount: 8,
    status: 'new'
  },
  {
    id: 'clinic-002',
    name: 'Centro Odontológico Mediterráneo',
    clientCode: 'CLI-002',
    productFamily: 'Ortodoncia',
    riskScore: 0.84,
    priorityScore: 0.88,
    riskLevel: 'critical',
    potentialRevenue: 38000,
    lastOrderDays: 72,
    inactivityRatio: 0.68,
    recommendedAction: 'Contacto comercial inmediato',
    signalCount: 7,
    status: 'contacted'
  },
  {
    id: 'clinic-003',
    name: 'Dental Care Barcelona',
    clientCode: 'CLI-003',
    productFamily: 'Implantología',
    riskScore: 0.78,
    priorityScore: 0.81,
    riskLevel: 'high',
    potentialRevenue: 52000,
    lastOrderDays: 64,
    inactivityRatio: 0.54,
    recommendedAction: 'Seguimiento activo',
    signalCount: 6,
    status: 'new'
  },
  {
    id: 'clinic-004',
    name: 'Clínica Dra. Martínez',
    clientCode: 'CLI-004',
    productFamily: 'Prótesis',
    riskScore: 0.72,
    priorityScore: 0.75,
    riskLevel: 'high',
    potentialRevenue: 29000,
    lastOrderDays: 58,
    inactivityRatio: 0.61,
    recommendedAction: 'Propuesta alternativa',
    signalCount: 5,
    status: 'new'
  },
  {
    id: 'clinic-005',
    name: 'Odontología Integral Madrid',
    clientCode: 'CLI-005',
    productFamily: 'Implantología',
    riskScore: 0.68,
    priorityScore: 0.72,
    riskLevel: 'high',
    potentialRevenue: 41000,
    lastOrderDays: 51,
    inactivityRatio: 0.48,
    recommendedAction: 'Campaña específica',
    signalCount: 5,
    status: 'contacted'
  },
  {
    id: 'clinic-006',
    name: 'Clínica Dental Salud',
    clientCode: 'CLI-006',
    productFamily: 'Ortodoncia',
    riskScore: 0.61,
    priorityScore: 0.64,
    riskLevel: 'medium',
    potentialRevenue: 22000,
    lastOrderDays: 45,
    inactivityRatio: 0.42,
    recommendedAction: 'Monitoreo continuo',
    signalCount: 4,
    status: 'new'
  },
  {
    id: 'clinic-007',
    name: 'Centro de Implantes Valencia',
    clientCode: 'CLI-007',
    productFamily: 'Implantología',
    riskScore: 0.58,
    priorityScore: 0.61,
    riskLevel: 'medium',
    potentialRevenue: 35000,
    lastOrderDays: 42,
    inactivityRatio: 0.39,
    recommendedAction: 'Revisión comercial',
    signalCount: 4,
    status: 'new'
  },
  {
    id: 'clinic-008',
    name: 'Dental Pro Sevilla',
    clientCode: 'CLI-008',
    productFamily: 'Prótesis',
    riskScore: 0.54,
    priorityScore: 0.57,
    riskLevel: 'medium',
    potentialRevenue: 27000,
    lastOrderDays: 38,
    inactivityRatio: 0.36,
    recommendedAction: 'Contacto preventivo',
    signalCount: 3,
    status: 'recovered'
  },
  {
    id: 'clinic-009',
    name: 'Clínica Dental Sonrisa',
    clientCode: 'CLI-009',
    productFamily: 'Implantología',
    riskScore: 0.48,
    priorityScore: 0.51,
    riskLevel: 'medium',
    potentialRevenue: 31000,
    lastOrderDays: 34,
    inactivityRatio: 0.31,
    recommendedAction: 'Seguimiento estándar',
    signalCount: 3,
    status: 'new'
  },
  {
    id: 'clinic-010',
    name: 'Odonto Center',
    clientCode: 'CLI-010',
    productFamily: 'Ortodoncia',
    riskScore: 0.42,
    priorityScore: 0.45,
    riskLevel: 'low',
    potentialRevenue: 18000,
    lastOrderDays: 28,
    inactivityRatio: 0.25,
    recommendedAction: 'Mantener relación',
    signalCount: 2,
    status: 'new'
  },
  {
    id: 'clinic-011',
    name: 'Dental Excellence',
    clientCode: 'CLI-011',
    productFamily: 'Implantología',
    riskScore: 0.86,
    priorityScore: 0.90,
    riskLevel: 'critical',
    potentialRevenue: 48000,
    lastOrderDays: 94,
    inactivityRatio: 0.71,
    recommendedAction: 'Intervención urgente',
    signalCount: 7,
    status: 'new'
  },
  {
    id: 'clinic-012',
    name: 'Clínica Ortodoncia Plus',
    clientCode: 'CLI-012',
    productFamily: 'Ortodoncia',
    riskScore: 0.74,
    priorityScore: 0.78,
    riskLevel: 'high',
    potentialRevenue: 33000,
    lastOrderDays: 61,
    inactivityRatio: 0.58,
    recommendedAction: 'Reunión comercial',
    signalCount: 6,
    status: 'contacted'
  }
];

// Mock signals
const createSignals = (riskLevel: string): Signal[] => {
  const baseSignals: Signal[] = [
    {
      id: 'sig-001',
      name: 'Deriva por Inactividad',
      severity: riskLevel === 'critical' || riskLevel === 'high' ? 'high' : 'medium',
      value: riskLevel === 'critical' ? 0.82 : 0.65,
      threshold: 0.60,
      description: 'Tiempo sin actividad significativamente superior al promedio histórico',
      category: 'inactivity'
    },
    {
      id: 'sig-002',
      name: 'Desviación vs Pares',
      severity: riskLevel === 'critical' ? 'critical' : 'high',
      value: riskLevel === 'critical' ? 0.78 : 0.61,
      threshold: 0.55,
      description: 'Comportamiento de compra diverge negativamente del grupo de referencia',
      category: 'peer'
    },
    {
      id: 'sig-003',
      name: 'Deterioro de Volumen',
      severity: riskLevel === 'critical' || riskLevel === 'high' ? 'high' : 'medium',
      value: riskLevel === 'critical' ? 0.71 : 0.52,
      threshold: 0.50,
      description: 'Reducción progresiva en volúmenes de compra',
      category: 'volume'
    },
    {
      id: 'sig-004',
      name: 'Patrón de Retorno Alterado',
      severity: riskLevel === 'high' ? 'high' : 'medium',
      value: 0.58,
      threshold: 0.45,
      description: 'Cambios en la frecuencia y regularidad de pedidos',
      category: 'behavior'
    }
  ];

  if (riskLevel === 'critical' || riskLevel === 'high') {
    baseSignals.push({
      id: 'sig-005',
      name: 'Riesgo de Migración',
      severity: 'high',
      value: 0.68,
      threshold: 0.50,
      description: 'Indicadores sugieren posible cambio de proveedor',
      category: 'behavior'
    });
  }

  return baseSignals.slice(0, riskLevel === 'critical' ? 5 : riskLevel === 'high' ? 4 : 3);
};

// Mock recommendations
const createRecommendations = (clinic: Clinic): Recommendation[] => {
  const recs: Recommendation[] = [];

  if (clinic.riskLevel === 'critical') {
    recs.push({
      id: 'rec-001',
      type: 'assign',
      priority: 'high',
      title: 'Asignar Responsable Comercial Senior',
      description: 'Designar ejecutivo de cuentas con experiencia en recuperación para contacto inmediato',
      estimatedImpact: '+40% recuperación'
    });
  }

  recs.push({
    id: 'rec-002',
    type: 'campaign',
    priority: clinic.riskLevel === 'critical' ? 'high' : 'medium',
    title: 'Campaña Específica de Retención',
    description: 'Activar campaña personalizada con incentivos especiales en productos de interés',
    estimatedImpact: '+25% engagement'
  });

  recs.push({
    id: 'rec-003',
    type: 'followup',
    priority: 'medium',
    title: 'Programar Seguimiento Telefónico',
    description: 'Contacto directo para entender necesidades actuales y posibles obstáculos',
    estimatedImpact: 'Insight cualitativo'
  });

  if (clinic.productFamily === 'Implantología') {
    recs.push({
      id: 'rec-004',
      type: 'alternative',
      priority: 'low',
      title: 'Presentar Línea Alternativa',
      description: 'Ofrecer productos complementarios o de gama diferente según preferencias',
      estimatedImpact: '+15% cross-sell'
    });
  }

  return recs;
};

// Mock clinic details
export const mockClinicDetails: Record<string, ClinicDetail> = {};

mockClinics.forEach(clinic => {
  mockClinicDetails[clinic.id] = {
    ...clinic,
    signals: createSignals(clinic.riskLevel),
    timeline: generateTimeline(clinic.riskLevel === 'critical' || clinic.riskLevel === 'high' ? 'high-risk' : 'normal'),
    recommendations: createRecommendations(clinic),
    totalPurchases: Math.floor(Math.random() * 50) + 20,
    avgOrderValue: Math.floor(clinic.potentialRevenue / 12),
    lastOrderDate: new Date(Date.now() - clinic.lastOrderDays * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    campaignResponse: Math.random() * 0.5 + 0.3
  };
});

// KPI data for overview
export const mockKPIs = {
  totalAtRisk: mockClinics.length,
  criticalClinics: mockClinics.filter(c => c.riskLevel === 'critical').length,
  totalRevenueAtRisk: mockClinics.reduce((sum, c) => sum + c.potentialRevenue, 0),
  avgRiskScore: mockClinics.reduce((sum, c) => sum + c.riskScore, 0) / mockClinics.length,
  activeInterventions: mockClinics.filter(c => c.status === 'contacted').length,
  recoveredLastMonth: mockClinics.filter(c => c.status === 'recovered').length
};
