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


# =============================================================================
# SERVICE IMPLEMENTATION
# =============================================================================
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
            "You are a strict data extraction AI. Read the provided document images "
            "and extract the required fields. You must output ONLY raw, valid JSON. "
            "Do not include markdown blocks, greetings, or explanations. "
            "Schema format: {\"document_type\": \"TNB_BILL\"|\"VENDOR_QUOTE\", "
            "\"account_number\": string|null, \"company_name\": string|null, "
            "\"baseline_kwh\": float|null, \"target_capex_myr\": float|null, "
            "\"equipment_type\": string|null}"
        )

    def extract_document_metrics(self, base64_images: List[str]) -> ExtractedDocument:
        """
        Sends base64 images to Qwen2-VL and validates the returned JSON.
        """
        if not base64_images:
            raise ValueError("No images provided for extraction.")

        # Construct multimodal prompt for Qwen2-VL (OpenAI-compatible format often used by vLLM)
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

            # RunPod wraps outputs based on the specific worker template (e.g., vLLM vs native)
            # Assuming a standard vLLM OpenAI wrapper structure inside the 'output' key:
            raw_output = result_data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")

            if not raw_output:
                raise RunPodError(f"Unexpected empty response from model. Full payload: {result_data}")

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