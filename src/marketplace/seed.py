"""Synthetic demo data (spec §7). Every company, bank and supplier is fictional."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from marketplace.rules import (
    LISTING_DAYS,
    estimate_aircon,
    estimate_led,
    estimate_solar,
    suggested_solar_kwp,
)

TODAY = date(2026, 10, 24)


def _listing(
    listing_id: str,
    listed: date,
    company: Dict[str, Any],
    history_kwh: List[float],
    bill_myr: float,
    upgrades: List[str],
    operations: Dict[str, Any],
    views: Dict[str, int],
    solar_kwp: Optional[float] = None,
    led_tubes: int = 0,
    aircon_units: int = 0,
    quote_attached: bool = False,
    bill_months: int = 6,
    real_cost_per_kwh: Optional[float] = None,
) -> Dict[str, Any]:
    average = sum(history_kwh) / len(history_kwh)
    estimates = []
    for kind in upgrades:
        if kind == "solar":
            estimates.append(estimate_solar(solar_kwp or suggested_solar_kwp(average), average))
        elif kind == "led":
            estimates.append(estimate_led(led_tubes))
        elif kind == "aircon":
            estimates.append(estimate_aircon(aircon_units))
    return {
        "id": listing_id,
        "status": "live",
        "listed_at": listed.isoformat(),
        "expires_at": (listed + timedelta(days=LISTING_DAYS)).isoformat(),
        "company": company,
        "bill": {
            "month": "Sep 2026",
            "amount_myr": bill_myr,
            "due": "2026-11-10",
            "usage_kwh": history_kwh[-1],
            "average_kwh": round(average, 2),
            "history": dict(zip(["Apr", "May", "Jun", "Jul", "Aug", "Sep"], history_kwh)),
            "months_of_bills": bill_months,
            "reading_type": "actual",
            "checks_passed": 8,
            "checks_total": 8,
            # B04 from the rules engine where known (spec §7), else a simple bill / kWh estimate.
            "real_cost_per_kwh": real_cost_per_kwh or round(bill_myr / history_kwh[-1], 2),
        },
        "operations": operations,
        "upgrades": [estimate.as_dict() for estimate in estimates],
        "quote_attached": quote_attached,
        "views": views,
    }


def _company(name, reg_no, sector, state, size, age_years, address, contact, phone, email) -> Dict[str, Any]:
    return {
        "name": name,
        "reg_no": reg_no,
        "sector": sector,
        "state": state,
        "size": size,
        "age_years": age_years,
        "status": "Active",
        "address": address,
        "contact_person": contact,
        "contact_phone": phone,
        "contact_email": email,
        "directors": [contact.split(" (")[0]],
    }


def seed_listings() -> List[Dict[str, Any]]:
    return [
        _listing(
            "GR-L-0871", date(2026, 10, 23),
            _company(
                "Kilang Contoh Sdn Bhd", "202301012345", "Manufacturing", "Selangor", "Small", 7,
                "Lot 12, Jalan Perindustrian 3, 40000 Shah Alam, Selangor",
                "Ahmad (Director)", "+60 12-000 0871", "ahmad@kilangcontoh.example",
            ),
            [3520, 3610, 3480, 3650, 3610, 4420], 2140,
            ["solar", "led"],
            {"daytime": True, "lighting": "Fluorescent", "aircon": "Non-inverter", "roof_access": True,
             "led_tubes": 40, "aircon_units": 3},
            {"investors": 18, "suppliers": 9},
            solar_kwp=23.1, led_tubes=40, real_cost_per_kwh=0.51,
        ),
        _listing(
            "GR-L-0866", date(2026, 10, 21),
            _company(
                "Roti Pagi Enterprise", "202001033218", "Food and beverage", "Kuala Lumpur", "Micro", 4,
                "No. 8, Jalan Pasar Baru, 55100 Kuala Lumpur",
                "Mei Ling (Owner)", "+60 12-000 0866", "owner@rotipagi.example",
            ),
            [1810, 1860, 1790, 1900, 1880, 1950], 1010,
            ["led", "aircon"],
            {"daytime": True, "lighting": "Fluorescent", "aircon": "Non-inverter", "roof_access": False},
            {"investors": 6, "suppliers": 4},
            led_tubes=24, aircon_units=2,
        ),
        _listing(
            "GR-L-0859", date(2026, 10, 19),
            _company(
                "Cetak Jaya Sdn Bhd", "201601022871", "Printing", "Selangor", "Small", 10,
                "Lot 3, Jalan Industri 5, 47100 Puchong, Selangor",
                "Rajesh (Director)", "+60 12-000 0859", "rajesh@cetakjaya.example",
            ),
            [5120, 5340, 5210, 5480, 5390, 5560], 2890,
            ["solar"],
            {"daytime": True, "lighting": "LED", "aircon": "Mixed", "roof_access": True},
            {"investors": 11, "suppliers": 7},
        ),
        _listing(
            "GR-L-0852", date(2026, 10, 16),
            _company(
                "Klinik Sejahtera Sdn Bhd", "201801045522", "Healthcare", "Penang", "Small", 8,
                "No. 21, Lebuh Pantai, 10300 George Town, Penang",
                "Dr. Farah (Director)", "+60 12-000 0852", "admin@kliniksejahtera.example",
            ),
            [2760, 2810, 2900, 2950, 2880, 3010], 1640,
            ["aircon", "led"],
            {"daytime": True, "lighting": "Fluorescent", "aircon": "Non-inverter", "roof_access": False},
            {"investors": 5, "suppliers": 6},
            led_tubes=30, aircon_units=4,
        ),
        _listing(
            "GR-L-0847", date(2026, 10, 14),
            _company(
                "Logistik Pantas Sdn Bhd", "201401011209", "Logistics", "Negeri Sembilan", "Small", 12,
                "Lot 45, Kawasan Perindustrian Nilai, 71800 Nilai, Negeri Sembilan",
                "Hafiz (Director)", "+60 12-000 0847", "hafiz@logistikpantas.example",
            ),
            [6900, 7050, 7120, 6980, 7210, 7300], 3790,
            ["solar", "led"],
            {"daytime": True, "lighting": "Fluorescent", "aircon": "Inverter", "roof_access": True},
            {"investors": 14, "suppliers": 10},
            led_tubes=80,
        ),
        _listing(
            "GR-L-0841", date(2026, 10, 10),
            _company(
                "Bengkel Auto Maju", "201901028804", "Automotive services", "Johor", "Micro", 6,
                "No. 17, Jalan Kempas Lama, 81200 Johor Bahru, Johor",
                "Kumar (Owner)", "+60 12-000 0841", "kumar@automaju.example",
            ),
            [1420, 1380, 1460, 1500, 1440, 1520], 790,
            ["solar"],
            {"daytime": True, "lighting": "LED", "aircon": "None", "roof_access": True},
            {"investors": 3, "suppliers": 5},
        ),
        _listing(
            "GR-L-0836", date(2026, 10, 7),
            _company(
                "Pusat Tuisyen Bijak", "202101019930", "Education", "Selangor", "Micro", 3,
                "No. 5, Jalan SS15/4, 47500 Subang Jaya, Selangor",
                "Aisyah (Owner)", "+60 12-000 0836", "aisyah@bijak.example",
            ),
            [980, 1010, 1040, 1090, 1060, 1120], 560,
            ["aircon"],
            {"daytime": False, "lighting": "LED", "aircon": "Non-inverter", "roof_access": False},
            {"investors": 2, "suppliers": 3},
            aircon_units=5, bill_months=4,
        ),
        _listing(
            "GR-L-0829", date(2026, 10, 2),
            _company(
                "Hotel Bayu Melaka Sdn Bhd", "201201007713", "Hospitality", "Melaka", "Small", 14,
                "No. 30, Jalan Merdeka, 75000 Melaka",
                "Tan (Director)", "+60 12-000 0829", "tan@bayumelaka.example",
            ),
            [8800, 9020, 9150, 9300, 9240, 9410], 4870,
            ["solar", "aircon", "led"],
            {"daytime": True, "lighting": "Fluorescent", "aircon": "Non-inverter", "roof_access": True},
            {"investors": 16, "suppliers": 12},
            aircon_units=12, led_tubes=120, quote_attached=True,
        ),
    ]


PARTNERS: Dict[str, Dict[str, Any]] = {
    "P-BH": {
        "id": "P-BH",
        "type": "investor",
        "name": "Bank Hijau Berhad",
        "unit": "SME Green Financing Unit",
        "contact_name": "Nurul",
        "contact_title": "Relationship Manager, SME Green Financing",
        "contact_phone": "+60 3-0000 1200",
        "contact_email": "green.sme@bankhijau.example",
        "address": "Menara Hijau, Jalan Sultan Ismail, 50250 Kuala Lumpur",
    },
    "P-SHS": {
        "id": "P-SHS",
        "type": "supplier",
        "name": "Suria Hijau Solar Sdn Bhd",
        "ssm_no": "202201054321",
        "seda_no": "RPVSP-2026-0318",
        "seda_valid_until": "2027-06-30",
        "categories": ["solar", "led"],
        "service_area": ["Selangor", "Kuala Lumpur", "Negeri Sembilan"],
        "contact_name": "Daniel",
        "contact_title": "Business Development Manager",
        "contact_phone": "+60 3-0000 3180",
        "contact_email": "sales@suriahijau.example",
        "address": "No. 2, Jalan Teknologi 3/1, 47810 Petaling Jaya, Selangor",
    },
}

# Spec §7: Bank Hijau's saved criteria give 5 of 5 on GR-L-0871.
DEFAULT_CRITERIA = {
    "P-BH": {
        "upgrade": "solar",
        "state": "Selangor",
        "capex_band": "RM20k–50k",
        "min_age_years": 5,
        "max_payback_years": 5,
    },
}

# Supplier proposals already sent this week (M04: 5 per week -> 3 left).
SUPPLIER_REQUESTS_USED_THIS_WEEK = {"P-SHS": 2}

SME_COMPANY_LISTING = "GR-L-0871"
SME_COMPANY_SSM = "202301012345"

# Orbyte credit wallet ledger for Kilang Contoh (balance RM6.00).
WALLET_LEDGER = [
    {"amount": 10.00, "type": "CREDIT", "reason": "GreenReady free starting credit", "at": "2026-10-20T09:00:00+08:00"},
    {"amount": -2.00, "type": "DEBIT", "reason": "Bill analysis · Aug 2026", "at": "2026-10-20T09:12:00+08:00"},
    {"amount": -2.00, "type": "DEBIT", "reason": "Bill analysis · Sep 2026", "at": "2026-10-23T10:03:00+08:00"},
    {"amount": 79.00, "type": "TOPUP", "reason": "Orbyte wallet top-up", "at": "2026-10-23T10:18:00+08:00"},
    {"amount": -79.00, "type": "DEBIT", "reason": "Preparation Pack · GR-L-0871", "at": "2026-10-23T10:20:00+08:00"},
]


def _at(day: date, hhmm: str) -> str:
    hour, minute = (int(part) for part in hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute).isoformat() + "+08:00"


def seed_audit() -> List[Dict[str, Any]]:
    day = date(2026, 10, 23)
    rows = [
        ("10:02", "Siti", "SME Staff", "Submitted Sep bill via eClaim", "Bill · Sep 2026"),
        ("10:03", "GreenReady AI", "System", "Read 23 fields (2 flagged under 85%)", "Bill · Sep 2026"),
        ("10:05", "Siti", "SME Staff", "Fixed 2 flagged fields", "Bill · Sep 2026"),
        ("10:06", "Rules engine", "System", "8/8 checks passed", "Bill · Sep 2026"),
        ("10:20", "Ahmad", "SME Owner", "Bought Preparation Pack (RM79)", "Pack · GR-L-0871"),
        ("10:21", "Ahmad", "SME Owner", "Approved listing GR-L-0871 for 90 days", "Listing · GR-L-0871"),
    ]
    return [
        {"at": _at(day, hhmm), "user": user, "role": role, "action": action, "object": obj}
        for hhmm, user, role, action, obj in rows
    ]
