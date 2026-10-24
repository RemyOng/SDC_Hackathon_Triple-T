"""Investor EOI and supplier proposal drafts.

GreenReady pre-fills the facts from the listing and the rules engine; the
partner only edits the bracketed fields. The same formulas used on the board
recompute savings and payback when the document is sent.
"""

import uuid
from datetime import timedelta
from typing import Any, Dict, List, Tuple

from core.calculator import GRID_EMISSION_FACTOR_KG_KWH, TNB_TARIFF_B_MYR_KWH
from marketplace.rules import (
    AGE_BANDS,
    SOLAR_YIELD_KWH_PER_KWP,
    SUPPLIER_CONNECTION_FEE_MYR,
    band_for,
)
from marketplace.store import BoardError, BoardStore, now
from marketplace.views import DISCLAIMER, evidence, identity, primary_upgrade, supplier_card

VALID_DAYS = 30

# key -> (label, suggested value). Suggested values come from the draft templates.
EOI_FIELDS: List[Tuple[str, str, str]] = [
    ("amount_range", "Indicative amount", "RM40,000 – RM50,000"),
    ("max_percent", "Up to % of final supplier quotation", "90"),
    ("tenure_years", "Indicative tenure (years)", "5"),
    ("facility_type", "Facility type", "Term financing under our green SME programme"),
    ("security", "Security / guarantee", "To be determined, e.g. guarantee scheme where eligible"),
    ("rm_name", "Relationship manager", ""),
    ("contact_days", "Contact within (working days)", "5"),
]

PROPOSAL_FIELDS: List[Tuple[str, str, str]] = [
    ("a_equipment", "Option A equipment", "[Brand] 550 W panels, [brand] string inverter"),
    ("a_price_min", "Option A price from (RM)", "43000"),
    ("a_price_max", "Option A price to (RM)", "47000"),
    ("a_inverter_warranty", "Option A inverter warranty (years)", "10"),
    ("a_panel_warranty", "Option A panel performance warranty (years)", "25"),
    ("b_equipment", "Option B equipment", "[Brand] high-efficiency panels, [brand] hybrid-ready inverter"),
    ("b_price_min", "Option B price from (RM)", "50000"),
    ("b_price_max", "Option B price to (RM)", "55000"),
    ("b_inverter_warranty", "Option B inverter warranty (years)", "12"),
    ("b_panel_warranty", "Option B panel performance warranty (years)", "30"),
    ("installations", "Commercial rooftop installations", "120+"),
    ("since_year", "Installing since", "2019"),
    ("survey_days", "Site survey within (working days)", "5"),
    ("quote_days", "Firm quotation within (working days after survey)", "3"),
    ("atap_weeks", "TNB Solar ATAP application (weeks)", "2–4"),
    ("install_weeks", "Installation and commissioning (weeks)", "1–2"),
    ("signer_name", "Your name", ""),
    ("signer_designation", "Your designation", ""),
]

PRICE_FIELDS = ("a_price_min", "a_price_max", "b_price_min", "b_price_max")


def _field_specs(specs: List[Tuple[str, str, str]]) -> List[Dict[str, str]]:
    return [{"key": key, "label": label, "suggested": value} for key, label, value in specs]


def _clean_fields(specs: List[Tuple[str, str, str]], values: Dict[str, Any]) -> Dict[str, str]:
    cleaned = {key: str(values.get(key, "")).strip() for key, _, _ in specs}
    missing = [label for key, label, _ in specs if not cleaned[key]]
    if missing:
        raise BoardError("Fill in every bracketed field before sending: " + ", ".join(missing) + ".", 422)
    return cleaned


def _dates() -> Dict[str, str]:
    today = now().date()
    return {"date": today.isoformat(), "valid_until": (today + timedelta(days=VALID_DAYS - 1)).isoformat()}


def _solar(listing: Dict[str, Any]) -> Dict[str, Any]:
    for upgrade in listing["upgrades"]:
        if upgrade["type"] == "solar":
            return upgrade
    raise BoardError("This listing does not include rooftop solar.", 409)


# --------------------------------------------------------------------- EOI
def eoi_draft(store: BoardStore, request_id: str, partner_id: str) -> Dict[str, Any]:
    request = store.get_request(request_id)
    if request["partner_id"] != partner_id:
        raise BoardError("This connection belongs to another partner.", 403)
    if request["status"] != "accepted":
        raise BoardError("You can send an EOI only after the owner accepts your request.", 409, "M05")
    listing = store.get_listing(request["listing_id"])
    upgrade = primary_upgrade(listing)
    company = listing["company"]
    bank = store.partners[partner_id]
    project = upgrade["label"].lower()
    if upgrade["type"] == "solar":
        project = f"rooftop solar PV system (approx. {upgrade['size']})"
    return {
        "type": "eoi",
        "request_id": request_id,
        "listing_id": listing["id"],
        **_dates(),
        "from": {key: bank[key] for key in ("name", "unit", "address", "contact_phone", "contact_email", "contact_title")},
        "to": identity(listing),
        "subject": f"GreenReady listing {listing['id']} — {project}",
        "summary": {
            "business": f"{company['size']} {company['sector'].lower()} business, {company['state']}, "
                        f"operating {band_for(company['age_years'], AGE_BANDS)}",
            "upgrade": f"{upgrade['label']}, {upgrade['size']}",
            "capex_myr": upgrade["capex_myr"],
            "saving_myr_year": upgrade["saving_myr_year"],
            "co2e_t_year": upgrade["co2e_t_year"],
            "payback_years": upgrade["payback_years"],
            "basis": upgrade["basis"],
            "evidence": evidence(listing),
        },
        "documents_requested": [
            "Latest 6 months' bank statements",
            "Latest SSM company profile",
            "Latest management or audited accounts",
            "Final supplier quotation from a SEDA-registered PV service provider"
            if upgrade["type"] == "solar" else "Final supplier quotation",
            "Identification documents of directors",
        ],
        "fields": _field_specs(EOI_FIELDS),
        "disclaimer": DISCLAIMER,
    }


