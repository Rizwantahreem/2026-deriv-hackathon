"""
Document schema definitions for KYC validation.
These models define the data structures for document submissions
compatible with Deriv's verification API format.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentType(str, Enum):
    """Types of documents accepted for KYC verification."""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVING_LICENSE = "driving_license"
    AADHAAR = "aadhaar"
    PAN_CARD = "pan_card"
    VOTER_ID = "voter_id"
    EMIRATES_ID = "emirates_id"
    UTILITY_BILL = "utility_bill"


class DocumentSide(str, Enum):
    """Which side of the document is being uploaded."""
    FRONT = "front"
    BACK = "back"
    SINGLE = "single"  # For documents that don't have sides (e.g., passport photo page)


class IssueSeverity(str, Enum):
    """Severity level of validation issues."""
    BLOCKING = "blocking"  # Must fix before submission
    WARNING = "warning"    # Should fix for better chance of approval
    INFO = "info"          # Informational only


class IssueType(str, Enum):
    """Types of issues that can be detected in documents."""
    MISSING_BACK = "missing_back"
    MISSING_DATE = "missing_date"
    BLURRY = "blurry"
    WRONG_DOCUMENT = "wrong_document"
    EXPIRED = "expired"
    CORNERS_CUT = "corners_cut"
    GLARE = "glare"
    TOO_DARK = "too_dark"
    TOO_BRIGHT = "too_bright"
    PHOTO_MISSING = "photo_missing"
    TEXT_UNREADABLE = "text_unreadable"
    ROTATED = "rotated"
    LOW_RESOLUTION = "low_resolution"
    WRONG_FORMAT = "wrong_format"
    OBSTRUCTED = "obstructed"


class DetectedIssue(BaseModel):
    """Represents a single issue detected in a document."""
    issue_type: IssueType
    severity: IssueSeverity
    description: str
    affected_area: Optional[str] = None  # e.g., "top-left corner", "photo area"
    suggestion: Optional[str] = None  # How to fix this issue


class DocumentSubmission(BaseModel):
    """
    Represents a document upload for KYC verification.
    This model is used for internal processing before formatting for Deriv API.
    """
    document_type: DocumentType
    issuing_country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    image_side: DocumentSide
    image_data: str = Field(..., description="Base64 encoded image data")
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Validation results (populated after analysis)
    is_valid: bool = False
    issues: List[DetectedIssue] = Field(default_factory=list)
    deriv_ready: bool = False


class ValidationResult(BaseModel):
    """
    Result of document validation analysis.
    Contains all information needed to guide the user.
    """
    is_valid: bool = Field(..., description="Whether the document passed validation")
    issues: List[DetectedIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    deriv_ready: bool = Field(False, description="Whether document can be submitted to Deriv")
    completion_percentage: float = Field(0.0, ge=0, le=100)
    
    # Document analysis results
    detected_document_type: Optional[DocumentType] = None
    detected_country: Optional[str] = None
    has_photo: bool = False
    is_readable: bool = False
    all_corners_visible: bool = False
    
    # Processing metadata
    processing_time_ms: Optional[float] = None
    ai_confidence: Optional[float] = None


class DerivUploadPayload(BaseModel):
    """
    Payload format for Deriv's document upload API.
    This matches Deriv's expected WebSocket message format.
    
    Based on Deriv API documentation:
    https://api.deriv.com/api-explorer#document_upload
    """
    document_upload: int = Field(1, description="API call identifier")
    document_type: str = Field(..., description="Type of document being uploaded")
    document_format: str = Field("PNG", description="Format of the document (PNG, JPG, PDF)")
    document_id: Optional[str] = Field(None, description="Document ID/number if applicable")
    expiration_date: Optional[str] = Field(None, description="Document expiry date (YYYY-MM-DD)")
    expected_checksum: str = Field(..., description="MD5 checksum of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    page_type: Optional[str] = Field(None, description="front or back for documents with two sides")
    
    # For passthrough to upload endpoint
    passthrough: Optional[dict] = None
    req_id: Optional[int] = None


class DerivUploadResponse(BaseModel):
    """
    Response format from Deriv's document upload API.
    Used for both mock and real responses.
    """
    echo_req: dict
    msg_type: str = "document_upload"
    document_upload: Optional[dict] = None
    error: Optional[dict] = None
    
    @property
    def is_success(self) -> bool:
        return self.error is None and self.document_upload is not None


class SessionDocument(BaseModel):
    """Tracks a document within a user session."""
    document_type: DocumentType
    front_uploaded: bool = False
    front_valid: bool = False
    back_uploaded: bool = False
    back_valid: bool = False
    back_required: bool = False
    validation_result: Optional[ValidationResult] = None
    uploaded_at: Optional[datetime] = None


class UserSession(BaseModel):
    """
    Tracks a user's KYC session with all uploaded documents.
    """
    session_id: str
    country_code: str
    language: str = "en"
    documents: dict[str, SessionDocument] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_complete: bool = False
    deriv_ready: bool = False
