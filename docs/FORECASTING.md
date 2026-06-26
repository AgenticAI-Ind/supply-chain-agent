# Demand Forecasting Methodology

## Overview

This document explains the demand forecasting methodology, model selection, and best practices.

## Model Selection

### Prophet Model

**When to Use:**
- 30-365 days of historical data
- Clear seasonal patterns
- Need interpretability
- Production environments
- Business stakeholders require explainability

**Advantages:**
- Handles missing data well
- Automatic seasonality detection
- Intuitive parameters
- Fast training
- Robust to outliers

**Limitations:**
- Linear trends only
- Limited external features
- Less accurate for complex patterns

### LSTM Model

**When to Use:**
- 200+ days of historical data
- Complex non-linear patterns
- Multiple external features
- High accuracy requirements
- Large-scale deployments

**Advantages:**
- Captures non-linear relationships
- Multiple feature support
- Long-term dependencies
- High accuracy potential

**Limitations:**
- Requires more data
- Longer training time
- Less interpretable
- Requires hyperparameter tuning

## Data Preparation

### Minimum Requirements

- **Data Points**: 30 minimum, 60+ recommended
- **Frequency**: Daily preferred, weekly acceptable
- **Quality**: < 10% missing values
- **Outliers**: Cleaned or explained

### Feature Engineering

**Temporal Features:**
- Day of week
- Month
- Quarter
- Holiday indicators

**Business Features:**
- Promotions
- Price changes
- Marketing campaigns
- Competitor actions

**External Features:**
- Weather data
- Economic indicators
- Market trends
- Social media sentiment

## Model Training

### Prophet Configuration

```python
model = Prophet(
    seasonality_mode='multiplicative',
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,
    interval_width=0.95
)
```

### LSTM Architecture

```python
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(30, 1)),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1)
])
```

## Model Evaluation

### Metrics

**MAE (Mean Absolute Error)**
- Average absolute difference
- Same units as data
- Target: < 10% of mean

**RMSE (Root Mean Squared Error)**
- Emphasizes large errors
- Sensitive to outliers
- Target: < 15% of mean

**MAPE (Mean Absolute Percentage Error)**
- Percentage-based metric
- Easy to interpret
- Target: < 10%

**MASE (Mean Absolute Scaled Error)**
- Baseline comparison
- Scale-independent
- Target: < 1.0

### Validation Strategy

1. **Train/Test Split**: 80/20
2. **Time Series CV**: Rolling window
3. **Holdout Set**: Last 30 days
4. **Production Monitoring**: Weekly accuracy checks

## Confidence Intervals

### Interpretation

- **80% CI**: Likely range (training default)
- **95% CI**: High confidence range (recommended)
- **99% CI**: Very conservative range

### Usage

- Inventory planning: 95% upper bound
- Capacity planning: 95% upper bound
- Budget forecasting: 80% median

## Seasonality Analysis

### Detection Method

Autocorrelation at various lags:
- Weekly: Lag 7
- Monthly: Lag 30
- Quarterly: Lag 90
- Yearly: Lag 365

### Handling Seasonality

**Additive**: Constant seasonal effect
```
Y(t) = Trend + Seasonality + Error
```

**Multiplicative**: Proportional seasonal effect
```
Y(t) = Trend × Seasonality × Error
```

## Production Deployment

### Model Versioning

- Version all models: v1.0.0, v1.1.0, etc.
- Store model artifacts in S3/GCS
- Track model lineage and parameters
- A/B test new models

### Retraining Schedule

**Fast-Moving SKUs**: Weekly
**Standard SKUs**: Monthly
**Slow-Moving SKUs**: Quarterly

### Monitoring

Track in production:
- Forecast vs. actual accuracy
- Model drift indicators
- Data quality metrics
- Feature distribution shifts

### Fallback Strategy

If model fails:
1. Use previous forecast
2. Use moving average
3. Use last year's data
4. Alert operations team

## Best Practices

### Data Quality

✅ **Do:**
- Clean outliers with business context
- Fill missing values appropriately
- Validate data ranges
- Document data sources

❌ **Don't:**
- Remove outliers blindly
- Forward-fill large gaps
- Mix data frequencies
- Use incomplete data

### Model Selection

✅ **Do:**
- Start simple (Prophet)
- Validate on holdout set
- Compare multiple models
- Consider interpretability

❌ **Don't:**
- Jump to complex models
- Overfit on training data
- Ignore business context
- Deploy without validation

### Feature Engineering

✅ **Do:**
- Use domain knowledge
- Test feature importance
- Document feature logic
- Version feature definitions

❌ **Don't:**
- Include future information
- Use highly correlated features
- Over-engineer features
- Ignore feature stability

## Troubleshooting

### Poor Accuracy

**Symptoms**: MAPE > 15%

**Solutions:**
- Add more historical data
- Include external features
- Try different model
- Check for data quality issues

### Model Overfitting

**Symptoms**: Training accuracy >> test accuracy

**Solutions:**
- Reduce model complexity
- Add regularization
- Use more training data
- Simplify features

### Seasonal Mismatch

**Symptoms**: Wrong seasonal pattern

**Solutions:**
- Verify seasonality mode
- Add custom seasonality
- Check data frequency
- Investigate outliers

## Advanced Topics

### Hierarchical Forecasting

Forecast at multiple levels:
- Total company demand
- Category demand
- Product demand
- Reconcile forecasts

### Ensemble Methods

Combine multiple models:
- Prophet + LSTM average
- Weighted ensemble
- Stacking approach
- Boosting techniques

### Probabilistic Forecasting

Generate full distributions:
- Quantile forecasts
- Prediction intervals
- Scenario analysis
- Risk assessment

## Resources

- Prophet Documentation: https://facebook.github.io/prophet/
- TensorFlow Time Series: https://www.tensorflow.org/tutorials/structured_data/time_series
- Forecasting Principles: https://otexts.com/fpp3/
