"""FastAPI application for the Risk Monitor API."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import Clinic, ClinicDetail, KPI, OverviewStats
from data_service import DataService

# Load environment variables
load_dotenv()

# Configuration
MODE = os.getenv('MODE', 'historical')
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', '..')).resolve()
PORT = int(os.getenv('PORT', 8000))

# Initialize FastAPI app
app = FastAPI(
    title="Risk Monitor API",
    description="REST API for commercial intelligence and risk monitoring",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data service
data_service = DataService(project_root=PROJECT_ROOT, mode=MODE)


# ========== Startup Event ==========

@app.on_event("startup")
async def startup_event():
    """
    Preload data and populate cache on application startup.
    
    This ensures the first API requests are fast by loading
    all data into memory and cache before serving requests.
    """
    print("=" * 60)
    print("🚀 Starting Risk Monitor API - Preloading data...")
    print("=" * 60)
    
    try:
        # Preload main data endpoints to populate cache
        print("📊 Loading KPIs...")
        data_service.get_kpis()
        
        print("🏥 Loading clinics list...")
        data_service.get_all_clinics()
        
        print("📈 Loading overview stats...")
        data_service.get_overview_stats()
        
        print("=" * 60)
        print("✅ Data preloaded successfully - API ready!")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"⚠️  Warning: Failed to preload data: {str(e)}")
        print("Data will be loaded on first request instead.")
        print("=" * 60)


# ========== Health Check ==========

@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "Risk Monitor API",
        "status": "healthy",
        "mode": MODE,
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    """Detailed health check with data availability."""
    queue_exists = data_service.global_queue_path.exists() or data_service.global_queue_parquet_path.exists()
    clients_exists = data_service.clients_path.exists()
    products_exists = data_service.products_path.exists()
    sales_exists = data_service.sales_path.exists()
    
    return {
        "status": "healthy",
        "mode": MODE,
        "data_available": {
            "global_queue": queue_exists,
            "clients": clients_exists,
            "products": products_exists,
            "sales": sales_exists
        },
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "global_queue": str(data_service.global_queue_path)
        }
    }

@app.post("/api/cache/clear")
def clear_cache():
    """
    Clear all caches and force data reload.
    
    Use this to manually refresh data after pipeline re-runs.
    """
    try:
        data_service.clear_cache()
        return {
            "status": "success",
            "message": "Cache cleared successfully. Next requests will load fresh data."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.get("/api/cache/info")
def cache_info():
    """Get information about current cache state."""
    import time
    cache_status = {}
    
    for key in data_service._results_cache.keys():
        timestamp = data_service._cache_timestamps.get(key, 0)
        age = time.time() - timestamp
        cache_status[key] = {
            "age_seconds": int(age),
            "ttl_seconds": data_service.CACHE_TTL,
            "valid": age < data_service.CACHE_TTL
        }
    
    return {
        "cache_ttl_seconds": data_service.CACHE_TTL,
        "cached_items": len(data_service._results_cache),
        "items": cache_status
    }

# ========== Main API Endpoints ==========

@app.get("/api/clinics", response_model=list[Clinic])
def get_clinics(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high, critical"),
    min_priority: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum priority score"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results")
):
    """
    Get all clinics with risk assessment.
    
    Supports filtering by risk level and minimum priority score.
    """
    try:
        clinics = data_service.get_all_clinics()
        
        # Apply filters
        if risk_level:
            clinics = [c for c in clinics if c.riskLevel == risk_level]
        
        if min_priority is not None:
            clinics = [c for c in clinics if c.priorityScore >= min_priority]
        
        # Sort by priority score (descending)
        clinics.sort(key=lambda c: c.priorityScore, reverse=True)
        
        # Apply limit
        if limit:
            clinics = clinics[:limit]
        
        return clinics
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading clinics: {str(e)}")


@app.get("/api/clinics/{clinic_id}", response_model=ClinicDetail)
def get_clinic_detail(clinic_id: str):
    """
    Get detailed information for a specific clinic.
    
    Includes signals, timeline, and recommendations.
    """
    try:
        clinic = data_service.get_clinic_detail(clinic_id)
        
        if clinic is None:
            raise HTTPException(status_code=404, detail=f"Clinic {clinic_id} not found")
        
        return clinic
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading clinic detail: {str(e)}")


@app.get("/api/kpis", response_model=list[KPI])
def get_kpis():
    """
    Get summary KPIs for the dashboard.
    
    Returns key metrics like at-risk clinics, critical clinics, revenue at risk, etc.
    """
    try:
        return data_service.get_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating KPIs: {str(e)}")


@app.get("/api/overview", response_model=OverviewStats)
def get_overview():
    """
    Get overview statistics for the dashboard.
    
    Returns aggregated statistics across all clinics.
    """
    try:
        return data_service.get_overview_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating overview: {str(e)}")


# ========== Additional Utility Endpoints ==========

@app.get("/api/risk-distribution")
def get_risk_distribution():
    """Get distribution of clinics by risk level."""
    try:
        clinics = data_service.get_all_clinics()
        
        distribution = {
            'low': sum(1 for c in clinics if c.riskLevel == 'low'),
            'medium': sum(1 for c in clinics if c.riskLevel == 'medium'),
            'high': sum(1 for c in clinics if c.riskLevel == 'high'),
            'critical': sum(1 for c in clinics if c.riskLevel == 'critical'),
        }
        
        return {
            'distribution': distribution,
            'total': len(clinics)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating distribution: {str(e)}")


@app.get("/api/product-families")
def get_product_families():
    """Get list of product families with clinic counts."""
    try:
        clinics = data_service.get_all_clinics()
        
        families = {}
        for clinic in clinics:
            family = clinic.productFamily
            if family not in families:
                families[family] = {
                    'name': family,
                    'totalClinics': 0,
                    'atRiskClinics': 0,
                    'revenueAtRisk': 0.0
                }
            
            families[family]['totalClinics'] += 1
            if clinic.riskLevel in ['high', 'critical']:
                families[family]['atRiskClinics'] += 1
                families[family]['revenueAtRisk'] += clinic.potentialRevenue
        
        return {
            'families': list(families.values())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading product families: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
