# API Documentation

Complete API reference for Supply Chain & Logistics Agent.

## Base URL

```
Production: https://api.yourcompany.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

Include API key in request headers:

```
X-API-Key: your-api-key-here
```

## Endpoints

### POST /forecast-demand

Generate demand forecast using ML models.

**Request Body:**
```json
{
  "product_id": "string",
  "historical_data": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "value": 100.0
    }
  ],
  "forecast_horizon": 30,
  "seasonality_mode": "additive",
  "include_confidence_intervals": true
}
```

**Response:**
```json
{
  "product_id": "string",
  "forecast": [...],
  "model_metrics": {
    "mae": 8.5,
    "rmse": 12.3,
    "mape": 6.2
  },
  "seasonality_detected": true
}
```

### POST /optimize-routes

Optimize delivery routes.

**Request Body:**
```json
{
  "depot": {
    "id": "depot-1",
    "name": "Main Depot",
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "stops": [...],
  "num_vehicles": 3,
  "optimization_objective": "cost"
}
```

**Response:**
```json
{
  "routes": [...],
  "total_distance_km": 191.5,
  "total_cost": 285.50,
  "cost_savings_vs_baseline": 22.3
}
```

### POST /manage-inventory

Optimize inventory levels.

**Request Body:**
```json
{
  "items": [...],
  "average_daily_demand": {},
  "optimization_strategy": "dynamic"
}
```

**Response:**
```json
{
  "recommendations": [...],
  "total_inventory_value": 2500000.00,
  "total_potential_savings": 625000.00
}
```

### POST /assess-supplier-risk

Assess supplier risk.

**Request Body:**
```json
{
  "suppliers": [...],
  "risk_tolerance": "medium"
}
```

**Response:**
```json
{
  "assessments": [...],
  "overall_supply_chain_risk": 0.72,
  "diversification_score": 0.65
}
```

### POST /track-shipment

Track shipment status.

**Request Body:**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "carrier": "fedex"
}
```

**Response:**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "current_status": "in_transit",
  "tracking_history": [...]
}
```

### POST /optimize-warehouse

Optimize warehouse layout.

**Request Body:**
```json
{
  "warehouse_id": "WH-001",
  "zones": [...],
  "products": [...]
}
```

**Response:**
```json
{
  "storage_recommendations": [...],
  "picking_efficiency_improvement": 35.2,
  "estimated_annual_savings": 180000.00
}
```

### GET /analytics/dashboard

Get analytics dashboard.

**Query Parameters:**
- `period_days`: Analysis period (default: 30)

**Response:**
```json
{
  "kpis": [...],
  "total_inventory_value": 2500000.00,
  "on_time_delivery_rate": 95.2,
  "forecast_accuracy": 88.5
}
```

## Error Responses

All endpoints return standard error format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limiting

- 60 requests per minute per API key
- 429 Too Many Requests on limit exceeded
- X-RateLimit-Remaining header shows remaining requests

## Pagination

For endpoints returning lists:

```
?limit=100&offset=0
```

## WebSocket Support

Real-time updates available at:

```
ws://localhost:8000/ws/tracking/{tracking_number}
```
