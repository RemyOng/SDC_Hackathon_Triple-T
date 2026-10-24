"""Opportunity Board data store.

The store hydrates the Supabase marketplace tables when credentials are
configured and falls back to the synthetic seed for local demo development.
`reset()` reloads the synthetic seed (the Ops "Reset demo" button).
"""

import copy
import logging
import os
import re
import threading
import uuid
from typing import Any, Dict, List, Optional

from marketplace import seed
from marketplace.bills import seed_bills
from marketplace.common import MYT, BoardError, now  # noqa: F401  (re-exported for other modules)
from marketplace.rules import SUPPLIER_CONNECTION_FEE_MYR, SUPPLIER_REQUESTS_PER_WEEK
from supabase import Client, create_client

logger = logging.getLogger(__name__)

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
        self._supabase: Optional[Client] = None
        self._db_listing_ids: Dict[str, str] = {}
        self._db_sme_ids: Dict[str, str] = {}
        self._load_supabase()

    def _load_supabase(self) -> None:
        """Load the marketplace read model from Supabase when configured.

        The in-memory seed remains the fallback for local development and for
        environments where the SQL schema has not been installed yet.
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key or os.getenv("GREENREADY_DATA_SOURCE", "supabase").lower() == "memory":
            return

        try:
            client = create_client(url, key)
            self._supabase = client
            listings = self._rows(client, "marketplace_listings")
            if not listings:
                logger.warning("Supabase has no marketplace listings; using the demo seed.")
            else:
                profiles = {row["id"]: row for row in self._rows(client, "sme_profiles")}
                upgrades = self._rows(client, "upgrade_options")
                partners = self._rows(client, "partners")
                criteria = self._rows(client, "partner_criteria")
                requests = self._rows(client, "connection_requests")
                documents = self._rows(client, "partner_documents")
                ledger = self._rows(client, "wallet_ledger")
                fees = self._rows(client, "partner_fees")
                audit = self._rows(client, "activity_audit_log")

                self._db_listing_ids = {
                    row["listing_code"]: row["id"] for row in listings if row.get("listing_code")
                }
                self._db_sme_ids = {
                    row["listing_code"]: row["sme_id"]
                    for row in listings
                    if row.get("listing_code") and row.get("sme_id")
                }
                self._replace_from_supabase(
                    listings, profiles, upgrades, partners, criteria, requests,
                    documents, ledger, fees, audit,
                )
                logger.info("Loaded GreenReady marketplace data from Supabase.")
        except Exception:
            logger.exception("Unable to load GreenReady data from Supabase; using the demo seed.")

    @staticmethod
    def _rows(client: Client, table: str) -> List[Dict[str, Any]]:
        result = client.table(table).select("*").execute()
        return result.data or []

    def _replace_from_supabase(
        self,
        listings: List[Dict[str, Any]],
        profiles: Dict[str, Dict[str, Any]],
        upgrades: List[Dict[str, Any]],
        partners: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
        requests: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        ledger: List[Dict[str, Any]],
        fees: List[Dict[str, Any]],
        audit: List[Dict[str, Any]],
    ) -> None:
        self.listings = {}
        upgrades_by_sme: Dict[str, List[Dict[str, Any]]] = {}
        for upgrade in upgrades:
            upgrades_by_sme.setdefault(upgrade["sme_id"], []).append({
                "type": upgrade["upgrade_type"],
                "label": self._upgrade_label(upgrade["upgrade_type"]),
                "size": upgrade["size_label"],
                "capex_myr": float(upgrade["capex_myr"]),
                "saving_myr_year": float(upgrade["saving_myr_year"]),
                "payback_years": float(upgrade["payback_years"]) if upgrade.get("payback_years") is not None else None,
                "co2e_t_year": float(upgrade["co2e_t_year"]),
                "basis": upgrade.get("basis", "estimate"),
            })

        for row in listings:
            code = row.get("listing_code") or row["id"]
            profile = profiles.get(row["sme_id"], {})
            options = upgrades_by_sme.get(row["sme_id"], [])
            evidence = row.get("evidence") or {}
            average_kwh = float(row.get("baseline_kwh") or 0)
            self.listings[code] = {
                "id": code,
                "status": row.get("status", "live"),
                "listed_at": self._date_value(row.get("listed_at")),
                "expires_at": self._date_value(row.get("expires_at")),
                "company": {
                    "name": profile.get("company_name") or row.get("masked_title", code),
                    "reg_no": profile.get("ssm_number", ""),
                    "sector": row.get("sector") or profile.get("sector_group", "Services"),
                    "state": row.get("state") or profile.get("state", ""),
                    "size": row.get("size_class") or profile.get("size_class", "Small"),
                    "age_years": self._age_from_band(row.get("age_band")),
                    "status": profile.get("company_status", "Active"),
                    "address": profile.get("address", ""),
                    "contact_person": profile.get("contact_person", ""),
                    "contact_phone": profile.get("contact_phone", ""),
                    "contact_email": profile.get("contact_email", ""),
                    "directors": profile.get("directors") or [],
                },
                "bill": {
                    "month": "Latest",
                    "amount_myr": self._band_amount(row.get("bill_band")),
                    "due": "",
                    "usage_kwh": average_kwh,
                    "average_kwh": average_kwh,
                    "history": {},
                    "months_of_bills": evidence.get("months_of_bills", 0),
                    "reading_type": evidence.get("reading_type", "unknown"),
                    "checks_passed": evidence.get("checks_passed", 0),
                    "checks_total": evidence.get("checks_total", 0),
                    "real_cost_per_kwh": 0,
                },
                "operations": {
                    "daytime": bool(row.get("daytime_operation")),
                    "lighting": row.get("lighting", ""),
                    "aircon": profile.get("aircon_type", ""),
                    "roof_access": profile.get("roof_access", "") in (True, "yes"),
                },
                "upgrades": options,
                "quote_attached": bool(row.get("quote_attached")),
                "views": {
                    "investors": row.get("views_investors", 0),
                    "suppliers": row.get("views_suppliers", 0),
                },
            }

        self.partners = {
            row["id"]: {**row, "type": row.get("partner_type", row.get("type", ""))}
            for row in partners
        }
        self.criteria = {row["partner_id"]: {
            key: value for key, value in row.items()
            if key not in {"partner_id", "updated_at"} and value not in (None, "")
        } for row in criteria}
        self.requests = {
            row["id"]: {
                **row,
                "listing_id": self._listing_code(row["listing_id"], listings),
                "document_ids": [],
            } for row in requests
        }
        self.documents = {
            row["id"]: {
                "id": row["id"],
                "type": row["doc_type"],
                "reference": row["reference"],
                "status": row["status"],
                "sent_at": row.get("sent_at", ""),
                "listing_id": self._listing_code(row["listing_id"], listings),
                "values": row.get("field_values") or {},
            } for row in documents
        }
        for document in documents:
            request = self.requests.get(document["request_id"])
            if request:
                request["document_ids"].append(document["id"])
        self.wallet_ledger = [{
            "id": row.get("id"),
            "amount": float(row.get("amount_myr", 0)),
            "reason": row.get("reason", ""),
            "reference": row.get("reference"),
            "created_at": row.get("created_at", ""),
        } for row in ledger]
        self.partner_fees = fees
        self.audit = [{
            "at": row.get("created_at", ""),
            "user": row.get("actor_role", "GreenReady"),
            "role": row.get("actor_role", "System"),
            "action": row.get("action_type", ""),
            "object": row.get("metadata", {}).get("document_id", ""),
        } for row in audit]
        self.supplier_week_used = {}
        self.counters = {"eoi": 141, "proposal": 317}
        self.companies = {}
        self.registered_ssm = {profile.get("ssm_number") for profile in profiles.values() if profile.get("ssm_number")}
        self.bills = seed_bills()

    @staticmethod
    def _upgrade_label(kind: str) -> str:
        return {"solar": "Rooftop solar", "led": "LED lighting", "aircon": "Inverter aircon"}.get(kind, kind)

    @staticmethod
    def _date_value(value: Any) -> str:
        return str(value or "")[:10]

    @staticmethod
    def _age_from_band(value: Optional[str]) -> float:
        try:
            numbers = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", value)]
            return sum(numbers[:2]) / len(numbers[:2]) if numbers else 5.0
        except (AttributeError, ValueError):
            return 5.0

    @staticmethod
    def _band_amount(value: Optional[str]) -> float:
        try:
            numbers = [float(part.replace(",", "")) for part in str(value).replace("RM", "").replace("k", "000").split("–")]
            return sum(numbers) / len(numbers)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _listing_code(listing_id: str, listings: List[Dict[str, Any]]) -> str:
        for listing in listings:
            if listing["id"] == listing_id:
                return listing.get("listing_code", listing_id)
        return listing_id

    def save_criteria(self, partner_id: str, values: Dict[str, Any]) -> None:
        self.criteria[partner_id] = values
        if not self._supabase:
            return
        try:
            self._supabase.table("partner_criteria").upsert({
                "partner_id": partner_id,
                **values,
            }).execute()
        except Exception as exc:
            logger.exception("Failed to save investor criteria to Supabase.")
            raise BoardError("We could not save your criteria. Please try again.", 503) from exc

    def ingestion_feed(self, role: str) -> List[Dict[str, Any]]:
        if role not in {"sme_owner", "sme_staff"}:
            raise BoardError("Ingested documents are only available to the SME.", 403)
        if not self._supabase:
            return []
        try:
            # This inbox is intentionally shared by both SME roles. It is an
            # ingestion monitor, not an account-scoped document view.
            try:
                documents = (
                    self._supabase.table("ingested_documents")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )
            except Exception:
                documents = (
                    self._supabase.table("ingested_document")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )

            try:
                audits = self._supabase.table("activity_audit_log").select(
                    "action_type,metadata,created_at"
                ).eq("action_type", "DOCUMENT_INGESTED").order("created_at", desc=True).limit(100).execute().data or []
            except Exception:
                logger.warning("Could not load ingestion audit metadata; showing document rows only.")
                audits = []
            audit_by_document = {
                (item.get("metadata") or {}).get("document_id"): item
                for item in audits
            }
            result = []
            for document in documents:
                extracted = document.get("extracted_json") or document.get("extracted") or {}
                storage_path = document.get("storage_path") or document.get("file_path") or ""
                source = extracted.get("_source") or {}
                metadata = (audit_by_document.get(document.get("id")) or {}).get("metadata") or {}
                file_url = document.get("file_url") or document.get("public_url")
                if not file_url and storage_path:
                    try:
                        file_url = self._supabase.storage.from_("raw_documents").get_public_url(storage_path)
                    except Exception:
                        logger.warning("Could not create a file URL for ingestion %s.", document.get("id"))
                filename = (
                    metadata.get("filename")
                    or document.get("filename")
                    or document.get("file_name")
                    or document.get("name")
                    or storage_path.rsplit("/", 1)[-1]
                    or "Unnamed document"
                )
                result.append({
                    "id": str(document.get("id") or filename),
                    "channel": document.get("source_channel") or document.get("channel") or "UNKNOWN",
                    "type": document.get("document_type") or document.get("type") or "UNKNOWN",
                    "status": document.get("status") or "UNKNOWN",
                    "filename": filename,
                    "sender": (
                        document.get("sender")
                        or document.get("sender_number")
                        or document.get("from_email")
                        or metadata.get("sender_number")
                        or metadata.get("from_email")
                        or source.get("from_email")
                        or source.get("sender_number")
                    ),
                    "subject": document.get("subject") or metadata.get("subject") or source.get("subject"),
                    "message_id": document.get("message_id") or metadata.get("message_id") or source.get("message_id"),
                    "created_at": document.get("created_at") or document.get("updated_at"),
                    "extracted": extracted,
                    "file_url": file_url,
                })
            return result
        except Exception as exc:
            logger.exception("Failed to load the SME ingestion feed from Supabase.")
            raise BoardError("We could not load ingested documents. Please try again.", 503) from exc

    def _persist_request(self, request: Dict[str, Any]) -> None:
        if not self._supabase:
            return
        listing_id = self._db_listing_ids.get(request["listing_id"])
        if not listing_id:
            raise BoardError("This listing is not available in the connected database.", 503)
        try:
            self._supabase.table("connection_requests").insert({
                "id": request["id"],
                "listing_id": listing_id,
                "partner_id": request["partner_id"],
                "partner_type": request["partner_type"],
                "message": request["message"],
                "status": request["status"],
                "created_at": request["created_at"],
            }).execute()
        except Exception as exc:
            logger.exception("Failed to persist connection request to Supabase.")
            raise BoardError("We could not send the connection request. Please try again.", 503) from exc

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
            if self._supabase and listing_id in self._db_listing_ids:
                try:
                    self._supabase.table("marketplace_listings").update({"status": "unlisted"}).eq(
                        "id", self._db_listing_ids[listing_id]
                    ).execute()
                except Exception as exc:
                    logger.exception("Failed to unlist the Supabase marketplace listing.")
                    raise BoardError("We could not unlist this listing. Please try again.", 503) from exc
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
                "id": str(uuid.uuid4()) if self._supabase else f"REQ-{uuid.uuid4().hex[:6].upper()}",
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
            self._persist_request(request)
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
            if self._supabase:
                try:
                    self._supabase.table("connection_requests").update({
                        "status": request["status"],
                        "decline_reason": request["decline_reason"],
                        "decided_at": request["decided_at"],
                    }).eq("id", request_id).execute()
                except Exception as exc:
                    logger.exception("Failed to persist request decision to Supabase.")
                    raise BoardError("We could not update this request. Please try again.", 503) from exc
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
        return round(sum(float(entry.get("amount", entry.get("amount_myr", 0))) for entry in self.wallet_ledger), 2)


def require_owner(role: str, action: str) -> None:
    """C05: only the company owner (authorised approver) can do this."""
    if role == "sme_staff":
        raise BoardError(
            f"Only the company owner can {action}. Ask Ahmad (Owner) to approve.", 403, "C05"
        )
    if role != "sme_owner":
        raise BoardError(f"Only the SME owner can {action}.", 403, "C05")


store = BoardStore()
