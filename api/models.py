"""Pydantic models for API responses matching frontend TypeScript types."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


RiskLevel = Literal['low', 'medium', 'high', 'critical']
Status = Literal['new', 'contacted', 'recovered', 'lost']
SignalCategory = Literal['inactivity', 'peer', 'volume', 'behavior']
RecommendationType = Literal['assign', 'campaign', 'followup', 'alternative']
Priority = Literal['high', 'medium', 'low']


class Clinic(BaseModel):
    """Clinic with risk assessment - matches frontend Clinic interface."""
    id: str
    name: str
    clientCode: str
    productFamily: str
    riskScore: float = Field(ge=0.0, le=1.0)
    priorityScore: float = Field(ge=0.0, le=1.0)
    riskLevel: RiskLevel
    potentialRevenue: float
    lastOrderDays: int
    inactivityRatio: float = Field(ge=0.0, le=1.0)
    recommendedAction: str
    signalCount: int
    status: Optional[Status] = 'new'


class Signal(BaseModel):
    """Risk signal detail - matches frontend Signal interface."""
    id: str
    name: str
    severity: RiskLevel
    value: float
    threshold: float
    description: str
    category: SignalCategory


class TimelineDataPoint(BaseModel):
    """Sales timeline data point - matches frontend TimelineDataPoint interface."""
    date: str
    sales: float
    rollingSales: Optional[float] = None
    campaignActive: Optional[bool] = False


class Recommendation(BaseModel):
    """Action recommendation - matches frontend Recommendation interface."""
    id: str
    type: RecommendationType
    priority: Priority
    title: str
    description: str
    estimatedImpact: str


class ClinicDetail(Clinic):
    """Extended clinic detail - matches frontend ClinicDetail interface."""
    signals: list[Signal]
    timeline: list[TimelineDataPoint]
    recommendations: list[Recommendation]
    totalPurchases: int
    avgOrderValue: float
    lastOrderDate: str
    campaignResponse: float = Field(ge=0.0, le=1.0)


class KPI(BaseModel):
    """Key Performance Indicator - matches frontend KPI interface."""
    label: str
    value: str | float
    change: Optional[float] = None
    trend: Optional[Literal['up', 'down', 'stable']] = None


class OverviewStats(BaseModel):
    """Overview statistics for dashboard."""
    totalClinics: int
    atRiskClinics: int
    criticalClinics: int
    highRiskClinics: int
    totalRevenueAtRisk: float
    avgRiskScore: float
    avgPriorityScore: float
