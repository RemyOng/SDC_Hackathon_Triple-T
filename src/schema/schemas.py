from typing import Any, List, Optional
import re

from pydantic import BaseModel, field_validator


# class ExtractedDocument(BaseModel):
#     document_type: str  # "TNB_BILL" or "VENDOR_QUOTE"
#     account_number: Optional[str] = None
#     company_name: Optional[str] = None
#     baseline_kwh: Optional[float] = None
#     target_capex_myr: Optional[float] = None
#     equipment_type: Optional[str] = None
#


class ExtractedDocument(BaseModel):
    # Core Identity
    account_number: Optional[str] = None
    company_name: Optional[str] = None
    billing_period: Optional[str] = None
    bill_date: Optional[str] = None
    due_date: Optional[str] = None
    tariff: Optional[str] = None
    reading_type: Optional[str] = None

    # Consumption & Metering
    current_month_usage_kwh: Optional[float] = None
    peak_usage_kwh: Optional[float] = None
    offpeak_usage_kwh: Optional[float] = None
    average_usage_kwh: Optional[float] = None
    history_6_months_kwh: Optional[List[float]] = None
    meter_reading_previous: Optional[float] = None
    meter_reading_current: Optional[float] = None
    peak_demand_kw: Optional[float] = None
    reactive_power_kvarh: Optional[float] = None

    # Financial Breakdown (MYR)
    energy_charge_myr: Optional[float] = None
    capacity_charge_myr: Optional[float] = None
    network_charge_myr: Optional[float] = None
    afa_charge_myr: Optional[float] = None
    retail_charge_myr: Optional[float] = None
    ee_incentive_myr: Optional[float] = None
    service_tax_myr: Optional[float] = None
    kwtbb_myr: Optional[float] = None
    current_charges_myr: Optional[float] = None
    total_payable_myr: Optional[float] = None
    previous_balance_myr: Optional[float] = None

    # Required for the marketplace flow
    target_capex_myr: Optional[float] = None
    equipment_type: Optional[str] = None

    @field_validator(
        "current_month_usage_kwh",
        "peak_usage_kwh",
        "offpeak_usage_kwh",
        "average_usage_kwh",
        "history_6_months_kwh",
        "meter_reading_previous",
        "meter_reading_current",
        "peak_demand_kw",
        "reactive_power_kvarh",
        "energy_charge_myr",
        "capacity_charge_myr",
        "network_charge_myr",
        "afa_charge_myr",
        "retail_charge_myr",
        "ee_incentive_myr",
        "service_tax_myr",
        "kwtbb_myr",
        "current_charges_myr",
        "total_payable_myr",
        "target_capex_myr",
        mode="before",
    )
    @classmethod
    def normalize_formatted_numbers(cls, value: Any) -> Any:
        """Accept the thousands separators commonly printed on TNB bills."""
        if isinstance(value, list):
            return [cls._normalize_number(item) for item in value]
        return cls._normalize_number(value)

    @staticmethod
    def _normalize_number(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = re.sub(r"(?i)\b(?:RM|kWh|kW|kVARh)\b", "", value)
        normalized = normalized.replace(",", "").strip()
        return None if normalized == "" else normalized
