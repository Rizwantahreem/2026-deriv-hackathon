"""
Mock Deriv API Client

Simulates the Deriv API for document submission without requiring
an actual Deriv account. This enables development and testing
while mimicking real Deriv API behavior.

Note: This is a MOCK implementation for hackathon development.
In production, this would be replaced with the actual Deriv API.
"""

import time
import random
import hashlib
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

from config.document_schema import (
    DocumentType,
    DocumentSide,
    IssueSeverity
)


class DerivStatus(str, Enum):
    """Document submission status from Deriv."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class DocumentSubmission(BaseModel):
    """Internal document submission model for mock API."""
    document_type: str
    document_format: str = "PNG"
    side: str = "front"
    image_data: str = ""
    checksum: str = ""
    file_size: int = 0
    country_code: str = ""


class MockDerivResponse(BaseModel):
    """Simulated Deriv API response."""
    status: DerivStatus
    document_id: str
    message: str
    processing_time_ms: int
    details: Optional[dict] = None


class DerivAPIError(Exception):
    """Exception for Deriv API errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Deriv API Error [{code}]: {message}")


class MockDerivClient:
    """
    Mock Deriv API client for document submission.
    
    Simulates:
    - Document upload
    - Validation responses
    - Processing delays
    - Various error scenarios
    
    This allows full testing of the KYC flow without a real Deriv account.
    """
    
    def __init__(self, simulate_delay: bool = True):
        """
        Initialize mock Deriv client.
        
        Args:
            simulate_delay: Whether to add realistic delays
        """
        self.simulate_delay = simulate_delay
        self.submitted_documents = {}  # Store submitted docs for session
        
    def submit_document(
        self,
        payload: DocumentSubmission,
        issue_score: int = 100
    ) -> MockDerivResponse:
        """
        Submit a document to mock Deriv API.
        
        Args:
            payload: Document submission payload
            issue_score: Score from issue detector (0-100)
            
        Returns:
            MockDerivResponse with simulated result
        """
        # Simulate network delay
        if self.simulate_delay:
            time.sleep(random.uniform(0.5, 1.5))
            
        # Generate document ID
        doc_id = self._generate_document_id(payload)
        
        # Determine outcome based on issue score
        response = self._determine_outcome(payload, issue_score, doc_id)
        
        # Store submission
        self.submitted_documents[doc_id] = {
            "payload": payload.model_dump(),
            "response": response.model_dump(),
            "timestamp": time.time()
        }
        
        return response
        
    def _generate_document_id(self, payload: DocumentSubmission) -> str:
        """Generate a unique document ID."""
        unique_string = f"{payload.document_type}_{payload.side}_{time.time()}"
        hash_obj = hashlib.md5(unique_string.encode())
        return f"DOC_{hash_obj.hexdigest()[:12].upper()}"
        
    def _determine_outcome(
        self,
        payload: DocumentSubmission,
        issue_score: int,
        doc_id: str
    ) -> MockDerivResponse:
        """Determine submission outcome based on score and payload."""
        processing_time = random.randint(500, 2000)
        
        # High score (80-100): Likely accepted
        if issue_score >= 80:
            return MockDerivResponse(
                status=DerivStatus.ACCEPTED,
                document_id=doc_id,
                message="Document accepted for verification",
                processing_time_ms=processing_time,
                details={
                    "next_step": "await_verification",
                    "estimated_time": "24-48 hours",
                    "document_type": payload.document_type
                }
            )
            
        # Medium score (50-79): Needs review
        elif issue_score >= 50:
            return MockDerivResponse(
                status=DerivStatus.NEEDS_REVIEW,
                document_id=doc_id,
                message="Document received but requires manual review",
                processing_time_ms=processing_time,
                details={
                    "reason": "Quality concerns detected",
                    "recommendation": "Consider resubmitting with clearer image",
                    "can_proceed": True
                }
            )
            
        # Low score (0-49): Rejected
        else:
            rejection_reasons = {
                "blurry": "Image quality too low - document text not readable",
                "incomplete": "Document appears incomplete or cut off",
                "wrong_type": "Document type doesn't match selected option",
                "unverifiable": "Unable to verify document authenticity"
            }
            reason_key = random.choice(list(rejection_reasons.keys()))
            
            return MockDerivResponse(
                status=DerivStatus.REJECTED,
                document_id=doc_id,
                message=rejection_reasons[reason_key],
                processing_time_ms=processing_time,
                details={
                    "rejection_code": reason_key.upper(),
                    "can_retry": True,
                    "max_retries": 3
                }
            )
            
    def check_document_status(self, document_id: str) -> MockDerivResponse:
        """
        Check status of a previously submitted document.
        
        Args:
            document_id: The document ID to check
            
        Returns:
            MockDerivResponse with current status
        """
        if document_id not in self.submitted_documents:
            raise DerivAPIError(
                code="DOC_NOT_FOUND",
                message=f"Document {document_id} not found"
            )
            
        stored = self.submitted_documents[document_id]
        
        # Simulate status progression over time
        elapsed = time.time() - stored["timestamp"]
        
        if elapsed > 60:  # After 1 minute, simulate completion
            return MockDerivResponse(
                status=DerivStatus.ACCEPTED,
                document_id=document_id,
                message="Document verification complete",
                processing_time_ms=0,
                details={"verified": True}
            )
        else:
            return MockDerivResponse(**stored["response"])
            
    def validate_document_type(
        self,
        document_type: DocumentType,
        country_code: str
    ) -> dict:
        """
        Validate if a document type is accepted for a country.
        
        Args:
            document_type: Type of document
            country_code: ISO country code
            
        Returns:
            Validation result dict
        """
        from config.deriv_context import get_document_requirements
        
        requirements = get_document_requirements(country_code, document_type.value)
        
        if requirements:
            return {
                "valid": True,
                "document_type": document_type.value,
                "country": country_code,
                "requirements": requirements
            }
        else:
            return {
                "valid": False,
                "document_type": document_type.value,
                "country": country_code,
                "error": f"{document_type.value} not accepted for {country_code}"
            }
            
    def get_accepted_documents(self, country_code: str) -> list:
        """
        Get list of accepted documents for a country.
        
        Args:
            country_code: ISO country code
            
        Returns:
            List of accepted document types
        """
        from config.deriv_context import get_supported_countries
        
        countries = get_supported_countries()
        
        for country in countries:
            if country["code"] == country_code:
                return country.get("supported_documents", [])
                
        return []
        
    def simulate_error(self, error_type: str = "network"):
        """
        Simulate various API errors for testing.
        
        Args:
            error_type: Type of error to simulate
        """
        errors = {
            "network": DerivAPIError("NETWORK_ERROR", "Connection timeout"),
            "rate_limit": DerivAPIError("RATE_LIMIT", "Too many requests"),
            "auth": DerivAPIError("UNAUTHORIZED", "Invalid API credentials"),
            "server": DerivAPIError("SERVER_ERROR", "Internal server error"),
            "maintenance": DerivAPIError("MAINTENANCE", "Service temporarily unavailable")
        }
        
        raise errors.get(error_type, errors["server"])


