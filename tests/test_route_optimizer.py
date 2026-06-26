"""Tests for route optimization module."""

import pytest
from src.route_optimizer import RouteOptimizer
from src.models import RouteOptimizationRequest, Location, RouteStop


@pytest.fixture
def optimizer():
    """Create optimizer instance."""
    return RouteOptimizer()


@pytest.fixture
def sample_route_request():
    """Generate sample route optimization request."""
    depot = Location(
        id="depot-1",
        name="Main Depot",
        latitude=37.7749,
        longitude=-122.4194,
        location_type="warehouse"
    )

    stops = [
        RouteStop(
            location=Location(
                id=f"stop-{i}",
                name=f"Customer {i}",
                latitude=37.7749 + (i * 0.01),
                longitude=-122.4194 + (i * 0.01),
                location_type="customer"
            )
        )
        for i in range(1, 6)
    ]

    return RouteOptimizationRequest(
        depot=depot,
        stops=stops,
        num_vehicles=2,
        optimization_objective="balanced"
    )


def test_route_optimization(optimizer, sample_route_request):
    """Test basic route optimization."""
    response = optimizer.optimize(sample_route_request)

    assert len(response.routes) > 0
    assert response.total_distance_km > 0
    assert response.total_time_minutes > 0
    assert 0 <= response.utilization_percentage <= 100


def test_distance_calculation(optimizer):
    """Test haversine distance calculation."""
    loc1 = Location(
        id="loc1",
        name="Location 1",
        latitude=37.7749,
        longitude=-122.4194,
        location_type="warehouse"
    )

    loc2 = Location(
        id="loc2",
        name="Location 2",
        latitude=37.8049,
        longitude=-122.4494,
        location_type="customer"
    )

    distance = optimizer._calculate_distance(loc1, loc2)
    assert distance > 0
    assert distance < 1000  # Reasonable distance in km
