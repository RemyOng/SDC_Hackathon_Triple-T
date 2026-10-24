"""TNB bill pipeline for the web app (UI spec B3–B6).

    file -> extract (RunPod VLM, or demo / manual) -> confidence gate (V12)
         -> 8 checks (V01–V08) -> insights (B01–B08) -> upgrade options (S/U rules)
         -> plain-English explanation (Claude explains; the rules decide every number)

AI only reads the bill and explains results. Every RM, kWh and tonne shown
comes from the deterministic functions in this module and marketplace.rules.
"""

import logging
import os
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.calculator import GRID_EMISSION_FACTOR_KG_KWH, TNB_TARIFF_B_MYR_KWH
from marketplace.common import BoardError, now
from marketplace.rules import (
    SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP,
    SOLAR_YIELD_KWH_PER_KWP,
    estimate_aircon,
    estimate_led,
    estimate_solar,
    suggested_solar_kwp,
)
from marketplace.tariffs import resolve_tariff
if TYPE_CHECKING:  # the store seeds bills from this module, so import it for typing only
    from marketplace.store import BoardStore

logger = logging.getLogger(__name__)

# Tariff B component rates (P-table). Together they make P01 = RM0.5068/kWh.
ENERGY_RATE = 0.2703
CAPACITY_RATE = 0.0883
NETWORK_RATE = 0.1482
KWTBB_RATE = 0.016
SERVICE_TAX_RATE = 0.08
REBATE_CAP_SHARE = 0.05          # V05: a rebate is a credit of at most 5% of usage charges
CONFIDENCE_THRESHOLD = 85        # V12
SPIKE_THRESHOLD_PCT = 15         # B03
ANALYSIS_PRICE_MYR = 2.0
TOLERANCE_MYR = 0.05
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"pdf", "png", "jpg", "jpeg", "webp"}

FIELDS: List[tuple] = [
    ("account_last4", "Account (last 4)", "text"),
    ("tariff", "Tariff", "text"),
    ("billing_period", "Billing period", "text"),
    ("bill_date", "Bill date", "text"),
    ("due_date", "Due date", "text"),
    ("reading_type", "Reading type", "text"),
    ("meter_reading_previous", "Previous reading (kWh)", "number"),
    ("meter_reading_current", "Current reading (kWh)", "number"),
    ("current_month_usage_kwh", "Usage (kWh)", "number"),
    ("peak_usage_kwh", "Peak usage (kWh)", "number"),
    ("offpeak_usage_kwh", "Off-peak usage (kWh)", "number"),
    ("energy_charge_myr", "Energy charge (RM)", "number"),
    ("capacity_charge_myr", "Capacity charge (RM)", "number"),
    ("network_charge_myr", "Network charge (RM)", "number"),
    ("afa_charge_myr", "AFA fuel adjustment (RM)", "number"),
    ("retail_charge_myr", "Retail charge (RM)", "number"),
    ("ee_incentive_myr", "Rebate / EE incentive (RM)", "number"),
    ("kwtbb_myr", "KWTBB 1.6% (RM)", "number"),
    ("service_tax_myr", "Service tax 8% (RM)", "number"),
    ("current_charges_myr", "Current charges (RM)", "number"),
    ("previous_balance_myr", "Previous balance (RM)", "number"),
    ("total_payable_myr", "Total due (RM)", "number"),
]
FIELD_LABELS = {key: label for key, label, _ in FIELDS}
NUMERIC = {key for key, _, kind in FIELDS if kind == "number"}
REQUIRED = NUMERIC - {"previous_balance_myr", "peak_usage_kwh", "offpeak_usage_kwh"}

