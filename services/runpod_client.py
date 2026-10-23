import json
import logging
import os
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
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        self.system_prompt = (
            "You are a strict data extraction AI processing Malaysian TNB electricity bills. "
            "Output ONLY valid JSON matching the exact schema requested. Do not include markdown blocks like ```json. "
            "Map the fields as follows based on the document text: "
            "billing_period = 'Tempoh Bil', bill_date = 'TARIKH BIL', tariff = 'TARIF', "
            "reading_type = 'JENIS BACAAN', current_month_usage_kwh = 'Jumlah Penggunaan Anda (kWh)', "
            "average_usage_kwh = 'Purata Penggunaan Anda', history_6_months_kwh = extract the 6 monthly kWh values as a list of floats from 'Penggunaan (kWh)', "
            "meter_reading_previous = 'Bacaan Meter Dahulu' (kWh row), meter_reading_current = 'Semasa' (kWh row), "
            "peak_demand_kw = 'Penggunaan (kW)' row value, reactive_power_kvarh = 'Penggunaan (kVARh)' row value, "
            "energy_charge_myr = 'Caj Penjanaan', capacity_charge_myr = 'Kapasiti', "
            "network_charge_myr = 'Caj Rangkaian', afa_charge_myr = 'AFA', retail_charge_myr = 'Caj Peruncitan', "
            "ee_incentive_myr = 'Insentif Cekap Tenaga', service_tax_myr = 'Cukai Perkhidmatan', "
            "kwtbb_myr = 'KWTBB', current_charges_myr = 'Caj Semasa', total_payable_myr = 'Jumlah Bil Anda'. "
            "Remove all 'RM' symbols and commas from numbers. Return null if a field is not found."
        )

    def extract_document_metrics(self, base64_images: List[str]) -> ExtractedDocument:
        """
        Sends base64 images to Qwen2-VL and validates the returned JSON.
        Handles dynamic worker templates (lists vs dicts).
        """
        if not base64_images:
            raise ValueError("No images provided for extraction.")

        # Construct multimodal prompt for Qwen2-VL
        content = [{"type": "text", "text": self.system_prompt}]
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
                "max_tokens": 1024
            }
        }

        try:
            logger.info("Sending %d images to RunPod endpoint %s", len(base64_images), self.endpoint_id)
            response = requests.post(self.url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()

            result_data = response.json()
            result_data = response.json()

            # --- DEFENSIVE OUTPUT PARSING ---
            try:
                output_data = result_data.get("output")
                raw_output = ""

                if isinstance(output_data, str):
                    raw_output = output_data
                elif isinstance(output_data, list) and len(output_data) > 0:
                    first_item = output_data[0]
                    if isinstance(first_item, str):
                        raw_output = first_item
                    elif isinstance(first_item, dict):
                        choices = first_item.get("choices", [])
                        if choices and isinstance(choices, list) and len(choices) > 0:
                            raw_output = choices[0].get("message", {}).get("content", "")
                        else:
                            raw_output = first_item.get("text", "") or first_item.get("message", {}).get("content", "")
                elif isinstance(output_data, dict):
                    choices = output_data.get("choices", [])
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        raw_output = choices[0].get("message", {}).get("content", "")
                    else:
                        raw_output = output_data.get("text", "")

                if not raw_output:
                    raise ValueError("Traversal succeeded but resulted in an empty string.")

            except Exception as parse_exc:
                logger.error("RunPod JSON structure violation! Failed to parse payload: %s", result_data)
                raise RunPodError(f"Failed to extract text from RunPod response: {parse_exc}") from parse_exc

            return self._parse_and_validate(raw_output)

        except requests.exceptions.Timeout as exc:
            logger.error("RunPod request timed out. The 48GB worker might be cold-starting.")
            raise RunPodError("Inference timed out.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("RunPod network error: %s", exc)
            raise RunPodError(f"Network error: {exc}") from exc


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