def send_eoi(store: BoardStore, request_id: str, partner_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
    with store.lock:
        draft = eoi_draft(store, request_id, partner_id)
        if any(store.documents[doc]["type"] == "eoi" for doc in store.get_request(request_id)["document_ids"]):
            raise BoardError("You have already sent an EOI for this listing.", 409)
        document = {
            **draft,
            "id": f"DOC-{uuid.uuid4().hex[:8].upper()}",
            "reference": store.next_reference("eoi"),
            "values": _clean_fields(EOI_FIELDS, values),
            "status": "sent",
            "sent_at": now().isoformat(timespec="seconds"),
        }
        store.add_document(document)
        store.attach_document(request_id, document["id"])
        store.log("investor", f"Sent EOI {document['reference']}", f"Request · {draft['listing_id']}")
        return document


# ---------------------------------------------------------------- proposal
def solar_estimate(kwp: float) -> Dict[str, float]:
    generation = kwp * SOLAR_YIELD_KWH_PER_KWP
    return {
        "generation_kwh_year": round(generation),
        "saving_myr_year": round(generation * TNB_TARIFF_B_MYR_KWH, 2),
        "co2e_t_year": round(generation * GRID_EMISSION_FACTOR_KG_KWH / 1000, 2),
    }


def proposal_draft(store: BoardStore, listing_id: str, partner_id: str) -> Dict[str, Any]:
    listing = store.get_listing(listing_id)
    card = supplier_card(store, listing, partner_id)
    if not card["match"]["visible"]:
        raise BoardError("This listing is outside your categories or service area.", 403, "M01")
    if "solar" not in card["match"]["matching_categories"]:
        raise BoardError("The proposal draft currently covers rooftop solar listings.", 409)
    solar = _solar(listing)
    kwp = float(solar["size"].split()[0])
    supplier = store.partners[partner_id]
    return {
        "type": "proposal",
        "listing_id": listing_id,
        **_dates(),
        "from": {key: supplier[key] for key in (
            "name", "ssm_no", "seda_no", "seda_valid_until", "address", "contact_phone", "contact_email")},
        "listing": {
            "upgrades": card["upgrade_labels"],
            "state": card["state"],
            "in_service_area": card["match"]["in_service_area"],
            "business": f"{card['size']} {card['sector'].lower()} business, operating {card['age_band']}",
            "usage_band": card["usage_band"],
            "daytime_operation": card["daytime_operation"],
            "suggested_size": solar["size"],
            "existing_quote": card["existing_quote"],
        },
        "system_kwp": kwp,
        "estimate": solar_estimate(kwp),
        "parameters": {
            "solar_yield_kwh_per_kwp": SOLAR_YIELD_KWH_PER_KWP,
            "tariff_myr_kwh": TNB_TARIFF_B_MYR_KWH,
            "grid_factor_kg_kwh": GRID_EMISSION_FACTOR_KG_KWH,
        },
        "fee_myr": SUPPLIER_CONNECTION_FEE_MYR,
        "requests_left": store.supplier_requests_left(partner_id),
        "fields": _field_specs(PROPOSAL_FIELDS),
        "disclaimer": DISCLAIMER,
    }


def _price(value: str, label: str) -> float:
    try:
        amount = float(value.replace(",", "").replace("RM", ""))
    except ValueError:
        raise BoardError(f"{label} must be a number in RM.", 422) from None
    if amount <= 0:
        raise BoardError(f"{label} must be more than RM0.", 422)
    return amount


def proposal_paybacks(saving: float, values: Dict[str, str]) -> Dict[str, Any]:
    labels = {key: label for key, label, _ in PROPOSAL_FIELDS}
    prices = {key: _price(values[key], labels[key]) for key in PRICE_FIELDS}
    for option in ("a", "b"):
        if prices[f"{option}_price_min"] > prices[f"{option}_price_max"]:
            raise BoardError(f"Option {option.upper()}: the 'from' price is higher than the 'to' price.", 422)
    return {
        option: [round(prices[f"{option}_price_min"] / saving, 1), round(prices[f"{option}_price_max"] / saving, 1)]
        for option in ("a", "b")
    }


def send_proposal(store: BoardStore, listing_id: str, partner_id: str, values: Dict[str, Any], message: str = "") -> Dict[str, Any]:
    with store.lock:
        draft = proposal_draft(store, listing_id, partner_id)
        cleaned = _clean_fields(PROPOSAL_FIELDS, values)
        paybacks = proposal_paybacks(draft["estimate"]["saving_myr_year"], cleaned)
        document = {
            **draft,
            "id": f"DOC-{uuid.uuid4().hex[:8].upper()}",
            "reference": store.next_reference("proposal"),
            "values": cleaned,
            "paybacks": paybacks,
            "status": "sent",
            "sent_at": now().isoformat(timespec="seconds"),
        }
        # Creating the request enforces M04 and duplicate checks before the document is kept.
        request = store.create_request("supplier", listing_id, message, document_id=document["id"])
        document["request_id"] = request["id"]
        store.add_document(document)
        return {"request": request, "document": document}
