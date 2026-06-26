"""
Demand Forecasting Module.

Implements time series forecasting using Prophet and LSTM models for
accurate demand prediction with seasonality, trends, and external factors.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("TensorFlow not available, LSTM forecasting disabled")

from .models import (
    DemandForecastRequest,
    DemandForecastResponse,
    ForecastDataPoint,
    TimeSeriesDataPoint
)
from .config import settings


logger = logging.getLogger(__name__)


class DemandForecaster:
    """Handles demand forecasting using multiple models."""

    def __init__(self):
        """Initialize the demand forecaster."""
        self.prophet_models: Dict[str, Prophet] = {}
        self.lstm_models: Dict[str, Any] = {}
        self.scalers: Dict[str, MinMaxScaler] = {}

    def forecast(
        self,
        request: DemandForecastRequest
    ) -> DemandForecastResponse:
        """
        Generate demand forecast using appropriate model.

        Args:
            request: Forecast request with historical data and parameters

        Returns:
            Forecast response with predictions and metrics
        """
        try:
            logger.info(f"Starting demand forecast for product {request.product_id}")

            # Validate input data
            self._validate_input_data(request)

            # Choose model based on data characteristics
            use_lstm = self._should_use_lstm(request)

            if use_lstm and TENSORFLOW_AVAILABLE:
                forecast_data, metrics, trend_info = self._forecast_lstm(request)
            else:
                forecast_data, metrics, trend_info = self._forecast_prophet(request)

            # Detect seasonality
            seasonality_detected = self._detect_seasonality(request.historical_data)

            response = DemandForecastResponse(
                product_id=request.product_id,
                forecast=forecast_data,
                model_metrics=metrics,
                trend_analysis=trend_info,
                seasonality_detected=seasonality_detected,
                model_version=settings.MODEL_VERSION,
                generated_at=datetime.utcnow()
            )

            logger.info(f"Forecast completed for product {request.product_id}")
            return response

        except Exception as e:
            logger.error(f"Forecasting error for product {request.product_id}: {e}")
            raise

    def _validate_input_data(self, request: DemandForecastRequest) -> None:
        """Validate input data quality."""
        if len(request.historical_data) < settings.MIN_HISTORICAL_DATA_POINTS:
            raise ValueError(
                f"Insufficient historical data. Need at least "
                f"{settings.MIN_HISTORICAL_DATA_POINTS} points, got {len(request.historical_data)}"
            )

        # Check for negative values
        values = [dp.value for dp in request.historical_data]
        if any(v < 0 for v in values):
            raise ValueError("Demand values cannot be negative")

        # Check for data gaps
        timestamps = sorted([dp.timestamp for dp in request.historical_data])
        gaps = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
        max_gap = max(gaps) if gaps else 0

        if max_gap > 30:
            logger.warning(f"Large data gap detected: {max_gap} days")

    def _should_use_lstm(self, request: DemandForecastRequest) -> bool:
        """Determine if LSTM should be used instead of Prophet."""
        # Use LSTM for complex patterns with many data points
        has_enough_data = len(request.historical_data) > 200
        has_external_features = request.external_regressors is not None

        return has_enough_data and has_external_features and TENSORFLOW_AVAILABLE

    def _forecast_prophet(
        self,
        request: DemandForecastRequest
    ) -> Tuple[List[ForecastDataPoint], Dict[str, float], Dict[str, Any]]:
        """Generate forecast using Prophet."""
        # Prepare data for Prophet
        df = pd.DataFrame([
            {
                'ds': dp.timestamp,
                'y': dp.value
            }
            for dp in request.historical_data
        ])

        # Initialize and configure Prophet
        model = Prophet(
            seasonality_mode=request.seasonality_mode,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95 if request.include_confidence_intervals else 0.8,
            changepoint_prior_scale=0.05,
        )

        # Add external regressors if provided
        if request.external_regressors:
            for regressor_name, values in request.external_regressors.items():
                df[regressor_name] = values[:len(df)]
                model.add_regressor(regressor_name)

        # Fit model
        model.fit(df)

        # Generate future dates
        future = model.make_future_dataframe(
            periods=request.forecast_horizon,
            freq='D'
        )

        # Add future regressor values if provided
        if request.external_regressors:
            for regressor_name, values in request.external_regressors.items():
                if len(values) >= len(future):
                    future[regressor_name] = values[:len(future)]

        # Make predictions
        forecast = model.predict(future)

        # Extract forecast for future period only
        forecast_future = forecast.tail(request.forecast_horizon)

        # Create forecast data points
        forecast_data = []
        for _, row in forecast_future.iterrows():
            forecast_data.append(ForecastDataPoint(
                timestamp=row['ds'],
                predicted_value=max(0, row['yhat']),  # Ensure non-negative
                lower_bound=max(0, row['yhat_lower']) if request.include_confidence_intervals else None,
                upper_bound=max(0, row['yhat_upper']) if request.include_confidence_intervals else None,
                confidence=0.95 if request.include_confidence_intervals else None
            ))

        # Calculate metrics on historical data
        historical_predictions = forecast.head(len(df))
        metrics = self._calculate_metrics(
            df['y'].values,
            historical_predictions['yhat'].values
        )

        # Extract trend analysis
        trend_info = self._extract_trend_analysis(model, forecast)

        # Store model for product
        self.prophet_models[request.product_id] = model

        return forecast_data, metrics, trend_info

    def _forecast_lstm(
        self,
        request: DemandForecastRequest
    ) -> Tuple[List[ForecastDataPoint], Dict[str, float], Dict[str, Any]]:
        """Generate forecast using LSTM neural network."""
        if not TENSORFLOW_AVAILABLE:
            raise RuntimeError("TensorFlow not available for LSTM forecasting")

        # Prepare data
        values = np.array([dp.value for dp in request.historical_data])

        # Normalize data
        scaler = MinMaxScaler(feature_range=(0, 1))
        values_scaled = scaler.fit_transform(values.reshape(-1, 1))

        # Create sequences for LSTM
        sequence_length = 30
        X, y = self._create_sequences(values_scaled, sequence_length)

        # Build or load LSTM model
        model = self._build_lstm_model(sequence_length)

        # Train model
        model.fit(
            X, y,
            epochs=50,
            batch_size=32,
            validation_split=0.2,
            verbose=0,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=5,
                    restore_best_weights=True
                )
            ]
        )

        # Generate forecasts
        forecast_values = []
        current_sequence = values_scaled[-sequence_length:].reshape(1, sequence_length, 1)

        for _ in range(request.forecast_horizon):
            # Predict next value
            next_value = model.predict(current_sequence, verbose=0)[0, 0]
            forecast_values.append(next_value)

            # Update sequence
            current_sequence = np.roll(current_sequence, -1, axis=1)
            current_sequence[0, -1, 0] = next_value

        # Inverse transform predictions
        forecast_values = scaler.inverse_transform(
            np.array(forecast_values).reshape(-1, 1)
        ).flatten()

        # Create forecast data points
        last_timestamp = request.historical_data[-1].timestamp
        forecast_data = []

        for i, value in enumerate(forecast_values):
            forecast_data.append(ForecastDataPoint(
                timestamp=last_timestamp + timedelta(days=i+1),
                predicted_value=max(0, float(value)),
                lower_bound=None,  # LSTM doesn't provide confidence intervals by default
                upper_bound=None,
                confidence=None
            ))

        # Calculate metrics
        train_predictions = model.predict(X, verbose=0)
        train_predictions = scaler.inverse_transform(train_predictions).flatten()
        actual_values = scaler.inverse_transform(y.reshape(-1, 1)).flatten()

        metrics = self._calculate_metrics(actual_values, train_predictions)

        # Trend analysis
        trend_info = {
            "trend": "increasing" if forecast_values[-1] > forecast_values[0] else "decreasing",
            "average_forecast": float(np.mean(forecast_values)),
            "volatility": float(np.std(forecast_values)),
            "model_type": "LSTM"
        }

        # Store model
        self.lstm_models[request.product_id] = model
        self.scalers[request.product_id] = scaler

        return forecast_data, metrics, trend_info

    def _create_sequences(
        self,
        data: np.ndarray,
        sequence_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        X, y = [], []
        for i in range(len(data) - sequence_length):
            X.append(data[i:i+sequence_length])
            y.append(data[i+sequence_length])
        return np.array(X), np.array(y)

    def _build_lstm_model(self, sequence_length: int) -> Any:
        """Build LSTM model architecture."""
        model = keras.Sequential([
            layers.LSTM(64, return_sequences=True, input_shape=(sequence_length, 1)),
            layers.Dropout(0.2),
            layers.LSTM(32, return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(16, activation='relu'),
            layers.Dense(1)
        ])

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )

        return model

    def _calculate_metrics(
        self,
        actual: np.ndarray,
        predicted: np.ndarray
    ) -> Dict[str, float]:
        """Calculate forecast accuracy metrics."""
        mae = mean_absolute_error(actual, predicted)
        rmse = np.sqrt(mean_squared_error(actual, predicted))
        mape = mean_absolute_percentage_error(actual, predicted) * 100

        # Calculate additional metrics
        mean_actual = np.mean(actual)
        mase = mae / (np.mean(np.abs(np.diff(actual))) + 1e-10)

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "mase": float(mase),
            "mean_actual": float(mean_actual)
        }

    def _extract_trend_analysis(
        self,
        model: Prophet,
        forecast: pd.DataFrame
    ) -> Dict[str, Any]:
        """Extract trend components from Prophet model."""
        trend = forecast['trend'].values

        trend_info = {
            "trend": "increasing" if trend[-1] > trend[0] else "decreasing",
            "trend_strength": float(np.abs(trend[-1] - trend[0]) / (np.mean(trend) + 1e-10)),
            "average_forecast": float(np.mean(forecast['yhat'].tail(30))),
            "volatility": float(np.std(forecast['yhat'].tail(30))),
            "model_type": "Prophet"
        }

        # Add seasonality components if present
        if 'yearly' in forecast.columns:
            trend_info["yearly_seasonality"] = float(np.std(forecast['yearly']))
        if 'weekly' in forecast.columns:
            trend_info["weekly_seasonality"] = float(np.std(forecast['weekly']))

        return trend_info

    def _detect_seasonality(
        self,
        historical_data: List[TimeSeriesDataPoint]
    ) -> bool:
        """Detect if data has significant seasonality."""
        values = np.array([dp.value for dp in historical_data])

        # Use autocorrelation to detect seasonality
        if len(values) < 14:
            return False

        # Calculate autocorrelation at weekly lag (7 days)
        mean = np.mean(values)
        var = np.var(values)

        if var < 1e-10:
            return False

        lag = 7
        if len(values) > lag:
            auto_corr = np.corrcoef(values[:-lag], values[lag:])[0, 1]
            return abs(auto_corr) > 0.3

        return False
