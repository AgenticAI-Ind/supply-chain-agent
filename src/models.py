"""
Pydantic models for Supply Chain & Logistics Agent.

This module defines all request and response models for the API endpoints,
providing comprehensive validation, documentation, and type safety.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

from pydantic import BaseModel, Field, validator, confloat, conint


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series."""

    timestamp: datetime = Field(..., description="Timestamp of the data point")
    value: float = Field(..., description="Value at this timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class DemandForecastRequest(BaseModel):
    """Request model for demand forecasting."""

    product_id: str = Field(..., description="Product identifier")
    historical_data: List[TimeSeriesDataPoint] = Field(
        ...,
        description="Historical demand data",
        min_items=30
    )
    forecast_horizon: conint(ge=1, le=365) = Field(
        30,
        description="Number of days to forecast ahead"
    )
    seasonality_mode: Literal["additive", "multiplicative"] = Field(
        "additive",
        description="Type of seasonality pattern"
    )
    include_confidence_intervals: bool = Field(
        True,
        description="Whether to include confidence intervals in predictions"
    )
    external_regressors: Optional[Dict[str, List[float]]] = Field(
        None,
        description="Additional features like promotions, holidays, etc."
    )


class ForecastDataPoint(BaseModel):
    """Single forecasted data point."""

    timestamp: datetime
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class DemandForecastResponse(BaseModel):
    """Response model for demand forecasting."""

    product_id: str
    forecast: List[ForecastDataPoint]
    model_metrics: Dict[str, float] = Field(
        ...,
        description="Model performance metrics (MAE, RMSE, MAPE, etc.)"
    )
    trend_analysis: Dict[str, Any] = Field(
        ...,
        description="Trend components and analysis"
    )
    seasonality_detected: bool
    model_version: str
    generated_at: datetime


class Location(BaseModel):
    """Geographic location with coordinates."""

    id: str = Field(..., description="Location identifier")
    name: str = Field(..., description="Location name")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    location_type: Literal["warehouse", "store", "customer", "supplier"] = "customer"


class DeliveryConstraints(BaseModel):
    """Constraints for delivery routing."""

    time_windows: Optional[List[tuple[datetime, datetime]]] = Field(
        None,
        description="Acceptable delivery time windows"
    )
    priority: conint(ge=1, le=10) = Field(5, description="Delivery priority (1=lowest, 10=highest)")
    service_time_minutes: conint(ge=0) = Field(10, description="Time required at location")
    package_weight_kg: Optional[float] = Field(None, ge=0)
    package_volume_m3: Optional[float] = Field(None, ge=0)
    special_requirements: Optional[List[str]] = None


class RouteStop(BaseModel):
    """A single stop on a delivery route."""

    location: Location
    constraints: Optional[DeliveryConstraints] = None


class VehicleCapacity(BaseModel):
    """Vehicle capacity constraints."""

    max_weight_kg: float = Field(..., ge=0)
    max_volume_m3: float = Field(..., ge=0)
    max_stops: conint(ge=1) = 50


class RouteOptimizationRequest(BaseModel):
    """Request model for route optimization."""

    depot: Location = Field(..., description="Starting/ending depot location")
    stops: List[RouteStop] = Field(..., min_items=1, description="Delivery stops")
    num_vehicles: conint(ge=1) = Field(1, description="Number of available vehicles")
    vehicle_capacity: Optional[VehicleCapacity] = None
    optimization_objective: Literal["distance", "time", "cost", "balanced"] = "balanced"
    avoid_tolls: bool = False
    avoid_highways: bool = False
    departure_time: Optional[datetime] = None


class OptimizedRoute(BaseModel):
    """A single optimized route."""

    vehicle_id: int
    stops_sequence: List[Location]
    total_distance_km: float
    total_time_minutes: float
    total_cost: float
    estimated_fuel_cost: float
    route_polyline: Optional[str] = Field(None, description="Encoded route polyline")
    turn_by_turn_directions: Optional[List[Dict[str, Any]]] = None


class RouteOptimizationResponse(BaseModel):
    """Response model for route optimization."""

    routes: List[OptimizedRoute]
    total_distance_km: float
    total_time_minutes: float
    total_cost: float
    optimization_time_ms: float
    utilization_percentage: float = Field(..., description="Vehicle capacity utilization")
    cost_savings_vs_baseline: Optional[float] = None
    generated_at: datetime


class InventoryItem(BaseModel):
    """Inventory item details."""

    product_id: str
    product_name: str
    sku: str
    current_stock: conint(ge=0)
    unit_cost: confloat(ge=0.0)
    holding_cost_percentage: confloat(ge=0.0, le=1.0) = Field(
        0.25,
        description="Annual holding cost as percentage of unit cost"
    )
    ordering_cost: confloat(ge=0.0) = Field(50.0, description="Fixed cost per order")
    lead_time_days: conint(ge=0) = Field(7, description="Supplier lead time")
    demand_variability: confloat(ge=0.0) = Field(0.2, description="Standard deviation of demand")
    service_level_target: confloat(ge=0.0, le=1.0) = Field(
        0.95,
        description="Target service level (e.g., 0.95 = 95%)"
    )


class InventoryManagementRequest(BaseModel):
    """Request model for inventory management."""

    items: List[InventoryItem] = Field(..., min_items=1)
    average_daily_demand: Dict[str, float] = Field(
        ...,
        description="Average daily demand per product"
    )
    forecast_horizon_days: conint(ge=1, le=365) = 90
    optimization_strategy: Literal["eoq", "dynamic", "just_in_time", "safety_stock"] = "dynamic"


class InventoryRecommendation(BaseModel):
    """Inventory recommendation for a single item."""

    product_id: str
    current_stock: int
    reorder_point: int
    safety_stock: int
    economic_order_quantity: int
    optimal_order_quantity: int
    days_until_stockout: Optional[float]
    recommended_action: Literal["order_now", "order_soon", "adequate", "overstock"]
    order_priority: conint(ge=1, le=10)
    estimated_annual_cost: float
    potential_savings: float


class InventoryManagementResponse(BaseModel):
    """Response model for inventory management."""

    recommendations: List[InventoryRecommendation]
    total_inventory_value: float
    total_annual_holding_cost: float
    total_annual_ordering_cost: float
    total_potential_savings: float
    stockout_risk_items: List[str]
    overstock_items: List[str]
    generated_at: datetime


class SupplierMetrics(BaseModel):
    """Historical supplier performance metrics."""

    on_time_delivery_rate: confloat(ge=0.0, le=1.0)
    quality_score: confloat(ge=0.0, le=1.0)
    lead_time_variance: float = Field(..., ge=0.0, description="Variance in delivery times")
    defect_rate: confloat(ge=0.0, le=1.0)
    response_time_hours: float = Field(..., ge=0.0)
    capacity_utilization: confloat(ge=0.0, le=1.0)
    price_stability: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="1.0 = stable, lower = volatile pricing"
    )


