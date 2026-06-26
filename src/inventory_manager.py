"""
Inventory Management Module.

Implements inventory optimization using Economic Order Quantity (EOQ),
safety stock calculations, reorder point determination, and dynamic optimization.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple
import math

import numpy as np
from scipy import stats

from .models import (
    InventoryManagementRequest,
    InventoryManagementResponse,
    InventoryRecommendation,
    InventoryItem
)
from .config import settings


logger = logging.getLogger(__name__)


class InventoryManager:
    """Handles inventory optimization and management."""

    def __init__(self):
        """Initialize the inventory manager."""
        pass

    def optimize(
        self,
        request: InventoryManagementRequest
    ) -> InventoryManagementResponse:
        """
        Optimize inventory levels and generate recommendations.

        Args:
            request: Inventory management request with items and demand data

        Returns:
            Recommendations for each item with costs and actions
        """
        try:
            logger.info(f"Starting inventory optimization for {len(request.items)} items")

            recommendations = []
            total_inventory_value = 0
            total_holding_cost = 0
            total_ordering_cost = 0
            total_savings = 0
            stockout_risk_items = []
            overstock_items = []

            for item in request.items:
                # Get average demand for this product
                avg_demand = request.average_daily_demand.get(item.product_id, 0)

                if avg_demand <= 0:
                    logger.warning(f"No demand data for product {item.product_id}, skipping")
                    continue

                # Calculate optimization metrics based on strategy
                if request.optimization_strategy == "eoq":
                    recommendation = self._optimize_eoq(item, avg_demand)
                elif request.optimization_strategy == "dynamic":
                    recommendation = self._optimize_dynamic(
                        item,
                        avg_demand,
                        request.forecast_horizon_days
                    )
                elif request.optimization_strategy == "just_in_time":
                    recommendation = self._optimize_jit(item, avg_demand)
                else:  # safety_stock
                    recommendation = self._optimize_safety_stock(item, avg_demand)

                recommendations.append(recommendation)

                # Aggregate metrics
                total_inventory_value += item.current_stock * item.unit_cost
                total_holding_cost += recommendation.estimated_annual_cost * item.holding_cost_percentage
                total_savings += recommendation.potential_savings

                # Identify risk categories
                if recommendation.recommended_action == "order_now":
                    stockout_risk_items.append(item.product_id)
                elif recommendation.recommended_action == "overstock":
                    overstock_items.append(item.product_id)

            # Calculate total ordering cost
            total_ordering_cost = self._calculate_total_ordering_cost(
                recommendations,
                request.items
            )

            response = InventoryManagementResponse(
                recommendations=recommendations,
                total_inventory_value=round(total_inventory_value, 2),
                total_annual_holding_cost=round(total_holding_cost, 2),
                total_annual_ordering_cost=round(total_ordering_cost, 2),
                total_potential_savings=round(total_savings, 2),
                stockout_risk_items=stockout_risk_items,
                overstock_items=overstock_items,
                generated_at=datetime.utcnow()
            )

            logger.info(
                f"Inventory optimization completed: {len(recommendations)} items, "
                f"${total_savings:.2f} potential savings"
            )

            return response

        except Exception as e:
            logger.error(f"Inventory optimization error: {e}")
            raise

    def _optimize_eoq(
        self,
        item: InventoryItem,
        avg_daily_demand: float
    ) -> InventoryRecommendation:
        """
        Optimize using Economic Order Quantity model.

        EOQ = sqrt((2 * D * S) / H)
        where D = annual demand, S = ordering cost, H = holding cost per unit
        """
        # Calculate annual demand
        annual_demand = avg_daily_demand * 365

        # Calculate holding cost per unit per year
        holding_cost_per_unit = item.unit_cost * item.holding_cost_percentage

        # Calculate EOQ
        if holding_cost_per_unit > 0:
            eoq = math.sqrt(
                (2 * annual_demand * item.ordering_cost) / holding_cost_per_unit
            )
        else:
            eoq = annual_demand / 12  # Monthly order as fallback

        eoq = int(max(1, eoq))

        # Calculate safety stock
        safety_stock = self._calculate_safety_stock(
            avg_daily_demand,
            item.lead_time_days,
            item.demand_variability,
            item.service_level_target
        )

        # Calculate reorder point
        reorder_point = int((avg_daily_demand * item.lead_time_days) + safety_stock)

        # Days until stockout
        days_until_stockout = None
        if avg_daily_demand > 0:
            days_until_stockout = max(0, (item.current_stock - safety_stock) / avg_daily_demand)

        # Determine recommended action
        action, priority = self._determine_action(
            item.current_stock,
            reorder_point,
            safety_stock,
            days_until_stockout
        )

        # Calculate costs
        annual_cost = self._calculate_annual_cost(
            annual_demand,
            eoq,
            item.unit_cost,
            item.ordering_cost,
            item.holding_cost_percentage
        )

        # Calculate potential savings vs current approach
        current_cost = self._calculate_current_cost(
            item,
            annual_demand
        )
        potential_savings = max(0, current_cost - annual_cost)

        return InventoryRecommendation(
            product_id=item.product_id,
            current_stock=item.current_stock,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            economic_order_quantity=eoq,
            optimal_order_quantity=eoq,
            days_until_stockout=round(days_until_stockout, 1) if days_until_stockout is not None else None,
            recommended_action=action,
            order_priority=priority,
            estimated_annual_cost=round(annual_cost, 2),
            potential_savings=round(potential_savings, 2)
        )

    def _optimize_dynamic(
        self,
        item: InventoryItem,
        avg_daily_demand: float,
        forecast_horizon: int
    ) -> InventoryRecommendation:
        """
        Dynamic optimization considering varying demand patterns.
        """
        # Use EOQ as base but adjust for forecast horizon
        base_recommendation = self._optimize_eoq(item, avg_daily_demand)

        # Adjust order quantity based on forecast horizon
        forecast_demand = avg_daily_demand * forecast_horizon
        optimal_order_qty = min(
            base_recommendation.economic_order_quantity,
            int(forecast_demand * 1.2)  # Don't exceed 120% of forecast demand
        )

        # Adjust safety stock dynamically based on demand variability
        dynamic_safety_stock = int(
            base_recommendation.safety_stock * (1 + item.demand_variability)
        )

        # Update reorder point
        reorder_point = int(
            (avg_daily_demand * item.lead_time_days) + dynamic_safety_stock
        )

        base_recommendation.optimal_order_quantity = optimal_order_qty
        base_recommendation.safety_stock = dynamic_safety_stock
        base_recommendation.reorder_point = reorder_point

        # Recalculate action
        days_until_stockout = None
        if avg_daily_demand > 0:
            days_until_stockout = max(
                0,
                (item.current_stock - dynamic_safety_stock) / avg_daily_demand
            )

        action, priority = self._determine_action(
            item.current_stock,
            reorder_point,
            dynamic_safety_stock,
            days_until_stockout
        )

        base_recommendation.recommended_action = action
        base_recommendation.order_priority = priority
        base_recommendation.days_until_stockout = (
            round(days_until_stockout, 1) if days_until_stockout is not None else None
        )

        return base_recommendation

    def _optimize_jit(
        self,
        item: InventoryItem,
        avg_daily_demand: float
    ) -> InventoryRecommendation:
        """
        Just-in-Time optimization minimizing inventory levels.
        """
        # Minimal safety stock
        safety_stock = int(avg_daily_demand * item.lead_time_days * 0.1)

        # Order frequently in small quantities
        order_quantity = int(avg_daily_demand * item.lead_time_days * 1.5)

        # Low reorder point
        reorder_point = int(avg_daily_demand * item.lead_time_days) + safety_stock

        # Calculate days until stockout
        days_until_stockout = None
        if avg_daily_demand > 0:
            days_until_stockout = max(0, (item.current_stock - safety_stock) / avg_daily_demand)

        action, priority = self._determine_action(
            item.current_stock,
            reorder_point,
            safety_stock,
            days_until_stockout
        )

        # JIT has higher ordering costs but lower holding costs
        annual_demand = avg_daily_demand * 365
        num_orders = max(1, annual_demand / order_quantity)
        annual_ordering_cost = num_orders * item.ordering_cost
        avg_inventory = order_quantity / 2 + safety_stock
        annual_holding_cost = avg_inventory * item.unit_cost * item.holding_cost_percentage
        annual_cost = annual_ordering_cost + annual_holding_cost

        current_cost = self._calculate_current_cost(item, annual_demand)
        potential_savings = max(0, current_cost - annual_cost)

        return InventoryRecommendation(
            product_id=item.product_id,
            current_stock=item.current_stock,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            economic_order_quantity=order_quantity,
            optimal_order_quantity=order_quantity,
            days_until_stockout=round(days_until_stockout, 1) if days_until_stockout is not None else None,
            recommended_action=action,
            order_priority=priority,
            estimated_annual_cost=round(annual_cost, 2),
            potential_savings=round(potential_savings, 2)
        )

    def _optimize_safety_stock(
        self,
        item: InventoryItem,
        avg_daily_demand: float
    ) -> InventoryRecommendation:
        """
        Optimize focusing on safety stock and service level.
        """
        # Calculate robust safety stock
        safety_stock = self._calculate_safety_stock(
            avg_daily_demand,
            item.lead_time_days,
            item.demand_variability,
            item.service_level_target
        )

        # Use EOQ for order quantity
        annual_demand = avg_daily_demand * 365
        holding_cost_per_unit = item.unit_cost * item.holding_cost_percentage

        if holding_cost_per_unit > 0:
            eoq = int(math.sqrt(
                (2 * annual_demand * item.ordering_cost) / holding_cost_per_unit
            ))
        else:
            eoq = int(annual_demand / 12)

        # Higher reorder point to ensure service level
        reorder_point = int((avg_daily_demand * item.lead_time_days) + safety_stock * 1.2)

        days_until_stockout = None
        if avg_daily_demand > 0:
            days_until_stockout = max(0, (item.current_stock - safety_stock) / avg_daily_demand)

        action, priority = self._determine_action(
            item.current_stock,
            reorder_point,
            safety_stock,
            days_until_stockout
        )

        annual_cost = self._calculate_annual_cost(
            annual_demand,
            eoq,
            item.unit_cost,
            item.ordering_cost,
            item.holding_cost_percentage
        )

        current_cost = self._calculate_current_cost(item, annual_demand)
        potential_savings = max(0, current_cost - annual_cost)

        return InventoryRecommendation(
            product_id=item.product_id,
            current_stock=item.current_stock,
            reorder_point=reorder_point,
            safety_stock=int(safety_stock),
            economic_order_quantity=eoq,
            optimal_order_quantity=eoq,
            days_until_stockout=round(days_until_stockout, 1) if days_until_stockout is not None else None,
            recommended_action=action,
            order_priority=priority,
            estimated_annual_cost=round(annual_cost, 2),
            potential_savings=round(potential_savings, 2)
        )

    def _calculate_safety_stock(
        self,
        avg_daily_demand: float,
        lead_time_days: int,
        demand_variability: float,
        service_level: float
    ) -> int:
        """
        Calculate safety stock using statistical method.

        Safety Stock = Z * σ_demand * sqrt(lead_time)
        where Z is the z-score for desired service level
        """
        # Get z-score for service level
        z_score = stats.norm.ppf(service_level)

        # Calculate standard deviation of demand
        std_demand = avg_daily_demand * demand_variability

        # Calculate safety stock
        safety_stock = z_score * std_demand * math.sqrt(lead_time_days)

        return int(max(0, safety_stock))

    def _determine_action(
        self,
        current_stock: int,
        reorder_point: int,
        safety_stock: int,
        days_until_stockout: float
    ) -> Tuple[str, int]:
        """Determine recommended action and priority."""
        if days_until_stockout is not None and days_until_stockout < 3:
            return "order_now", 10
        elif current_stock <= reorder_point:
            priority = 8 if current_stock <= safety_stock else 6
            return "order_now", priority
        elif current_stock <= reorder_point * 1.5:
            return "order_soon", 4
        elif current_stock > reorder_point * 3:
            return "overstock", 2
        else:
            return "adequate", 1

    def _calculate_annual_cost(
        self,
        annual_demand: float,
        order_quantity: int,
        unit_cost: float,
        ordering_cost: float,
        holding_cost_percentage: float
    ) -> float:
        """Calculate total annual inventory cost."""
        # Number of orders per year
        num_orders = annual_demand / order_quantity if order_quantity > 0 else 0

        # Annual ordering cost
        annual_ordering_cost = num_orders * ordering_cost

        # Average inventory level
        avg_inventory = order_quantity / 2

        # Annual holding cost
        annual_holding_cost = avg_inventory * unit_cost * holding_cost_percentage

        return annual_ordering_cost + annual_holding_cost

    def _calculate_current_cost(
        self,
        item: InventoryItem,
        annual_demand: float
    ) -> float:
        """Calculate current inventory cost (baseline)."""
        # Assume monthly orders currently
        order_quantity = annual_demand / 12 if annual_demand > 0 else item.current_stock

        return self._calculate_annual_cost(
            annual_demand,
            int(order_quantity),
            item.unit_cost,
            item.ordering_cost,
            item.holding_cost_percentage
        )

    def _calculate_total_ordering_cost(
        self,
        recommendations: List[InventoryRecommendation],
        items: List[InventoryItem]
    ) -> float:
        """Calculate total annual ordering cost for all items."""
        total_cost = 0

        item_dict = {item.product_id: item for item in items}

        for rec in recommendations:
            item = item_dict.get(rec.product_id)
            if not item:
                continue

            # Estimate annual orders
            annual_demand = rec.current_stock * 365 / 30  # Rough estimate
            num_orders = annual_demand / rec.optimal_order_quantity if rec.optimal_order_quantity > 0 else 0

            total_cost += num_orders * item.ordering_cost

        return total_cost
