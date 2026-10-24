import json
import logging
import os
import time
import requests
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError
from schema.schemas import ExtractedDocument

logger = logging.getLogger(__name__)


class RunPodError(Exception):
    """Raised when inference fails or times out."""


class ParseError(Exception):
    """Raised when the LLM hallucinates outside the requested JSON schema."""


class RunPodVLMClient:
    """
    Dedicated client for Qwen2-VL on RunPod Serverless.
    Enforces JSON schema output and handles endpoint timeouts.
    """

    def __init__(self, endpoint_id: Optional[str] = None, api_key: Optional[str] = None):
        self.endpoint_id = endpoint_id or os.getenv("RUNPOD_ENDPOINT_ID")
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")

        if not self.endpoint_id or not self.api_key:
            raise ValueError("RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY must be configured.")

        # Using the /runsync endpoint blocks until completion (good for FastAPI webhooks)
        self.url = f"https://api.runpod.ai/v2/{self.endpoint_id}/runsync"
        self.status_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/status"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.system_prompt = (
            "You are a strict data extraction AI processing Malaysian TNB electricity bills. "
            "Output ONLY one complete JSON object matching the exact schema requested. "
            "Always include every field in the schema, even when its value is null. "
            "Use the bill image and any supplied OCR text together; prefer values visibly printed on the bill. "
            "Do not include markdown blocks like ```json. "
            "Map the fields as follows based on the document text: "
            "billing_period = 'Tempoh Bil', bill_date = 'TARIKH BIL', tariff = 'TARIF', "
            "reading_type = 'JENIS BACAAN', current_month_usage_kwh = 'Jumlah Penggunaan Anda (kWh)', "
            "peak_usage_kwh = peak-period usage in kWh if shown, offpeak_usage_kwh = off-peak usage in kWh if shown, "
            "average_usage_kwh = 'Purata Penggunaan Anda', history_6_months_kwh = extract the 6 monthly kWh values as a list of floats from 'Penggunaan (kWh)', "
            "meter_reading_previous = 'Bacaan Meter Dahulu' (kWh row) only when explicitly shown, meter_reading_current = 'Semasa' (kWh row) only when explicitly shown, "
            "Do not calculate or infer meter readings from monthly usage; return null when those rows are absent. "
            "peak_demand_kw = 'Penggunaan (kW)' row value, reactive_power_kvarh = 'Penggunaan (kVARh)' row value, "
            "energy_charge_myr = 'Caj Penjanaan', capacity_charge_myr = 'Kapasiti', "
            "network_charge_myr = 'Caj Rangkaian', afa_charge_myr = 'AFA', retail_charge_myr = 'Caj Peruncitan', "
            "ee_incentive_myr = 'Insentif Cekap Tenaga', service_tax_myr = 'Cukai Perkhidmatan', "
            "kwtbb_myr = 'KWTBB', current_charges_myr = 'Caj Semasa', "
            "previous_balance_myr = 'Baki Terdahulu', total_payable_myr = 'Jumlah Bil Anda'. "
            "For a bill with a detailed 'Maklumat Meter' table, map 'Bacaan Dahulu' to meter_reading_previous, "
            "'Meter Semasa' to meter_reading_current, 'Penggunaan' to current_month_usage_kwh, and the unit-specific "
            "rows to peak_demand_kw (kW) and reactive_power_kvarh (kVARh). "
            "Remove all 'RM' symbols and commas from numbers. Return null if a field is not found."
        )

    def extract_document_metrics(
        self,
        base64_images: List[str],
        document_text: str = "",
    ) -> ExtractedDocument:
        """
        Sends base64 images to Qwen2-VL and validates the returned JSON.
        Handles dynamic worker templates (lists vs dicts).
        """
        if not base64_images:
            raise ValueError("No images provided for extraction.")

        # Construct multimodal prompt for Qwen2-VL
        prompt = self.system_prompt
        if document_text:
            prompt += (
                "\n\nOCR TEXT EXTRACTED FROM THE ORIGINAL BILL:\n"
                f"{document_text[:16000]}\n"
                "\nUse this text to recover small or low-contrast values from the image. "
                "Do not omit readable financial, metering, or consumption fields."
            )
        content = [{"type": "text", "text": prompt}]
        for b64_img in base64_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_img}"}
            })

        payload = {
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "temperature": 0.1,  # Low temp for deterministic extraction
                "max_tokens": 2048
            }
        }

        try:
            logger.info("Sending %d images to RunPod endpoint %s", len(base64_images), self.endpoint_id)
            response = requests.post(self.url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()

            result_data = response.json()
            result_data = self._wait_for_result(result_data)
            raw_output = self._extract_output_text(result_data)
            return self._parse_and_validate(raw_output)

        except requests.exceptions.Timeout as exc:
            logger.error("RunPod request timed out. The 48GB worker might be cold-starting.")
            raise RunPodError("Inference timed out.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("RunPod network error: %s", exc)
            raise RunPodError(f"Network error: {exc}") from exc

    def _wait_for_result(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle RunPod returning a job id before the worker has completed."""
        status = result_data.get("status")
        job_id = result_data.get("id")
        if status in {"IN_QUEUE", "IN_PROGRESS"} and job_id:
            logger.info("RunPod job %s is %s; polling for completion.", job_id, status)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                time.sleep(2)
                response = requests.get(
                    f"{self.status_url}/{job_id}",
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()
                result_data = response.json()
                status = result_data.get("status")
                if status not in {"IN_QUEUE", "IN_PROGRESS"}:
                    break
            else:
                raise RunPodError(f"RunPod job {job_id} did not complete within 120 seconds.")

        if status == "FAILED":
            detail = result_data.get("error") or "RunPod worker failed without a reason."
            raise RunPodError(f"RunPod extraction failed: {detail}")
        if status not in {"COMPLETED", None}:
            raise RunPodError(f"Unexpected RunPod job status: {status or 'missing'}")
        return result_data

    @staticmethod
    def _extract_output_text(result_data: Dict[str, Any]) -> str:
        output_data = result_data.get("output")
        raw_output = ""
        if isinstance(output_data, str):
            raw_output = output_data
        elif isinstance(output_data, list) and output_data:
            first_item = output_data[0]
            if isinstance(first_item, str):
                raw_output = first_item
            elif isinstance(first_item, dict):
                choices = first_item.get("choices", [])
                if choices:
                    raw_output = choices[0].get("message", {}).get("content", "")
                else:
                    raw_output = first_item.get("text", "") or first_item.get("message", {}).get("content", "")
        elif isinstance(output_data, dict):
            choices = output_data.get("choices", [])
            if choices:
                raw_output = choices[0].get("message", {}).get("content", "")
            else:
                raw_output = output_data.get("text", "")
        if not raw_output:
            logger.error("RunPod returned no model output: %s", result_data)
            raise RunPodError("RunPod completed without returning extraction output.")
        return raw_output


    def _parse_and_validate(self, raw_text: str) -> ExtractedDocument:
        """Strips markdown and validates against the Pydantic schema."""

        clean_text = raw_text.strip()
        # Handle models that ignore instructions and wrap in ```json
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        try:
            data = json.loads(clean_text.strip())
            # Pydantic validates types (e.g., ensures target_capex_myr is a float)
            return ExtractedDocument(**data)
        except json.JSONDecodeError as exc:
            logger.error("LLM failed to output valid JSON: %s", clean_text)
            raise ParseError(f"JSON decode failed: {exc}") from exc
        except ValidationError as exc:
            logger.error("LLM output JSON but it violated the strict schema: %s", exc.json())
            raise ParseError(f"Schema validation failed: {exc}") from exc