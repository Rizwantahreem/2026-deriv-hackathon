"""
Gemini OCR Service - Real document analysis using Google Gemini Vision API.

Provides:
- Document analysis with OCR extraction
- Structured JSON response parsing
- Quality assessment (blur, lighting, corners)
- Country-specific field extraction
- Error handling with graceful fallbacks
- Groq fallback when Gemini quota exceeded
"""

import os
import json
import base64
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Use new google.genai package (google.generativeai is deprecated)
from google import genai


# Load API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

print(f"[OCR Service] Gemini API Key: {'YES' if GEMINI_API_KEY else 'NO'}")

class DocumentQuality(Enum):
    """Document quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNREADABLE = "unreadable"


@dataclass
class OCRResult:
    """Result from OCR analysis."""
    success: bool
    document_type: str
    quality: DocumentQuality
    quality_score: int  # 0-100
    extracted_fields: Dict[str, Any]
    issues: List[Dict[str, str]]
    suggestions: List[str]
    raw_response: str
    error_message: Optional[str] = None


# Load country forms for OCR prompts
CONFIG_PATH = Path(__file__).parent.parent / "config" / "country_forms.json"

def load_ocr_prompts() -> Dict[str, str]:
    """Load OCR prompts from config."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ocr_prompts", {})
    except Exception:
        return {}


