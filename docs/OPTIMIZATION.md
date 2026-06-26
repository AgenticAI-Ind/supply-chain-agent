# Route and Inventory Optimization Guide

## Route Optimization

### Vehicle Routing Problem (VRP)

The Vehicle Routing Problem aims to find optimal routes for a fleet of vehicles serving customers, subject to constraints.

### Problem Formulation

**Objective:**
Minimize total cost = transportation cost + vehicle cost + penalty costs

**Constraints:**
- Each customer visited exactly once
- Vehicle capacity not exceeded
- Time windows respected
- Route starts and ends at depot

### Optimization Algorithms

#### 1. Greedy Heuristics

**Nearest Neighbor:**
- Start at depot
- Visit nearest unvisited customer
- Return to depot

**Pros**: Fast, simple
**Cons**: Suboptimal solutions

#### 2. Metaheuristics

**Guided Local Search (GLS):**
- Iteratively improve initial solution
- Escape local optima using penalties
- Balance intensification and diversification

**Used in**: Our production system

#### 3. Exact Methods

**Constraint Programming:**
- Google OR-Tools CP-SAT solver
- Guarantees optimal solution
- May take longer for large problems

### Constraint Types

#### Capacity Constraints

```python
capacity_dimension = routing.AddDimensionWithVehicleCapacity(
    demand_callback,
    0,  # null capacity slack
    vehicle_capacities,
    True,
    'Capacity'
)
```

#### Time Window Constraints

```python
time_dimension = routing.AddDimension(
    time_callback,
    max_waiting_time,
    max_time_per_vehicle,
    False,
    'Time'
)
```

### Performance Tuning

**Search Strategy:**
- PATH_CHEAPEST_ARC: Distance-focused
- PATH_MOST_CONSTRAINED_ARC: Constraint-focused
- AUTOMATIC: Solver chooses

**Local Search:**
- GUIDED_LOCAL_SEARCH: Recommended
- SIMULATED_ANNEALING: Alternative
- TABU_SEARCH: Another option

**Time Limits:**
- Small problems (< 20 stops): 5 seconds
- Medium problems (20-50 stops): 30 seconds
- Large problems (> 50 stops): 60 seconds

### Real-World Considerations

**Traffic:**
- Integrate real-time traffic data
- Use time-dependent travel times
- Consider rush hour patterns

**Driver Preferences:**
- Consistent routes
- Break times
- Skill requirements

**Service Time:**
- Unloading time
- Paperwork
- Customer interaction

## Inventory Optimization

### Economic Order Quantity (EOQ)

#### Formula Derivation

**Total Cost Function:**
```
TC(Q) = (D/Q)S + (Q/2)H

Where:
Q = Order quantity
D = Annual demand
S = Ordering cost per order
H = Holding cost per unit per year
```

**Minimizing Total Cost:**
```
dTC/dQ = -DS/Q² + H/2 = 0
Q* = √(2DS/H)
```

#### Example Calculation

```
D = 5,000 units/year
S = $50/order
H = $5/unit/year

EOQ = √(2 × 5,000 × 50 / 5)
    = √100,000
    = 316 units
```

**Orders per year**: 5,000 / 316 = 15.8
**Order frequency**: 365 / 15.8 = 23 days

### Safety Stock Calculation

#### Formula

```
SS = Z × σ_D × √LT

Where:
Z = Service level z-score
σ_D = Standard deviation of daily demand
LT = Lead time in days
```

#### Service Level Z-Scores

| Service Level | Z-Score |
|---------------|---------|
| 90% | 1.282 |
| 95% | 1.645 |
| 97.5% | 1.960 |
| 99% | 2.326 |
| 99.5% | 2.576 |

#### Example Calculation

```
Average daily demand = 100 units
Standard deviation = 20 units
Lead time = 7 days
Service level = 95% (Z = 1.645)

SS = 1.645 × 20 × √7
   = 1.645 × 20 × 2.646
   = 87 units
```

### Reorder Point (ROP)

#### Formula

```
ROP = (Average Daily Demand × Lead Time) + Safety Stock
```

#### Example

