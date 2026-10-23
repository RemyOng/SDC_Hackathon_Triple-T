import logging
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple

from postgrest.exceptions import APIError
from storage3.utils import StorageException
from supabase import Client, create_client

# Configure module-level logger
logger = logging.getLogger(__name__)

ChannelType = Literal["WHATSAPP", "GMAIL"]
DocType = Literal["TNB_BILL", "VENDOR_QUOTE", "SPAM", "UNKNOWN"]
DocStatus = Literal["PROCESSING", "COMPLETED", "FAILED", "NEEDS_HUMAN"]
ActorRole = Literal["SYSTEM", "SME_OWNER", "STAFF"]



class SupabaseServiceError(Exception):
    """Base exception for all Supabase service failures."""


class DatabaseOperationError(SupabaseServiceError):
    """Raised when a PostgREST query, insert, or update fails."""


class StorageOperationError(SupabaseServiceError):
    """Raised when file uploading or URL retrieval fails in Supabase Storage."""


@dataclass
class SMEProfileInit:
    company_name: Optional[str] = None
    ssm_number: Optional[str] = None
    industry: Optional[str] = None
    state: Optional[str] = None
    wallet_balance_credits: int = 0



class SupabaseService:
    """
    Production-grade persistence adapter with explicit error boundaries,
    type validation, and structured audit logs.
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.getenv("SUPABASE_URL", "")

        self.key = (
                key
                or os.getenv("SUPABASE_SECRET_KEY")
                or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )

        if not self.url or not self.key:
            logger.critical("Supabase credentials missing from environment.")
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be configured in environment variables."
            )

        try:
            self.client: Client = create_client(self.url, self.key)
            self.bucket_name = "raw_documents"
        except Exception as exc:
            logger.exception("Failed to initialize Supabase client instance.")
            raise SupabaseServiceError(
                f"Client initialization failed: {exc}"
            ) from exc


    def get_or_create_sme(
        self,
        identifier: str,
        channel: ChannelType,
        profile_data: Optional[SMEProfileInit] = None,
    ) -> str:
        """
        Resolves an SME by channel identifier or initializes a lean profile.
        Raises DatabaseOperationError on query failure.
        """
        if not identifier or not identifier.strip():
            raise ValueError("Sender identifier cannot be empty.")

        col = "whatsapp_number" if channel == "WHATSAPP" else "email_address"
        clean_id = (
            identifier.strip().lower()
            if channel == "GMAIL"
            else identifier.strip()
        )

        # Check existing record
        try:
            res = (
                self.client.table("sme_profiles")
                .select("id")
                .eq(col, clean_id)
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                logger.info(
                    "Resolved existing SME profile: %s via %s",
                    res.data[0]["id"],
                    col,
                )
                return res.data[0]["id"]
        except APIError as exc:
            logger.error(
                "PostgREST query error during SME lookup (%s=%s): %s",
                col,
                clean_id,
                exc.message,
            )
            raise DatabaseOperationError(
                f"Lookup failed for identifier '{clean_id}': {exc.message}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during SME lookup.")
            raise DatabaseOperationError(
                f"Unexpected error resolving SME: {exc}"
            ) from exc

        # nsert minimal record if not found
        data = profile_data or SMEProfileInit()
        record: Dict[str, Any] = {
            col: clean_id,
            "company_name": data.company_name
            or f"Entity_{re.sub(r'[^a-zA-Z0-9]', '', clean_id)[-6:]}",
            "ssm_number": data.ssm_number,
            "industry": data.industry,
            "state": data.state,
            "wallet_balance_credits": data.wallet_balance_credits,
        }

        try:
            insert_res = (
                self.client.table("sme_profiles").insert(record).execute()
            )
            if not insert_res.data:
                raise DatabaseOperationError("Insert succeeded but returned no data.")
            sme_id = insert_res.data[0]["id"]
            logger.info("Initialized new lean SME profile: %s", sme_id)
            return sme_id
        except APIError as exc:
            logger.error(
                "Failed to insert new SME profile for %s: %s",
                clean_id,
                exc.message,
            )
            raise DatabaseOperationError(
                f"Failed to create SME profile: {exc.message}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error inserting SME profile.")
            raise DatabaseOperationError(
                f"Unexpected error creating SME: {exc}"
            ) from exc

    def update_sme_profile(self, sme_id: str, updates: Dict[str, Any]) -> None:
        """
        Enriches an existing profile when bill/quote extraction discovers new facts.
        """
        if not updates:
            return

        try:
            self.client.table("sme_profiles").update(updates).eq(
                "id", sme_id
            ).execute()
            logger.info("Successfully updated SME profile %s", sme_id)
        except APIError as exc:
            logger.error(
                "Failed to update profile for %s: %s", sme_id, exc.message
            )
            raise DatabaseOperationError(
                f"Profile update failed: {exc.message}"
            ) from exc


    def upload_document(
        self, sme_id: str, filename: str, file_bytes: bytes
    ) -> Tuple[str, str]:
        """
        Uploads file bytes to Supabase Storage: {sme_id}/{uuid}/{clean_filename}
        Returns: (storage_path, public_url)
        """
        if not file_bytes:
            raise ValueError("File payload cannot be empty.")

        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename) or "document.bin"
        file_uuid = uuid.uuid4().hex[:10]
        storage_path = f"{sme_id}/{file_uuid}/{clean_name}"

        try:
            # Upload raw file
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"cache-control": "3600", "upsert": "true"},
            )
            public_url = self.client.storage.from_(
                self.bucket_name
            ).get_public_url(storage_path)
            logger.info("Uploaded document to storage: %s", storage_path)
            return storage_path, public_url
        except StorageException as exc:
            logger.error(
                "Supabase Storage error uploading %s: %s",
                storage_path,
                str(exc),
            )
            raise StorageOperationError(
                f"Storage upload failed for '{clean_name}': {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during storage upload.")
            raise StorageOperationError(
                f"Unexpected storage failure: {exc}"
            ) from exc


    def register_incoming_document(
        self,
        sme_id: str,
        storage_path: str,
        channel: ChannelType,
        doc_type: DocType = "UNKNOWN",
    ) -> str:
        """
        Inserts initial ingestion entry with status='PROCESSING'.
        """
        record = {
            "sme_id": sme_id,
            "source_channel": channel,
            "document_type": doc_type,
            "storage_path": storage_path,
            "status": "PROCESSING",
        }
        try:
            res = (
                self.client.table("ingested_documents")
                .insert(record)
                .execute()
            )
            if not res.data:
                raise DatabaseOperationError(
                    "Insert into ingested_documents returned no data."
                )
            doc_id = res.data[0]["id"]
            logger.info("Registered incoming document ID: %s", doc_id)
            return doc_id
        except APIError as exc:
            logger.error(
                "Database error registering document %s: %s",
                storage_path,
                exc.message,
            )
            raise DatabaseOperationError(
                f"Document registration failed: {exc.message}"
            ) from exc

    def update_document_results(
        self,
        document_id: str,
        extracted_json: Dict[str, Any],
        doc_type: DocType,
        status: DocStatus = "COMPLETED",
    ) -> None:
        """
        Updates parsed metrics and document classification status.
        """
        try:
            self.client.table("ingested_documents").update(
                {
                    "extracted_json": extracted_json,
                    "document_type": doc_type,
                    "status": status,
                }
            ).eq("id", document_id).execute()
            logger.info(
                "Updated document %s status to %s", document_id, status
            )
        except APIError as exc:
            logger.error(
                "Database error updating document %s: %s",
                document_id,
                exc.message,
            )
            raise DatabaseOperationError(
                f"Failed updating document results: {exc.message}"
            ) from exc


    def log_audit_event(
        self,
        sme_id: str,
        action_type: str,
        actor_role: ActorRole = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None,
        audit_id: Optional[str] = None,
    ) -> None:
        """
        Inserts an immutable trace. Failures here are logged as errors
        but suppressed so non-critical audit issues do not halt the core workflow.
        """
        try:
            self.client.table("activity_audit_log").insert(
                {
                    "sme_id": sme_id,
                    "audit_id": audit_id,
                    "action_type": action_type,
                    "actor_role": actor_role,
                    "metadata": metadata or {},
                }
            ).execute()
        except APIError as exc:
            logger.error(
                "Audit log write failed for SME %s [%s]: %s",
                sme_id,
                action_type,
                exc.message,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected failure writing audit log for SME %s", sme_id
            )