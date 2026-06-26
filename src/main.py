"""
Supply Chain & Logistics Agent - Main FastAPI Application.

This production-ready application provides comprehensive supply chain management
capabilities including demand forecasting, route optimization, inventory management,
supplier risk assessment, shipment tracking, and warehouse optimization.
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import db_manager, redis_manager, get_db_session
from .models import (
    DemandForecastRequest,
    DemandForecastResponse,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    InventoryManagementRequest,
    InventoryManagementResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    ShipmentTrackingRequest,
    ShipmentTrackingResponse,
    WarehouseOptimizationRequest,
    WarehouseOptimizationResponse,
    AnalyticsDashboardResponse,
    HealthCheckResponse,
    ErrorResponse
)
from .demand_forecaster import DemandForecaster
from .route_optimizer import RouteOptimizer
from .inventory_manager import InventoryManager
from .supplier_risk_assessor import SupplierRiskAssessor
from .shipment_tracker import ShipmentTracker
from .warehouse_optimizer import WarehouseOptimizer
from .analytics import AnalyticsEngine


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.start_time = time.time()
        self.demand_forecaster = DemandForecaster()
        self.route_optimizer = RouteOptimizer()
        self.inventory_manager = InventoryManager()
        self.risk_assessor = SupplierRiskAssessor()
        self.shipment_tracker = ShipmentTracker()
        self.warehouse_optimizer = WarehouseOptimizer()
        self.analytics_engine = AnalyticsEngine()


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Supply Chain & Logistics Agent...")

    try:
        # Initialize database
        await db_manager.initialize()
        logger.info("Database initialized")

        # Initialize Redis
        await redis_manager.initialize()
        logger.info("Redis initialized")

        logger.info("Application startup complete")

        yield

    finally:
        # Shutdown
        logger.info("Shutting down Supply Chain & Logistics Agent...")

        await db_manager.close()
        await redis_manager.close()
        await app_state.shipment_tracker.close()

        logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready Supply Chain & Logistics optimization agent with ML-powered forecasting, route optimization, and risk assessment",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.DEBUG else "An unexpected error occurred"
        ).dict()
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns system health status and connectivity information.
    """
    uptime = time.time() - app_state.start_time

    # Check database connectivity
    db_connected = db_manager._initialized

    # Check Redis connectivity
    cache_connected = redis_manager._initialized

    # Check external APIs
    external_apis = {
        "google_maps": bool(settings.GOOGLE_MAPS_API_KEY),
        "fedex": bool(settings.FEDEX_API_KEY),
        "ups": bool(settings.UPS_API_KEY),
        "dhl": bool(settings.DHL_API_KEY)
    }

    # Determine overall status
    if db_connected and cache_connected:
        status_value = "healthy"
    elif db_connected or cache_connected:
        status_value = "degraded"
    else:
        status_value = "unhealthy"

    return HealthCheckResponse(
        status=status_value,
        version=settings.APP_VERSION,
        uptime_seconds=uptime,
        database_connected=db_connected,
        cache_connected=cache_connected,
        external_apis=external_apis,
        timestamp=datetime.utcnow()
    )


# Demand Forecasting Endpoint
@app.post(
    f"{settings.API_PREFIX}/forecast-demand",
    response_model=DemandForecastResponse,
    tags=["Forecasting"]
)
async def forecast_demand(
    request: DemandForecastRequest
) -> DemandForecastResponse:
    """
    Generate demand forecast using time series ML models.

    This endpoint uses Prophet or LSTM models to generate accurate demand
    forecasts with seasonality, trends, and confidence intervals.

    **Features:**
    - Prophet and LSTM time series forecasting
    - Seasonality detection (yearly, weekly)
    - Trend analysis
    - Confidence intervals
    - External regressor support
    - Model performance metrics (MAE, RMSE, MAPE)

    **Use Cases:**
    - Inventory planning
    - Production scheduling
    - Capacity planning
    - Budget forecasting
    """
    try:
        logger.info(f"Forecast demand request for product: {request.product_id}")
        response = app_state.demand_forecaster.forecast(request)
        return response
    except Exception as e:
        logger.error(f"Forecast demand error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting failed: {str(e)}"
        )


# Route Optimization Endpoint
@app.post(
    f"{settings.API_PREFIX}/optimize-routes",
    response_model=RouteOptimizationResponse,
    tags=["Route Optimization"]
)
async def optimize_routes(
    request: RouteOptimizationRequest
) -> RouteOptimizationResponse:
    """
    Optimize delivery routes for multiple vehicles.

    Uses Google OR-Tools to solve vehicle routing problems with constraints
    including capacity, time windows, and multiple optimization objectives.

    **Features:**
    - Multi-vehicle route optimization
    - Capacity constraints (weight, volume)
    - Time window constraints
    - Multiple optimization objectives (distance, time, cost, balanced)
    - Real-time traffic consideration
    - Cost savings analysis

    **Use Cases:**
    - Last-mile delivery optimization
    - Field service scheduling
    - Fleet management
    - Distribution planning
    """
    try:
        logger.info(f"Route optimization request with {len(request.stops)} stops")
        response = app_state.route_optimizer.optimize(request)
        return response
    except Exception as e:
        logger.error(f"Route optimization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route optimization failed: {str(e)}"
        )


