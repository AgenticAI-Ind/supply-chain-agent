"""
Supply Chain & Logistics Agent Package.

A production-ready supply chain optimization system with ML-powered forecasting,
route optimization, inventory management, and risk assessment.
"""

from .config import settings
from .main import app

__version__ = "1.0.0"
__all__ = ["app", "settings"]
