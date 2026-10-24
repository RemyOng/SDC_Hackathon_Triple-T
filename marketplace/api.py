"""Opportunity Board API (spec §9.3). Mounted under /api/greenready.

The caller's role comes from the `X-Demo-Role` header set by the demo role
switcher; in Orbyte it would come from the Orbyte Connect session.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from marketplace import bills, documents, onboarding, orbyte, views
from marketplace.rules import (
    AGE_BANDS,
    CAPEX_BANDS,
    INVESTOR_SUBSCRIPTION_MYR_MONTH,
    SUPPLIER_CONNECTION_FEE_MYR,
    SUPPLIER_REQUESTS_PER_WEEK,
    UPGRADE_LABELS,
    repayment_check,
)
from marketplace.seed import SME_COMPANY_LISTING
from marketplace.store import ROLE_LABELS, ROLE_PARTNER, BoardError, store

router = APIRouter(prefix="/api/greenready", tags=["GreenReady Opportunity Board"])

SME_ROLES = {"sme_owner", "sme_staff"}


def board_error_handler(_: Request, exc: BoardError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "rule": exc.rule})


def current_role(x_demo_role: str = Header("sme_owner")) -> str:
    if x_demo_role not in ROLE_LABELS:
        raise HTTPException(400, f"Unknown role '{x_demo_role}'.")
    return x_demo_role


def _partner(role: str, allowed: set) -> str:
    if role not in allowed:
        raise BoardError("This page is not available for your role.", 403)
    return ROLE_PARTNER[role]


class RequestIn(BaseModel):
    listing_id: str
    message: str = Field("", max_length=1000)


class DeclineIn(BaseModel):
    reason: str = Field("", max_length=500)


class RepaymentIn(BaseModel):
    loan_myr: float = Field(gt=0)
    tenor_years: float = Field(gt=0, le=30)
    rate_percent: float = Field(ge=0, le=30)


class CriteriaIn(BaseModel):
    upgrade: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[str] = None
    capex_band: Optional[str] = None
    min_age_years: Optional[int] = Field(None, ge=0)
    min_saving_myr: Optional[int] = Field(None, ge=0)
    max_payback_years: Optional[float] = Field(None, gt=0)


class EoiIn(BaseModel):
    request_id: str
    values: Dict[str, Any]


class ProposalIn(BaseModel):
    listing_id: str
    values: Dict[str, Any]
    message: str = Field("", max_length=1000)


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class RegisterIn(BaseModel):
    ssm_no: str
    owner_name: str = Field(max_length=120)
    email: str = Field(max_length=200)
    phone: str = Field("", max_length=40)
    pdpa_consent: bool = False
    answers: Dict[str, str] = {}
    aircon_units: int = Field(0, ge=0, le=500)


# ------------------------------------------------- sign-in and onboarding
@router.post("/auth/login")
def login(body: LoginIn) -> Dict[str, Any]:
    return onboarding.login(body.email, body.password)


@router.get("/onboarding/ssm/{ssm_no}")
def ssm_lookup(ssm_no: str) -> Dict[str, Any]:
    return onboarding.lookup_company(store, ssm_no)


@router.post("/onboarding/register")
def register(body: RegisterIn) -> Dict[str, Any]:
    return onboarding.register(store, body.model_dump())


class BillFieldsIn(BaseModel):
    values: Dict[str, Any] = {}
    confirm_all: bool = False


# -------------------------------------------------------------------- bills
def _sme(role: str) -> None:
    if role not in SME_ROLES:
        raise BoardError("Bills belong to the SME. Switch to the owner or staff role.", 403)


@router.get("/bills")
def list_bills(role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    ordered = sorted(store.bills.values(), key=lambda bill: bill["uploaded_at"], reverse=True)
    return {
        "bills": [bills.summary(bill) for bill in ordered],
        "price_myr": bills.ANALYSIS_PRICE_MYR,
        "balance_myr": store.wallet_balance(),
        "ai_reader": bills.ai_reader(),
    }


@router.get("/bills/{bill_id}")
def get_bill(bill_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    return bills.detail(bills.get(store, bill_id))


@router.post("/bills/upload")
async def upload_bill(file: UploadFile = File(...), role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    content = await file.read(bills.MAX_UPLOAD_BYTES + 1)
    return bills.detail(bills.upload(store, role, file.filename or "bill", content))


@router.post("/bills/manual")
def manual_bill(body: Dict[str, Any], role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    return bills.detail(bills.manual(store, role, body))


@router.patch("/bills/{bill_id}/fields")
def correct_bill(bill_id: str, body: BillFieldsIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    return bills.detail(bills.correct(store, role, bill_id, body.values, body.confirm_all))


@router.get("/bills/{bill_id}/recommendations")
def bill_recommendations(bill_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    _sme(role)
    operations = store.get_listing(SME_COMPANY_LISTING)["operations"]
    result = bills.recommendations(store, bills.get(store, bill_id), operations)
    listing = store.get_listing(SME_COMPANY_LISTING)
    result["pack"] = {"listing_id": listing["id"], "status": listing["status"]} if listing["status"] == "live" else None
    return result


# ------------------------------------------------------------ Orbyte shell
@router.get("/session")
def session(role: str = Depends(current_role)) -> Dict[str, Any]:
    partner = store.partners.get(ROLE_PARTNER.get(role, ""))
    return {
        "role": role,
        "role_label": ROLE_LABELS[role],
        "organization": partner["name"] if partner else orbyte.ORGANIZATION["name"],
        "roles": [{"id": key, "label": label} for key, label in ROLE_LABELS.items()],
        "supplier_requests_left": store.supplier_requests_left(ROLE_PARTNER["supplier"]),
        "requests_per_week": SUPPLIER_REQUESTS_PER_WEEK,
    }


@router.get("/menus")
def menus(role: str = Depends(current_role)) -> Dict[str, Any]:
    return orbyte.menus_for(role)


@router.get("/action-items")
def action_items(role: str = Depends(current_role)) -> Dict[str, Any]:
    return orbyte.action_items(store, role)


@router.get("/wallet")
def wallet(role: str = Depends(current_role)) -> Dict[str, Any]:
    if role not in SME_ROLES:
        raise BoardError("The credit wallet belongs to the SME.", 403)
    return orbyte.wallet(store)


@router.get("/wallet/transactions")
def wallet_transactions(role: str = Depends(current_role)) -> Dict[str, Any]:
    if role != "sme_owner":
        raise BoardError("Only the owner can view wallet transactions.", 403, "C05")
    return orbyte.wallet_transactions(store)


# -------------------------------------------------------------------- board
@router.get("/board/filters")
def board_filters() -> Dict[str, Any]:
    listings = store.live_listings()
    return {
        "sectors": sorted({item["company"]["sector"] for item in listings}),
        "states": sorted({item["company"]["state"] for item in listings}),
        "upgrades": [{"id": key, "label": label} for key, label in UPGRADE_LABELS.items()],
        "capex_bands": [label for _, _, label in CAPEX_BANDS],
        "age_bands": [label for _, _, label in AGE_BANDS],
    }


@router.get("/board")
def board(role: str = Depends(current_role)) -> Dict[str, Any]:
    partner_id = _partner(role, {"investor", "supplier"})
    payload: Dict[str, Any] = {
        "listings": views.board_for(store, role, partner_id),
        "note": "Listings are not scored or ranked. Newest first.",
    }
    if role == "investor":
        payload["criteria"] = store.criteria.get(partner_id, {})
    else:
        partner = store.partners[partner_id]
        payload["requests_left"] = store.supplier_requests_left(partner_id)
        payload["requests_per_week"] = SUPPLIER_REQUESTS_PER_WEEK
        payload["categories"] = [UPGRADE_LABELS[kind] for kind in partner["categories"]]
        payload["service_area"] = partner["service_area"]
    return payload


@router.get("/criteria")
def get_criteria(role: str = Depends(current_role)) -> Dict[str, Any]:
    return store.criteria.get(_partner(role, {"investor"}), {})


@router.put("/criteria")
def put_criteria(body: CriteriaIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    partner_id = _partner(role, {"investor"})
    store.criteria[partner_id] = {key: value for key, value in body.model_dump().items() if value not in (None, "")}
    store.log(role, "Saved My criteria", "Criteria")
    return store.criteria[partner_id]


@router.get("/listings/{listing_id}")
def listing_detail(listing_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    listing = store.get_listing(listing_id)
    if role in SME_ROLES:
        if listing_id != SME_COMPANY_LISTING:
            raise BoardError("You can only open your own company's listing.", 403)
        return views.sme_listing(store, listing)
    partner_id = _partner(role, {"investor", "supplier"})
    if listing["status"] != "live" and not store.is_connected(partner_id, listing_id):
        raise BoardError("This listing is no longer live.", 410)
    if role == "investor":
        return views.investor_detail(store, listing, partner_id)
    detail = views.supplier_detail(store, listing, partner_id)
    if not detail["match"]["visible"]:
        raise BoardError("This listing is outside your categories or service area.", 403, "M01")
    detail["requests_left"] = store.supplier_requests_left(partner_id)
    return detail


@router.get("/sme/listing")
def sme_listing(role: str = Depends(current_role)) -> Dict[str, Any]:
    if role not in SME_ROLES:
        raise BoardError("Only the SME can see its own listing.", 403)
    return views.sme_listing(store, store.get_listing(SME_COMPANY_LISTING))


@router.post("/listings/{listing_id}/unlist")
def unlist(listing_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    listing = store.unlist(listing_id, role)
    return {"id": listing["id"], "status": listing["status"]}


@router.post("/listings/{listing_id}/repayment-check")
def listing_repayment_check(listing_id: str, body: RepaymentIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    partner_id = _partner(role, {"investor"})
    card = views.investor_card(store, store.get_listing(listing_id), partner_id)
    try:
        result = repayment_check(card["saving_approx_myr"], body.loan_myr, body.tenor_years, body.rate_percent)
    except ValueError as exc:
        raise BoardError(str(exc), 422) from exc
    result["note"] = "Your terms, your decision. GreenReady does not assess credit."
    return result


# ----------------------------------------------------------------- requests
@router.post("/requests")
def create_request(body: RequestIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    if role == "supplier":
        raise BoardError("Suppliers connect by sending a proposal.", 400)
    return store.create_request(role, body.listing_id, body.message)


@router.get("/requests")
def list_requests(role: str = Depends(current_role)) -> Dict[str, Any]:
    ordered = sorted(store.requests.values(), key=lambda item: item["created_at"], reverse=True)
    if role in SME_ROLES:
        return {"requests": [
            views.request_for_sme(store, request)
            for request in ordered if request["listing_id"] == SME_COMPANY_LISTING
        ]}
    partner_id = _partner(role, {"investor", "supplier"})
    card = views.investor_card if role == "investor" else views.supplier_card
    return {"requests": [
        {
            **request,
            "listing": card(store, store.get_listing(request["listing_id"]), partner_id),
            "documents": [store.documents[document_id] for document_id in request["document_ids"]],
        }
        for request in ordered if request["partner_id"] == partner_id
    ]}


@router.post("/requests/{request_id}/accept")
def accept_request(request_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    return views.request_for_sme(store, store.decide(request_id, role, accept=True))


@router.post("/requests/{request_id}/decline")
def decline_request(request_id: str, body: DeclineIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    return views.request_for_sme(store, store.decide(request_id, role, accept=False, reason=body.reason))


# ---------------------------------------------------------------- documents
@router.get("/documents/eoi/draft")
def eoi_draft(request_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    return documents.eoi_draft(store, request_id, _partner(role, {"investor"}))


@router.post("/documents/eoi")
def send_eoi(body: EoiIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    return documents.send_eoi(store, body.request_id, _partner(role, {"investor"}), body.values)


@router.get("/documents/proposal/draft")
def proposal_draft(listing_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    return documents.proposal_draft(store, listing_id, _partner(role, {"supplier"}))


@router.post("/documents/proposal")
def send_proposal(body: ProposalIn, role: str = Depends(current_role)) -> Dict[str, Any]:
    return documents.send_proposal(store, body.listing_id, _partner(role, {"supplier"}), body.values, body.message)


@router.get("/documents/{document_id}")
def get_document(document_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    document = store.documents.get(document_id)
    if not document:
        raise BoardError(f"Document {document_id} not found.", 404)
    owner_partner = {"eoi": "P-BH", "proposal": "P-SHS"}[document["type"]]
    if role in SME_ROLES:
        if document["listing_id"] != SME_COMPANY_LISTING:
            raise BoardError("This document belongs to another company.", 403)
    elif ROLE_PARTNER.get(role) != owner_partner:
        raise BoardError("You can only open documents you sent.", 403)
    return document


@router.post("/documents/{document_id}/accept")
def accept_document(document_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    return store.respond_to_document(document_id, role, accept=True)


@router.post("/documents/{document_id}/decline")
def decline_document(document_id: str, role: str = Depends(current_role)) -> Dict[str, Any]:
    return store.respond_to_document(document_id, role, accept=False)


# --------------------------------------------------------- billing / audit
@router.get("/billing")
def billing(role: str = Depends(current_role)) -> Dict[str, Any]:
    partner_id = _partner(role, {"investor", "supplier"})
    if role == "investor":
        return {
            "plan": "Bank / investor subscription",
            "monthly_fee_myr": INVESTOR_SUBSCRIPTION_MYR_MONTH,
            "next_invoice": "2026-11-01",
            "invoices": [
                {"number": "OR-INV-2026-1001", "period": "Oct 2026", "amount_myr": INVESTOR_SUBSCRIPTION_MYR_MONTH, "status": "Paid"},
            ],
        }
    fees = [fee for fee in store.partner_fees if fee["partner_id"] == partner_id]
    pending = [
        {"request_id": request["id"], "listing_id": request["listing_id"], "sent_at": request["created_at"]}
        for request in store.requests.values()
        if request["partner_id"] == partner_id and request["status"] == "requested"
    ]
    return {
        "plan": "Pay per accepted connection",
        "fee_per_connection_myr": SUPPLIER_CONNECTION_FEE_MYR,
        "next_invoice": "2026-11-01",
        "accepted_connections": fees,
        "pending_requests": pending,
        "requests_left": store.supplier_requests_left(partner_id),
        "requests_per_week": SUPPLIER_REQUESTS_PER_WEEK,
        "month_to_date_myr": sum(fee["amount_myr"] for fee in fees),
    }


@router.get("/audit")
def audit(role: str = Depends(current_role), object: Optional[str] = None) -> Dict[str, Any]:
    rows = store.audit
    if role in {"investor", "supplier"}:
        name = store.partners[ROLE_PARTNER[role]]["name"]
        rows = [row for row in rows if row["user"] == name]
    if object:
        rows = [row for row in rows if object.lower() in row["object"].lower()]
    return {"events": list(reversed(rows))}


@router.post("/ops/reset")
def reset_demo(role: str = Depends(current_role)) -> Dict[str, str]:
    if role != "ops":
        raise BoardError("Only Orbyte Ops can reset the demo.", 403)
    store.reset()
    return {"status": "reset"}
