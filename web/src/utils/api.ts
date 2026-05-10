/**
 * API client for the Risk Monitor backend
 * 
 * Connects the React frontend to the FastAPI backend
 */

import type { Clinic, ClinicDetail, KPI } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Generic API error class
 */
export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchJSON<T>(endpoint: string): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new APIError(response.status, error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown'}`);
  }
}

/**
 * Get all clinics with optional filters
 */
export async function getClinics(params?: {
  riskLevel?: 'low' | 'medium' | 'high' | 'critical';
  minPriority?: number;
  limit?: number;
}): Promise<Clinic[]> {
  const searchParams = new URLSearchParams();
  
  if (params?.riskLevel) searchParams.set('risk_level', params.riskLevel);
  if (params?.minPriority !== undefined) searchParams.set('min_priority', params.minPriority.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  
  const query = searchParams.toString();
  return fetchJSON<Clinic[]>(`/api/clinics${query ? `?${query}` : ''}`);
}

/**
 * Get detailed information for a specific clinic
 */
export async function getClinicDetail(clinicId: string): Promise<ClinicDetail> {
  return fetchJSON<ClinicDetail>(`/api/clinics/${clinicId}`);
}

/**
 * Get dashboard KPIs
 */
export async function getKPIs(): Promise<KPI[]> {
  return fetchJSON<KPI[]>('/api/kpis');
}

/**
 * Get overview statistics
 */
export async function getOverview(): Promise<{
  totalClinics: number;
  atRiskClinics: number;
  criticalClinics: number;
  highRiskClinics: number;
  totalRevenueAtRisk: number;
  avgRiskScore: number;
  avgPriorityScore: number;
}> {
  return fetchJSON('/api/overview');
}

/**
 * Get risk distribution
 */
export async function getRiskDistribution(): Promise<{
  distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  total: number;
}> {
  return fetchJSON('/api/risk-distribution');
}

/**
 * Get product families with stats
 */
export async function getProductFamilies(): Promise<{
  families: Array<{
    name: string;
    totalClinics: number;
    atRiskClinics: number;
    revenueAtRisk: number;
  }>;
}> {
  return fetchJSON('/api/product-families');
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  mode: string;
  data_available: {
    global_queue: boolean;
    clients: boolean;
    products: boolean;
    sales: boolean;
  };
}> {
  return fetchJSON('/health');
}
