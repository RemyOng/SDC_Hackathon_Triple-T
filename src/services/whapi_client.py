import requests
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class WhatsAppDocument:
    sender_number: str
    filename: str
    file_bytes: bytes


class WhapiClient:
    """
    Dedicated client for handling all Whapi.cloud interactions.
    Strictly isolated from FastAPI routing and AI logic.
    """

    def __init__(self, api_token: str):
        self.token = api_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

    def extract_media_info(self, payload: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """
        Parses the Whapi webhook payload to find documents or images.
        Returns: (sender_number, filename, media_download_url) or None if not media.
        """
        try:
            messages = payload.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            # Extract standard phone number (e.g., from '60123456789@s.whatsapp.net')
            sender = msg.get("chat_id", "").split("@")[0]
            msg_type = msg.get("type")

            if msg_type not in ["document", "image"]:
                return None

            # Whapi nests file details under the type key (e.g., msg['document'])
            media_info = msg.get(msg_type, {})

            # Fallback filename if it's a raw photo from the camera
            filename = media_info.get("file_name") or f"whatsapp_{msg_type}.jpeg"
            media_url = media_info.get("link")

            if not media_url:
                return None

            return sender, filename, media_url

        except (KeyError, IndexError) as e:
            print(f"[WhapiClient] Payload parsing error: {e}")
            return None

    def download_file(self, media_url: str) -> Optional[bytes]:
        """
        Downloads the raw file bytes using the Whapi secure media link.
        """
        try:
            response = requests.get(media_url, headers=self.headers, stream=True)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"[WhapiClient] Failed to download media: {e}")
            return None

    def process_webhook(self, payload: Dict[str, Any]) -> Optional[WhatsAppDocument]:
        """
        Orchestrator method: takes a raw webhook JSON and returns a clean dataclass
        containing the sender, filename, and the actual file bytes.
        """
        media_info = self.extract_media_info(payload)
        if not media_info:
            return None

        sender, filename, media_url = media_info

        file_bytes = self.download_file(media_url)
        if not file_bytes:
            return None

        return WhatsAppDocument(
            sender_number=sender,
            filename=filename,
            file_bytes=file_bytes
        )