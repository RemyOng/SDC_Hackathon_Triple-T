from pydantic import BaseModel
from typing import Optional


class ExtractedDocument(BaseModel):
    document_type: str  # "TNB_BILL" or "VENDOR_QUOTE"
    account_number: Optional[str] = None
    company_name: Optional[str] = None
    baseline_kwh: Optional[float] = None
    target_capex_myr: Optional[float] = None
    equipment_type: Optional[str] = None