CHARGE_ROWS = [
    ("energy_charge_myr", "Energy", "What it costs to generate the electricity you used."),
    ("capacity_charge_myr", "Capacity", "Your share of keeping power stations ready for peak demand."),
    ("network_charge_myr", "Network", "Carrying electricity over TNB's grid to your premises."),
    ("afa_charge_myr", "AFA", "Monthly fuel-cost adjustment. A minus sign means a discount."),
    ("retail_charge_myr", "Retail", "Fixed monthly charge for billing and customer service."),
    ("ee_incentive_myr", "Rebate", "Energy-efficiency incentive. It can change month to month."),
    ("kwtbb_myr", "KWTBB", "1.6% Renewable Energy Fund levy on your usage charges."),
    ("service_tax_myr", "Service tax", "8% government service tax."),
]


# ------------------------------------------------------------- sample bills
def _sample_fields(month: str, period: str, bill_date: str, due: str, prev_reading: int, kwh: int,
                   afa: float, rebate: float, network: Optional[float] = None) -> Dict[str, Any]:
    energy = round(kwh * ENERGY_RATE, 2)
    capacity = round(kwh * CAPACITY_RATE, 2)
    network = round(kwh * NETWORK_RATE, 2) if network is None else network
    subtotal = round(energy + capacity + network + afa + 20.00 + rebate, 2)
    kwtbb = round(subtotal * KWTBB_RATE, 2)
    tax = round(subtotal * SERVICE_TAX_RATE, 2)
    current = round(subtotal + kwtbb + tax, 2)
    return {
        "account_last4": "0871", "tariff": "B — Low voltage commercial", "billing_period": period,
        "bill_date": bill_date, "due_date": due, "reading_type": "Actual",
        "meter_reading_previous": prev_reading, "meter_reading_current": prev_reading + kwh,
        "current_month_usage_kwh": kwh, "energy_charge_myr": energy, "capacity_charge_myr": capacity,
        "network_charge_myr": network, "afa_charge_myr": afa, "retail_charge_myr": 20.00,
        "ee_incentive_myr": rebate, "kwtbb_myr": kwtbb, "service_tax_myr": tax,
        "current_charges_myr": current, "previous_balance_myr": 0.00, "total_payable_myr": current,
        "_month": month,
    }


SAMPLE_SEP = _sample_fields("Sep 2026", "01.09.2026 – 30.09.2026", "03.10.2026", "10.11.2026",
                            128_560, 4_420, afa=-203.31, rebate=-104.20)
SAMPLE_AUG = _sample_fields("Aug 2026", "01.08.2026 – 31.08.2026", "03.09.2026", "10.10.2026",
                            124_950, 3_610, afa=-166.06, rebate=-85.10)
HISTORY = {"Apr": 3520, "May": 3610, "Jun": 3480, "Jul": 3650, "Aug": 3610, "Sep": 4420}

# Demo AI read: two fields come back under the 85% threshold, one of them misread
# (6 read as 0), so the review step and a failing check are visible in the demo.
DEMO_CONFIDENCE = {"network_charge_myr": 78.0, "afa_charge_myr": 81.0}
DEMO_MISREADS = {"network_charge_myr": 586.36}