class SupplierInfo(BaseModel):
    """Supplier information and details."""

    supplier_id: str
    supplier_name: str
    country: str
    years_in_business: conint(ge=0)
    financial_stability_score: confloat(ge=0.0, le=1.0)
    certifications: List[str] = Field(default_factory=list)
    historical_metrics: SupplierMetrics
    product_categories: List[str]


class RiskAssessmentRequest(BaseModel):
    """Request model for supplier risk assessment."""

    suppliers: List[SupplierInfo] = Field(..., min_items=1)
    risk_factors: List[str] = Field(
        default_factory=lambda: [
            "delivery_reliability",
            "quality",
            "financial_stability",
            "geopolitical",
            "capacity",
            "pricing"
        ]
    )
    risk_tolerance: Literal["low", "medium", "high"] = "medium"


class RiskScore(BaseModel):
    """Risk score breakdown."""

    overall_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Overall risk score (0=high risk, 1=low risk)"
    )
    delivery_risk: confloat(ge=0.0, le=1.0)
    quality_risk: confloat(ge=0.0, le=1.0)
    financial_risk: confloat(ge=0.0, le=1.0)
    capacity_risk: confloat(ge=0.0, le=1.0)
    geopolitical_risk: confloat(ge=0.0, le=1.0)
    risk_category: Literal["low", "medium", "high", "critical"]


class SupplierRiskAssessment(BaseModel):
    """Risk assessment for a single supplier."""

    supplier_id: str
    supplier_name: str
    risk_score: RiskScore
    risk_factors_identified: List[str]
    recommendations: List[str]
    alternative_suppliers: Optional[List[str]] = None
    monitoring_frequency: Literal["daily", "weekly", "monthly", "quarterly"]