class DerivSubmissionManager:
    """
    High-level manager for Deriv document submissions.
    
    Handles the full workflow of:
    1. Preparing submission payload
    2. Submitting document
    3. Handling responses
    4. Tracking submission history
    """
    
    def __init__(self):
        self.client = MockDerivClient()
        self.submission_history = []
        
    def prepare_and_submit(
        self,
        document_type: str,
        side: str,
        image_data: str,  # Base64
        checksum: str,
        country_code: str,
        issue_score: int = 100,
        file_size: int = 0
    ) -> dict:
        """
        Prepare payload and submit document.
        
        Args:
            document_type: Type of document (string)
            side: Front or back
            image_data: Base64 encoded image
            checksum: MD5 checksum of image
            country_code: User's country code
            issue_score: Score from issue detection
            file_size: Size of file in bytes
            
        Returns:
            Submission result dict
        """
        # Create payload
        payload = DocumentSubmission(
            document_type=document_type,
            side=side,
            image_data=image_data,
            checksum=checksum,
            country_code=country_code,
            file_size=file_size
        )
        
        # Submit
        response = self.client.submit_document(payload, issue_score)
        
        # Create result
        result = {
            "success": response.status != DerivStatus.REJECTED,
            "document_id": response.document_id,
            "status": response.status.value,
            "message": response.message,
            "details": response.details,
            "can_proceed": response.status in [DerivStatus.ACCEPTED, DerivStatus.NEEDS_REVIEW]
        }
        
        # Track history
        self.submission_history.append({
            "document_id": response.document_id,
            "document_type": document_type,
            "side": side,
            "status": response.status.value,
            "timestamp": time.time()
        })
        
        return result
        
    def get_submission_status(self, document_id: str) -> dict:
        """Check status of a submission."""
        try:
            response = self.client.check_document_status(document_id)
            return {
                "found": True,
                "status": response.status.value,
                "message": response.message
            }
        except DerivAPIError as e:
            return {
                "found": False,
                "error": e.message
            }
            
    def get_history(self) -> list:
        """Get submission history."""
        return self.submission_history
        
    def can_submit(self, issue_score: int) -> dict:
        """
        Check if document is ready for submission.
        
        Args:
            issue_score: Score from issue detection
            
        Returns:
            Readiness status dict
        """
        if issue_score >= 80:
            return {
                "ready": True,
                "recommendation": "submit",
                "message": "Your document looks good! Ready to submit."
            }
        elif issue_score >= 50:
            return {
                "ready": True,
                "recommendation": "review",
                "message": "You can submit, but consider fixing issues for faster approval."
            }
        else:
            return {
                "ready": False,
                "recommendation": "fix",
                "message": "Please fix the highlighted issues before submitting."
            }


# ============================================================================
# MODULE-LEVEL INSTANCES
# ============================================================================

_client = None
_manager = None


def get_deriv_client() -> MockDerivClient:
    """Get singleton mock Deriv client."""
    global _client
    if _client is None:
        _client = MockDerivClient()
    return _client


def get_submission_manager() -> DerivSubmissionManager:
    """Get singleton submission manager."""
    global _manager
    if _manager is None:
        _manager = DerivSubmissionManager()
    return _manager


def submit_document(
    document_type: str,
    side: str,
    image_data: str,
    checksum: str,
    country_code: str,
    issue_score: int = 100
) -> dict:
    """
    Convenience function to submit a document.
    
    Args:
        document_type: Document type string
        side: 'front' or 'back'
        image_data: Base64 image
        checksum: MD5 checksum
        country_code: Country code
        issue_score: Quality score
        
    Returns:
        Submission result
    """
    manager = get_submission_manager()
    
    return manager.prepare_and_submit(
        document_type=document_type,
        side=side,
        image_data=image_data,
        checksum=checksum,
        country_code=country_code,
        issue_score=issue_score
    )