```
Daily demand = 100 units
Lead time = 7 days
Safety stock = 87 units

ROP = (100 × 7) + 87
    = 787 units
```

**Action**: Order when inventory drops below 787 units

### ABC Analysis

#### Classification

**Class A:**
- Top 20% of items by value
- 80% of total inventory value
- Tight control, frequent review

**Class B:**
- Next 30% of items
- 15% of total value
- Moderate control

**Class C:**
- Remaining 50% of items
- 5% of total value
- Simple controls, periodic review

#### Management Strategies

| Class | Review Frequency | Service Level | Safety Stock |
|-------|------------------|---------------|--------------|
| A | Daily/Weekly | 98-99% | High |
| B | Weekly/Monthly | 95-97% | Medium |
| C | Monthly/Quarterly | 90-95% | Low |

### Inventory Turnover

#### Formula

```
Inventory Turnover = Cost of Goods Sold / Average Inventory
```

#### Industry Benchmarks

| Industry | Average Turnover |
|----------|------------------|
| Grocery | 15-20 |
| Electronics | 6-8 |
| Fashion | 4-6 |
| Furniture | 3-4 |
| Automotive | 8-12 |

#### Improvement Strategies

**Increase Turnover:**
- Reduce order quantities
- Eliminate slow-moving items
- Improve demand forecasting
- Negotiate shorter lead times

### Dynamic Inventory Management

#### Adjusting to Variability

**High Demand Variability:**
- Increase safety stock
- More frequent reviews
- Consider buffer stock

**High Lead Time Variability:**
- Increase safety stock
- Earlier ordering
- Alternative suppliers

#### Seasonal Adjustments

**Pre-Season:**
- Build inventory early
- Higher safety stock
- Larger order quantities

**Peak Season:**
- Frequent replenishment
- Monitor stockouts closely
- Expedite when needed

**Post-Season:**
- Reduce inventory
- Clear slow-movers
- Return to normal levels

### Multi-Echelon Optimization

#### Supply Chain Levels

1. **Manufacturing/Supplier**
2. **Distribution Centers**
3. **Regional Warehouses**
4. **Retail Stores**

#### Optimization Strategy

**Push System:**
- Forecast-driven
- Central planning
- Bulk shipments

**Pull System:**
- Demand-driven
- Decentralized
- Frequent replenishment

**Hybrid:**
- Push for long lead time items
- Pull for fast-moving items
- Best of both worlds

### Inventory Metrics

#### Days of Inventory

```
DOI = (Average Inventory / COGS) × 365
```

Target: 30-60 days for most industries

#### Fill Rate

```
Fill Rate = Orders Fulfilled / Total Orders
```

Target: 95-98%

#### Stockout Rate

```
Stockout Rate = Stockout Incidents / Total Demand Occasions
```

Target: < 5%

#### Carrying Cost

```
Carrying Cost = Inventory Value × Carrying Cost %
```

Typical carrying cost: 20-30% annually

### Optimization Software

Our system implements:
- EOQ calculations
- Safety stock optimization
- Reorder point determination
- ABC classification
- Multi-constraint optimization
- Real-time adjustments

### Best Practices

✅ **Do:**
- Review assumptions regularly
- Adjust for seasonality
- Monitor service levels
- Track total costs
- Use data-driven decisions

❌ **Don't:**
- Apply one-size-fits-all
- Ignore demand patterns
- Over-optimize on cost alone
- Neglect supplier reliability
- Set unrealistic service levels

### Case Study

**Company**: Electronics Retailer
**SKUs**: 5,000
**Annual Revenue**: $50M

**Before Optimization:**
- Average inventory: $8M
- Turnover: 6.25x
- Stockout rate: 12%
- Holding cost: $2M/year

**After Optimization:**
- Average inventory: $6M (25% reduction)
- Turnover: 8.33x (33% improvement)
- Stockout rate: 3% (75% reduction)
- Holding cost: $1.5M/year ($500K savings)

**Additional Benefits:**
- Better cash flow
- Reduced obsolescence
- Improved customer satisfaction
- Lower emergency shipping costs

**Total Annual Benefit**: $850K
