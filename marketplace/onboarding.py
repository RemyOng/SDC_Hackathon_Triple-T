"""Sign-in (Orbyte Connect, mocked) and SME onboarding (UI spec A1–A4).

The SSM registry below is synthetic; in production the company profile would
come from an SSM data provider and sign-in from Orbyte Connect.
"""

import re
import uuid
from datetime import date
from typing import Any, Dict, Optional

from marketplace.rules import AGE_BANDS, band_for
from marketplace.store import BoardError, BoardStore, now

FREE_CREDIT_MYR = 10.0
ANALYSIS_PRICE_MYR = 2.0
SSM_PATTERN = re.compile(r"^\d{12}$")

# Demo accounts on the sign-in screen (spec §9.4: no login friction).
DEMO_PASSWORD = "demo"
ACCOUNTS = {
    "ahmad@kilangcontoh.example": "sme_owner",
    "siti@kilangcontoh.example": "sme_staff",
    "green.sme@bankhijau.example": "investor",
    "sales@suriahijau.example": "supplier",
    "ops@orbyte.example": "ops",
}

SSM_REGISTRY: Dict[str, Dict[str, Any]] = {
    "202301012345": {
        "name": "Kilang Contoh Sdn Bhd", "type": "Private limited (Sdn Bhd)", "status": "Active",
        "incorporated": "2019-05-14", "msic": "25920", "nature": "Treatment and coating of metals",
        "state": "Selangor", "directors": ["Ahmad"], "employees": 28, "revenue_myr": 4_200_000,
    },
    "201901023456": {
        "name": "Perabot Jati Sdn Bhd", "type": "Private limited (Sdn Bhd)", "status": "Active",
        "incorporated": "2019-03-12", "msic": "31001", "nature": "Manufacture of wooden furniture",
        "state": "Johor", "directors": ["Lim Wei Jie", "Nadia"], "employees": 22, "revenue_myr": 2_400_000,
    },
    "202101045678": {
        "name": "Dobi Bersih Sdn Bhd", "type": "Private limited (Sdn Bhd)", "status": "Active",
        "incorporated": "2021-08-02", "msic": "96010", "nature": "Laundry and dry-cleaning services",
        "state": "Selangor", "directors": ["Priya"], "employees": 6, "revenue_myr": 450_000,
    },
    "201801034567": {
        "name": "Syarikat Lama Sdn Bhd", "type": "Private limited (Sdn Bhd)", "status": "Wound up",
        "incorporated": "2018-01-20", "msic": "47190", "nature": "Retail sale in non-specialised stores",
        "state": "Perak", "directors": ["Osman"], "employees": 0, "revenue_myr": 0,
    },
}

# MSIC section (first two digits) -> GreenReady sector group (C04).
SECTOR_GROUPS = [
    (range(10, 34), "Manufacturing"),
    (range(45, 48), "Wholesale and retail"),
    (range(55, 57), "Hospitality"),
    (range(49, 54), "Logistics"),
    (range(85, 86), "Education"),
    (range(86, 89), "Healthcare"),
]

REGIONS = {
    "Central": {"Selangor", "Kuala Lumpur", "Putrajaya"},
    "Northern": {"Penang", "Kedah", "Perlis", "Perak"},
    "Southern": {"Johor", "Melaka", "Negeri Sembilan"},
    "East Coast": {"Kelantan", "Terengganu", "Pahang"},
    "East Malaysia": {"Sabah", "Sarawak", "Labuan"},
}

QUESTION_CHOICES = {
    "lighting": {"fluorescent", "led", "not_sure"},
    "aircon": {"non_inverter", "inverter", "mixed", "not_sure", "none"},
    "roof_access": {"yes", "no", "not_sure"},
    "daytime": {"yes", "no"},
}


def login(email: str, password: str) -> Dict[str, Any]:
    role = ACCOUNTS.get(email.strip().lower())
    if not role or password != DEMO_PASSWORD:
        raise BoardError(
            "We couldn't sign you in with that email and password. "
            "If your company already uses GreenReady, ask your company owner to add you.",
            401,
        )
    return {"role": role, "email": email.strip().lower()}


def _sector(msic: str) -> str:
    section = int(msic[:2])
    for codes, label in SECTOR_GROUPS:
        if section in codes:
            return label
    return "Services"


