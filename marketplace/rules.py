"""Deterministic Opportunity Board rules: bands, upgrade estimates, matching.

Every number a partner sees is derived here from the SME's own data and the
P-parameters below, so the same formula is applied to every listing.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.calculator import (
    GRID_EMISSION_FACTOR_KG_KWH,
    TNB_TARIFF_B_MYR_KWH,
    EquipmentQuote,
    compute_green_metrics,
)

# Parameters (P-table, read-only in the demo)
SOLAR_YIELD_KWH_PER_KWP = 1_320
SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP = 1_991
LED_KWH_SAVED_PER_TUBE_YEAR = 67.6
LED_BENCHMARK_CAPEX_MYR_PER_TUBE = 40
AIRCON_KWH_SAVED_PER_UNIT_YEAR = 1_052
AIRCON_BENCHMARK_CAPEX_MYR_PER_UNIT = 2_200
SUPPLIER_REQUESTS_PER_WEEK = 5
LISTING_DAYS = 90
SUPPLIER_CONNECTION_FEE_MYR = 200
INVESTOR_SUBSCRIPTION_MYR_MONTH = 2_500

UPGRADE_LABELS = {
    "solar": "Rooftop solar",
    "led": "LED lighting",
    "aircon": "Inverter aircon",
}

# (lower bound inclusive, upper bound exclusive, label). None = open-ended.
Band = Tuple[float, Optional[float], str]

USAGE_BANDS: List[Band] = [
    (0, 1_000, "Under 1,000 kWh/month"),
    (1_000, 3_000, "1,000–3,000 kWh/month"),
    (3_000, 5_000, "3,000–5,000 kWh/month"),
    (5_000, 10_000, "5,000–10,000 kWh/month"),
    (10_000, None, "Over 10,000 kWh/month"),
]
BILL_BANDS: List[Band] = [
    (0, 500, "Under RM500"),
    (500, 1_500, "RM500–1,500"),
    (1_500, 2_500, "RM1,500–2,500"),
    (2_500, 5_000, "RM2,500–5,000"),
    (5_000, None, "Over RM5,000"),
]
CAPEX_BANDS: List[Band] = [
    (0, 5_000, "Under RM5k"),
    (5_000, 20_000, "RM5k–20k"),
    (20_000, 50_000, "RM20k–50k"),
    (50_000, 100_000, "RM50k–100k"),
    (100_000, None, "Over RM100k"),
]
AGE_BANDS: List[Band] = [
    (0, 2, "Under 2 years"),
    (2, 5, "2–5 years"),
    (5, 10, "5–10 years"),
    (10, None, "10+ years"),
]


def band_for(value: float, bands: Sequence[Band]) -> str:
    for low, high, label in bands:
        if value >= low and (high is None or value < high):
            return label
    return bands[-1][2]


def band_bounds(label: str, bands: Sequence[Band]) -> Tuple[float, Optional[float]]:
    for low, high, band_label in bands:
        if band_label == label:
            return low, high
    raise ValueError(f"Unknown band: {label}")


@dataclass
class UpgradeEstimate:
    type: str
    label: str
    size: str
    capex_myr: float
    saving_myr_year: float
    payback_years: Optional[float]
    co2e_t_year: float
    basis: str  # "estimate" (benchmark price) or "exact" (valid quote attached)

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _kwh_saving_estimate(kind: str, size: str, kwh_saved: float, capex: float) -> UpgradeEstimate:
    saving = kwh_saved * TNB_TARIFF_B_MYR_KWH
    return UpgradeEstimate(
        type=kind,
        label=UPGRADE_LABELS[kind],
        size=size,
        capex_myr=round(capex, 2),
        saving_myr_year=round(saving, 2),
        payback_years=round(capex / saving, 2) if saving > 0 else None,
        co2e_t_year=round(kwh_saved * GRID_EMISSION_FACTOR_KG_KWH / 1000.0, 3),
        basis="estimate",
    )


def estimate_solar(kwp: float, baseline_monthly_kwh: float, capex_myr: Optional[float] = None) -> UpgradeEstimate:
    capex = capex_myr if capex_myr is not None else kwp * SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP
    result = compute_green_metrics(
        baseline_monthly_kwh=baseline_monthly_kwh,
        quote=EquipmentQuote(
            system_capacity_kwp=kwp,
            total_capex_myr=capex,
            estimated_annual_kwh_gen=kwp * SOLAR_YIELD_KWH_PER_KWP,
        ),
    )
    return UpgradeEstimate(
        type="solar",
        label=UPGRADE_LABELS["solar"],
        size=f"{kwp:g} kWp",
        capex_myr=result.target_capex_myr,
        saving_myr_year=result.projected_annual_savings_myr,
        payback_years=result.payback_period_years,
        co2e_t_year=result.annual_tco2e_avoided,
        basis="exact" if capex_myr is not None else "estimate",
    )


def estimate_led(tubes: int) -> UpgradeEstimate:
    return _kwh_saving_estimate(
        "led", f"{tubes} tubes",
        tubes * LED_KWH_SAVED_PER_TUBE_YEAR,
        tubes * LED_BENCHMARK_CAPEX_MYR_PER_TUBE,
    )


def estimate_aircon(units: int) -> UpgradeEstimate:
    return _kwh_saving_estimate(
        "aircon", f"{units} units",
        units * AIRCON_KWH_SAVED_PER_UNIT_YEAR,
        units * AIRCON_BENCHMARK_CAPEX_MYR_PER_UNIT,
    )


def suggested_solar_kwp(baseline_monthly_kwh: float, daytime_share: float = 0.684) -> float:
    """Size solar to cover the daytime share of usage, rounded to 0.1 kWp."""
    annual_daytime_kwh = baseline_monthly_kwh * 12 * daytime_share
    return round(annual_daytime_kwh / SOLAR_YIELD_KWH_PER_KWP, 1)


# ---------------------------------------------------------------------------
# Approximate figures for partners (exact kWh and RM stay hidden)
# ---------------------------------------------------------------------------

def approx_money(value: float) -> int:
    """Round down to 2 significant figures: 15,453 -> 15,000; 1,370 -> 1,300."""
    if value <= 0:
        return 0
    magnitude = 10 ** (int(math.log10(value)) - 1)
    return int(value // magnitude * magnitude)


def approx_years(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value * 2) / 2  # nearest half year


def approx_tonnes(value: float) -> int:
    return int(value)


# ---------------------------------------------------------------------------
# Investor criteria (M02) and repayment check
# ---------------------------------------------------------------------------

def criteria_checks(card: Dict[str, Any], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return one check per criterion the investor has set; unset ones are skipped."""
    checks = []
    if criteria.get("upgrade"):
        checks.append({
            "label": UPGRADE_LABELS.get(criteria["upgrade"], criteria["upgrade"]),
            "passed": criteria["upgrade"] in card["upgrades"],
        })
    if criteria.get("state"):
        checks.append({"label": criteria["state"], "passed": card["state"] == criteria["state"]})
    if criteria.get("sector"):
        checks.append({"label": criteria["sector"], "passed": card["sector"] == criteria["sector"]})
    if criteria.get("capex_band"):
        checks.append({"label": criteria["capex_band"], "passed": card["capex_band"] == criteria["capex_band"]})
    if criteria.get("min_age_years"):
        low, _ = band_bounds(card["age_band"], AGE_BANDS)
        checks.append({"label": f"{criteria['min_age_years']}+ years", "passed": low >= criteria["min_age_years"]})
    if criteria.get("min_saving_myr"):
        checks.append({
            "label": f"Saving RM{criteria['min_saving_myr']:,}+/year",
            "passed": card["saving_approx_myr"] >= criteria["min_saving_myr"],
        })
    if criteria.get("max_payback_years"):
        payback = card["payback_approx_years"]
        checks.append({
            "label": f"Payback under {criteria['max_payback_years']:g} years",
            "passed": payback is not None and payback < criteria["max_payback_years"],
        })
    return checks


def repayment_check(saving_myr_year: float, loan_myr: float, tenor_years: float, rate_percent: float) -> Dict[str, Any]:
    """Savings coverage on the investor's own terms: yearly saving / yearly instalment."""
    if loan_myr <= 0 or tenor_years <= 0 or rate_percent < 0:
        raise ValueError("Loan amount and tenor must be positive and the rate cannot be negative.")
    months = tenor_years * 12
    monthly_rate = rate_percent / 100 / 12
    if monthly_rate == 0:
        monthly = loan_myr / months
    else:
        monthly = loan_myr * monthly_rate / (1 - (1 + monthly_rate) ** -months)
    yearly = monthly * 12
    return {
        "monthly_instalment_myr": round(monthly, 2),
        "yearly_instalment_myr": round(yearly, 2),
        "saving_used_myr_year": saving_myr_year,
        "coverage": round(saving_myr_year / yearly, 2),
    }
