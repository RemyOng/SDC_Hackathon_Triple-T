import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


GRID_EMISSION_FACTOR_KG_KWH = 0.760
TNB_TARIFF_B_MYR_KWH = 0.5068

@dataclass
class EquipmentQuote:
    """Represents the proposed green technology upgrade (e.g., Solar PV)."""
    system_capacity_kwp: float
    total_capex_myr: float
    estimated_annual_kwh_gen: float

@dataclass
class AuditResult:
    """The strictly deterministic financial and environmental math output."""
    baseline_annual_kwh: float
    target_capex_myr: float
    projected_annual_savings_myr: float
    annual_tco2e_avoided: float
    payback_period_years: Optional[float]


def compute_green_metrics(
    baseline_monthly_kwh: float,
    quote: EquipmentQuote
) -> AuditResult:
    """
    Calculates carbon offset and financial ROI using strict Malaysian parameters.
    Isolated from the VLM to guarantee zero hallucinations in the final dossier.
    """

    if baseline_monthly_kwh < 0 or quote.total_capex_myr < 0 or quote.estimated_annual_kwh_gen < 0:
        logger.error("Negative values passed to deterministic calculator.")
        raise ValueError("Inputs to green metrics calculation cannot be negative.")

    # Baseline Extrapolation
    baseline_annual_kwh = baseline_monthly_kwh * 12.0

    # Environmental Math (Carbon Offset) Convert total generated kWh to metric tonnes of CO2e avoided
    total_kg_co2e = quote.estimated_annual_kwh_gen * GRID_EMISSION_FACTOR_KG_KWH
    annual_tco2e_avoided = total_kg_co2e / 1000.0

    # Financial Math (Savings & Payback)
    usable_kwh_offset = min(baseline_annual_kwh, quote.estimated_annual_kwh_gen)
    projected_annual_savings_myr = usable_kwh_offset * TNB_TARIFF_B_MYR_KWH

    # Calculate ROI safely
    if projected_annual_savings_myr > 0:
        payback_period_years = round(quote.total_capex_myr / projected_annual_savings_myr, 2)
    else:
        payback_period_years = None
        logger.warning("Projected savings are zero; payback period is undefined.")

    # Return structured output ensuring float precision
    return AuditResult(
        baseline_annual_kwh=round(baseline_annual_kwh, 2),
        target_capex_myr=round(quote.total_capex_myr, 2),
        projected_annual_savings_myr=round(projected_annual_savings_myr, 2),
        annual_tco2e_avoided=round(annual_tco2e_avoided, 3),
        payback_period_years=payback_period_years
    )