def _size(employees: int, revenue: float, sector: str) -> str:
    """C03: SME Corporation Malaysia size definitions."""
    if employees < 5 or revenue < 300_000:
        return "Micro"
    if sector == "Manufacturing":
        return "Small" if employees < 75 and revenue < 15_000_000 else "Medium"
    return "Small" if employees < 30 and revenue < 3_000_000 else "Medium"


def _region(state: str) -> str:
    return next((region for region, states in REGIONS.items() if state in states), "Unknown")


def lookup_company(store: BoardStore, ssm_no: str) -> Dict[str, Any]:
    ssm_no = ssm_no.strip()
    if not SSM_PATTERN.match(ssm_no):
        raise BoardError("Enter the 12-digit SSM registration number, e.g. 201901023456.", 422)
    record = SSM_REGISTRY.get(ssm_no)
    if not record:
        raise BoardError("We couldn't find this number in the SSM registry (demo). Try 201901023456 or 202101045678.", 404)
    incorporated = date.fromisoformat(record["incorporated"])
    age_years = (now().date() - incorporated).days / 365.25
    sector = _sector(record["msic"])
    region = _region(record["state"])
    registered = ssm_no in store.registered_ssm
    checks = {
        "active": {"rule": "C01", "passed": record["status"] == "Active", "label": f"Status: {record['status']}"},
        "age": {"rule": "C02", "passed": True, "label": band_for(age_years, AGE_BANDS)},
        "size": {"rule": "C03", "passed": True, "label": _size(record["employees"], record["revenue_myr"], sector)},
        "sector": {"rule": "C04", "passed": True, "label": sector},
        "region": {"rule": "C06", "passed": region != "East Malaysia", "label": region},
        "duplicate": {"rule": "C07", "passed": not registered, "label": "New to GreenReady" if not registered else "Already registered"},
    }
    blocked = None
    if registered:
        blocked = "This company already has a GreenReady account. Ask the owner for access."
    elif not checks["active"]["passed"]:
        blocked = "Only active companies can join GreenReady. SSM shows this company as " + record["status"].lower() + "."
    elif not checks["region"]["passed"]:
        blocked = "Sabah and Sarawak tariffs are not supported yet."
    return {"ssm_no": ssm_no, **record, "sector": sector, "region": region, "checks": checks, "blocked": blocked}


def register(store: BoardStore, body: Dict[str, Any]) -> Dict[str, Any]:
    with store.lock:
        profile = lookup_company(store, body.get("ssm_no", ""))
        if profile["blocked"]:
            failed = next(check["rule"] for check in profile["checks"].values() if not check["passed"])
            raise BoardError(profile["blocked"], 409, failed)
        owner = str(body.get("owner_name", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        if not owner or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise BoardError("Enter your name and a valid email address.", 422)
        if not body.get("pdpa_consent"):
            raise BoardError("Please agree to the PDPA notice to continue.", 422)
        answers = body.get("answers") or {}
        for key, choices in QUESTION_CHOICES.items():
            if answers.get(key) not in choices:
                raise BoardError("Answer all four quick questions.", 422)
        company_id = f"CO-{uuid.uuid4().hex[:6].upper()}"
        company = {
            "id": company_id,
            "ssm_no": profile["ssm_no"],
            "name": profile["name"],
            "sector": profile["sector"],
            "state": profile["state"],
            "size": profile["checks"]["size"]["label"],
            "age_band": profile["checks"]["age"]["label"],
            "owner_name": owner,
            "email": email,
            "phone": str(body.get("phone", "")).strip(),
            "answers": answers,
            "aircon_units": int(body.get("aircon_units") or 0),
            "pdpa": {"version": "PDPA-2026-1", "consented_at": now().isoformat(timespec="seconds")},
            "wallet_myr": FREE_CREDIT_MYR,
            "created_at": now().isoformat(timespec="seconds"),
        }
        store.companies[company_id] = company
        store.registered_ssm.add(profile["ssm_no"])
        store.audit.append({
            "at": company["created_at"], "user": owner, "role": "SME Owner",
            "action": f"Created GreenReady account for {company['name']} (RM10 free credit)",
            "object": f"Company · {company_id}",
        })
        return {
            "company": company,
            "free_credit_myr": FREE_CREDIT_MYR,
            "free_analyses": int(FREE_CREDIT_MYR // ANALYSIS_PRICE_MYR),
        }


def find_company(store: BoardStore, company_id: Optional[str]) -> Optional[Dict[str, Any]]:
    return store.companies.get(company_id or "")
