"""
Supplier Risk Assessment Module.

Implements ML-based supplier risk scoring using multiple risk factors
including delivery reliability, quality, financial stability, and geopolitical risks.
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple

import numpy as np
from sklearn.preprocessing import StandardScaler

from .models import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    SupplierRiskAssessment,
    RiskScore,
    SupplierInfo
)
from .config import settings


logger = logging.getLogger(__name__)


class SupplierRiskAssessor:
    """Handles supplier risk assessment and monitoring."""

    def __init__(self):
        """Initialize the risk assessor."""
        self.scaler = StandardScaler()
        self.risk_thresholds = {
            "low": 0.75,
            "medium": 0.50,
            "high": 0.30,
            "critical": 0.0
        }

    def assess(
        self,
        request: RiskAssessmentRequest
    ) -> RiskAssessmentResponse:
        """
        Assess risk for all suppliers.

        Args:
            request: Risk assessment request with supplier information

        Returns:
            Risk assessment response with scores and recommendations
        """
        try:
            logger.info(f"Starting risk assessment for {len(request.suppliers)} suppliers")

            assessments = []
            high_risk_suppliers = []

            for supplier in request.suppliers:
                assessment = self._assess_supplier(supplier, request.risk_factors)
                assessments.append(assessment)

                if assessment.risk_score.risk_category in ["high", "critical"]:
                    high_risk_suppliers.append(supplier.supplier_id)

            # Calculate diversification score
            diversification_score = self._calculate_diversification_score(request.suppliers)

            # Calculate overall supply chain risk
            overall_risk = self._calculate_overall_risk(assessments)

            # Generate recommendations
            recommended_actions = self._generate_recommendations(
                assessments,
                diversification_score,
                request.risk_tolerance
            )

            response = RiskAssessmentResponse(
                assessments=assessments,
                high_risk_suppliers=high_risk_suppliers,
                diversification_score=diversification_score,
                overall_supply_chain_risk=overall_risk,
                recommended_actions=recommended_actions,
                generated_at=datetime.utcnow()
            )

            logger.info(
                f"Risk assessment completed: {len(high_risk_suppliers)} high-risk suppliers, "
                f"overall risk: {overall_risk:.2f}"
            )

            return response

        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            raise

    def _assess_supplier(
        self,
        supplier: SupplierInfo,
        risk_factors: List[str]
    ) -> SupplierRiskAssessment:
        """
        Assess risk for a single supplier.

        Args:
            supplier: Supplier information
            risk_factors: List of risk factors to consider

        Returns:
            Risk assessment for the supplier
        """
        # Calculate individual risk scores
        delivery_risk = self._assess_delivery_risk(supplier)
        quality_risk = self._assess_quality_risk(supplier)
        financial_risk = self._assess_financial_risk(supplier)
        capacity_risk = self._assess_capacity_risk(supplier)
        geopolitical_risk = self._assess_geopolitical_risk(supplier)

        # Calculate overall weighted risk score
        weights = settings.RISK_ASSESSMENT_WEIGHTS
        overall_score = (
            delivery_risk * weights.get("delivery_reliability", 0.25) +
            quality_risk * weights.get("quality", 0.25) +
            financial_risk * weights.get("financial_stability", 0.20) +
            capacity_risk * weights.get("capacity", 0.15) +
            geopolitical_risk * weights.get("geopolitical", 0.10) +
            supplier.historical_metrics.price_stability * weights.get("pricing", 0.05)
        )

        # Determine risk category
        risk_category = self._determine_risk_category(overall_score)

        # Create risk score object
        risk_score = RiskScore(
            overall_score=round(overall_score, 3),
            delivery_risk=round(delivery_risk, 3),
            quality_risk=round(quality_risk, 3),
            financial_risk=round(financial_risk, 3),
            capacity_risk=round(capacity_risk, 3),
            geopolitical_risk=round(geopolitical_risk, 3),
            risk_category=risk_category
        )

        # Identify specific risk factors
        risk_factors_identified = self._identify_risk_factors(
            supplier,
            delivery_risk,
            quality_risk,
            financial_risk,
            capacity_risk,
            geopolitical_risk
        )

        # Generate recommendations
        recommendations = self._generate_supplier_recommendations(
            supplier,
            risk_score,
            risk_factors_identified
        )

        # Determine monitoring frequency
        monitoring_frequency = self._determine_monitoring_frequency(risk_category)

        return SupplierRiskAssessment(
            supplier_id=supplier.supplier_id,
            supplier_name=supplier.supplier_name,
            risk_score=risk_score,
            risk_factors_identified=risk_factors_identified,
            recommendations=recommendations,
            monitoring_frequency=monitoring_frequency
        )

    def _assess_delivery_risk(self, supplier: SupplierInfo) -> float:
        """
        Assess delivery reliability risk.

        Returns score from 0 (high risk) to 1 (low risk).
        """
        metrics = supplier.historical_metrics

        # On-time delivery is the primary factor
        delivery_score = metrics.on_time_delivery_rate

        # Adjust for lead time variance
        variance_penalty = min(0.2, metrics.lead_time_variance / 10)
        delivery_score -= variance_penalty

        # Adjust for response time
        if metrics.response_time_hours > 48:
            delivery_score -= 0.1
        elif metrics.response_time_hours > 24:
            delivery_score -= 0.05

        return max(0.0, min(1.0, delivery_score))

    def _assess_quality_risk(self, supplier: SupplierInfo) -> float:
        """
        Assess quality risk.

        Returns score from 0 (high risk) to 1 (low risk).
        """
        metrics = supplier.historical_metrics

        # Quality score is primary factor
        quality_score = metrics.quality_score

        # Defect rate significantly impacts score
        defect_penalty = metrics.defect_rate * 2
        quality_score -= defect_penalty

        # Certifications provide boost
        certification_bonus = min(0.1, len(supplier.certifications) * 0.02)
        quality_score += certification_bonus

        return max(0.0, min(1.0, quality_score))

    def _assess_financial_risk(self, supplier: SupplierInfo) -> float:
        """
        Assess financial stability risk.

        Returns score from 0 (high risk) to 1 (low risk).
        """
        # Financial stability score is primary factor
        financial_score = supplier.financial_stability_score

        # Years in business provides stability
        if supplier.years_in_business >= 20:
            financial_score += 0.1
        elif supplier.years_in_business >= 10:
            financial_score += 0.05
        elif supplier.years_in_business < 3:
            financial_score -= 0.1

        # Price stability indicates financial health
        price_stability_bonus = supplier.historical_metrics.price_stability * 0.1
        financial_score += price_stability_bonus

        return max(0.0, min(1.0, financial_score))

    def _assess_capacity_risk(self, supplier: SupplierInfo) -> float:
        """
        Assess capacity risk.

        Returns score from 0 (high risk) to 1 (low risk).
        """
        metrics = supplier.historical_metrics

        # Optimal utilization is around 70-80%
        utilization = metrics.capacity_utilization

        if 0.70 <= utilization <= 0.85:
            capacity_score = 1.0
        elif utilization > 0.95:
            # Over-capacity is risky
            capacity_score = 0.5
        elif utilization < 0.50:
            # Under-utilization may indicate problems
            capacity_score = 0.7
        else:
            # Scale based on distance from optimal
            if utilization > 0.85:
                capacity_score = 1.0 - (utilization - 0.85) * 5
            else:
                capacity_score = 0.7 + (utilization - 0.50) * 1.5

        return max(0.0, min(1.0, capacity_score))

    def _assess_geopolitical_risk(self, supplier: SupplierInfo) -> float:
        """
        Assess geopolitical risk based on country.

        Returns score from 0 (high risk) to 1 (low risk).
        """
        # Simplified geopolitical risk scoring
        # In production, this would use external risk databases
        high_risk_countries = [
            "Venezuela", "Iran", "North Korea", "Syria", "Yemen",
            "Afghanistan", "Sudan", "Somalia"
        ]
        medium_risk_countries = [
            "Russia", "Ukraine", "Belarus", "Myanmar", "Zimbabwe",
            "Libya", "Iraq", "Lebanon"
        ]
        low_risk_countries = [
            "USA", "Canada", "Germany", "UK", "France", "Japan",
            "Singapore", "Australia", "Netherlands", "Switzerland"
        ]

        country = supplier.country.strip()

        if country in high_risk_countries:
            return 0.3
        elif country in medium_risk_countries:
            return 0.6
        elif country in low_risk_countries:
            return 0.95
        else:
            # Default moderate risk for unknown countries
            return 0.75

    def _determine_risk_category(self, overall_score: float) -> str:
        """Determine risk category from overall score."""
        if overall_score >= self.risk_thresholds["low"]:
            return "low"
        elif overall_score >= self.risk_thresholds["medium"]:
            return "medium"
        elif overall_score >= self.risk_thresholds["high"]:
            return "high"
        else:
            return "critical"

    def _identify_risk_factors(
        self,
        supplier: SupplierInfo,
        delivery_risk: float,
        quality_risk: float,
        financial_risk: float,
        capacity_risk: float,
        geopolitical_risk: float
    ) -> List[str]:
        """Identify specific risk factors for a supplier."""
        risk_factors = []

        if delivery_risk < 0.7:
            risk_factors.append("Poor on-time delivery performance")
        if supplier.historical_metrics.lead_time_variance > 5:
            risk_factors.append("High lead time variance")
        if quality_risk < 0.7:
            risk_factors.append("Quality concerns")
        if supplier.historical_metrics.defect_rate > 0.05:
            risk_factors.append("High defect rate")
        if financial_risk < 0.6:
            risk_factors.append("Financial instability")
        if supplier.years_in_business < 3:
            risk_factors.append("Limited operating history")
        if capacity_risk < 0.6:
            risk_factors.append("Capacity constraints")
        if supplier.historical_metrics.capacity_utilization > 0.95:
            risk_factors.append("Over-capacity utilization")
        if geopolitical_risk < 0.6:
            risk_factors.append("Geopolitical concerns")
        if supplier.historical_metrics.price_stability < 0.7:
            risk_factors.append("Price volatility")

        return risk_factors

    def _generate_supplier_recommendations(
        self,
        supplier: SupplierInfo,
        risk_score: RiskScore,
        risk_factors: List[str]
    ) -> List[str]:
        """Generate recommendations for a specific supplier."""
        recommendations = []

        if risk_score.risk_category in ["high", "critical"]:
            recommendations.append("Consider identifying alternative suppliers")
            recommendations.append("Increase inventory buffer for products from this supplier")

        if risk_score.delivery_risk < 0.7:
            recommendations.append("Implement delivery performance improvement plan")
            recommendations.append("Consider penalty clauses for late deliveries")

        if risk_score.quality_risk < 0.7:
            recommendations.append("Conduct quality audit")
            recommendations.append("Implement enhanced quality control processes")

        if risk_score.financial_risk < 0.6:
            recommendations.append("Request financial statements and credit reports")
            recommendations.append("Consider requiring payment guarantees")

        if risk_score.capacity_risk < 0.6:
            recommendations.append("Assess supplier capacity expansion plans")
            recommendations.append("Develop contingency suppliers for peak demand")

        if risk_score.geopolitical_risk < 0.6:
            recommendations.append("Diversify sourcing to lower-risk regions")
            recommendations.append("Monitor geopolitical developments closely")

        if not recommendations:
            recommendations.append("Maintain current supplier relationship")
            recommendations.append("Continue standard monitoring procedures")

        return recommendations

    def _determine_monitoring_frequency(self, risk_category: str) -> str:
        """Determine appropriate monitoring frequency based on risk."""
        frequency_map = {
            "low": "quarterly",
            "medium": "monthly",
            "high": "weekly",
            "critical": "daily"
        }
        return frequency_map.get(risk_category, "monthly")

    def _calculate_diversification_score(
        self,
        suppliers: List[SupplierInfo]
    ) -> float:
        """
        Calculate supplier diversification score.

        Higher score indicates better diversification.
        """
        if not suppliers:
            return 0.0

        # Country diversification
        countries = [s.country for s in suppliers]
        unique_countries = len(set(countries))
        country_diversity = min(1.0, unique_countries / 5)  # Target 5+ countries

        # Product category diversification
        all_categories = []
        for supplier in suppliers:
            all_categories.extend(supplier.product_categories)

        category_overlap = len(all_categories) / len(set(all_categories)) if all_categories else 1
        category_diversity = 1.0 / category_overlap

        # Number of suppliers
        supplier_count_score = min(1.0, len(suppliers) / 10)  # Target 10+ suppliers

        # Weighted combination
        diversification_score = (
            country_diversity * 0.4 +
            category_diversity * 0.3 +
            supplier_count_score * 0.3
        )

        return round(diversification_score, 3)

    def _calculate_overall_risk(
        self,
        assessments: List[SupplierRiskAssessment]
    ) -> float:
        """Calculate overall supply chain risk."""
        if not assessments:
            return 1.0

        # Weighted average of supplier risks
        # Give more weight to critical suppliers
        total_weight = 0
        weighted_sum = 0

        for assessment in assessments:
            # Weight based on risk category (higher risk = higher weight)
            weight = {
                "critical": 4.0,
                "high": 3.0,
                "medium": 2.0,
                "low": 1.0
            }.get(assessment.risk_score.risk_category, 2.0)

            weighted_sum += assessment.risk_score.overall_score * weight
            total_weight += weight

        overall_risk = weighted_sum / total_weight if total_weight > 0 else 0.5

        return round(overall_risk, 3)

    def _generate_recommendations(
        self,
        assessments: List[SupplierRiskAssessment],
        diversification_score: float,
        risk_tolerance: str
    ) -> List[str]:
        """Generate overall supply chain recommendations."""
        recommendations = []

        # Diversification recommendations
        if diversification_score < 0.5:
            recommendations.append("Increase supplier diversification across regions and categories")
            recommendations.append("Identify and qualify additional suppliers")

        # High-risk supplier recommendations
        high_risk_count = sum(
            1 for a in assessments
            if a.risk_score.risk_category in ["high", "critical"]
        )

        if high_risk_count > 0:
            recommendations.append(
                f"Address {high_risk_count} high-risk supplier(s) as priority"
            )

        # Risk tolerance-specific recommendations
        if risk_tolerance == "low":
            recommendations.append("Implement dual-sourcing strategy for critical components")
            recommendations.append("Increase safety stock levels for high-risk suppliers")
        elif risk_tolerance == "medium":
            recommendations.append("Balance cost optimization with risk mitigation")
            recommendations.append("Develop contingency plans for critical suppliers")
        else:  # high
            recommendations.append("Focus on cost optimization while monitoring key risks")
            recommendations.append("Implement basic risk mitigation for critical suppliers only")

        # General best practices
        recommendations.append("Conduct regular supplier audits and performance reviews")
        recommendations.append("Maintain updated supplier scorecards and risk profiles")

        return recommendations