class RiskAssessmentResponse(BaseModel):
    """Response model for supplier risk assessment."""

    assessments: List[SupplierRiskAssessment]
    high_risk_suppliers: List[str]
    diversification_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Supplier diversification score"
    )
    overall_supply_chain_risk: confloat(ge=0.0, le=1.0)
    recommended_actions: List[str]
    generated_at: datetime


class ShipmentStatus(str, Enum):
    """Shipment status enumeration."""

    CREATED = "created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    EXCEPTION = "exception"
    CANCELLED = "cancelled"


class TrackingEvent(BaseModel):
    """A single tracking event in shipment history."""

    timestamp: datetime
    status: ShipmentStatus
    location: Optional[str] = None
    description: str
    facility: Optional[str] = None


class ShipmentTrackingRequest(BaseModel):
    """Request model for shipment tracking."""

    tracking_number: str
    carrier: Literal["fedex", "ups", "dhl", "usps"] = "fedex"
    include_detailed_history: bool = True


class ShipmentTrackingResponse(BaseModel):
    """Response model for shipment tracking."""

    tracking_number: str
    carrier: str
    current_status: ShipmentStatus
    current_location: Optional[Location] = None
    origin: Optional[Location] = None
    destination: Optional[Location] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    tracking_history: List[TrackingEvent]
    delivery_proof: Optional[Dict[str, Any]] = None
    exceptions: List[str] = Field(default_factory=list)
    last_updated: datetime


class WarehouseZone(BaseModel):
    """Warehouse zone definition."""

    zone_id: str
    zone_name: str
    zone_type: Literal["receiving", "storage", "picking", "packing", "shipping"]
    area_sqm: float = Field(..., ge=0)
    current_utilization: confloat(ge=0.0, le=1.0)


class ProductStorageInfo(BaseModel):
    """Product storage requirements and velocity."""

    product_id: str
    dimensions_m3: float = Field(..., ge=0)
    weight_kg: float = Field(..., ge=0)
    quantity_on_hand: conint(ge=0)
    daily_pick_velocity: float = Field(..., ge=0, description="Average picks per day")
    storage_requirements: Optional[List[str]] = Field(
        default=None,
        description="Special storage requirements (e.g., refrigerated, hazmat)"
    )


class WarehouseOptimizationRequest(BaseModel):
    """Request model for warehouse optimization."""

    warehouse_id: str
    zones: List[WarehouseZone]
    products: List[ProductStorageInfo]
    optimization_goal: Literal["space", "picking_efficiency", "balanced"] = "balanced"


class StorageRecommendation(BaseModel):
    """Storage recommendation for a product."""

    product_id: str
    recommended_zone: str
    recommended_location: Optional[str] = None
    pick_path_optimization: Optional[int] = Field(
        None,
        description="Optimal position in pick path"
    )
    rationale: str


class WarehouseOptimizationResponse(BaseModel):
    """Response model for warehouse optimization."""

    warehouse_id: str
    storage_recommendations: List[StorageRecommendation]
    space_utilization_current: float
    space_utilization_optimized: float
    picking_efficiency_improvement: float = Field(
        ...,
        description="Percentage improvement in picking efficiency"
    )
    potential_capacity_increase: float = Field(
        ...,
        description="Additional capacity gained in cubic meters"
    )
    layout_changes_required: List[str]
    estimated_implementation_cost: float
    estimated_annual_savings: float
    generated_at: datetime


class SupplyChainKPI(BaseModel):
    """Supply chain KPI metric."""

    metric_name: str
    current_value: float
    target_value: Optional[float] = None
    previous_period_value: Optional[float] = None
    trend: Literal["improving", "stable", "declining"]
    unit: str


class AnalyticsDashboardResponse(BaseModel):
    """Response model for analytics dashboard."""

    kpis: List[SupplyChainKPI]
    total_inventory_value: float
    total_orders_processed: int
    on_time_delivery_rate: float
    average_lead_time_days: float
    stockout_incidents: int
    perfect_order_rate: float
    cash_to_cash_cycle_days: float
    supply_chain_cost_percentage: float
    forecast_accuracy: float
    supplier_performance_score: float
    warehouse_utilization: float
    transportation_cost: float
    period_start: datetime
    period_end: datetime
    generated_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: float
    database_connected: bool
    cache_connected: bool
    external_apis: Dict[str, bool]
    timestamp: datetime
