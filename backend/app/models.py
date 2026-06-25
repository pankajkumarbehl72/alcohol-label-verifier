from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ApplicationFields(BaseModel):
    brand_name: str
    class_type: str
    alcohol_content: str
    net_contents: str
    producer_name_address: Optional[str] = None
    country_of_origin: Optional[str] = None


class ExtractedLabelFields(BaseModel):
    brand_name: Optional[str] = None
    class_type: Optional[str] = None
    alcohol_content: Optional[str] = None
    net_contents: Optional[str] = None
    producer_name_address: Optional[str] = None
    country_of_origin: Optional[str] = None
    government_warning: Optional[str] = None
    raw_text: Optional[str] = None
    extraction_method: str = "unknown"


class FieldCheck(BaseModel):
    field: str
    status: CheckStatus
    expected: Optional[str] = None
    found: Optional[str] = None
    score: Optional[float] = None
    message: str


class VerificationResponse(BaseModel):
    overall_status: CheckStatus
    checks: List[FieldCheck]
    extracted_fields: ExtractedLabelFields
    processing_time_seconds: float
    metadata: Dict[str, Any] = {}
