"""
Route Optimization Module.

Implements multi-stop route optimization using Google OR-Tools with support
for vehicle capacity constraints, time windows, and multiple optimization objectives.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np

from .models import (
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    OptimizedRoute,
    Location,
    VehicleCapacity
)
from .config import settings


logger = logging.getLogger(__name__)


class RouteOptimizer:
    """Handles route optimization for logistics operations."""

    def __init__(self):
        """Initialize the route optimizer."""
        self.distance_matrix_cache: Dict[str, np.ndarray] = {}

    def optimize(
        self,
        request: RouteOptimizationRequest
    ) -> RouteOptimizationResponse:
        """
        Optimize delivery routes for multiple vehicles.

        Args:
            request: Route optimization request with stops and constraints

        Returns:
            Optimized routes with costs and metrics
        """
        try:
            logger.info(
                f"Starting route optimization with {len(request.stops)} stops "
                f"and {request.num_vehicles} vehicles"
            )

            # Build distance matrix
            distance_matrix, time_matrix = self._build_matrices(request)

            # Create routing model
            manager, routing = self._create_routing_model(request, distance_matrix)

            # Set optimization parameters
            search_parameters = self._configure_search_parameters(request)

            # Add constraints
            if request.vehicle_capacity:
                self._add_capacity_constraints(routing, manager, request)

            self._add_time_window_constraints(routing, manager, request, time_matrix)

            # Set cost function based on objective
            self._set_cost_function(routing, manager, request, distance_matrix, time_matrix)

            # Solve
            start_time = datetime.utcnow()
            solution = routing.SolveWithParameters(search_parameters)
            optimization_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            if not solution:
                raise ValueError("No solution found for route optimization")

            # Extract routes from solution
            routes = self._extract_routes(
                request,
                manager,
                routing,
                solution,
                distance_matrix,
                time_matrix
            )

            # Calculate metrics
            total_distance = sum(r.total_distance_km for r in routes)
            total_time = sum(r.total_time_minutes for r in routes)
            total_cost = sum(r.total_cost for r in routes)

            # Calculate utilization
            utilization = self._calculate_utilization(request, routes)

            # Calculate baseline cost for comparison
            baseline_cost = self._calculate_baseline_cost(request, distance_matrix)
            cost_savings = ((baseline_cost - total_cost) / baseline_cost * 100) if baseline_cost > 0 else 0

            response = RouteOptimizationResponse(
                routes=routes,
                total_distance_km=total_distance,
                total_time_minutes=total_time,
                total_cost=total_cost,
                optimization_time_ms=optimization_time_ms,
                utilization_percentage=utilization,
                cost_savings_vs_baseline=cost_savings,
                generated_at=datetime.utcnow()
            )

            logger.info(
                f"Route optimization completed: {len(routes)} routes, "
                f"{total_distance:.2f}km, {cost_savings:.1f}% savings"
            )

            return response

        except Exception as e:
            logger.error(f"Route optimization error: {e}")
            raise

    def _build_matrices(
        self,
        request: RouteOptimizationRequest
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Build distance and time matrices for all locations."""
        # Create list of all locations (depot + stops)
        locations = [request.depot] + [stop.location for stop in request.stops]
        n = len(locations)

        distance_matrix = np.zeros((n, n))
        time_matrix = np.zeros((n, n))

        # Calculate distances and times
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_km = self._calculate_distance(
                        locations[i],
                        locations[j]
                    )
                    distance_matrix[i][j] = distance_km

                    # Estimate time based on distance and speed
                    time_minutes = (distance_km / settings.DEFAULT_VEHICLE_SPEED_KMH) * 60
                    time_matrix[i][j] = time_minutes

        return distance_matrix, time_matrix

    def _calculate_distance(
        self,
        loc1: Location,
        loc2: Location
    ) -> float:
        """
        Calculate haversine distance between two locations.

        Args:
            loc1: First location
            loc2: Second location

        Returns:
            Distance in kilometers
        """
        # Haversine formula
        R = 6371  # Earth's radius in km

        lat1, lon1 = math.radians(loc1.latitude), math.radians(loc1.longitude)
        lat2, lon2 = math.radians(loc2.latitude), math.radians(loc2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        distance = R * c

        # Add factor for road routing (typically 1.2-1.4x straight line)
        return distance * 1.3

    def _create_routing_model(
        self,
        request: RouteOptimizationRequest,
        distance_matrix: np.ndarray
    ) -> Tuple[pywrapcp.RoutingIndexManager, pywrapcp.RoutingModel]:
        """Create OR-Tools routing model."""
        # Create routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(distance_matrix),
            request.num_vehicles,
            0  # Depot index
        )

        # Create routing model
        routing = pywrapcp.RoutingModel(manager)

        return manager, routing

    def _configure_search_parameters(
        self,
        request: RouteOptimizationRequest
    ) -> pywrapcp.DefaultRoutingSearchParameters:
        """Configure search parameters for optimization."""
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()

        # Set search strategy based on optimization objective
        if request.optimization_objective == "distance":
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
        elif request.optimization_objective == "time":
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC
            )
        else:
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
            )

        # Set local search metaheuristic
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )

        # Set time limit
        search_parameters.time_limit.seconds = settings.MAX_ROUTE_OPTIMIZATION_TIME_MS // 1000

        return search_parameters

    def _add_capacity_constraints(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        request: RouteOptimizationRequest
    ) -> None:
        """Add vehicle capacity constraints."""
        if not request.vehicle_capacity:
            return

        # Create demand callback
        def demand_callback(from_index):
            """Return demand at location."""
            from_node = manager.IndexToNode(from_index)
            if from_node == 0:  # Depot
                return 0

            stop = request.stops[from_node - 1]
            if stop.constraints and stop.constraints.package_weight_kg:
                return int(stop.constraints.package_weight_kg)
            return 0

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        # Add capacity dimension
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [int(request.vehicle_capacity.max_weight_kg)] * request.num_vehicles,
            True,  # start cumul to zero
            'Capacity'
        )

    def _add_time_window_constraints(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        request: RouteOptimizationRequest,
        time_matrix: np.ndarray
    ) -> None:
        """Add time window constraints."""
        # Create time callback
        def time_callback(from_index, to_index):
            """Return travel time between locations."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(time_matrix[from_node][to_node])

        time_callback_index = routing.RegisterTransitCallback(time_callback)

        # Add time dimension
        horizon = 24 * 60  # 24 hours in minutes
        routing.AddDimension(
            time_callback_index,
            horizon,  # allow waiting time
            horizon,  # maximum time per vehicle
            False,  # don't force start cumul to zero
            'Time'
        )

        time_dimension = routing.GetDimensionOrDie('Time')

        # Add time windows for stops
        for i, stop in enumerate(request.stops):
            index = manager.NodeToIndex(i + 1)  # +1 because depot is 0

            if stop.constraints and stop.constraints.time_windows:
                for start_time, end_time in stop.constraints.time_windows:
                    # Convert to minutes from start of day
                    start_minutes = start_time.hour * 60 + start_time.minute
                    end_minutes = end_time.hour * 60 + end_time.minute

                    time_dimension.CumulVar(index).SetRange(start_minutes, end_minutes)

    def _set_cost_function(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        request: RouteOptimizationRequest,
        distance_matrix: np.ndarray,
        time_matrix: np.ndarray
    ) -> None:
        """Set cost function based on optimization objective."""
        if request.optimization_objective == "distance":
            # Cost = distance only
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(distance_matrix[from_node][to_node] * 100)  # Scale for precision

            distance_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        elif request.optimization_objective == "time":
            # Cost = time only
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(time_matrix[from_node][to_node])

            time_callback_index = routing.RegisterTransitCallback(time_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(time_callback_index)

        elif request.optimization_objective == "cost":
            # Cost = fuel + vehicle time cost
            def cost_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                distance = distance_matrix[from_node][to_node]
                time = time_matrix[from_node][to_node]

                fuel_cost = distance * settings.FUEL_COST_PER_KM
                time_cost = (time / 60) * settings.VEHICLE_COST_PER_HOUR

                return int((fuel_cost + time_cost) * 100)

            cost_callback_index = routing.RegisterTransitCallback(cost_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(cost_callback_index)

        else:  # balanced
            # Cost = weighted combination
            def balanced_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                distance = distance_matrix[from_node][to_node]
                time = time_matrix[from_node][to_node]

                return int((distance * 50 + time * 10))

            balanced_callback_index = routing.RegisterTransitCallback(balanced_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(balanced_callback_index)

    def _extract_routes(
        self,
        request: RouteOptimizationRequest,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution: pywrapcp.Assignment,
        distance_matrix: np.ndarray,
        time_matrix: np.ndarray
    ) -> List[OptimizedRoute]:
        """Extract optimized routes from solution."""
        routes = []
        locations = [request.depot] + [stop.location for stop in request.stops]

        for vehicle_id in range(request.num_vehicles):
            index = routing.Start(vehicle_id)
            route_distance = 0
            route_time = 0
            route_stops = []

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_stops.append(locations[node_index])

                next_index = solution.Value(routing.NextVar(index))
                next_node = manager.IndexToNode(next_index)

                # Add distance and time
                route_distance += distance_matrix[node_index][next_node]
                route_time += time_matrix[node_index][next_node]

                index = next_index

            # Add final depot
            node_index = manager.IndexToNode(index)
            route_stops.append(locations[node_index])

            # Skip empty routes
            if len(route_stops) <= 2:  # Only depot start and end
                continue

            # Calculate costs
            fuel_cost = route_distance * settings.FUEL_COST_PER_KM
            time_cost = (route_time / 60) * settings.VEHICLE_COST_PER_HOUR
            total_cost = fuel_cost + time_cost

            routes.append(OptimizedRoute(
                vehicle_id=vehicle_id,
                stops_sequence=route_stops,
                total_distance_km=round(route_distance, 2),
                total_time_minutes=round(route_time, 2),
                total_cost=round(total_cost, 2),
                estimated_fuel_cost=round(fuel_cost, 2)
            ))

        return routes

    def _calculate_utilization(
        self,
        request: RouteOptimizationRequest,
        routes: List[OptimizedRoute]
    ) -> float:
        """Calculate vehicle capacity utilization."""
        if not request.vehicle_capacity:
            return 100.0

        total_capacity = request.num_vehicles * request.vehicle_capacity.max_weight_kg
        total_load = 0

        for stop in request.stops:
            if stop.constraints and stop.constraints.package_weight_kg:
                total_load += stop.constraints.package_weight_kg

        utilization = (total_load / total_capacity * 100) if total_capacity > 0 else 0
        return round(min(utilization, 100.0), 2)

    def _calculate_baseline_cost(
        self,
        request: RouteOptimizationRequest,
        distance_matrix: np.ndarray
    ) -> float:
        """Calculate baseline cost without optimization (nearest neighbor)."""
        # Simple nearest neighbor from depot
        unvisited = set(range(1, len(distance_matrix)))
        current = 0
        total_distance = 0

        while unvisited:
            nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
            total_distance += distance_matrix[current][nearest]
            current = nearest
            unvisited.remove(nearest)

        # Return to depot
        total_distance += distance_matrix[current][0]

        # Calculate cost
        fuel_cost = total_distance * settings.FUEL_COST_PER_KM
        time_cost = (total_distance / settings.DEFAULT_VEHICLE_SPEED_KMH) * settings.VEHICLE_COST_PER_HOUR

        return fuel_cost + time_cost