def _field_rows(values: Dict[str, Any], source: str, confidence: Optional[Dict[str, float]] = None,
                misreads: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    rows = []
    for index, (key, label, kind) in enumerate(FIELDS):
        value = (misreads or {}).get(key, values.get(key))
        score = None
        if source == "AI":
            score = (confidence or {}).get(key, 99.0 - (index % 5) * 1.5)
        missing = value is None and key in REQUIRED
        rows.append({
            "key": key, "label": label, "kind": kind, "value": value, "source": source,
            "confidence": score,
            "flagged": missing or (score is not None and score < CONFIDENCE_THRESHOLD),
        })
    return rows


def seed_bills() -> Dict[str, Dict[str, Any]]:
    """Aug (WhatsApp) and Sep (eClaim, after Siti fixed the 2 flagged fields)."""
    seeded = {}
    for bill_id, sample, source, uploaded_at, by in (
        ("BILL-0826", SAMPLE_AUG, "WhatsApp", "2026-09-04T09:12:00+08:00", "sme_owner"),
        ("BILL-0926", SAMPLE_SEP, "eClaim", "2026-10-23T10:02:00+08:00", "sme_staff"),
    ):
        fields = _field_rows(sample, "AI", DEMO_CONFIDENCE)
        for row in fields:
            if row["key"] in DEMO_CONFIDENCE:
                row.update(source="Corrected", confidence=100.0, flagged=False)
        history = {month: kwh for month, kwh in HISTORY.items()}
        if sample is SAMPLE_AUG:
            history = {"Mar": 3490, **{m: k for m, k in HISTORY.items() if m != "Sep"}}
        bill = {
            "id": bill_id, "month": sample["_month"], "source": source, "mode": "ai", "filename": None,
            "uploaded_at": uploaded_at, "uploaded_by": by, "fields": fields, "history": history, "notice": None,
            "charged_myr": ANALYSIS_PRICE_MYR, "processing_ms": 41_000, "checks": [], "insights": None,
            "status": "processing", "explanation": None,
        }
        analyse(bill)
        seeded[bill_id] = bill
    return seeded


# ------------------------------------------------------------------ helpers
def values_of(bill: Dict[str, Any]) -> Dict[str, Any]:
    return {row["key"]: row["value"] for row in bill["fields"]}


def _num(values: Dict[str, Any], key: str) -> float:
    value = values.get(key)
    return float(value) if value not in (None, "") else 0.0


def _check(rule: str, label: str, expected: float, found: float, unit: str = "RM",
           tolerance: float = TOLERANCE_MYR) -> Dict[str, Any]:
    return {
        "rule": rule, "label": label, "unit": unit,
        "expected": round(expected, 2), "found": round(found, 2),
        "passed": abs(expected - found) <= tolerance,
    }


def run_checks(values: Dict[str, Any]) -> List[Dict[str, Any]]:
    kwh = _num(values, "current_month_usage_kwh")
    energy, capacity, network = (_num(values, k) for k in ("energy_charge_myr", "capacity_charge_myr", "network_charge_myr"))
    afa, retail, rebate = (_num(values, k) for k in ("afa_charge_myr", "retail_charge_myr", "ee_incentive_myr"))
    kwtbb, tax = _num(values, "kwtbb_myr"), _num(values, "service_tax_myr")
    subtotal_found = _num(values, "current_charges_myr") - kwtbb - tax
    tariff = resolve_tariff(values.get("tariff"))
    peak_kwh, offpeak_kwh = _num(values, "peak_usage_kwh"), _num(values, "offpeak_usage_kwh")
    rate_kwh = peak_kwh + offpeak_kwh if tariff and tariff.tou and peak_kwh + offpeak_kwh else kwh
    expected_energy = None
    expected_capacity = None
    expected_network = None
    if tariff:
        if tariff.tou and peak_kwh + offpeak_kwh:
            expected_energy = peak_kwh * (tariff.energy_peak_rate or 0) + offpeak_kwh * (tariff.energy_offpeak_rate or 0)
        elif tariff.energy_rate is not None:
            expected_energy = rate_kwh * tariff.energy_rate
        if tariff.capacity_rate is not None:
            demand = _num(values, "peak_demand_kw")
            expected_capacity = demand * tariff.capacity_rate if tariff.demand_based and demand else rate_kwh * tariff.capacity_rate
        if tariff.network_rate is not None:
            demand = _num(values, "peak_demand_kw")
            expected_network = demand * tariff.network_rate if tariff.demand_based and demand else rate_kwh * tariff.network_rate
    expected_energy = expected_energy if expected_energy is not None else energy
    expected_capacity = expected_capacity if expected_capacity is not None else capacity
    expected_network = expected_network if expected_network is not None else network
    subtotal_expected = energy + capacity + network + afa + retail + rebate
    usage_charges = energy + capacity + network
    rebate_cap = (tariff.rebate_cap if tariff else REBATE_CAP_SHARE) or REBATE_CAP_SHARE
    rebate_ok = rebate <= 0 and -rebate <= usage_charges * rebate_cap + TOLERANCE_MYR
    expected_total = subtotal_expected * (1 + (tariff and KWTBB_RATE or KWTBB_RATE) + (tariff and SERVICE_TAX_RATE or SERVICE_TAX_RATE)) + _num(values, "previous_balance_myr")
    tariff_note = tariff.name if tariff else "Tariff not recognised; bill arithmetic only"
    return [
        _check("V01", "Meter reading", _num(values, "meter_reading_current") - _num(values, "meter_reading_previous"),
               kwh, unit="kWh", tolerance=0.5),
        _check("V02", f"Energy charge ({tariff_note})", expected_energy, energy),
        _check("V03", f"Capacity charge ({tariff_note})", expected_capacity, capacity),
        _check("V04", f"Network charge ({tariff_note})", expected_network, network),
        {"rule": "V05", "label": "Rebate", "unit": "RM", "expected": round(-usage_charges * rebate_cap, 2),
         "found": round(rebate, 2), "passed": rebate_ok, "note": f"Allowed credit up to {rebate_cap:.0%} of usage charges"},
        _check("V06", "Usage subtotal", subtotal_expected, subtotal_found),
        _check("V07", "KWTBB 1.6%", subtotal_expected * KWTBB_RATE, kwtbb),
        _check("V08", "Total due (incl. 8% service tax)", expected_total, _num(values, "total_payable_myr"), tolerance=0.10),
    ]


def build_insights(values: Dict[str, Any], history: Dict[str, float]) -> Dict[str, Any]:
    kwh = _num(values, "current_month_usage_kwh")
    actual = str(values.get("reading_type", "Actual")).lower().startswith("a")
    series = list(history.values()) or [kwh]
    baseline = sum(series) / len(series)
    spike = (kwh / baseline - 1) * 100 if baseline and actual else None
    rebate = _num(values, "ee_incentive_myr")
    total = _num(values, "total_payable_myr") - _num(values, "previous_balance_myr")
    gross_up = 1 + KWTBB_RATE + SERVICE_TAX_RATE
    usage_dependent = sum(_num(values, k) for k in ("energy_charge_myr", "capacity_charge_myr", "network_charge_myr", "afa_charge_myr"))
    recent, earlier = series[-3:], series[:-3] or series[-3:]
    trend = (sum(recent) / len(recent) / (sum(earlier) / len(earlier)) - 1) * 100
    real_cost = (total - rebate * gross_up) / kwh if kwh else 0
    return {
        "daily_kwh": {"rule": "B01", "value": round(kwh / 30, 1), "label": "Daily usage", "unit": "kWh/day"},
        "baseline_kwh": {"rule": "B02", "value": round(baseline), "label": "6-month average", "unit": "kWh"},
        "spike_pct": {"rule": "B03", "value": None if spike is None else round(spike), "label": "Change vs average",
                      "alert": spike is not None and spike >= SPIKE_THRESHOLD_PCT,
                      "note": None if actual else "Estimated reading — not used for spike alerts (V11)"},
        "real_cost_per_kwh": {"rule": "B04", "value": round(real_cost, 2), "label": "Real cost per kWh",
                              "note": "Before one-off rebates"},
        "variable_share": {"rule": "B05", "value": round(usage_dependent / (usage_dependent + _num(values, "retail_charge_myr")) * 100) if usage_dependent else 0,
                           "label": "Share that changes with usage", "unit": "%"},
        "rebate": {"rule": "B06", "value": round(-rebate, 2), "label": "Rebate this month",
                   "note": "Incentives can change; savings estimates never count on them"},
        "marginal_saving": {"rule": "B07", "value": round(TNB_TARIFF_B_MYR_KWH * gross_up, 3), "label": "Saved per kWh you cut",
                            "unit": "RM/kWh"},
        "trend_pct": {"rule": "B08", "value": round(trend), "label": "Last 3 months vs 3 before", "unit": "%"},
    }


# ----------------------------------------------------------------- pipeline
def _extract_with_runpod(file_bytes: bytes, filename: str) -> Optional[Dict[str, Any]]:
    if not (os.getenv("RUNPOD_ENDPOINT_ID") and os.getenv("RUNPOD_API_KEY")):
        return None
    from services.document_processor import extract_document_text, process_bytes_to_base64
    from services.runpod_client import RunPodVLMClient

    extracted = RunPodVLMClient().extract_document_metrics(
        process_bytes_to_base64(file_bytes, filename),
        extract_document_text(file_bytes, filename),
    )
    data = extracted.model_dump()
    # Keep values extracted from the bill; only provide the marketplace's
    # derived aliases/defaults where the extraction schema has no equivalent.
    data["previous_balance_myr"] = data.get("previous_balance_myr", 0.0)
    data["account_last4"] = (data.get("account_number") or "")[-4:] or None
    return data


def _month_label(values: Dict[str, Any]) -> str:
    period = str(values.get("billing_period") or "")
    for token in period.replace("–", " ").replace("-", " ").split():
        parts = token.split(".")
        if len(parts) == 3 and parts[1].isdigit():
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{months[int(parts[1]) - 1]} {parts[2]}"
    return "Uploaded bill"


def _new_bill(store: "BoardStore", role: str, source: str, mode: str, fields: List[Dict[str, Any]],
              history: Dict[str, float], filename: Optional[str], month: str, notice: Optional[str],
              charged: float, started: float) -> Dict[str, Any]:
    bill = {
        "id": f"BILL-{uuid.uuid4().hex[:6].upper()}",
        "month": month,
        "source": source,
        "mode": mode,
        "filename": filename,
        "uploaded_at": now().isoformat(timespec="seconds"),
        "uploaded_by": role,
        "fields": fields,
        "history": history,
        "notice": notice,
        "charged_myr": charged,
        "processing_ms": int((time.perf_counter() - started) * 1000),
        "checks": [],
        "insights": None,
        "status": "processing",
        "explanation": None,
    }
    analyse(bill)
    return bill


def analyse(bill: Dict[str, Any]) -> None:
    """V12: no calculation runs while any field is still flagged."""
    if any(row["flagged"] for row in bill["fields"]):
        bill["status"], bill["checks"], bill["insights"] = "needs_review", [], None
        return
    values = values_of(bill)
    bill["checks"] = run_checks(values)
    bill["insights"] = build_insights(values, bill["history"])
    bill["status"] = "ready" if all(check["passed"] for check in bill["checks"]) else "check_failed"
    bill["explanation"] = None


def _charge(store: "BoardStore", month: str) -> float:
    if store.wallet_balance() < ANALYSIS_PRICE_MYR:
        raise BoardError("Your Orbyte credit wallet has less than RM2. Top up to analyse another bill.", 402)
    store.wallet_ledger.append({
        "amount": -ANALYSIS_PRICE_MYR, "type": "DEBIT", "reason": f"Bill analysis · {month}",
        "at": now().isoformat(timespec="seconds"),
    })
    return ANALYSIS_PRICE_MYR


def upload(store: "BoardStore", role: str, filename: str, file_bytes: bytes) -> Dict[str, Any]:
    started = time.perf_counter()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_TYPES:
        raise BoardError("Upload a PDF, JPG, PNG or WEBP of your TNB bill.", 415)
    if not file_bytes:
        raise BoardError("That file is empty. Try again or enter the bill manually.", 422)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise BoardError("That file is over 10 MB. Try a smaller photo or a PDF.", 413)

    notice = None
    try:
        data = _extract_with_runpod(file_bytes, filename)
    except Exception as exc:  # VLM timeout or unreadable file -> manual entry (spec fallback)
        logger.warning("RunPod extraction failed for %s: %s", filename, exc)
        raise BoardError("We couldn't read this. Try a clearer photo or enter it manually.", 422) from exc

    if data is None:
        mode, values, fields = "demo", SAMPLE_SEP, _field_rows(SAMPLE_SEP, "AI", DEMO_CONFIDENCE, DEMO_MISREADS)
        notice = ("Demo extraction: the bill-reading AI (RunPod) isn't connected on this server, so these are the "
                  "sample bill's fields. Check them, or use manual entry for your own bill.")
        history = dict(HISTORY)
    else:
        mode, values, fields = "ai", data, _field_rows(data, "AI", {})
        history = {f"M{index + 1}": value for index, value in enumerate(data.get("history_6_months_kwh") or []) if value}

    with store.lock:
        month = values.get("_month") or _month_label(values)
        charged = _charge(store, month)
        bill = _new_bill(store, role, "Upload", mode, fields, history, filename, month, notice, charged, started)
        store.bills[bill["id"]] = bill
        flagged = sum(row["flagged"] for row in fields)
        store.log(role, f"Uploaded {month} bill ({filename})", f"Bill · {month}")
        store.log("system", f"AI read {len(fields)} fields ({flagged} flagged under {CONFIDENCE_THRESHOLD}%)", f"Bill · {month}")
        _log_result(store, bill)
        return bill


def manual(store: "BoardStore", role: str, values: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    cleaned = _clean_values(values)
    missing = [FIELD_LABELS[key] for key in REQUIRED if cleaned.get(key) is None]
    if missing:
        raise BoardError("Fill in: " + ", ".join(missing) + ".", 422)
    history_values = values.get("history") or {}
    history = {str(k): float(v) for k, v in history_values.items() if v not in (None, "")} or {"This month": cleaned["current_month_usage_kwh"]}
    with store.lock:
        month = str(values.get("month") or _month_label(cleaned))
        charged = _charge(store, month)
        bill = _new_bill(store, role, "Manual entry", "manual", _field_rows(cleaned, "Manual"), history, None, month, None, charged, started)
        store.bills[bill["id"]] = bill
        store.log(role, f"Entered {month} bill manually", f"Bill · {month}")
        _log_result(store, bill)
        return bill


def _clean_values(values: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, label, kind in FIELDS:
        raw = values.get(key)
        if raw in (None, ""):
            cleaned[key] = 0.0 if key == "previous_balance_myr" else None
            continue
        if kind == "number":
            try:
                cleaned[key] = float(str(raw).replace(",", "").replace("RM", "").strip())
            except ValueError:
                raise BoardError(f"{label} must be a number.", 422) from None
        else:
            cleaned[key] = str(raw).strip()
    return cleaned


def correct(store: "BoardStore", role: str, bill_id: str, values: Dict[str, Any], confirm_all: bool) -> Dict[str, Any]:
    with store.lock:
        bill = get(store, bill_id)
        cleaned = _clean_values({**values_of(bill), **values})
        changed = []
        for row in bill["fields"]:
            if row["key"] in values and cleaned[row["key"]] != row["value"]:
                row.update(value=cleaned[row["key"]], source="Corrected", confidence=100.0, flagged=False)
                changed.append(row["label"])
            elif row["key"] in values or confirm_all:
                row["flagged"] = row["value"] is None and row["key"] in REQUIRED
        if changed:
            store.log(role, f"Fixed {len(changed)} field{'s' if len(changed) > 1 else ''}: {', '.join(changed)}", f"Bill · {bill['month']}")
        if confirm_all:
            store.log(role, "Confirmed all fields", f"Bill · {bill['month']}")
        analyse(bill)
        _log_result(store, bill)
        return bill


def _log_result(store: "BoardStore", bill: Dict[str, Any]) -> None:
    if bill["checks"]:
        passed = sum(check["passed"] for check in bill["checks"])
        store.log("system", f"{passed}/{len(bill['checks'])} checks passed", f"Bill · {bill['month']}")


def get(store: "BoardStore", bill_id: str) -> Dict[str, Any]:
    bill = store.bills.get(bill_id)
    if not bill:
        raise BoardError(f"Bill {bill_id} not found.", 404)
    return bill


def summary(bill: Dict[str, Any]) -> Dict[str, Any]:
    values = values_of(bill)
    passed = sum(check["passed"] for check in bill["checks"])
    return {
        "id": bill["id"], "month": bill["month"], "source": bill["source"], "status": bill["status"],
        "total_myr": values.get("total_payable_myr"), "usage_kwh": values.get("current_month_usage_kwh"),
        "checks": f"{passed}/{len(bill['checks'])}" if bill["checks"] else None,
        "charged_myr": bill["charged_myr"], "uploaded_at": bill["uploaded_at"],
    }


def detail(bill: Dict[str, Any]) -> Dict[str, Any]:
    values = values_of(bill)
    return {
        **{key: bill[key] for key in ("id", "month", "source", "mode", "filename", "uploaded_at", "fields", "history",
                                      "notice", "charged_myr", "processing_ms", "checks", "insights", "status")},
        "values": values,
        "charges": [
            {"key": key, "label": label, "help": help_text, "value": values.get(key)} for key, label, help_text in CHARGE_ROWS
        ],
        "threshold": CONFIDENCE_THRESHOLD,
        "disclaimer": "Estimates for preparation only. Not financial advice.",
    }


# ---------------------------------------------------------- recommendations
def recommendations(store: "BoardStore", bill: Dict[str, Any], operations: Dict[str, Any]) -> Dict[str, Any]:
    """S01–S04 eligibility from the four onboarding answers, then U-rule estimates."""
    if bill["status"] not in {"ready", "check_failed"}:
        raise BoardError("Finish checking the flagged fields first — recommendations need a checked bill.", 409, "V12")
    history = list(bill["history"].values())
    baseline = sum(history) / len(history)
    options, skipped = [], []
    if operations.get("lighting") in {"Fluorescent", "Not sure"}:
        options.append({**estimate_led(operations.get("led_tubes", 40)).as_dict(), "rule": "S01", "basis_rules": "U01, U05–U09"})
    else:
        skipped.append("LED lighting — you already use LED (S01)")
    if operations.get("aircon") in {"Non-inverter", "Mixed", "Not sure"} and operations.get("aircon_units", 0) > 0:
        options.append({**estimate_aircon(operations["aircon_units"]).as_dict(), "rule": "S02", "basis_rules": "U02"})
    else:
        skipped.append("Inverter aircon — no non-inverter units reported (S02)")
    if operations.get("roof_access") and operations.get("daytime"):
        kwp = suggested_solar_kwp(baseline)
        options.append({**estimate_solar(kwp, baseline).as_dict(), "rule": "S03", "basis_rules": "U03–U04"})
    else:
        skipped.append("Rooftop solar — needs roof access and daytime operation (S03)")

    if bill.get("explanation") is None:
        bill["explanation"] = explain(bill, options)
    return {
        "bill_id": bill["id"],
        "options": options,
        "skipped": skipped,
        "monitor_only": not options,  # S04
        "explanation": bill["explanation"],
        "parameters": [
            {"label": "TNB tariff (energy + capacity + network)", "value": f"RM{TNB_TARIFF_B_MYR_KWH}/kWh", "source": "TNB Tariff B, 2025 schedule"},
            {"label": "Grid emission factor", "value": f"{GRID_EMISSION_FACTOR_KG_KWH:.3f} kg CO2e/kWh", "source": "Energy Commission, Peninsular grid"},
            {"label": "Solar yield", "value": f"{SOLAR_YIELD_KWH_PER_KWP:,} kWh/kWp/year", "source": "SEDA benchmark"},
            {"label": "Solar benchmark price", "value": f"RM{SOLAR_BENCHMARK_CAPEX_MYR_PER_KWP:,}/kWp", "source": "Market benchmark 2026"},
        ],
        "formulas": [
            "Yearly saving = kWh saved per year × RM0.5068",
            "Payback = cost ÷ yearly saving",
            "CO2e avoided = kWh saved per year × 0.740 kg ÷ 1,000",
            "Solar size = 6-month average × 12 × 68.4% daytime share ÷ 1,320 kWh/kWp",
        ],
        "note": "Same formulas for every option. No supplier is paying for this ranking.",
        "disclaimer": "Estimates for preparation only. Not financial advice.",
    }


# ------------------------------------------------------------ AI explanation
EXPLAIN_SYSTEM = (
    "You explain a Malaysian SME's TNB electricity bill check and upgrade options to the business owner. "
    "Every number has already been calculated by GreenReady's rules engine; use only the numbers given, "
    "never calculate, estimate or invent new figures, and never recommend a supplier, bank or loan. "
    "Write plain English for a busy owner: a one-sentence headline, then three short bullet points "
    "(what changed on this bill, which upgrade pays back fastest and why, one practical next step), "
    "then one closing line saying these are estimates for preparation only, not financial advice. "
    "No markdown headings, no bold, under 120 words."
)


def _rules_explanation(bill: Dict[str, Any], options: List[Dict[str, Any]]) -> str:
    insights = bill["insights"] or {}
    spike = insights.get("spike_pct", {}).get("value")
    lines = [f"Your {bill['month']} bill passed {sum(c['passed'] for c in bill['checks'])} of {len(bill['checks'])} checks."]
    if spike is not None:
        lines.append(f"• Usage is {abs(spike)}% {'above' if spike >= 0 else 'below'} your 6-month average.")
    if options:
        fastest = min(options, key=lambda option: option["payback_years"] or 99)
        lines.append(f"• {fastest['label']} pays back fastest, in about {fastest['payback_years']:.1f} years, "
                     f"saving about RM{fastest['saving_myr_year']:,.0f} a year.")
        biggest = max(options, key=lambda option: option["saving_myr_year"])
        if biggest is not fastest:
            lines.append(f"• {biggest['label']} saves the most: about RM{biggest['saving_myr_year']:,.0f} a year.")
    lines.append("Estimates for preparation only. Not financial advice.")
    return "\n".join(lines)


def explanation_facts(bill: Dict[str, Any], options: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The rule-computed facts an AI writer may use. Send this, with EXPLAIN_SYSTEM, to the model."""
    return {
        "bill_month": bill["month"],
        "checks_passed": f"{sum(c['passed'] for c in bill['checks'])}/{len(bill['checks'])}",
        "failed_checks": [c["label"] for c in bill["checks"] if not c["passed"]],
        "insights": {key: {"label": item["label"], "value": item["value"]} for key, item in (bill["insights"] or {}).items()},
        "options": [
            {key: option[key] for key in ("label", "size", "capex_myr", "saving_myr_year", "payback_years", "co2e_t_year", "basis")}
            for option in options
        ],
    }


def explain(bill: Dict[str, Any], options: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based summary for now.

    To add an AI-written summary later (e.g. the RunPod-hosted model), call it here with
    EXPLAIN_SYSTEM and json.dumps(explanation_facts(...)), return
    {"source": "ai", "model": <name>, "text": <reply>}, and fall back to the rules text on any error.
    """
    return {"source": "rules", "model": None, "text": _rules_explanation(bill, options)}


def ai_reader() -> str:
    return "runpod" if os.getenv("RUNPOD_ENDPOINT_ID") and os.getenv("RUNPOD_API_KEY") else "demo"
