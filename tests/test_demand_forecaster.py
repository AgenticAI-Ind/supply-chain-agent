"""Tests for demand forecasting module."""

import pytest
from datetime import datetime, timedelta
from src.demand_forecaster import DemandForecaster
from src.models import DemandForecastRequest, TimeSeriesDataPoint


@pytest.fixture
def forecaster():
    """Create forecaster instance."""
    return DemandForecaster()


@pytest.fixture
def sample_historical_data():
    """Generate sample historical data."""
    base_time = datetime.utcnow() - timedelta(days=60)
    return [
        TimeSeriesDataPoint(
            timestamp=base_time + timedelta(days=i),
            value=100 + (i % 7) * 10 + (i % 30) * 5
        )
        for i in range(60)
    ]


def test_prophet_forecast(forecaster, sample_historical_data):
    """Test Prophet forecasting."""
    request = DemandForecastRequest(
        product_id="TEST-001",
        historical_data=sample_historical_data,
        forecast_horizon=30,
        seasonality_mode="additive"
    )

    response = forecaster.forecast(request)

    assert response.product_id == "TEST-001"
    assert len(response.forecast) == 30
    assert response.seasonality_detected in [True, False]
    assert "mae" in response.model_metrics
    assert response.model_metrics["mae"] >= 0


def test_seasonality_detection(forecaster, sample_historical_data):
    """Test seasonality detection."""
    detected = forecaster._detect_seasonality(sample_historical_data)
    assert isinstance(detected, bool)


def test_insufficient_data(forecaster):
    """Test with insufficient historical data."""
    insufficient_data = [
        TimeSeriesDataPoint(
            timestamp=datetime.utcnow() - timedelta(days=i),
            value=100.0
        )
        for i in range(10)  # Only 10 points
    ]

    request = DemandForecastRequest(
        product_id="TEST-001",
        historical_data=insufficient_data,
        forecast_horizon=30
    )

    with pytest.raises(ValueError):
        forecaster.forecast(request)
