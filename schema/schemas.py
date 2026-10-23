from pydantic import BaseModel
from typing import Optional, List


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
    tariff: Optional[str] = None
    reading_type: Optional[str] = None

    # Consumption & Metering
    current_month_usage_kwh: Optional[float] = None
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

    # Required for the marketplace flow
    target_capex_myr: Optional[float] = None
    equipment_type: Optional[str] = None