class GeminiOCR:
    """
    Gemini Vision API wrapper for document OCR and analysis.
    With Groq fallback when Gemini quota is exceeded.
    """
    
    # Gemini models to try (in order of preference)
    # gemini-2.5-flash has separate quota from 2.0 models
    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = "gemini-2.5-flash"  # Primary model (has separate quota)
        self.ocr_prompts = load_ocr_prompts()
        
        # Create Gemini client
        self._client = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        
        self._call_count = 0
        self._last_error = None
        self._used_provider = None  # Track which provider was used
    
    @property
    def call_count(self) -> int:
        """Get number of API calls made."""
        return self._call_count
    
    def is_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(self.api_key) and self._client is not None
    
    # Note: Groq vision models have been decommissioned (Jan 2026)
    # Using Gemini only for vision tasks
    
    def _call_with_retry(self, prompt: str, image_bytes: bytes, max_retries: int = 2) -> Optional[str]:
        """Call Gemini API with retry logic."""
        
        if not self._client:
            print("[GEMINI OCR] No client configured")
            return None
        
        # Try Gemini models in order
        for model_name in self.GEMINI_MODELS:
            for attempt in range(max_retries):
                try:
                    print(f"[GEMINI OCR] Trying model: {model_name} (attempt {attempt + 1})")
                    
                    # Use new google.genai API
                    response = self._client.models.generate_content(
                        model=model_name,
                        contents=[
                            genai.types.Part(text=prompt),
                            genai.types.Part(inline_data=genai.types.Blob(data=image_bytes, mime_type="image/jpeg"))
                        ]
                    )
                    
                    self._call_count += 1
                    self._used_provider = "gemini"
                    print(f"[GEMINI OCR] Success with {model_name}!")
                    return response.text
                    
                except Exception as e:
                    error_str = str(e)
                    self._last_error = error_str
                    
                    # Check if it's a rate limit error
                    if "429" in error_str or "quota" in error_str.lower():
                        # Extract retry delay if present
                        match = re.search(r'retry in (\d+\.?\d*)', error_str.lower())
                        if match:
                            delay = float(match.group(1))
                            if delay < 10:  # Only wait if less than 10 seconds
                                print(f"[GEMINI OCR] Rate limited. Waiting {delay:.1f}s...")
                                time.sleep(delay + 1)
                                continue
                        
                        # Try next model (different models have different quotas)
                        print(f"[GEMINI OCR] Quota exceeded for {model_name}, trying next model...")
                        break  # Break retry loop, try next model
                    
                    elif "404" in error_str or "not found" in error_str.lower():
                        print(f"[GEMINI OCR] Model {model_name} not found, trying next...")
                        break  # Try next model
                    
                    else:
                        # Other error, retry with same model
                        print(f"[GEMINI OCR] Error: {error_str[:100]}")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                        continue
        
        print("[GEMINI OCR] All models failed")
        return None
    
    def analyze_document(
        self,
        image_bytes: bytes,
        document_type: str,
        country_code: str,
        side: str = "front"
    ) -> OCRResult:
        """
        Analyze a document image using Gemini Vision.
        
        Args:
            image_bytes: Raw image bytes
            document_type: Type of document (cnic, aadhaar, passport, etc.)
            country_code: ISO country code
            side: Document side (front/back)
        
        Returns:
            OCRResult with extracted data and quality assessment
        """
        print(f"\n{'='*60}")
        print(f"[GEMINI OCR] Starting document analysis")
        print(f"[GEMINI OCR] Document Type: {document_type}, Country: {country_code}, Side: {side}")
        print(f"[GEMINI OCR] Image size: {len(image_bytes)} bytes")
        print(f"[GEMINI OCR] Gemini API: {'YES' if self.api_key else 'NO'}")
        
        if not self.is_configured():
            print(f"[OCR] ERROR: No API configured!")
            return OCRResult(
                success=False,
                document_type=document_type,
                quality=DocumentQuality.UNREADABLE,
                quality_score=0,
                extracted_fields={},
                issues=[{"type": "ERROR", "message": "No API configured", "severity": "blocking"}],
                suggestions=["Please configure GEMINI_API_KEY in .env file"],
                raw_response="",
                error_message="No API key configured"
            )
        
        try:
            # Build prompt
            prompt = self._build_prompt(document_type, country_code, side)
            
            # Call API with retry logic (using new google.genai with raw bytes)
            print(f"[OCR] >>> CALLING GEMINI API <<<")
            response_text = self._call_with_retry(prompt, image_bytes)
            
            if response_text is None:
                # All models failed
                error_msg = self._last_error or "All API models failed"
                
                # Check if it's a quota error
                if "quota" in error_msg.lower() or "429" in error_msg:
                    return OCRResult(
                        success=False,
                        document_type=document_type,
                        quality=DocumentQuality.UNREADABLE,
                        quality_score=0,
                        extracted_fields={},
                        issues=[{
                            "type": "RATE_LIMIT",
                            "severity": "blocking",
                            "message": "API quota exceeded. Please wait a few minutes and try again.",
                            "suggestion": "Wait 1-2 minutes before retrying"
                        }],
                        suggestions=["API rate limit reached. Please wait and try again."],
                        raw_response="",
                        error_message="Rate limit exceeded - please wait and retry"
                    )
                
                return OCRResult(
                    success=False,
                    document_type=document_type,
                    quality=DocumentQuality.UNREADABLE,
                    quality_score=0,
                    extracted_fields={},
                    issues=[{"type": "ERROR", "message": error_msg, "severity": "blocking"}],
                    suggestions=["Please try again"],
                    raw_response="",
                    error_message=error_msg
                )
            
            print(f"[GEMINI OCR] Response length: {len(response_text)} chars")
            
            # Parse response
            result = self._parse_response(response_text, document_type)
            print(f"[GEMINI OCR] Parsed result - Success: {result.success}, Score: {result.quality_score}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"[GEMINI OCR] ERROR: {str(e)}")
            print(f"{'='*60}\n")
            return OCRResult(
                success=False,
                document_type=document_type,
                quality=DocumentQuality.UNREADABLE,
                quality_score=0,
                extracted_fields={},
                issues=[{"type": "ERROR", "message": str(e), "severity": "blocking"}],
                suggestions=["Please try again with a clearer image"],
                raw_response="",
                error_message=str(e)
            )
    
    def _build_prompt(self, document_type: str, country_code: str, side: str) -> str:
        """Build the OCR prompt for Gemini."""
        
        # Get custom prompt if available
        custom_prompt = self.ocr_prompts.get(document_type, "")
        
        # Side-aware document requirements
        doc_requirements = {
            "cnic": {
                "name": "Pakistani CNIC (Computerized National Identity Card)",
                "front": {
                    "required_elements": "13-digit CNIC number, name in Urdu and English, father's name, date of birth, photo, gender",
                    "extract_fields": "cnic_number, name_english, name_urdu, father_name, date_of_birth, gender"
                },
                "back": {
                    "required_elements": "Permanent address, current address, issue date, expiry date. NOTE: The name on the back is NOT the cardholder's name",
                    "extract_fields": "permanent_address, current_address, address, issue_date, expiry_date"
                }
            },
            "aadhaar": {
                "name": "Indian Aadhaar Card",
                "front": {
                    "required_elements": "12-digit Aadhaar number, name, date of birth, gender, photo, QR code",
                    "extract_fields": "aadhaar_number, name, date_of_birth, gender"
                },
                "back": {
                    "required_elements": "Full address, QR code, VID number",
                    "extract_fields": "address, vid_number"
                }
            },
            "passport": {
                "name": "Passport",
                "front": {
                    "required_elements": "Passport number, surname, given names, date of birth, expiry date, photo, MRZ zone",
                    "extract_fields": "passport_number, surname, given_names, date_of_birth, expiry_date, nationality"
                },
                "photo_page": {
                    "required_elements": "Passport number, surname, given names, date of birth, expiry date, photo, MRZ zone",
                    "extract_fields": "passport_number, surname, given_names, date_of_birth, expiry_date, nationality"
                }
            },
            "driving_license": {
                "name": "Driving License",
                "front": {
                    "required_elements": "License number, name, date of birth, photo, expiry date",
                    "extract_fields": "license_number, name, date_of_birth, expiry_date"
                },
                "back": {
                    "required_elements": "Address, vehicle categories, additional information",
                    "extract_fields": "address, categories"
                }
            },
            "utility_bill": {
                "name": "Utility Bill / Bank Statement",
                "front": {
                    "required_elements": "Account holder name, full address, bill/issue/due date within last 3 months, company name/logo",
                    "extract_fields": "account_holder_name, address, bill_date, issue_date, due_date, statement_date, company_name"
                }
            },
            "emirates_id": {
                "name": "UAE Emirates ID",
                "front": {
                    "required_elements": "Emirates ID number, name in English and Arabic, nationality, photo",
                    "extract_fields": "emirates_id_number, name_english, name_arabic, nationality"
                },
                "back": {
                    "required_elements": "Date of birth, gender, card number, expiry date",
                    "extract_fields": "date_of_birth, gender, card_number, expiry_date"
                }
            }
        }

        doc_info_raw = doc_requirements.get(document_type, {
            "name": document_type.upper(),
            "front": {
                "required_elements": "standard ID document elements",
                "extract_fields": "name, id_number, date_of_birth"
            }
        })

        # Look up side-specific info, fallback to front
        doc_name = doc_info_raw.get("name", document_type.upper())
        side_info = doc_info_raw.get(side, doc_info_raw.get("front", {}))
        doc_info = {
            "name": doc_name,
            "required_elements": side_info.get("required_elements", "standard ID document elements"),
            "extract_fields": side_info.get("extract_fields", "name, id_number, date_of_birth")
        }
        
        base_prompt = f"""
You are a STRICT document verification expert. Your job is to analyze images and determine if they are valid identity documents.

CRITICAL TASK: Analyze this image and determine if it is a valid {doc_info['name']} ({side} side) from {country_code}.

STEP 1 - DOCUMENT TYPE VERIFICATION:
First, determine if this image shows a REAL {doc_info['name']}.
- Is this actually an official identity document?
- Is this the correct document type ({document_type})?
- A photo of a person, selfie, random object, or non-document image should be marked as document_detected: false

STEP 2 - If it IS a valid document, assess quality:
- Is the image clear and readable?
- Are all corners visible?
- Is there blur, glare, or shadows?
- Can you read the text clearly?

STEP 3 - If valid, extract these fields: {doc_info['extract_fields']}

Required elements for a valid {doc_info['name']}: {doc_info['required_elements']}

RESPOND WITH ONLY THIS JSON (no other text):

{{
    "document_detected": true/false,
    "is_valid_document_type": true/false,
    "rejection_reason": "reason if document_detected is false, else null",
    "document_type_detected": "what type of document this actually is, or 'NOT_A_DOCUMENT' if not a document",
    "has_required_photo": true/false,
    "has_required_elements": true/false,
    
    "quality_assessment": {{
        "overall_quality": "excellent/good/acceptable/poor/unreadable",
        "quality_score": 0-100,
        "is_blurry": true/false,
        "is_too_dark": true/false,
        "is_too_bright": true/false,
        "has_glare": true/false,
        "all_corners_visible": true/false,
        "is_rotated": true/false,
        "text_readable": true/false
    }},
    
    "extracted_fields": {{
        // Only populate if document_detected is true
        // Extract: {doc_info['extract_fields']}
        // Set to null if not readable
    }},
    
    "issues": [
        {{
            "type": "ISSUE_TYPE",
            "severity": "blocking/warning/info",
            "message": "Description",
            "suggestion": "How to fix"
        }}
    ],
    
    "verification_status": "verified/needs_review/rejected",
    "confidence_score": 0-100
}}

STRICT RULES:
1. If the image is NOT a {doc_info['name']}, set document_detected: false and quality_score: 0
2. A photo of a baby, person, selfie, or random image is NOT a document - reject it
3. If you cannot clearly identify this as a {doc_info['name']}, set is_valid_document_type: false
4. For ID documents (cnic, aadhaar, passport), has_required_photo must check for an ID photo on the document
5. Be STRICT - when in doubt, mark as poor quality or reject
6. Return ONLY valid JSON, no markdown code blocks

{custom_prompt}
"""
        return base_prompt
    
    def _parse_response(self, response_text: str, document_type: str) -> OCRResult:
        """Parse Gemini response into OCRResult."""
        
        print(f"[GEMINI OCR] Parsing response...")
        
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Remove code block markers
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)
            
            # Also try to find JSON within the response
            if "{" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                cleaned = cleaned[start:end]
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Check if document was detected
            document_detected = data.get("document_detected", False)
            is_valid_type = data.get("is_valid_document_type", False)
            rejection_reason = data.get("rejection_reason")
            
            print(f"[GEMINI OCR] Document detected: {document_detected}")
            print(f"[GEMINI OCR] Valid document type: {is_valid_type}")
            
            # If document not detected or wrong type, return rejection
            if not document_detected or not is_valid_type:
                reason = rejection_reason or "This does not appear to be a valid document"
                detected_type = data.get("document_type_detected", "NOT_A_DOCUMENT")
                
                print(f"[GEMINI OCR] REJECTED: {reason}")
                
                return OCRResult(
                    success=False,
                    document_type=detected_type,
                    quality=DocumentQuality.UNREADABLE,
                    quality_score=0,
                    extracted_fields={},
                    issues=[{
                        "type": "INVALID_DOCUMENT",
                        "severity": "blocking",
                        "message": f"This is not a valid {document_type}. Detected: {detected_type}",
                        "suggestion": f"Please upload a clear photo of your {document_type}"
                    }],
                    suggestions=[f"Upload a valid {document_type} document", reason],
                    raw_response=response_text
                )
            
            # Extract quality info
            quality_data = data.get("quality_assessment", {})
            quality_str = quality_data.get("overall_quality", "poor")
            quality_score = quality_data.get("quality_score", 50)
            
            # Map to enum
            quality_map = {
                "excellent": DocumentQuality.EXCELLENT,
                "good": DocumentQuality.GOOD,
                "acceptable": DocumentQuality.ACCEPTABLE,
                "poor": DocumentQuality.POOR,
                "unreadable": DocumentQuality.UNREADABLE
            }
            quality = quality_map.get(quality_str.lower(), DocumentQuality.POOR)
            
            # Extract issues
            issues = data.get("issues", [])
            if not isinstance(issues, list):
                issues = []
            
            # Build suggestions from issues
            suggestions = [
                issue.get("suggestion", "")
                for issue in issues
                if issue.get("suggestion")
            ]
            
            # Add quality-based suggestions
            if quality_data.get("is_blurry"):
                suggestions.append("Hold camera steady and tap to focus")
            if quality_data.get("is_too_dark"):
                suggestions.append("Move to a well-lit area")
            if quality_data.get("has_glare"):
                suggestions.append("Avoid direct lighting to reduce glare")
            if not quality_data.get("all_corners_visible", True):
                suggestions.append("Ensure all 4 corners of the document are visible")
            
            # Check for required photo
            has_photo = data.get("has_required_photo", True)
            if not has_photo and document_type in ["cnic", "aadhaar", "passport", "driving_license"]:
                issues.append({
                    "type": "MISSING_PHOTO",
                    "severity": "blocking",
                    "message": "ID photo not detected on document",
                    "suggestion": "Ensure the photo on your ID is clearly visible"
                })
                quality_score = min(quality_score, 30)
            
            print(f"[GEMINI OCR] Quality: {quality_str}, Score: {quality_score}")
            print(f"[GEMINI OCR] Extracted fields: {list(data.get('extracted_fields', {}).keys())}")
            
            return OCRResult(
                success=document_detected and is_valid_type,
                document_type=data.get("document_type_detected", document_type),
                quality=quality,
                quality_score=quality_score,
                extracted_fields=data.get("extracted_fields", {}),
                issues=issues,
                suggestions=list(set(suggestions)),  # Deduplicate
                raw_response=response_text
            )
            
        except json.JSONDecodeError as e:
            print(f"[GEMINI OCR] JSON parse error: {e}")
            # Try to extract key info from unstructured response
            return self._parse_unstructured_response(response_text, document_type)
    
    def _parse_unstructured_response(self, response_text: str, document_type: str) -> OCRResult:
        """Fallback parser for non-JSON responses."""
        
        # Try to detect quality keywords
        text_lower = response_text.lower()
        
        if "unreadable" in text_lower or "cannot read" in text_lower:
            quality = DocumentQuality.UNREADABLE
            score = 10
        elif "blurry" in text_lower or "blur" in text_lower:
            quality = DocumentQuality.POOR
            score = 30
        elif "dark" in text_lower or "lighting" in text_lower:
            quality = DocumentQuality.POOR
            score = 35
        elif "good" in text_lower or "clear" in text_lower:
            quality = DocumentQuality.GOOD
            score = 75
        else:
            quality = DocumentQuality.ACCEPTABLE
            score = 50
        
        # Build issues from detected problems
        issues = []
        suggestions = []
        
        if "blur" in text_lower:
            issues.append({"type": "BLURRY", "severity": "blocking", "message": "Document is blurry"})
            suggestions.append("Hold camera steady and tap to focus")
        
        if "dark" in text_lower:
            issues.append({"type": "TOO_DARK", "severity": "warning", "message": "Image is too dark"})
            suggestions.append("Move to a well-lit area")
        
        if "corner" in text_lower:
            issues.append({"type": "CORNERS_CUT", "severity": "blocking", "message": "Corners not visible"})
            suggestions.append("Ensure all 4 corners are visible")
        
        return OCRResult(
            success=quality not in [DocumentQuality.UNREADABLE, DocumentQuality.POOR],
            document_type=document_type,
            quality=quality,
            quality_score=score,
            extracted_fields={},
            issues=issues,
            suggestions=suggestions,
            raw_response=response_text
        )
    
    def extract_field_value(
        self,
        extracted_fields: Dict[str, Any],
        field_name: str,
        expected_pattern: Optional[str] = None
    ) -> Tuple[Optional[str], bool]:
        """
        Extract and validate a specific field from OCR results.
        
        Returns:
            Tuple of (value, is_valid)
        """
        value = extracted_fields.get(field_name)
        
        if value is None:
            return None, False
        
        value_str = str(value).strip()
        
        if not value_str:
            return None, False
        
        # Validate against pattern if provided
        if expected_pattern:
            if re.match(expected_pattern, value_str, re.IGNORECASE):
                return value_str, True
            else:
                return value_str, False
        
        return value_str, True
    
    def compare_with_form(
        self,
        extracted_fields: Dict[str, Any],
        form_data: Dict[str, Any],
        country_code: str,
        side: str = "front",
        document_type: str = "",
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Compare OCR extracted fields with user-submitted form data.
        Side-aware: different fields are compared for front vs back.

        Returns:
            Tuple of (all_match, list_of_mismatches)
        """
        mismatches = []

        def normalize_text(value: Any) -> str:
            return str(value).casefold().strip().replace("-", "").replace(" ", "")

        # Side-aware field mappings: {country: {side: {ocr_field: form_field}}}
        field_mappings_by_side = {
            "PK": {
                "front": {
                    "cnic_number": "cnic",
                    "name": "full_name",
                    "name_english": "full_name",
                    "date_of_birth": "date_of_birth",
                },
                "back": {
                    # CNIC back has address, NOT the cardholder's name
                    "address": "address_line1",
                    "current_address": "address_line1",
                    "permanent_address": "address_line1",
                },
            },
            "IN": {
                "front": {
                    "aadhaar_number": "aadhaar",
                    "name": "full_name",
                    "date_of_birth": "date_of_birth",
                },
                "back": {
                    "address": "address_line1",
                },
            },
            "GB": {
                "front": {
                    "surname": "last_name",
                    "given_names": "first_name",
                    "date_of_birth": "date_of_birth",
                },
                "photo_page": {
                    "surname": "last_name",
                    "given_names": "first_name",
                    "date_of_birth": "date_of_birth",
                },
            },
            "AE": {
                "front": {
                    "name": "full_name",
                    "name_english": "full_name",
                    "emirates_id_number": "emirates_id",
                },
                "back": {
                    "date_of_birth": "date_of_birth",
                    "gender": "gender",
                },
            },
        }

        # Look up side-specific mappings, fallback to front
        country_sides = field_mappings_by_side.get(country_code, {})
        mappings = country_sides.get(side, country_sides.get("front", {}))

        # Check if user indicated renting/moved — skip address comparison
        address_status = str(form_data.get("address_status", "") or "")
        skip_address = address_status in (
            "Moved from document address",
            "Renting a different address",
        )

        for ocr_field, form_field in mappings.items():
            # Skip address fields if user is renting/moved
            if skip_address and form_field == "address_line1":
                continue

            ocr_value = extracted_fields.get(ocr_field)
            form_value = form_data.get(form_field)

            if ocr_value and form_value:
                ocr_normalized = normalize_text(ocr_value)
                form_normalized = normalize_text(form_value)

                if ocr_normalized != form_normalized:
                    mismatches.append({
                        "field": form_field,
                        "form_value": str(form_value),
                        "document_value": str(ocr_value),
                        "message": f"{form_field} on document doesn't match form"
                    })

        return len(mismatches) == 0, mismatches


# Global instance
ocr_service = GeminiOCR()


def analyze_document(
    image_bytes: bytes,
    document_type: str,
    country_code: str,
    side: str = "front"
) -> OCRResult:
    """Convenience function for document analysis."""
    return ocr_service.analyze_document(image_bytes, document_type, country_code, side)


def get_call_count() -> int:
    """Get total API calls made."""
    return ocr_service.call_count
