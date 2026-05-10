export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Clinic {
  id: string;
  name: string;
  clientCode: string;
  productFamily: string;
  riskScore: number;
  priorityScore: number;
  riskLevel: RiskLevel;
  potentialRevenue: number;
  lastOrderDays: number;
  inactivityRatio: number;
  recommendedAction: string;
  signalCount: number;
  status?: 'new' | 'contacted' | 'recovered' | 'lost';
}

export interface Signal {
  id: string;
  name: string;
  severity: RiskLevel;
  value: number;
  threshold: number;
  description: string;
  category: 'inactivity' | 'peer' | 'volume' | 'behavior';
}

export interface TimelineDataPoint {
  date: string;
  sales: number;
  rollingSales?: number;
  campaignActive?: boolean;
}

export interface Recommendation {
  id: string;
  type: 'assign' | 'campaign' | 'followup' | 'alternative';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  estimatedImpact: string;
}

export interface ClinicDetail extends Clinic {
  signals: Signal[];
  timeline: TimelineDataPoint[];
  recommendations: Recommendation[];
  totalPurchases: number;
  avgOrderValue: number;
  lastOrderDate: string;
  campaignResponse: number;
}

export interface KPI {
  label: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
}
