"""
Deriv API Client — Real WebSocket integration with graceful mock fallback.

Connects to Deriv's WebSocket API (wss://ws.derivws.com/websockets/v3)
for document_upload, get_account_status, and authorize calls.

When no API token is configured or the connection fails, falls back to
structured mock responses that mirror Deriv's exact API response format.

Reference: https://api.deriv.com/api-explorer#document_upload
"""

import json
import time
import asyncio
import hashlib
import logging
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

from config.settings import settings
from config.document_schema import (
    DocumentType,
    DocumentSide,
    IssueSeverity,
    DerivUploadPayload,
    DerivUploadResponse,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & MODELS
# ============================================================================

class DerivStatus(str, Enum):
    """Document submission status from Deriv."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class SubmissionRecord(BaseModel):
    """Internal record of a document submission."""
    document_id: str
    document_type: str
    side: str
    country_code: str
    status: DerivStatus
    quality_score: int = 0
    risk_level: str = "LOW"
    risk_score: int = 0
    risk_factors: list = Field(default_factory=list)
    form_data: dict = Field(default_factory=dict)
    ocr_data: dict = Field(default_factory=dict)
    mismatches: list = Field(default_factory=list)
    message: str = ""
    timestamp: float = Field(default_factory=time.time)
    reviewer_action: Optional[str] = None  # approve / reject / None
    reviewer_notes: str = ""


# ============================================================================
# DERIV WEBSOCKET CLIENT
# ============================================================================

class DerivWebSocketClient:
    """
    Real Deriv WebSocket API client.

    Connects to wss://ws.derivws.com/websockets/v3?app_id={app_id}
    and sends/receives JSON messages per Deriv's API spec.

    Falls back to structured mock responses when:
    - No API token is configured
    - WebSocket connection fails
    - Response indicates auth error
    """

    def __init__(self):
        self.app_id = settings.DERIV_APP_ID
        self.api_token = settings.DERIV_API_TOKEN
        self.ws_url = f"{settings.DERIV_WS_URL}?app_id={self.app_id}"
        self._ws = None
        self._req_id = 0
        self._authorized = False
        self._connection_tested = False
        self._connection_available = False

    @property
    def is_configured(self) -> bool:
        """Check if real API token is available."""
        return bool(self.api_token)

    def _next_req_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _connect(self):
        """Establish WebSocket connection."""
        if self._ws is not None:
            return

        try:
            import websockets
            self._ws = await asyncio.wait_for(
                websockets.connect(self.ws_url),
                timeout=5.0
            )
            self._connection_available = True
            logger.info(f"[Deriv WS] Connected to {self.ws_url}")
        except Exception as e:
            self._ws = None
            self._connection_available = False
            logger.warning(f"[Deriv WS] Connection failed: {e}")

    async def _send_and_receive(self, payload: dict) -> dict:
        """Send a message and wait for the response."""
        if self._ws is None:
            await self._connect()

        if self._ws is None:
            raise ConnectionError("WebSocket not connected")

        payload["req_id"] = self._next_req_id()

        await self._ws.send(json.dumps(payload))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
        return json.loads(raw)

    async def test_connection(self) -> bool:
        """Test if Deriv WebSocket is reachable (ping)."""
        if self._connection_tested:
            return self._connection_available

        try:
            await self._connect()
            if self._ws:
                response = await self._send_and_receive({"ping": 1})
                self._connection_available = response.get("msg_type") == "ping"
                logger.info(f"[Deriv WS] Ping OK: {self._connection_available}")
            else:
                self._connection_available = False
        except Exception as e:
            self._connection_available = False
            logger.warning(f"[Deriv WS] Ping failed: {e}")

        self._connection_tested = True
        return self._connection_available

    async def authorize(self) -> dict:
        """Authorize the session with an API token."""
        if not self.api_token:
            return {"error": {"code": "NO_TOKEN", "message": "No API token configured"}}

        try:
            response = await self._send_and_receive({
                "authorize": self.api_token
            })

            if response.get("error"):
                logger.warning(f"[Deriv WS] Auth failed: {response['error']}")
                self._authorized = False
            else:
                self._authorized = True
                logger.info("[Deriv WS] Authorized successfully")

            return response
        except Exception as e:
            logger.warning(f"[Deriv WS] Auth error: {e}")
            return {"error": {"code": "CONNECTION_ERROR", "message": str(e)}}

    async def get_account_status(self) -> dict:
        """Get the account KYC status from Deriv."""
        try:
            if not self._authorized and self.api_token:
                await self.authorize()

            response = await self._send_and_receive({
                "get_account_status": 1
            })
            return response
        except Exception as e:
            logger.warning(f"[Deriv WS] get_account_status failed: {e}")
            return _mock_account_status()

    async def document_upload(self, payload: DerivUploadPayload) -> dict:
        """
        Send document_upload call to Deriv's API.

        The actual binary upload is a two-step process in Deriv:
        1. Send document_upload JSON with metadata -> get upload_url
        2. POST binary to upload_url

        For the hackathon, we send step 1 to demonstrate real API integration.
        """
        try:
            if not self._authorized and self.api_token:
                await self.authorize()

            msg = {
                "document_upload": 1,
                "document_type": payload.document_type,
                "document_format": payload.document_format,
                "expected_checksum": payload.expected_checksum,
                "file_size": payload.file_size,
            }

            if payload.document_id:
                msg["document_id"] = payload.document_id
            if payload.expiration_date:
                msg["expiration_date"] = payload.expiration_date
            if payload.page_type:
                msg["page_type"] = payload.page_type

            response = await self._send_and_receive(msg)
            logger.info(f"[Deriv WS] document_upload response: {response.get('msg_type')}")
            return response

        except Exception as e:
            logger.warning(f"[Deriv WS] document_upload failed: {e}")
            return None  # Caller will use mock fallback

    async def close(self):
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("[Deriv WS] Connection closed")


# ============================================================================
# MOCK RESPONSE HELPERS (mirror exact Deriv API format)
# ============================================================================

def _mock_account_status() -> dict:
    """Mock get_account_status response in Deriv's format."""
    return {
        "msg_type": "get_account_status",
        "get_account_status": {
            "status": ["cashier_locked", "unwelcome"],
            "authentication": {
                "document": {"status": "none"},
                "identity": {"status": "none"},
                "needs_verification": ["identity", "document"]
            },
            "currency_config": {}
        }
    }


def _mock_document_upload_response(
    document_type: str,
    issue_score: int,
    doc_id: str
) -> dict:
    """Mock document_upload response in Deriv's exact API format."""

    if issue_score >= 80:
        status = "accepted"
        message = "Document accepted for verification"
    elif issue_score >= 50:
        status = "needs_review"
        message = "Document received but requires manual review"
    else:
        status = "rejected"
        message = "Document quality too low — please resubmit"

    return {
        "msg_type": "document_upload",
        "echo_req": {
            "document_upload": 1,
            "document_type": document_type,
        },
        "document_upload": {
            "call_type": doc_id,
            "checksum": "",
            "document_id": doc_id,
            "size": 0,
            "status": status,
        }
    }


def _generate_document_id(document_type: str, side: str) -> str:
    """Generate a unique document ID."""
    unique = f"{document_type}_{side}_{time.time()}"
    return f"DOC_{hashlib.md5(unique.encode()).hexdigest()[:12].upper()}"


# ============================================================================
# SUBMISSION MANAGER (high-level orchestrator)
# ============================================================================

class DerivSubmissionManager:
    """
    High-level manager for Deriv document submissions.

    Orchestrates:
    1. Building DerivUploadPayload
    2. Attempting real Deriv WebSocket call
    3. Falling back to mock if connection unavailable
    4. Tracking all submissions for compliance dashboard
    """

    def __init__(self):
        self.client = DerivWebSocketClient()
        self.submission_history: list[SubmissionRecord] = []

    def prepare_and_submit(
        self,
        document_type: str,
        side: str,
        image_data: str,
        checksum: str,
        country_code: str,
        issue_score: int = 100,
        file_size: int = 0,
        form_data: dict = None,
        ocr_data: dict = None,
        mismatches: list = None,
        risk_level: str = "LOW",
        risk_score: int = 0,
        risk_factors: list = None,
    ) -> dict:
        """
        Prepare payload and submit document.

        Tries real Deriv WebSocket API first, falls back to mock.
        """
        doc_id = _generate_document_id(document_type, side)

        # Build Deriv API payload
        payload = DerivUploadPayload(
            document_type=document_type,
            document_format="PNG",
            expected_checksum=checksum,
            file_size=file_size or len(image_data),
            page_type=side if side in ("front", "back") else None,
        )

        # Try real Deriv API
        deriv_response = None
        used_real_api = False

        if self.client.is_configured:
            try:
                loop = asyncio.new_event_loop()
                deriv_response = loop.run_until_complete(
                    self.client.document_upload(payload)
                )
                loop.close()
                if deriv_response and not deriv_response.get("error"):
                    used_real_api = True
                    doc_id = deriv_response.get("document_upload", {}).get(
                        "document_id", doc_id
                    )
                    logger.info(f"[Deriv] Real API submission: {doc_id}")
            except Exception as e:
                logger.warning(f"[Deriv] Real API failed, using mock: {e}")

        # Fall back to mock
        if not used_real_api:
            deriv_response = _mock_document_upload_response(
                document_type, issue_score, doc_id
            )
            logger.info(f"[Deriv] Mock submission: {doc_id}")

        # Determine status
        upload_info = deriv_response.get("document_upload", {})
        status_str = upload_info.get("status", "pending")
        status_map = {
            "accepted": DerivStatus.ACCEPTED,
            "rejected": DerivStatus.REJECTED,
            "needs_review": DerivStatus.NEEDS_REVIEW,
            "pending": DerivStatus.PENDING,
        }
        status = status_map.get(status_str, DerivStatus.PENDING)

        # If there are data mismatches, always flag for manual review
        if mismatches:
            status = DerivStatus.NEEDS_REVIEW

        # Determine message
        messages = {
            DerivStatus.ACCEPTED: "Document accepted for verification",
            DerivStatus.NEEDS_REVIEW: "Document flagged for manual compliance review",
            DerivStatus.REJECTED: "Document rejected — please resubmit with better quality",
            DerivStatus.PENDING: "Document submitted, awaiting processing",
        }

        # Create submission record
        record = SubmissionRecord(
            document_id=doc_id,
            document_type=document_type,
            side=side,
            country_code=country_code,
            status=status,
            quality_score=issue_score,
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors or [],
            form_data=form_data or {},
            ocr_data=ocr_data or {},
            mismatches=mismatches or [],
            message=messages.get(status, "Submitted"),
        )
        self.submission_history.append(record)

        return {
            "success": status != DerivStatus.REJECTED,
            "document_id": doc_id,
            "status": status.value,
            "message": record.message,
            "can_proceed": status in (DerivStatus.ACCEPTED, DerivStatus.NEEDS_REVIEW),
            "used_real_api": used_real_api,
            "deriv_response": deriv_response,
        }

    def get_submission_status(self, document_id: str) -> dict:
        """Check status of a submission."""
        for record in self.submission_history:
            if record.document_id == document_id:
                return {
                    "found": True,
                    "status": record.status.value,
                    "message": record.message,
                    "quality_score": record.quality_score,
                }
        return {"found": False, "error": f"Document {document_id} not found"}

    def get_all_submissions(self) -> list[SubmissionRecord]:
        """Get all submission records (for compliance dashboard)."""
        return self.submission_history

    def get_pending_reviews(self) -> list[SubmissionRecord]:
        """Get submissions needing manual review."""
        return [
            r for r in self.submission_history
            if r.status == DerivStatus.NEEDS_REVIEW and r.reviewer_action is None
        ]

    def get_flagged_submissions(self) -> list[SubmissionRecord]:
        """Get submissions with risk flags (HIGH risk or mismatches)."""
        return [
            r for r in self.submission_history
            if r.risk_level == "HIGH" or r.mismatches
        ]

    def review_submission(self, document_id: str, action: str, notes: str = "") -> bool:
        """Mark a submission as reviewed (approve/reject)."""
        for record in self.submission_history:
            if record.document_id == document_id:
                record.reviewer_action = action
                record.reviewer_notes = notes
                if action == "approve":
                    record.status = DerivStatus.ACCEPTED
                elif action == "reject":
                    record.status = DerivStatus.REJECTED
                return True
        return False

    def get_analytics(self) -> dict:
        """Get submission analytics for dashboard."""
        if not self.submission_history:
            return {
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "pending_review": 0,
                "by_country": {},
                "by_doc_type": {},
                "avg_quality_score": 0,
                "avg_risk_score": 0,
                "high_risk_count": 0,
            }

        total = len(self.submission_history)
        accepted = sum(1 for r in self.submission_history if r.status == DerivStatus.ACCEPTED)
        rejected = sum(1 for r in self.submission_history if r.status == DerivStatus.REJECTED)
        pending = sum(1 for r in self.submission_history if r.status == DerivStatus.NEEDS_REVIEW)

        by_country = {}
        by_doc_type = {}
        for r in self.submission_history:
            by_country[r.country_code] = by_country.get(r.country_code, 0) + 1
            by_doc_type[r.document_type] = by_doc_type.get(r.document_type, 0) + 1

        avg_quality = sum(r.quality_score for r in self.submission_history) / total
        avg_risk = sum(r.risk_score for r in self.submission_history) / total
        high_risk = sum(1 for r in self.submission_history if r.risk_level == "HIGH")

        return {
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "pending_review": pending,
            "by_country": by_country,
            "by_doc_type": by_doc_type,
            "avg_quality_score": round(avg_quality, 1),
            "avg_risk_score": round(avg_risk, 1),
            "high_risk_count": high_risk,
        }

    def can_submit(self, issue_score: int) -> dict:
        """Check if document is ready for submission."""
        if issue_score >= 80:
            return {
                "ready": True,
                "recommendation": "submit",
                "message": "Document looks good! Ready to submit.",
            }
        elif issue_score >= 50:
            return {
                "ready": True,
                "recommendation": "review",
                "message": "You can submit, but consider fixing issues for faster approval.",
            }
        else:
            return {
                "ready": False,
                "recommendation": "fix",
                "message": "Please fix the highlighted issues before submitting.",
            }

    def get_history(self) -> list:
        """Get submission history as dicts."""
        return [r.model_dump() for r in self.submission_history]

    def seed_demo_data(self):
        """Populate dashboard with realistic demo submissions."""
        if self.submission_history:
            return  # Already has data

        _now = time.time()
        demo = [
            # ── Pakistan CNIC ──
            SubmissionRecord(
                document_id="DOC-PK-001",
                document_type="cnic", side="front", country_code="PK",
                status=DerivStatus.ACCEPTED, quality_score=92,
                risk_level="LOW", risk_score=12, risk_factors=[],
                form_data={"full_name": "Muhammad Ahmed Khan", "cnic": "35202-1234567-1",
                           "date_of_birth": "1990-05-15", "city": "Lahore"},
                ocr_data={"name_english": "Muhammad Ahmed Khan", "cnic_number": "35202-1234567-1",
                          "date_of_birth": "1990-05-15", "gender": "M"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 3600,
            ),
            SubmissionRecord(
                document_id="DOC-PK-002",
                document_type="cnic", side="back", country_code="PK",
                status=DerivStatus.ACCEPTED, quality_score=88,
                risk_level="LOW", risk_score=8, risk_factors=[],
                form_data={"address_line1": "House 45, Street 12, DHA Phase 5", "city": "Lahore"},
                ocr_data={"permanent_address": "House 45, Street 12, DHA Phase 5, Lahore"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 3500,
            ),
            SubmissionRecord(
                document_id="DOC-PK-003",
                document_type="utility_bill", side="front", country_code="PK",
                status=DerivStatus.ACCEPTED, quality_score=85,
                risk_level="LOW", risk_score=10, risk_factors=[],
                form_data={"full_name": "Muhammad Ahmed Khan", "address_line1": "House 45, Street 12, DHA Phase 5"},
                ocr_data={"account_holder_name": "Muhammad Ahmed Khan", "address": "House 45, Street 12, DHA Phase 5, Lahore",
                          "bill_date": "2026-01-15", "company_name": "LESCO"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 3400,
            ),
            # ── UAE Emirates ID — name transliteration flagged ──
            SubmissionRecord(
                document_id="DOC-AE-001",
                document_type="emirates_id", side="front", country_code="AE",
                status=DerivStatus.NEEDS_REVIEW, quality_score=80,
                risk_level="MEDIUM", risk_score=42,
                risk_factors=[{"factor": "name_variation", "detail": "Arabic/English transliteration difference", "severity": "medium"}],
                form_data={"full_name": "Mohammed Al Maktoum", "emirates_id": "784-1990-1234567-1",
                           "date_of_birth": "1990-06-15", "city": "Dubai"},
                ocr_data={"name_english": "Mohammad Al Maktoum", "emirates_id_number": "784-1990-1234567-1",
                          "name_arabic": "محمد آل مكتوم", "nationality": "UAE"},
                mismatches=[{"field": "full_name", "form_value": "Mohammed Al Maktoum",
                            "document_value": "Mohammad Al Maktoum", "message": "Name transliteration variation"}],
                message="Document flagged for manual compliance review",
                timestamp=_now - 2800,
            ),
            SubmissionRecord(
                document_id="DOC-AE-002",
                document_type="emirates_id", side="back", country_code="AE",
                status=DerivStatus.ACCEPTED, quality_score=86,
                risk_level="LOW", risk_score=10, risk_factors=[],
                form_data={"date_of_birth": "1990-06-15", "gender": "Male"},
                ocr_data={"date_of_birth": "1990-06-15", "gender": "M",
                          "card_number": "784-1990-1234567-1", "expiry_date": "2028-06-14"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 2700,
            ),
            # ── UK Passport — high quality ──
            SubmissionRecord(
                document_id="DOC-GB-001",
                document_type="passport", side="photo_page", country_code="GB",
                status=DerivStatus.ACCEPTED, quality_score=95,
                risk_level="LOW", risk_score=5, risk_factors=[],
                form_data={"first_name": "James", "last_name": "Wilson",
                           "date_of_birth": "1988-03-10"},
                ocr_data={"given_names": "James Edward", "surname": "Wilson",
                          "date_of_birth": "1988-03-10", "passport_number": "533456789",
                          "expiry_date": "2028-11-20", "nationality": "British"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 2000,
            ),
            SubmissionRecord(
                document_id="DOC-GB-002",
                document_type="driving_license", side="front", country_code="GB",
                status=DerivStatus.ACCEPTED, quality_score=90,
                risk_level="LOW", risk_score=8, risk_factors=[],
                form_data={"first_name": "James", "last_name": "Wilson",
                           "date_of_birth": "1988-03-10"},
                ocr_data={"name": "James E Wilson", "date_of_birth": "1988-03-10",
                          "license_number": "WILSO803109JE9AB", "expiry_date": "2030-03-10"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 1900,
            ),
            # ── Pakistan — blurry / rejected ──
            SubmissionRecord(
                document_id="DOC-PK-004",
                document_type="cnic", side="front", country_code="PK",
                status=DerivStatus.REJECTED, quality_score=25,
                risk_level="HIGH", risk_score=72,
                risk_factors=[
                    {"factor": "quality_anomaly", "detail": "Very low quality — possible intentional obscuring", "severity": "high"},
                    {"factor": "missing_fields", "detail": "Could not extract CNIC number or name", "severity": "high"},
                ],
                form_data={"full_name": "Ali Hassan", "cnic": "42101-9876543-2"},
                ocr_data={},
                mismatches=[], message="Document rejected — please resubmit with better quality",
                timestamp=_now - 1500,
            ),
            # ── UAE — DOB mismatch, high risk ──
            SubmissionRecord(
                document_id="DOC-AE-003",
                document_type="emirates_id", side="front", country_code="AE",
                status=DerivStatus.NEEDS_REVIEW, quality_score=72,
                risk_level="HIGH", risk_score=65,
                risk_factors=[
                    {"factor": "data_mismatch", "detail": "DOB mismatch between form and document", "severity": "high"},
                    {"factor": "name_inconsistency", "detail": "Name differs significantly", "severity": "medium"},
                ],
                form_data={"full_name": "Fatima Al Rashid", "emirates_id": "784-1985-9876543-2",
                           "date_of_birth": "1985-12-01", "city": "Abu Dhabi"},
                ocr_data={"name_english": "Fatimah Al Rasheed", "emirates_id_number": "784-1985-9876543-2",
                          "name_arabic": "فاطمة الرشيد", "nationality": "UAE"},
                mismatches=[
                    {"field": "full_name", "form_value": "Fatima Al Rashid",
                     "document_value": "Fatimah Al Rasheed", "message": "Name transliteration mismatch"},
                    {"field": "date_of_birth", "form_value": "1985-12-01",
                     "document_value": "1985-01-12", "message": "DOB mismatch — possible day/month swap"},
                ],
                message="Document flagged for manual compliance review",
                timestamp=_now - 1200,
            ),
            # ── UK — utility bill ──
            SubmissionRecord(
                document_id="DOC-GB-003",
                document_type="utility_bill", side="front", country_code="GB",
                status=DerivStatus.ACCEPTED, quality_score=87,
                risk_level="LOW", risk_score=10, risk_factors=[],
                form_data={"first_name": "James", "last_name": "Wilson",
                           "address_line1": "14 Kensington Gardens, London"},
                ocr_data={"account_holder_name": "James Wilson",
                          "address": "14 Kensington Gardens, London W8 4PX",
                          "bill_date": "2026-01-28", "company_name": "British Gas"},
                mismatches=[], message="Document accepted for verification",
                timestamp=_now - 800,
            ),
            # ── Pakistan — medium risk, address mismatch ──
            SubmissionRecord(
                document_id="DOC-PK-005",
                document_type="cnic", side="back", country_code="PK",
                status=DerivStatus.NEEDS_REVIEW, quality_score=75,
                risk_level="MEDIUM", risk_score=38,
                risk_factors=[{"factor": "data_mismatch", "detail": "Address differs from form", "severity": "medium"}],
                form_data={"address_line1": "Flat 7, Block C, Gulberg III", "city": "Lahore"},
                ocr_data={"permanent_address": "House 12, Model Town, Lahore"},
                mismatches=[{"field": "address_line1", "form_value": "Flat 7, Block C, Gulberg III",
                            "document_value": "House 12, Model Town, Lahore",
                            "message": "Address on document doesn't match form"}],
                message="Document flagged for manual compliance review",
                timestamp=_now - 500,
            ),
        ]

        self.submission_history.extend(demo)


# ============================================================================
# MODULE-LEVEL INSTANCES
# ============================================================================

_client = None
_manager = None


def get_deriv_client() -> DerivWebSocketClient:
    """Get singleton Deriv WebSocket client."""
    global _client
    if _client is None:
        _client = DerivWebSocketClient()
    return _client


def get_submission_manager() -> DerivSubmissionManager:
    """Get singleton submission manager with demo data."""
    global _manager
    if _manager is None:
        _manager = DerivSubmissionManager()
        _manager.seed_demo_data()
    return _manager


def submit_document(
    document_type: str,
    side: str,
    image_data: str,
    checksum: str,
    country_code: str,
    issue_score: int = 100,
    form_data: dict = None,
    ocr_data: dict = None,
    mismatches: list = None,
    risk_level: str = "LOW",
    risk_score: int = 0,
    risk_factors: list = None,
) -> dict:
    """
    Convenience function to submit a document.
    Tries real Deriv API, falls back to mock.
    """
    manager = get_submission_manager()

    return manager.prepare_and_submit(
        document_type=document_type,
        side=side,
        image_data=image_data,
        checksum=checksum,
        country_code=country_code,
        issue_score=issue_score,
        form_data=form_data,
        ocr_data=ocr_data,
        mismatches=mismatches,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_factors=risk_factors,
    )
