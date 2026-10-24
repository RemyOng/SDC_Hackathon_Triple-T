"""In-memory demo store for the Opportunity Board.

Mocks the Supabase tables listings / partners / requests / documents /
wallet_ledger / audit_log (spec §9.2) so the demo runs without credentials.
`reset()` reloads the synthetic seed (the Ops "Reset demo" button).
"""

import copy
import threading
import uuid
from typing import Any, Dict, List, Optional

from marketplace import seed
from marketplace.bills import seed_bills
from marketplace.common import MYT, BoardError, now  # noqa: F401  (re-exported for other modules)
from marketplace.rules import SUPPLIER_CONNECTION_FEE_MYR, SUPPLIER_REQUESTS_PER_WEEK

ROLE_LABELS = {
    "sme_owner": "SME Owner",
    "sme_staff": "SME Staff",
    "investor": "Investor",
    "supplier": "Supplier",
    "ops": "Orbyte Ops",
}
ROLE_USERS = {"sme_owner": "Ahmad", "sme_staff": "Siti", "ops": "Orbyte Ops"}
ROLE_PARTNER = {"investor": "P-BH", "supplier": "P-SHS"}


class BoardStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.listings: Dict[str, Dict[str, Any]] = {
                listing["id"]: listing for listing in seed.seed_listings()
            }
            self.partners = copy.deepcopy(seed.PARTNERS)
            self.criteria = copy.deepcopy(seed.DEFAULT_CRITERIA)
            self.supplier_week_used = dict(seed.SUPPLIER_REQUESTS_USED_THIS_WEEK)
            self.requests: Dict[str, Dict[str, Any]] = {}
            self.documents: Dict[str, Dict[str, Any]] = {}
            self.wallet_ledger = copy.deepcopy(seed.WALLET_LEDGER)
            self.partner_fees: List[Dict[str, Any]] = []
            self.audit: List[Dict[str, Any]] = seed.seed_audit()
            self.counters = {"eoi": 141, "proposal": 317}
            self.companies: Dict[str, Dict[str, Any]] = {}
            self.registered_ssm = {seed.SME_COMPANY_SSM}
            self.bills: Dict[str, Dict[str, Any]] = seed_bills()

    # ------------------------------------------------------------------ audit
    def log(self, role: str, action: str, obj: str) -> None:
        """`role` is a demo role, or "system" for the AI reader and rules engine."""
        if role in ROLE_PARTNER:
            user = self.partners[ROLE_PARTNER[role]]["name"]
        else:
            user = ROLE_USERS.get(role, "GreenReady")
        self.audit.append({
            "at": now().isoformat(timespec="seconds"),
            "user": user,
            "role": "System" if role == "system" else ROLE_LABELS.get(role, role),
            "action": action,
            "object": obj,
        })

    # --------------------------------------------------------------- listings
    def live_listings(self) -> List[Dict[str, Any]]:
        today = now().date().isoformat()
        for listing in self.listings.values():
            if listing["status"] == "live" and listing["expires_at"] < today:
                listing["status"] = "expired"
        # M03: newest first only. No score or "best" ordering exists.
        return sorted(
            (item for item in self.listings.values() if item["status"] == "live"),
            key=lambda item: (item["listed_at"], item["id"]),
            reverse=True,
        )

    def get_listing(self, listing_id: str) -> Dict[str, Any]:
        listing = self.listings.get(listing_id)
        if not listing:
            raise BoardError(f"Listing {listing_id} not found.", 404)
        return listing

    def unlist(self, listing_id: str, role: str) -> Dict[str, Any]:
        require_owner(role, "unlist this listing")
        with self.lock:
            listing = self.get_listing(listing_id)
            listing["status"] = "unlisted"
            for request in self.requests.values():
                if request["listing_id"] == listing_id and request["status"] == "requested":
                    request["status"] = "expired"
            self.log(role, f"Unlisted {listing_id}", f"Listing · {listing_id}")
            return listing

    # --------------------------------------------------------------- requests
    def request_for(self, partner_id: str, listing_id: str) -> Optional[Dict[str, Any]]:
        matches = [
            request for request in self.requests.values()
            if request["partner_id"] == partner_id and request["listing_id"] == listing_id
        ]
        return max(matches, key=lambda item: item["created_at"]) if matches else None

    def is_connected(self, partner_id: str, listing_id: str) -> bool:
        request = self.request_for(partner_id, listing_id)
        return bool(request and request["status"] == "accepted")

    def supplier_requests_left(self, partner_id: str) -> int:
        return max(SUPPLIER_REQUESTS_PER_WEEK - self.supplier_week_used.get(partner_id, 0), 0)

    def create_request(
        self,
        role: str,
        listing_id: str,
        message: str = "",
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        partner_id = ROLE_PARTNER.get(role)
        if not partner_id:
            raise BoardError("Only investors and suppliers can send requests.", 403)
        with self.lock:
            listing = self.get_listing(listing_id)
            if listing["status"] != "live":
                raise BoardError("This listing is no longer live.", 409)
            existing = self.request_for(partner_id, listing_id)
            if existing and existing["status"] in {"requested", "accepted"}:
                raise BoardError("You already have a request for this listing.", 409)
            partner = self.partners[partner_id]
            if partner["type"] == "supplier":
                if self.supplier_requests_left(partner_id) == 0:
                    raise BoardError(
                        "You have used all 5 proposal requests this week. The limit resets on Monday.",
                        429, "M04",
                    )
                self.supplier_week_used[partner_id] = self.supplier_week_used.get(partner_id, 0) + 1

            request = {
                "id": f"REQ-{uuid.uuid4().hex[:6].upper()}",
                "listing_id": listing_id,
                "partner_id": partner_id,
                "partner_type": partner["type"],
                "message": message.strip(),
                "status": "requested",
                "created_at": now().isoformat(timespec="seconds"),
                "decided_at": None,
                "decline_reason": None,
                "document_ids": [document_id] if document_id else [],
            }
            self.requests[request["id"]] = request
            what = "sent a proposal" if document_id else "requested to connect"
            self.log(role, f"{partner['name']} {what}", f"Listing · {listing_id}")
            return request

    def get_request(self, request_id: str) -> Dict[str, Any]:
        request = self.requests.get(request_id)
        if not request:
            raise BoardError(f"Request {request_id} not found.", 404)
        return request

    def decide(self, request_id: str, role: str, accept: bool, reason: str = "") -> Dict[str, Any]:
        require_owner(role, "accept or decline requests")
        with self.lock:
            request = self.get_request(request_id)
            if request["status"] != "requested":
                raise BoardError(f"This request is already {request['status']}.", 409)
            partner = self.partners[request["partner_id"]]
            request["status"] = "accepted" if accept else "declined"
            request["decided_at"] = now().isoformat(timespec="seconds")
            request["decline_reason"] = None if accept else (reason.strip() or None)
            if accept and partner["type"] == "supplier":
                # Charged to the supplier's monthly invoice, never to the SME.
                self.partner_fees.append({
                    "partner_id": partner["id"],
                    "amount_myr": SUPPLIER_CONNECTION_FEE_MYR,
                    "request_id": request_id,
                    "listing_id": request["listing_id"],
                    "at": request["decided_at"],
                })
            for document_id in request["document_ids"]:
                document = self.documents[document_id]
                if document["status"] == "sent":
                    document["status"] = "accepted" if accept else "declined"
            verb = "Accepted" if accept else "Declined"
            self.log(role, f"{verb} {partner['name']}", f"Request · {request['listing_id']}")
            return request

    # -------------------------------------------------------------- documents
    def next_reference(self, kind: str) -> str:
        self.counters[kind] += 1
        year = now().year
        if kind == "eoi":
            return f"GR-EOI-{year}-{self.counters[kind]:04d}"
        return f"SHS-P-{year % 100}-{self.counters[kind]:04d}"

    def add_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        self.documents[document["id"]] = document
        return document

    def attach_document(self, request_id: str, document_id: str) -> None:
        self.get_request(request_id)["document_ids"].append(document_id)

    def respond_to_document(self, document_id: str, role: str, accept: bool) -> Dict[str, Any]:
        """Owner replies to a non-binding EOI. Nothing is signed or committed."""
        require_owner(role, "reply to an EOI")
        with self.lock:
            document = self.documents.get(document_id)
            if not document:
                raise BoardError(f"Document {document_id} not found.", 404)
            if document["status"] != "sent":
                raise BoardError(f"This document is already {document['status']}.", 409)
            document["status"] = "accepted" if accept else "declined"
            verb = "Welcomed" if accept else "Declined"
            self.log(role, f"{verb} EOI {document['reference']}", f"Request · {document['listing_id']}")
            return document

    # ----------------------------------------------------------------- wallet
    def wallet_balance(self) -> float:
        return round(sum(entry["amount"] for entry in self.wallet_ledger), 2)


def require_owner(role: str, action: str) -> None:
    """C05: only the company owner (authorised approver) can do this."""
    if role == "sme_staff":
        raise BoardError(
            f"Only the company owner can {action}. Ask Ahmad (Owner) to approve.", 403, "C05"
        )
    if role != "sme_owner":
        raise BoardError(f"Only the SME owner can {action}.", 403, "C05")


store = BoardStore()
