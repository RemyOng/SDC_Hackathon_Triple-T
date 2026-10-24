"""TNB Peninsular Malaysia tariff schedule effective 1 July 2025 to 31 December 2027.

Rates are transcribed from Suruhanjaya Tenaga's published schedule. Monetary
rates are MYR; energy rates are MYR/kWh and demand rates are MYR/kW/month.
The bill validator uses these definitions only when the uploaded tariff can
be identified. Otherwise it validates the bill's internal arithmetic without
inventing a tariff model.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Tariff:
    code: str
    name: str
    energy_rate: Optional[float]
    capacity_rate: Optional[float]
    network_rate: Optional[float]
    retail_charge: float
    tou: bool = False
    energy_peak_rate: Optional[float] = None
    energy_offpeak_rate: Optional[float] = None
    demand_based: bool = False
    rebate_cap: Optional[float] = None


TARIFFS: Dict[str, Tariff] = {
    "DOMESTIC_GENERAL": Tariff("DOMESTIC_GENERAL", "Domestic General", .2703, .0455, .1285, 10, rebate_cap=.05),
    "DOMESTIC_TOU": Tariff("DOMESTIC_TOU", "Domestic ToU", None, .0455, .1285, 10, True, .2852, .2443, rebate_cap=.05),
    "LOW_VOLTAGE_GENERAL": Tariff("LOW_VOLTAGE_GENERAL", "Non-domestic Low Voltage General", .2703, .0883, .1482, 20, rebate_cap=.05),
    "LOW_VOLTAGE_TOU": Tariff("LOW_VOLTAGE_TOU", "Non-domestic Low Voltage ToU", None, .0883, .1482, 20, True, .2852, .2443, rebate_cap=.05),
    "MEDIUM_VOLTAGE_GENERAL": Tariff("MEDIUM_VOLTAGE_GENERAL", "Non-domestic Medium Voltage General", .2983, 29.43, 59.84, 200, demand_based=True, rebate_cap=.05),
    "MEDIUM_VOLTAGE_TOU": Tariff("MEDIUM_VOLTAGE_TOU", "Non-domestic Medium Voltage ToU", None, 30.19, 66.87, 200, True, .3132, .2723, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_GENERAL": Tariff("HIGH_VOLTAGE_GENERAL", "Non-domestic High Voltage General", .4303, 16.68, 14.53, 250, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_TOU": Tariff("HIGH_VOLTAGE_TOU", "Non-domestic High Voltage ToU", None, 21.76, 23.06, 250, True, .4452, .4043, demand_based=True, rebate_cap=.05),
    "LOW_VOLTAGE_AGRICULTURE": Tariff("LOW_VOLTAGE_AGRICULTURE", "Low Voltage Agriculture / Water / Sewerage", .2703, .0619, .1119, 10, rebate_cap=.05),
    "LOW_VOLTAGE_AGRICULTURE_TOU": Tariff("LOW_VOLTAGE_AGRICULTURE_TOU", "Low Voltage Agriculture / Water / Sewerage ToU", None, .0619, .1119, 10, True, .2852, .2443, rebate_cap=.05),
    "MEDIUM_VOLTAGE_AGRICULTURE": Tariff("MEDIUM_VOLTAGE_AGRICULTURE", "Medium Voltage Agriculture / Water / Sewerage", .2703, 24.50, 44.84, 200, demand_based=True, rebate_cap=.05),
    "MEDIUM_VOLTAGE_AGRICULTURE_TOU": Tariff("MEDIUM_VOLTAGE_AGRICULTURE_TOU", "Medium Voltage Agriculture / Water / Sewerage ToU", None, 27.83, 50.65, 200, True, .2852, .2443, demand_based=True, rebate_cap=.05),
    "STREET_LIGHTING": Tariff("STREET_LIGHTING", "Street Lighting", .2703, .0244, .1425, 5, rebate_cap=.05),
    "MEDIUM_VOLTAGE_BULK": Tariff("MEDIUM_VOLTAGE_BULK", "Medium Voltage Bulk ToU", None, 30.21, 37.17, 200, True, .3032, .2623, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_BULK": Tariff("HIGH_VOLTAGE_BULK", "High Voltage Bulk ToU", None, 29.24, 26.02, 250, True, .4052, .3643, demand_based=True, rebate_cap=.05),
    "MEDIUM_VOLTAGE_TES": Tariff("MEDIUM_VOLTAGE_TES", "Medium Voltage Thermal Energy Storage ToU", None, 26.63, 68.28, 200, True, .3132, .2723, demand_based=True, rebate_cap=.05),
    "MEDIUM_VOLTAGE_TRACTION": Tariff("MEDIUM_VOLTAGE_TRACTION", "Medium Voltage Traction", .2983, 21.51, 53.69, 200, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_TRACTION": Tariff("HIGH_VOLTAGE_TRACTION", "High Voltage Traction", .4303, 17.12, 15.54, 250, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_ULTRA": Tariff("HIGH_VOLTAGE_ULTRA", "High Voltage Ultra ToU", None, 21.76, 23.06, 250, True, .5518, .5109, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_ULTRA_BULK": Tariff("HIGH_VOLTAGE_ULTRA_BULK", "High Voltage Ultra Bulk ToU", None, 29.24, 26.02, 250, True, .5118, .4709, demand_based=True, rebate_cap=.05),
    "MEDIUM_VOLTAGE_BACKFEED": Tariff("MEDIUM_VOLTAGE_BACKFEED", "Medium Voltage Backfeed", .2983, 29.43, None, 200, demand_based=True, rebate_cap=.05),
    "HIGH_VOLTAGE_BACKFEED": Tariff("HIGH_VOLTAGE_BACKFEED", "High Voltage Backfeed", .4303, 16.68, None, 250, demand_based=True, rebate_cap=.05),
    "COGEN_MEDIUM_GENERAL": Tariff("COGEN_MEDIUM_GENERAL", "Co-generator Medium Voltage General", .2983, 29.43, 59.84, 200, demand_based=True, rebate_cap=.05),
    "COGEN_MEDIUM_TOU": Tariff("COGEN_MEDIUM_TOU", "Co-generator Medium Voltage ToU", None, 30.19, 66.87, 200, True, .3132, .2723, demand_based=True, rebate_cap=.05),
    "COGEN_HIGH_GENERAL": Tariff("COGEN_HIGH_GENERAL", "Co-generator High Voltage General", .4303, 16.68, 14.53, 250, demand_based=True, rebate_cap=.05),
    "COGEN_HIGH_TOU": Tariff("COGEN_HIGH_TOU", "Co-generator High Voltage ToU", None, 21.76, 23.06, 250, True, .4452, .4043, demand_based=True, rebate_cap=.05),
}


def resolve_tariff(label: object) -> Optional[Tariff]:
    text = str(label or "").lower().replace("-", " ").replace("_", " ")
    if not text:
        return None
    aliases = {
        "a": "DOMESTIC_GENERAL", "domestic": "DOMESTIC_GENERAL", "domestik am": "DOMESTIC_GENERAL",
        "domestic tou": "DOMESTIC_TOU", "domestik tou": "DOMESTIC_TOU",
        "b": "LOW_VOLTAGE_GENERAL", "tariff b": "LOW_VOLTAGE_GENERAL",
        "low voltage": "LOW_VOLTAGE_GENERAL", "bukan domestik voltan rendah am": "LOW_VOLTAGE_GENERAL",
        "low voltage tou": "LOW_VOLTAGE_TOU", "bukan domestik voltan rendah tou": "LOW_VOLTAGE_TOU",
        "street lighting": "STREET_LIGHTING", "lampu jalan": "STREET_LIGHTING",
        "agriculture": "LOW_VOLTAGE_AGRICULTURE", "pertanian": "LOW_VOLTAGE_AGRICULTURE",
    }
    for key, code in aliases.items():
        if (len(key) == 1 and text.strip() == key) or (len(key) > 1 and key in text):
            return TARIFFS[code]
    for code, tariff in TARIFFS.items():
        if tariff.name.lower() in text:
            return tariff
    if "high voltage" in text or "voltan tinggi" in text:
        return TARIFFS["HIGH_VOLTAGE_TOU" if "tou" in text else "HIGH_VOLTAGE_GENERAL"]
    if "medium voltage" in text or "voltan sederhana" in text:
        return TARIFFS["MEDIUM_VOLTAGE_TOU" if "tou" in text else "MEDIUM_VOLTAGE_GENERAL"]
    return None
