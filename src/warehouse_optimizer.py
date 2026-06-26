"""
Warehouse Optimization Module.

Implements warehouse space optimization and picking efficiency improvements
using layout optimization algorithms and ABC analysis.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple

import numpy as np

from .models import (
    WarehouseOptimizationRequest,
    WarehouseOptimizationResponse,
    StorageRecommendation,
    WarehouseZone,
    ProductStorageInfo
)


logger = logging.getLogger(__name__)


class WarehouseOptimizer:
    """Handles warehouse layout and picking optimization."""

    def __init__(self):
        """Initialize the warehouse optimizer."""
        pass

    def optimize(
        self,
        request: WarehouseOptimizationRequest
    ) -> WarehouseOptimizationResponse:
        """
        Optimize warehouse layout and storage.

        Args:
            request: Warehouse optimization request

        Returns:
            Optimization response with recommendations and metrics
        """
        try:
            logger.info(
                f"Starting warehouse optimization for {request.warehouse_id} "
                f"with {len(request.products)} products"
            )

            # Perform ABC analysis on products
            abc_classification = self._abc_analysis(request.products)

            # Calculate current space utilization
            current_utilization = self._calculate_space_utilization(
                request.zones,
                request.products
            )

            # Generate storage recommendations
            recommendations = self._generate_storage_recommendations(
                request,
                abc_classification
            )

            # Calculate optimized metrics
            optimized_utilization = self._calculate_optimized_utilization(
                request,
                recommendations
            )

            # Calculate picking efficiency improvement
            picking_improvement = self._calculate_picking_improvement(
                request.products,
                abc_classification,
                recommendations
            )

            # Calculate capacity gains
            capacity_increase = self._calculate_capacity_increase(
                request.zones,
                current_utilization,
                optimized_utilization
            )

            # Identify required layout changes
            layout_changes = self._identify_layout_changes(
                request,
                recommendations
            )

            # Estimate costs and savings
            implementation_cost = self._estimate_implementation_cost(
                layout_changes,
                len(request.products)
            )

            annual_savings = self._estimate_annual_savings(
                picking_improvement,
                capacity_increase,
                len(request.products)
            )

            response = WarehouseOptimizationResponse(
                warehouse_id=request.warehouse_id,
                storage_recommendations=recommendations,
                space_utilization_current=current_utilization,
                space_utilization_optimized=optimized_utilization,
                picking_efficiency_improvement=picking_improvement,
                potential_capacity_increase=capacity_increase,
                layout_changes_required=layout_changes,
                estimated_implementation_cost=implementation_cost,
                estimated_annual_savings=annual_savings,
                generated_at=datetime.utcnow()
            )

            logger.info(
                f"Warehouse optimization completed: "
                f"{picking_improvement:.1f}% picking improvement, "
                f"${annual_savings:,.2f} annual savings"
            )

            return response

        except Exception as e:
            logger.error(f"Warehouse optimization error: {e}")
            raise

    def _abc_analysis(
        self,
        products: List[ProductStorageInfo]
    ) -> Dict[str, str]:
        """
        Perform ABC analysis based on pick velocity.

        A items: Top 20% by velocity (80% of picks)
        B items: Next 30% (15% of picks)
        C items: Remaining 50% (5% of picks)
        """
        # Sort products by pick velocity
        sorted_products = sorted(
            products,
            key=lambda p: p.daily_pick_velocity,
            reverse=True
        )

        total_picks = sum(p.daily_pick_velocity for p in products)
        cumulative_picks = 0
        abc_classification = {}

        for product in sorted_products:
            cumulative_picks += product.daily_pick_velocity
            cumulative_percentage = cumulative_picks / total_picks if total_picks > 0 else 0

            if cumulative_percentage <= 0.80:
                abc_classification[product.product_id] = "A"
            elif cumulative_percentage <= 0.95:
                abc_classification[product.product_id] = "B"
            else:
                abc_classification[product.product_id] = "C"

        return abc_classification

    def _calculate_space_utilization(
        self,
        zones: List[WarehouseZone],
        products: List[ProductStorageInfo]
    ) -> float:
        """Calculate current space utilization."""
        total_storage_space = sum(
            z.area_sqm for z in zones
            if z.zone_type == "storage"
        )

        if total_storage_space == 0:
            return 0.0

        # Calculate space used by products
        # Assuming dimensions_m3 can be converted to sqm with typical height
        typical_height = 2.5  # meters
        total_used_space = sum(
            p.dimensions_m3 * p.quantity_on_hand / typical_height
            for p in products
        )

        utilization = (total_used_space / total_storage_space) * 100
        return min(100.0, round(utilization, 2))

    def _generate_storage_recommendations(
        self,
        request: WarehouseOptimizationRequest,
        abc_classification: Dict[str, str]
    ) -> List[StorageRecommendation]:
        """Generate storage location recommendations."""
        recommendations = []

        # Find picking zone (closest to packing/shipping)
        picking_zones = [z for z in request.zones if z.zone_type == "picking"]
        storage_zones = [z for z in request.zones if z.zone_type == "storage"]

        # Sort products by classification and velocity
        products_sorted = sorted(
            request.products,
            key=lambda p: (
                abc_classification.get(p.product_id, "C"),
                -p.daily_pick_velocity
            )
        )

        pick_position = 1

        for product in products_sorted:
            classification = abc_classification.get(product.product_id, "C")

            # A items go to picking zone or front of storage
            if classification == "A" and picking_zones:
                zone = picking_zones[0].zone_id
                rationale = "High-velocity item placed in picking zone for efficiency"
            # B items go to main storage area
            elif classification == "B" and storage_zones:
                zone = storage_zones[0].zone_id
                rationale = "Medium-velocity item placed in accessible storage location"
            # C items go to back of storage
            elif storage_zones:
                zone = storage_zones[-1].zone_id if len(storage_zones) > 1 else storage_zones[0].zone_id
                rationale = "Low-velocity item placed in long-term storage"
            else:
                zone = request.zones[0].zone_id
                rationale = "Default storage location"

            # Check for special requirements
            if product.storage_requirements:
                if "refrigerated" in [r.lower() for r in product.storage_requirements]:
                    # Find refrigerated zone if available
                    rationale += " (refrigeration required)"
                if "hazmat" in [r.lower() for r in product.storage_requirements]:
                    rationale += " (hazmat handling required)"

            recommendations.append(StorageRecommendation(
                product_id=product.product_id,
                recommended_zone=zone,
                pick_path_optimization=pick_position if classification == "A" else None,
                rationale=rationale
            ))

            if classification == "A":
                pick_position += 1

        return recommendations

    def _calculate_optimized_utilization(
        self,
        request: WarehouseOptimizationRequest,
        recommendations: List[StorageRecommendation]
    ) -> float:
        """Calculate space utilization after optimization."""
        # Optimization typically improves utilization by 10-20%
        current = self._calculate_space_utilization(request.zones, request.products)

        # Better slotting and organization improves effective utilization
        improvement_factor = 1.15  # 15% improvement

        optimized = min(95.0, current * improvement_factor)  # Cap at 95% for operational efficiency

        return round(optimized, 2)

    def _calculate_picking_improvement(
        self,
        products: List[ProductStorageInfo],
        abc_classification: Dict[str, str],
        recommendations: List[StorageRecommendation]
    ) -> float:
        """Calculate picking efficiency improvement percentage."""
        # Calculate current average pick distance (assuming random placement)
        total_picks = sum(p.daily_pick_velocity for p in products)

        if total_picks == 0:
            return 0.0

        # Current: assume average distance of 50m per pick
        current_distance = 50.0

        # Optimized: A items at 20m, B items at 40m, C items at 60m
        optimized_distance = 0

        for product in products:
            classification = abc_classification.get(product.product_id, "C")
            picks = product.daily_pick_velocity

            if classification == "A":
                distance = 20.0
            elif classification == "B":
                distance = 40.0
            else:
                distance = 60.0

            optimized_distance += (picks * distance)

        optimized_distance /= total_picks

        # Calculate improvement
        improvement = ((current_distance - optimized_distance) / current_distance) * 100

        return round(max(0, improvement), 2)

    def _calculate_capacity_increase(
        self,
        zones: List[WarehouseZone],
        current_utilization: float,
        optimized_utilization: float
    ) -> float:
        """Calculate additional capacity gained in cubic meters."""
        total_storage_space = sum(
            z.area_sqm for z in zones
            if z.zone_type == "storage"
        )

        # Convert to cubic meters (assume 5m height)
        typical_height = 5.0
        total_volume = total_storage_space * typical_height

        # Calculate additional usable capacity
        utilization_gain = (optimized_utilization - current_utilization) / 100
        capacity_increase = total_volume * utilization_gain

        return round(max(0, capacity_increase), 2)

    def _identify_layout_changes(
        self,
        request: WarehouseOptimizationRequest,
        recommendations: List[StorageRecommendation]
    ) -> List[str]:
        """Identify required layout changes."""
        changes = []

        # Count moves by zone
        zone_moves: Dict[str, int] = {}
        for rec in recommendations:
            zone_moves[rec.recommended_zone] = zone_moves.get(rec.recommended_zone, 0) + 1

        # High-velocity items to picking zone
        picking_zone_items = sum(
            1 for rec in recommendations
            if rec.pick_path_optimization is not None
        )

        if picking_zone_items > 0:
            changes.append(
                f"Relocate {picking_zone_items} high-velocity items to picking zone"
            )

        # Reorganization by zone
        for zone_id, count in zone_moves.items():
            if count > 10:
                changes.append(
                    f"Reorganize {count} items in zone {zone_id}"
                )

        # General optimizations
        if request.optimization_goal in ["picking_efficiency", "balanced"]:
            changes.append("Implement pick path optimization with sequential locations")
            changes.append("Create dedicated fast-pick area for A items")

        if request.optimization_goal in ["space", "balanced"]:
            changes.append("Optimize vertical storage utilization")
            changes.append("Consolidate slow-moving items to free up premium space")

        changes.append("Update warehouse management system with new locations")
        changes.append("Train staff on new layout and procedures")

        return changes

    def _estimate_implementation_cost(
        self,
        layout_changes: List[str],
        num_products: int
    ) -> float:
        """Estimate implementation cost."""
        # Base cost for planning and setup
        base_cost = 5000.0

        # Cost per layout change
        change_cost = len(layout_changes) * 500.0

        # Cost per product move (labor + equipment)
        move_cost = num_products * 15.0

        # WMS updates
        system_cost = 2000.0

        # Training
        training_cost = 1000.0

        total_cost = base_cost + change_cost + move_cost + system_cost + training_cost

        return round(total_cost, 2)

    def _estimate_annual_savings(
        self,
        picking_improvement: float,
        capacity_increase: float,
        num_products: int
    ) -> float:
        """Estimate annual cost savings."""
        # Labor savings from picking efficiency
        # Assume $20/hour labor cost, 8 hour days, 250 working days
        # Average 100 picks per day per product
        annual_picks = num_products * 100 * 250
        time_per_pick_minutes = 3.0
        total_pick_time_hours = annual_picks * time_per_pick_minutes / 60

        time_saved_hours = total_pick_time_hours * (picking_improvement / 100)
        labor_savings = time_saved_hours * 20.0

        # Capacity savings (avoided warehouse expansion)
        # Assume $100 per cubic meter per year for warehouse space
        capacity_savings = capacity_increase * 100.0

        # Improved accuracy and reduced errors
        error_reduction_savings = num_products * 50.0

        total_savings = labor_savings + capacity_savings + error_reduction_savings

        return round(total_savings, 2)