# Inventory Management Endpoint
@app.post(
    f"{settings.API_PREFIX}/manage-inventory",
    response_model=InventoryManagementResponse,
    tags=["Inventory Management"]
)
async def manage_inventory(
    request: InventoryManagementRequest
) -> InventoryManagementResponse:
    """
    Optimize inventory levels and generate reorder recommendations.

    Implements EOQ, safety stock calculations, and dynamic optimization
    strategies to minimize costs while maintaining service levels.

    **Features:**
    - Economic Order Quantity (EOQ) optimization
    - Safety stock calculation
    - Reorder point determination
    - Multiple optimization strategies (EOQ, Dynamic, JIT, Safety Stock)
    - Service level optimization
    - Cost analysis (holding, ordering)
    - Stockout risk assessment

    **Use Cases:**
    - Inventory planning
    - Replenishment automation
    - Working capital optimization
    - Stockout prevention
    """
    try:
        logger.info(f"Inventory management request for {len(request.items)} items")
        response = app_state.inventory_manager.optimize(request)
        return response
    except Exception as e:
        logger.error(f"Inventory management error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inventory optimization failed: {str(e)}"
        )


# Supplier Risk Assessment Endpoint
@app.post(
    f"{settings.API_PREFIX}/assess-supplier-risk",
    response_model=RiskAssessmentResponse,
    tags=["Risk Assessment"]
)
async def assess_supplier_risk(
    request: RiskAssessmentRequest
) -> RiskAssessmentResponse:
    """
    Assess supplier risk using ML-based scoring.

    Evaluates suppliers across multiple risk dimensions including delivery
    reliability, quality, financial stability, and geopolitical factors.

    **Features:**
    - Multi-factor risk scoring
    - Delivery reliability assessment
    - Quality risk evaluation
    - Financial stability analysis
    - Geopolitical risk consideration
    - Capacity risk assessment
    - Supplier diversification analysis
    - Automated recommendations
    - Risk-based monitoring frequency

    **Use Cases:**
    - Supplier selection
    - Risk mitigation planning
    - Diversification strategy
    - Compliance monitoring
    """
    try:
        logger.info(f"Risk assessment request for {len(request.suppliers)} suppliers")
        response = app_state.risk_assessor.assess(request)
        return response
    except Exception as e:
        logger.error(f"Risk assessment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


# Shipment Tracking Endpoint
@app.post(
    f"{settings.API_PREFIX}/track-shipment",
    response_model=ShipmentTrackingResponse,
    tags=["Shipment Tracking"]
)
async def track_shipment(
    request: ShipmentTrackingRequest
) -> ShipmentTrackingResponse:
    """
    Track shipment in real-time across carriers.

    Integrates with major carriers (FedEx, UPS, DHL, USPS) to provide
    real-time tracking information and delivery status.

    **Features:**
    - Multi-carrier support (FedEx, UPS, DHL, USPS)
    - Real-time tracking updates
    - Detailed tracking history
    - Location tracking
    - Exception monitoring
    - Estimated delivery time
    - Delivery proof

    **Use Cases:**
    - Customer service
    - Proactive exception management
    - Delivery performance monitoring
    - SLA compliance tracking
    """
    try:
        logger.info(f"Shipment tracking request: {request.tracking_number}")
        response = await app_state.shipment_tracker.track(request)
        return response
    except Exception as e:
        logger.error(f"Shipment tracking error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shipment tracking failed: {str(e)}"
        )


# Warehouse Optimization Endpoint
@app.post(
    f"{settings.API_PREFIX}/optimize-warehouse",
    response_model=WarehouseOptimizationResponse,
    tags=["Warehouse Optimization"]
)
async def optimize_warehouse(
    request: WarehouseOptimizationRequest
) -> WarehouseOptimizationResponse:
    """
    Optimize warehouse layout and picking efficiency.

    Uses ABC analysis and layout optimization algorithms to improve
    space utilization and picking efficiency.

    **Features:**
    - ABC analysis for product classification
    - Layout optimization
    - Pick path optimization
    - Space utilization improvement
    - Capacity increase calculation
    - ROI analysis
    - Implementation planning

    **Use Cases:**
    - Warehouse layout planning
    - Picking efficiency improvement
    - Space optimization
    - Labor cost reduction
    """
    try:
        logger.info(f"Warehouse optimization request: {request.warehouse_id}")
        response = app_state.warehouse_optimizer.optimize(request)
        return response
    except Exception as e:
        logger.error(f"Warehouse optimization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Warehouse optimization failed: {str(e)}"
        )


# Analytics Dashboard Endpoint
@app.get(
    f"{settings.API_PREFIX}/analytics/dashboard",
    response_model=AnalyticsDashboardResponse,
    tags=["Analytics"]
)
async def get_analytics_dashboard(
    period_days: int = 30,
    session: AsyncSession = Depends(get_db_session)
) -> AnalyticsDashboardResponse:
    """
    Get comprehensive supply chain analytics dashboard.

    Provides KPIs and metrics for monitoring supply chain performance
    and identifying improvement opportunities.

    **Metrics Included:**
    - Inventory turnover
    - Order fulfillment cycle time
    - On-time delivery rate
    - Fill rate
    - Perfect order rate
    - Cash-to-cash cycle time
    - Supply chain cost percentage
    - Forecast accuracy
    - Supplier performance
    - Warehouse utilization
    - Transportation costs

    **Use Cases:**
    - Performance monitoring
    - Executive reporting
    - Trend analysis
    - Continuous improvement
    """
    try:
        logger.info(f"Analytics dashboard request for {period_days} days")
        response = await app_state.analytics_engine.get_dashboard(session, period_days)
        return response
    except Exception as e:
        logger.error(f"Analytics dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {str(e)}"
        )


# Root endpoint
@app.get("/", tags=["General"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "documentation": "/docs",
        "health_check": "/health",
        "api_prefix": settings.API_PREFIX
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1
    )
