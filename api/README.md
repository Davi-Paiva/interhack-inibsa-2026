# Risk Monitor API

REST API for the commercial intelligence and risk monitoring platform. This API reads outputs from the ML pipeline and exposes them via REST endpoints for the frontend.

## Architecture

```
ML Pipeline Outputs → Data Service → FastAPI → React Frontend
```

The API acts as a bridge between the ML pipeline (which produces parquet/JSON files) and the React frontend (which consumes REST endpoints).

## Quick Start

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

Key settings:
- `MODE`: `historical` or `daily` (determines which pipeline outputs to read)
- `PROJECT_ROOT`: Path to project root (default: `..`)
- `PORT`: API port (default: `8000`)

### 3. Run the API Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### Health & Status

- `GET /` - Health check
- `GET /health` - Detailed health with data availability

### Main Endpoints

- `GET /api/clinics` - List all clinics with risk assessment
  - Query params: `risk_level`, `min_priority`, `limit`
- `GET /api/clinics/{clinic_id}` - Get detailed clinic information
- `GET /api/kpis` - Get dashboard KPIs
- `GET /api/overview` - Get overview statistics

### Utility Endpoints

- `GET /api/risk-distribution` - Get risk level distribution
- `GET /api/product-families` - Get product families with stats

## Data Flow

### Input Data (from ML Pipeline)

The API reads from:

1. **Global Alert Queue** (`backend/global_prioritization/output/{mode}/global_alert_queue.json`)
   - Prioritized list of risk alerts
   - Contains risk scores, recommended actions, etc.

2. **Master Data** (`backend/processed_data/{mode}/`)
   - `clients.csv` - Client information
   - `products.csv` - Product information
   - `sales_enriched.csv` - Sales history

3. **Explanations** (`backend/explainability_engine/output/{mode}/`)
   - Explanation texts for risk signals

### Output Format (for Frontend)

The API transforms pipeline outputs into frontend-compatible models:

```typescript
interface Clinic {
  id: string;
  name: string;
  clientCode: string;
  productFamily: string;
  riskScore: number;      // 0.0 - 1.0
  priorityScore: number;  // 0.0 - 1.0
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  potentialRevenue: number;
  lastOrderDays: number;
  inactivityRatio: number;
  recommendedAction: string;
  signalCount: number;
  status?: 'new' | 'contacted' | 'recovered' | 'lost';
}
```

See `models.py` for complete type definitions.

## Development

### Project Structure

```
api/
├── main.py              # FastAPI application and routes
├── models.py            # Pydantic models (match frontend TypeScript types)
├── data_service.py      # Data loading and transformation logic
├── requirements.txt     # Python dependencies
├── .env.example         # Environment configuration template
└── README.md           # This file
```

### Adding New Endpoints

1. Add route to `main.py`
2. Add data loading logic to `data_service.py` if needed
3. Define response model in `models.py`
4. Test with FastAPI docs at `/docs`

### Testing

```bash
# Start the server
uvicorn main:app --reload

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/clinics
curl http://localhost:8000/api/kpis
```

## Integration with Frontend

Update the frontend to use the API instead of mock data:

```typescript
// Before (mock data)
import { mockClinics } from '../data/mockData';

// After (API call)
const response = await fetch('http://localhost:8000/api/clinics');
const clinics = await response.json();
```

Create an API client in the frontend:

```typescript
// src/utils/api.ts
const API_BASE = 'http://localhost:8000';

export async function getClinics() {
  const res = await fetch(`${API_BASE}/api/clinics`);
  return res.json();
}

export async function getClinicDetail(id: string) {
  const res = await fetch(`${API_BASE}/api/clinics/${id}`);
  return res.json();
}
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use proper environment configuration
2. **CORS**: Update allowed origins in `main.py`
3. **Logging**: Add structured logging for production
4. **Authentication**: Add API key or OAuth if needed
5. **Rate Limiting**: Consider adding rate limiting
6. **Monitoring**: Add health checks and monitoring

### Running in Production

```bash
# Install dependencies
pip install -r requirements.txt

# Run with gunicorn (production WSGI server)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Troubleshooting

### No data available

If `/health` shows `data_available: false`:

1. Check that ML pipeline has run: `python -m backend.global_prioritization --mode historical`
2. Verify output files exist in `backend/global_prioritization/output/historical/`
3. Check `MODE` environment variable matches directory name

### Import errors

```bash
# Make sure you're in the api directory
cd api
pip install -r requirements.txt
```

### CORS errors in frontend

Update `allow_origins` in `main.py` to include your frontend URL.

## Future Enhancements

- [ ] Caching layer (Redis) for frequently accessed data
- [ ] WebSocket support for real-time updates
- [ ] Bulk operations (update multiple clinic statuses)
- [ ] Export endpoints (CSV, PDF reports)
- [ ] Historical trend analysis endpoints
- [ ] Campaign management endpoints
- [ ] User authentication and authorization
