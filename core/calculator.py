import logging
from dataclasses import dataclass
from math import isfinite
from typing import Optional

logger = logging.getLogger(__name__)


GRID_EMISSION_FACTOR_KG_KWH = 0.740  # Energy Commission Peninsular grid factor
TNB_TARIFF_B_MYR_KWH = 0.5068
HOURS_PER_YEAR = 8_760

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
    average_monthly_baseline_kwh: float
    annual_generation_kwh: float
    average_monthly_generation_kwh: float
    usable_offset_kwh: float
    energy_coverage_percent: Optional[float]
    remaining_grid_kwh: float
    excess_generation_kwh: float
    target_capex_myr: float
    projected_annual_savings_myr: float
    average_monthly_savings_myr: float
    annual_tco2e_avoided: float
    average_monthly_tco2e_avoided: float
    simple_roi_percent: Optional[float]
    specific_yield_kwh_per_kwp: Optional[float]
    capacity_factor_percent: Optional[float]
    payback_period_years: Optional[float]


def compute_green_metrics(
    baseline_monthly_kwh: float,
    quote: EquipmentQuote
) -> AuditResult:
    """
    Calculates carbon offset and financial ROI using strict Malaysian parameters.
    Isolated from the VLM to guarantee zero hallucinations in the final dossier.
    """

    if (
        baseline_monthly_kwh < 0
        or quote.system_capacity_kwp < 0
        or quote.total_capex_myr < 0
        or quote.estimated_annual_kwh_gen < 0
    ):
        logger.error("Negative values passed to deterministic calculator.")
        raise ValueError("Inputs to green metrics calculation cannot be negative.")
    values = (
        baseline_monthly_kwh,
        quote.system_capacity_kwp,
        quote.total_capex_myr,
        quote.estimated_annual_kwh_gen,
    )
    if not all(isfinite(value) for value in values):
        raise ValueError("Inputs to green metrics calculation must be finite numbers.")

    # Baseline Extrapolation
    baseline_annual_kwh = baseline_monthly_kwh * 12.0
    average_monthly_generation_kwh = quote.estimated_annual_kwh_gen / 12.0

    # Only generation that offsets on-site consumption is counted as savings or avoided emissions.
    usable_kwh_offset = min(baseline_annual_kwh, quote.estimated_annual_kwh_gen)
    remaining_grid_kwh = max(baseline_annual_kwh - quote.estimated_annual_kwh_gen, 0.0)
    excess_generation_kwh = max(quote.estimated_annual_kwh_gen - baseline_annual_kwh, 0.0)
    energy_coverage_percent = (
        usable_kwh_offset / baseline_annual_kwh * 100.0
        if baseline_annual_kwh > 0
        else None
    )

    # Environmental Math (Carbon Offset) Convert usable kWh to metric tonnes of CO2e avoided.
    total_kg_co2e = usable_kwh_offset * GRID_EMISSION_FACTOR_KG_KWH
    annual_tco2e_avoided = total_kg_co2e / 1000.0

    # Financial Math (Savings & Payback)
    projected_annual_savings_myr = usable_kwh_offset * TNB_TARIFF_B_MYR_KWH
    average_monthly_savings_myr = projected_annual_savings_myr / 12.0
    average_monthly_tco2e_avoided = annual_tco2e_avoided / 12.0
    simple_roi_percent = (
        projected_annual_savings_myr / quote.total_capex_myr * 100.0
        if quote.total_capex_myr > 0
        else None
    )

    if quote.system_capacity_kwp > 0:
        specific_yield_kwh_per_kwp = (
            quote.estimated_annual_kwh_gen / quote.system_capacity_kwp
        )
        capacity_factor_percent = (
            quote.estimated_annual_kwh_gen
            / (quote.system_capacity_kwp * HOURS_PER_YEAR)
            * 100.0
        )
        if capacity_factor_percent > 100.0:
            raise ValueError("Estimated generation cannot exceed 100% capacity factor.")
    else:
        specific_yield_kwh_per_kwp = None
        capacity_factor_percent = None

    # Calculate ROI safely
    if projected_annual_savings_myr > 0:
        payback_period_years = round(quote.total_capex_myr / projected_annual_savings_myr, 2)
    else:
        payback_period_years = None
        logger.warning("Projected savings are zero; payback period is undefined.")

    # Return structured output ensuring float precision
    return AuditResult(
        baseline_annual_kwh=round(baseline_annual_kwh, 2),
        average_monthly_baseline_kwh=round(baseline_annual_kwh / 12.0, 2),
        annual_generation_kwh=round(quote.estimated_annual_kwh_gen, 2),
        average_monthly_generation_kwh=round(average_monthly_generation_kwh, 2),
        usable_offset_kwh=round(usable_kwh_offset, 2),
        energy_coverage_percent=(
            round(energy_coverage_percent, 2)
            if energy_coverage_percent is not None
            else None
        ),
        remaining_grid_kwh=round(remaining_grid_kwh, 2),
        excess_generation_kwh=round(excess_generation_kwh, 2),
        target_capex_myr=round(quote.total_capex_myr, 2),
        projected_annual_savings_myr=round(projected_annual_savings_myr, 2),
        average_monthly_savings_myr=round(average_monthly_savings_myr, 2),
        annual_tco2e_avoided=round(annual_tco2e_avoided, 3),
        average_monthly_tco2e_avoided=round(average_monthly_tco2e_avoided, 3),
        simple_roi_percent=(
            round(simple_roi_percent, 2)
            if simple_roi_percent is not None
            else None
        ),
        specific_yield_kwh_per_kwp=(
            round(specific_yield_kwh_per_kwp, 2)
            if specific_yield_kwh_per_kwp is not None
            else None
        ),
        capacity_factor_percent=(
            round(capacity_factor_percent, 2)
            if capacity_factor_percent is not None
            else None
        ),
        payback_period_years=payback_period_years
    )