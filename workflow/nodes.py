from typing import Dict, Any
from workflow.state import GraphState

from db.db_manager import SupabaseService
from services.runpod_client import RunPodVLMClient
from services.document_processor import fetch_and_convert_to_base64
from core.calculator import compute_green_metrics, EquipmentQuote, AuditResult
from marketplace.rules import (
    SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP,
    SOLAR_YIELD_KWH_PER_KWP,
    suggested_solar_kwp,
)
from schema.schemas import ExtractedDocument

# Initialize singletons for the nodes to use
supabase = SupabaseService()
runpod = RunPodVLMClient()


def node_extract_data(state: GraphState) -> Dict[str, Any]:
    """Downloads document, converts to base64 images, and extracts VLM JSON."""
    base64_images = fetch_and_convert_to_base64(state["document_url"], state["filename"])
    extracted_doc: ExtractedDocument = runpod.extract_document_metrics(base64_images)

    supabase.update_document_results(
        document_id=state["document_id"],
        extracted_json=extracted_doc.model_dump(),
        doc_type="TNB_BILL",
        status="COMPLETED" if baseline_monthly_kwh(extracted_doc.model_dump()) > 0 else "NEEDS_HUMAN"
    )

    supabase.log_audit_event(
        sme_id=state["sme_id"],
        action_type="VLM_EXTRACTION_COMPLETED"
    )
    return {"extracted_data": extracted_doc.model_dump()}


def baseline_monthly_kwh(data: Dict[str, Any]) -> float:
    """Average monthly usage: bill average, else the 6-month history, else this month."""
    if data.get("average_usage_kwh"):
        return float(data["average_usage_kwh"])
    history = [value for value in data.get("history_6_months_kwh") or [] if value]
    if history:
        return sum(history) / len(history)
    return float(data.get("current_month_usage_kwh") or 0.0)


def node_calculate_impact(state: GraphState) -> Dict[str, Any]:
    """Runs deterministic Python math based on extracted data."""
    data = state["extracted_data"] or {}
    baseline = baseline_monthly_kwh(data)

    # Solar sized to the daytime share of usage; benchmark CapEx unless a quote gave one.
    kwp = suggested_solar_kwp(baseline)
    quote = EquipmentQuote(
        system_capacity_kwp=kwp,
        total_capex_myr=data.get("target_capex_myr") or kwp * SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP,
        estimated_annual_kwh_gen=kwp * SOLAR_YIELD_KWH_PER_KWP,
    )

    metrics: AuditResult = compute_green_metrics(
        baseline_monthly_kwh=baseline,
        quote=quote
    )

    supabase.log_audit_event(
        sme_id=state["sme_id"],
        action_type="MATH_VALIDATED"
    )
    return {"audit_metrics": {**metrics.__dict__, "system_capacity_kwp": kwp}}


def node_publish_to_marketplace(state: GraphState) -> Dict[str, Any]:
    """Pushes the verified dossier to the Streamlit deal board."""
    metrics = state["audit_metrics"] or {}
    data = state["extracted_data"] or {}

    supabase.client.table("marketplace_listings").insert({
        "sme_id": state["sme_id"],
        "masked_title": f"SME Verified Lead - {data.get('equipment_type') or 'Rooftop solar'}",
        "baseline_kwh": metrics.get("average_monthly_baseline_kwh", 0),
        "target_capex_myr": metrics.get("target_capex_myr", 0),
        "annual_tco2e_avoided": metrics.get("annual_tco2e_avoided", 0),
        "listing_status": "ACTIVE"
    }).execute()

    supabase.log_audit_event(
        sme_id=state["sme_id"],
        action_type="PUBLISHED_TO_DEAL_BOARD"
    )
    return {}