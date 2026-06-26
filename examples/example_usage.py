"""
Example usage of Supply Chain & Logistics Agent API.

This script demonstrates how to use all the major endpoints of the API
with realistic examples.
"""

import requests
import json
from datetime import datetime, timedelta


# API Base URL
BASE_URL = "http://localhost:8000/api/v1"


def example_demand_forecast():
    """Example: Demand Forecasting"""
    print("\n=== Demand Forecasting Example ===")

    # Generate historical data (60 days)
    base_time = datetime.utcnow() - timedelta(days=60)
    historical_data = [
        {
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "value": 100 + (i % 7) * 10 + (i % 30) * 5  # Weekly and monthly patterns
        }
        for i in range(60)
    ]

    request_data = {
        "product_id": "WIDGET-A-001",
        "historical_data": historical_data,
        "forecast_horizon": 30,
        "seasonality_mode": "additive",
        "include_confidence_intervals": True
    }

    response = requests.post(f"{BASE_URL}/forecast-demand", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Product: {result['product_id']}")
        print(f"Forecast Points: {len(result['forecast'])}")
        print(f"Model Metrics: MAE={result['model_metrics']['mae']:.2f}, "
              f"RMSE={result['model_metrics']['rmse']:.2f}")
        print(f"Seasonality Detected: {result['seasonality_detected']}")
        print(f"First 5 predictions:")
        for i, point in enumerate(result['forecast'][:5]):
            print(f"  Day {i+1}: {point['predicted_value']:.2f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_route_optimization():
    """Example: Route Optimization"""
    print("\n=== Route Optimization Example ===")

    request_data = {
        "depot": {
            "id": "depot-sf",
            "name": "San Francisco Depot",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "location_type": "warehouse"
        },
        "stops": [
            {
                "location": {
                    "id": f"customer-{i}",
                    "name": f"Customer {i}",
                    "latitude": 37.7749 + (i * 0.02),
                    "longitude": -122.4194 + (i * 0.02),
                    "location_type": "customer"
                },
                "constraints": {
                    "priority": 5,
                    "service_time_minutes": 15,
                    "package_weight_kg": 25.0
                }
            }
            for i in range(1, 11)
        ],
        "num_vehicles": 3,
        "vehicle_capacity": {
            "max_weight_kg": 500.0,
            "max_volume_m3": 20.0,
            "max_stops": 50
        },
        "optimization_objective": "cost"
    }

    response = requests.post(f"{BASE_URL}/optimize-routes", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Number of Routes: {len(result['routes'])}")
        print(f"Total Distance: {result['total_distance_km']:.2f} km")
        print(f"Total Time: {result['total_time_minutes']:.2f} minutes")
        print(f"Total Cost: ${result['total_cost']:.2f}")
        print(f"Vehicle Utilization: {result['utilization_percentage']:.1f}%")
        print(f"Cost Savings: {result['cost_savings_vs_baseline']:.1f}%")

        for i, route in enumerate(result['routes']):
            print(f"\nRoute {i+1}:")
            print(f"  Stops: {len(route['stops_sequence'])}")
            print(f"  Distance: {route['total_distance_km']:.2f} km")
            print(f"  Cost: ${route['total_cost']:.2f}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_inventory_management():
    """Example: Inventory Management"""
    print("\n=== Inventory Management Example ===")

    request_data = {
        "items": [
            {
                "product_id": f"PROD-{i:03d}",
                "product_name": f"Product {i}",
                "sku": f"SKU-{i:03d}",
                "current_stock": 500 + (i * 50),
                "unit_cost": 25.00 + (i * 2),
                "holding_cost_percentage": 0.25,
                "ordering_cost": 50.0,
                "lead_time_days": 7,
                "demand_variability": 0.2,
                "service_level_target": 0.95
            }
            for i in range(1, 6)
        ],
        "average_daily_demand": {
            f"PROD-{i:03d}": 50.0 + (i * 5)
            for i in range(1, 6)
        },
        "forecast_horizon_days": 90,
        "optimization_strategy": "dynamic"
    }

    response = requests.post(f"{BASE_URL}/manage-inventory", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Total Inventory Value: ${result['total_inventory_value']:,.2f}")
        print(f"Annual Holding Cost: ${result['total_annual_holding_cost']:,.2f}")
        print(f"Annual Ordering Cost: ${result['total_annual_ordering_cost']:,.2f}")
        print(f"Total Potential Savings: ${result['total_potential_savings']:,.2f}")
        print(f"Stockout Risk Items: {len(result['stockout_risk_items'])}")

        print("\nTop 3 Recommendations:")
        for rec in result['recommendations'][:3]:
            print(f"\n  Product: {rec['product_id']}")
            print(f"  Current Stock: {rec['current_stock']}")
            print(f"  Reorder Point: {rec['reorder_point']}")
            print(f"  EOQ: {rec['economic_order_quantity']}")
            print(f"  Action: {rec['recommended_action']}")
            print(f"  Priority: {rec['order_priority']}/10")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_supplier_risk_assessment():
    """Example: Supplier Risk Assessment"""
    print("\n=== Supplier Risk Assessment Example ===")

    request_data = {
        "suppliers": [
            {
                "supplier_id": "SUP-001",
                "supplier_name": "Acme Manufacturing",
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
            },
            {
                "supplier_id": "SUP-002",
                "supplier_name": "Global Parts Co",
                "country": "China",
                "years_in_business": 8,
                "financial_stability_score": 0.70,
                "certifications": ["ISO9001"],
                "historical_metrics": {
                    "on_time_delivery_rate": 0.78,
                    "quality_score": 0.75,
                    "lead_time_variance": 5.0,
                    "defect_rate": 0.05,
                    "response_time_hours": 36.0,
                    "capacity_utilization": 0.92,
                    "price_stability": 0.65
                },
                "product_categories": ["Components", "Raw Materials"]
            }
        ],
        "risk_tolerance": "medium"
    }

    response = requests.post(f"{BASE_URL}/assess-supplier-risk", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Overall Supply Chain Risk: {result['overall_supply_chain_risk']:.2f}")
        print(f"Diversification Score: {result['diversification_score']:.2f}")
        print(f"High Risk Suppliers: {len(result['high_risk_suppliers'])}")

        print("\nSupplier Assessments:")
        for assessment in result['assessments']:
            print(f"\n  Supplier: {assessment['supplier_name']}")
            print(f"  Overall Risk Score: {assessment['risk_score']['overall_score']:.2f}")
            print(f"  Risk Category: {assessment['risk_score']['risk_category']}")
            print(f"  Monitoring Frequency: {assessment['monitoring_frequency']}")
            print(f"  Risk Factors: {', '.join(assessment['risk_factors_identified'][:3])}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_shipment_tracking():
    """Example: Shipment Tracking"""
    print("\n=== Shipment Tracking Example ===")

    request_data = {
        "tracking_number": "1Z999AA10123456784",
        "carrier": "fedex",
        "include_detailed_history": True
    }

    response = requests.post(f"{BASE_URL}/track-shipment", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Tracking Number: {result['tracking_number']}")
        print(f"Carrier: {result['carrier']}")
        print(f"Status: {result['current_status']}")
        if result['estimated_delivery']:
            print(f"Estimated Delivery: {result['estimated_delivery']}")

        print(f"\nTracking History ({len(result['tracking_history'])} events):")
        for event in result['tracking_history'][-5:]:
            print(f"  {event['timestamp']}: {event['description']} - {event['location']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_warehouse_optimization():
    """Example: Warehouse Optimization"""
    print("\n=== Warehouse Optimization Example ===")

    request_data = {
        "warehouse_id": "WH-SF-001",
        "zones": [
            {
                "zone_id": "ZONE-PICK",
                "zone_name": "Fast Pick Zone",
                "zone_type": "picking",
                "area_sqm": 500.0,
                "current_utilization": 0.80
            },
            {
                "zone_id": "ZONE-MAIN",
                "zone_name": "Main Storage",
                "zone_type": "storage",
                "area_sqm": 3000.0,
                "current_utilization": 0.65
            },
            {
                "zone_id": "ZONE-BULK",
                "zone_name": "Bulk Storage",
                "zone_type": "storage",
                "area_sqm": 2000.0,
                "current_utilization": 0.70
            }
        ],
        "products": [
            {
                "product_id": f"PROD-{i:03d}",
                "dimensions_m3": 0.5,
                "weight_kg": 10.0,
                "quantity_on_hand": 100 if i < 10 else 500,
                "daily_pick_velocity": 50.0 if i < 10 else 5.0
            }
            for i in range(50)
        ],
        "optimization_goal": "picking_efficiency"
    }

    response = requests.post(f"{BASE_URL}/optimize-warehouse", json=request_data)

    if response.status_code == 200:
        result = response.json()
        print(f"Warehouse: {result['warehouse_id']}")
        print(f"Current Utilization: {result['space_utilization_current']:.1f}%")
        print(f"Optimized Utilization: {result['space_utilization_optimized']:.1f}%")
        print(f"Picking Efficiency Improvement: {result['picking_efficiency_improvement']:.1f}%")
        print(f"Capacity Increase: {result['potential_capacity_increase']:.2f} m³")
        print(f"Implementation Cost: ${result['estimated_implementation_cost']:,.2f}")
        print(f"Annual Savings: ${result['estimated_annual_savings']:,.2f}")

        print("\nLayout Changes Required:")
        for change in result['layout_changes_required'][:5]:
            print(f"  - {change}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def example_analytics_dashboard():
    """Example: Analytics Dashboard"""
    print("\n=== Analytics Dashboard Example ===")

    response = requests.get(f"{BASE_URL}/analytics/dashboard?period_days=30")

    if response.status_code == 200:
        result = response.json()
        print(f"Analysis Period: {result['period_start']} to {result['period_end']}")
        print(f"\nKey Metrics:")
        print(f"  Total Inventory Value: ${result['total_inventory_value']:,.2f}")
        print(f"  Orders Processed: {result['total_orders_processed']}")
        print(f"  On-Time Delivery Rate: {result['on_time_delivery_rate']:.1f}%")
        print(f"  Average Lead Time: {result['average_lead_time_days']:.1f} days")
        print(f"  Perfect Order Rate: {result['perfect_order_rate']:.1f}%")
        print(f"  Forecast Accuracy: {result['forecast_accuracy']:.1f}%")
        print(f"  Supplier Performance: {result['supplier_performance_score']:.1f}")

        print("\nTop KPIs:")
        for kpi in result['kpis'][:5]:
            print(f"  {kpi['metric_name']}: {kpi['current_value']:.2f} {kpi['unit']}")
            print(f"    Target: {kpi['target_value']}, Trend: {kpi['trend']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


if __name__ == "__main__":
    print("Supply Chain & Logistics Agent - API Examples")
    print("=" * 60)

    # Run all examples
    example_demand_forecast()
    example_route_optimization()
    example_inventory_management()
    example_supplier_risk_assessment()
    example_shipment_tracking()
    example_warehouse_optimization()
    example_analytics_dashboard()

    print("\n" + "=" * 60)
    print("All examples completed!")
