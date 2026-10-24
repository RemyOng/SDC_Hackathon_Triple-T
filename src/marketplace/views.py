"""Role projections of a listing (Opportunity Board Views document).

Partners only ever receive what is built here: bands and approximate figures
until the owner accepts their request (M05). Nothing here scores or ranks.
"""

from typing import Any, Dict, List, Optional

from marketplace.rules import (
    AGE_BANDS,
    BILL_BANDS,
    CAPEX_BANDS,
    UPGRADE_LABELS,
    USAGE_BANDS,
    approx_money,
    approx_tonnes,
    approx_years,
    band_for,
    criteria_checks,
)
from marketplace.store import BoardStore

DISCLAIMER = "Estimates for preparation only. Not financial advice."

HIDDEN_BEFORE_ACCEPTANCE = {
    "investor": [
        "Company name and registration number",
        "Address (only the state is shown), contact details, director names",
        "Exact kWh and RM figures, individual charge lines",
        "Bill and quote files",
    ],
    "supplier": [
        "Company name and registration number",
        "Address (only the state is shown), contact details, director names",
        "Exact kWh and RM figures, monthly bill, individual charge lines",
        "Bill files and other suppliers' quotes or prices",
    ],
}

UNLOCKED_AFTER_ACCEPTANCE = {
    "investor": [
        "Full Preparation Pack, 6 months of bills, quotes, SSM profile",
        "\"Send EOI\" button (the non-binding letter)",
    ],
    "supplier": [
        "Company name, contact person, site address (for the survey)",
        "Bill summary (exact usage) for accurate sizing",
        "\"Send firm quotation\" button",
    ],
}


def primary_upgrade(listing: Dict[str, Any]) -> Dict[str, Any]:
    return listing["upgrades"][0]


def evidence(listing: Dict[str, Any], include_quote: bool = True) -> Dict[str, Any]:
    bill = listing["bill"]
    badge = {
        "months_of_bills": bill["months_of_bills"],
        "reading_type": bill["reading_type"],
        "checks_passed": bill["checks_passed"],
        "checks_total": bill["checks_total"],
    }
    if include_quote:
        badge["quote_attached"] = listing["quote_attached"]
    return badge


def _base_card(listing: Dict[str, Any]) -> Dict[str, Any]:
    company = listing["company"]
    return {
        "id": listing["id"],
        "sector": company["sector"],
        "state": company["state"],
        "size": company["size"],
        "age_band": band_for(company["age_years"], AGE_BANDS),
        "company_status": company["status"],
        "upgrades": [upgrade["type"] for upgrade in listing["upgrades"]],
        "upgrade_labels": [upgrade["label"] for upgrade in listing["upgrades"]],
        "usage_band": band_for(listing["bill"]["average_kwh"], USAGE_BANDS),
        "capex_band": band_for(primary_upgrade(listing)["capex_myr"], CAPEX_BANDS),
        "listed_at": listing["listed_at"],
        "disclaimer": DISCLAIMER,
    }


def identity(listing: Dict[str, Any]) -> Dict[str, Any]:
    company = listing["company"]
    return {
        "company_name": company["name"],
        "reg_no": company["reg_no"],
        "address": company["address"],
        "contact_person": company["contact_person"],
        "contact_phone": company["contact_phone"],
        "contact_email": company["contact_email"],
        "directors": company["directors"],
    }


