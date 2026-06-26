"""
API endpoint tests for Supply Chain & Logistics Agent.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.main import app
from src.models import (
    TimeSeriesDataPoint,
    Location,
    RouteStop,
    InventoryItem,
    SupplierInfo,
    SupplierMetrics
)


client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "version" in data
    assert "uptime_seconds" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data


def test_demand_forecast():
    """Test demand forecasting endpoint."""
    # Generate historical data
    base_time = datetime.utcnow() - timedelta(days=60)
    historical_data = [
        {
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "value": 100 + (i % 7) * 10 + (i % 30) * 5
        }
        for i in range(60)
    ]

    request_data = {
        "product_id": "TEST-001",
        "historical_data": historical_data,
        "forecast_horizon": 30,
        "seasonality_mode": "additive",
        "include_confidence_intervals": True
    }

    response = client.post("/api/v1/forecast-demand", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "TEST-001"
    assert len(data["forecast"]) == 30
    assert "model_metrics" in data
    assert "mae" in data["model_metrics"]


def test_route_optimization():
    """Test route optimization endpoint."""
    request_data = {
        "depot": {
            "id": "depot-1",
            "name": "Main Depot",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "location_type": "warehouse"
        },
        "stops": [
            {
                "location": {
                    "id": f"stop-{i}",
                    "name": f"Stop {i}",
                    "latitude": 37.7749 + (i * 0.01),
                    "longitude": -122.4194 + (i * 0.01),
                    "location_type": "customer"
                }
            }
            for i in range(1, 6)
        ],
        "num_vehicles": 2,
        "optimization_objective": "balanced"
    }

    response = client.post("/api/v1/optimize-routes", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) > 0
    assert data["total_distance_km"] > 0
    assert data["utilization_percentage"] >= 0


def test_inventory_management():
    """Test inventory management endpoint."""
    request_data = {
        "items": [
            {
                "product_id": "PROD-001",
                "product_name": "Widget A",
                "sku": "WGT-A-001",
                "current_stock": 500,
                "unit_cost": 25.00,
                "holding_cost_percentage": 0.25,
                "ordering_cost": 50.0,
                "lead_time_days": 7,
                "demand_variability": 0.2,
                "service_level_target": 0.95
            }
        ],
        "average_daily_demand": {
            "PROD-001": 50.0
        },
        "optimization_strategy": "eoq"
    }

    response = client.post("/api/v1/manage-inventory", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) == 1
    rec = data["recommendations"][0]
    assert rec["product_id"] == "PROD-001"
    assert rec["economic_order_quantity"] > 0
    assert rec["reorder_point"] > 0


def test_supplier_risk_assessment():
    """Test supplier risk assessment endpoint."""
    request_data = {
        "suppliers": [
            {
                "supplier_id": "SUP-001",
                "supplier_name": "Acme Corp",
                "country": "USA",
                "years_in_business": 15,
                "financial_stability_score": 0.85,
                "certifications": ["ISO9001", "ISO14001"],
                "historical_metrics": {
                    "on_time_delivery_rate": 0.92,
                    "quality_score": 0.88,
                    "lead_time_variance": 2.5,
                    "defect_rate": 0.02,
                    "response_time_hours": 18.0,
                    "capacity_utilization": 0.75,
                    "price_stability": 0.90
                },
                "product_categories": ["Electronics", "Components"]
            }
        ],
        "risk_tolerance": "medium"
    }

    response = client.post("/api/v1/assess-supplier-risk", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["assessments"]) == 1
    assessment = data["assessments"][0]
    assert assessment["supplier_id"] == "SUP-001"
    assert 0 <= assessment["risk_score"]["overall_score"] <= 1
    assert assessment["risk_score"]["risk_category"] in ["low", "medium", "high", "critical"]


@pytest.mark.asyncio
async def test_shipment_tracking():
    """Test shipment tracking endpoint."""
    request_data = {
        "tracking_number": "1Z999AA10123456784",
        "carrier": "fedex",
        "include_detailed_history": True
    }

    response = client.post("/api/v1/track-shipment", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["tracking_number"] == "1Z999AA10123456784"
    assert data["carrier"] == "fedex"
    assert data["current_status"] in [
        "created", "picked_up", "in_transit",
        "out_for_delivery", "delivered", "delayed", "exception"
    ]


def test_warehouse_optimization():
    """Test warehouse optimization endpoint."""
    request_data = {
        "warehouse_id": "WH-001",
        "zones": [
            {
                "zone_id": "ZONE-PICK",
                "zone_name": "Picking Zone",
                "zone_type": "picking",
                "area_sqm": 1000.0,
                "current_utilization": 0.75
            },
            {
                "zone_id": "ZONE-STOR",
                "zone_name": "Storage Zone",
                "zone_type": "storage",
                "area_sqm": 5000.0,
                "current_utilization": 0.65
            }
        ],
        "products": [
            {
                "product_id": f"PROD-{i:03d}",
                "dimensions_m3": 0.5,
                "weight_kg": 10.0,
                "quantity_on_hand": 100,
                "daily_pick_velocity": 50.0 if i < 5 else 10.0
            }
            for i in range(20)
        ],
        "optimization_goal": "balanced"
    }

    response = client.post("/api/v1/optimize-warehouse", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["warehouse_id"] == "WH-001"
    assert len(data["storage_recommendations"]) == 20
    assert data["space_utilization_optimized"] >= data["space_utilization_current"]
    assert data["estimated_annual_savings"] > 0


def test_analytics_dashboard():
    """Test analytics dashboard endpoint."""
    response = client.get("/api/v1/analytics/dashboard?period_days=30")
    assert response.status_code == 200
    data = response.json()
    assert len(data["kpis"]) > 0
    assert "total_inventory_value" in data
    assert "on_time_delivery_rate" in data
    assert "forecast_accuracy" in data


def test_invalid_forecast_request():
    """Test demand forecast with invalid data."""
    request_data = {
        "product_id": "TEST-001",
        "historical_data": [],  # Empty data
        "forecast_horizon": 30
    }

    response = client.post("/api/v1/forecast-demand", json=request_data)
    assert response.status_code == 422  # Validation error


def test_invalid_route_request():
    """Test route optimization with invalid data."""
    request_data = {
        "depot": {
            "id": "depot-1",
            "name": "Main Depot",
            "latitude": 37.7749,
            "longitude": -122.4194
        },
        "stops": [],  # No stops
        "num_vehicles": 2
    }

    response = client.post("/api/v1/optimize-routes", json=request_data)
    assert response.status_code == 422  # Validation error