def _request_summary(request: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not request:
        return None
    return {key: request[key] for key in ("id", "status", "created_at", "decided_at", "document_ids")}


# ---------------------------------------------------------------- investor
def investor_card(store: BoardStore, listing: Dict[str, Any], partner_id: str) -> Dict[str, Any]:
    upgrade = primary_upgrade(listing)
    card = _base_card(listing)
    card.update({
        "bill_band": band_for(listing["bill"]["amount_myr"], BILL_BANDS),
        "saving_approx_myr": approx_money(upgrade["saving_myr_year"]),
        "payback_approx_years": approx_years(upgrade["payback_years"]),
        "co2e_approx_t": approx_tonnes(upgrade["co2e_t_year"]),
        "evidence": evidence(listing),
    })
    checks = criteria_checks(card, store.criteria.get(partner_id, {}))
    card["criteria"] = {
        "checks": checks,
        "passed": sum(check["passed"] for check in checks),
        "total": len(checks),
    }
    request = store.request_for(partner_id, listing["id"])
    card["my_request"] = _request_summary(request)
    if request and request["status"] == "accepted":
        card["identity"] = identity(listing)
    return card


def investor_detail(store: BoardStore, listing: Dict[str, Any], partner_id: str) -> Dict[str, Any]:
    detail = investor_card(store, listing, partner_id)
    detail["hidden"] = HIDDEN_BEFORE_ACCEPTANCE["investor"]
    detail["unlocks"] = UNLOCKED_AFTER_ACCEPTANCE["investor"]
    if "identity" in detail:
        detail["unlocked"] = unlocked_pack(listing)
    return detail


# ---------------------------------------------------------------- supplier
def supplier_matches(partner: Dict[str, Any], listing: Dict[str, Any]) -> Dict[str, Any]:
    """M01: suppliers only see listings in their categories and service area."""
    categories = [kind for kind in partner["categories"] if kind in
                  [upgrade["type"] for upgrade in listing["upgrades"]]]
    in_area = listing["company"]["state"] in partner["service_area"]
    return {"in_service_area": in_area, "matching_categories": categories,
            "visible": in_area and bool(categories)}


def supplier_card(store: BoardStore, listing: Dict[str, Any], partner_id: str) -> Dict[str, Any]:
    partner = store.partners[partner_id]
    card = _base_card(listing)
    ops = listing["operations"]
    card.update({
        "match": supplier_matches(partner, listing),
        "daytime_operation": ops["daytime"],
        "lighting": ops["lighting"],
        "existing_quote": listing["quote_attached"],
        "evidence": evidence(listing, include_quote=False),
    })
    for upgrade in listing["upgrades"]:
        if upgrade["type"] == "solar":
            card["suggested_solar_size"] = upgrade["size"]
    request = store.request_for(partner_id, listing["id"])
    card["my_request"] = _request_summary(request)
    if request and request["status"] == "accepted":
        card["identity"] = identity(listing)
    return card


def supplier_detail(store: BoardStore, listing: Dict[str, Any], partner_id: str) -> Dict[str, Any]:
    detail = supplier_card(store, listing, partner_id)
    detail["hidden"] = HIDDEN_BEFORE_ACCEPTANCE["supplier"]
    detail["unlocks"] = UNLOCKED_AFTER_ACCEPTANCE["supplier"]
    if "identity" in detail:
        bill = listing["bill"]
        detail["unlocked"] = {
            "average_kwh": bill["average_kwh"],
            "usage_kwh": bill["usage_kwh"],
            "history": bill["history"],
            "operations": listing["operations"],
        }
    return detail


# --------------------------------------------------------------------- SME
def unlocked_pack(listing: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "bill": listing["bill"],
        "upgrades": listing["upgrades"],
        "ssm_profile": {
            key: listing["company"][key]
            for key in ("name", "reg_no", "sector", "size", "age_years", "status", "state")
        },
        "quote_attached": listing["quote_attached"],
    }


def partner_public(partner: Dict[str, Any]) -> Dict[str, Any]:
    """What the SME sees about a partner (the partner's own name is visible)."""
    keys = ["id", "type", "name", "contact_name", "contact_title", "address"]
    if partner["type"] == "supplier":
        keys += ["seda_no", "seda_valid_until", "categories", "service_area"]
    else:
        keys += ["unit"]
    return {key: partner[key] for key in keys}


def request_for_sme(store: BoardStore, request: Dict[str, Any]) -> Dict[str, Any]:
    partner = store.partners[request["partner_id"]]
    documents = [store.documents[document_id] for document_id in request["document_ids"]]
    receives = UNLOCKED_AFTER_ACCEPTANCE[partner["type"]][:1]
    return {
        **request,
        "partner": partner_public(partner),
        "documents": documents,
        "will_receive": receives + [
            "Your company name, contact person and site address",
            "Exact usage from your bills",
        ],
    }


def sme_listing(store: BoardStore, listing: Dict[str, Any]) -> Dict[str, Any]:
    requests = [
        request_for_sme(store, request)
        for request in sorted(store.requests.values(), key=lambda item: item["created_at"], reverse=True)
        if request["listing_id"] == listing["id"]
    ]
    return {
        **listing,
        "upgrade_labels": [UPGRADE_LABELS[upgrade["type"]] for upgrade in listing["upgrades"]],
        "evidence": evidence(listing),
        "requests": requests,
        "partner_preview": investor_card(store, listing, partner_id="__preview__"),
        "hidden": HIDDEN_BEFORE_ACCEPTANCE["investor"],
        "disclaimer": DISCLAIMER,
    }


def board_for(store: BoardStore, role: str, partner_id: Optional[str]) -> List[Dict[str, Any]]:
    listings = store.live_listings()
    if role == "investor":
        return [investor_card(store, listing, partner_id) for listing in listings]
    if role == "supplier":
        cards = [supplier_card(store, listing, partner_id) for listing in listings]
        return [card for card in cards if card["match"]["visible"]]
    raise ValueError(role)
