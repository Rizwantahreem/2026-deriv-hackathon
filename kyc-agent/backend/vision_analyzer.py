"""
Vision Analyzer - Gemini Vision API integration for document analysis.
Extracts document features and assesses quality using AI.
"""

import google.generativeai as genai
from typing import Optional
import json
import time
import re
import logging

from config import settings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class VisionAnalysisError(Exception):
    """Raised when vision analysis fails."""
    pass


class GeminiVisionAnalyzer:
    """
    Analyzes document images using Google Gemini Vision API.
    Extracts document type, quality issues, and verifies required fields.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini Vision Analyzer.

        Args:
            api_key: Gemini API key. Uses settings.GEMINI_API_KEY if not provided.
        """
        self.api_key = api_key or settings.GEMINI_API_KEY

        logger.info(f"Initializing GeminiVisionAnalyzer")
        logger.info(f"API Key present: {bool(self.api_key)}")
        logger.info(f"API Key prefix: {self.api_key[:10] if self.api_key else 'None'}...")

        if not self.api_key:
            logger.error("GEMINI_API_KEY not configured")
            raise VisionAnalysisError("GEMINI_API_KEY not configured")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        logger.info("Gemini API configured successfully")

        # List available models first and use them dynamically
        available_model_names = []
        try:
            logger.info("Listing available Gemini models...")
            available_models = list(genai.list_models())
            # Filter for models that support generateContent
            for m in available_models:
                supported_methods = [method.name if hasattr(method, 'name') else str(method) for method in (m.supported_generation_methods or [])]
                if 'generateContent' in supported_methods or 'generate_content' in str(supported_methods).lower():
                    # Prefer vision-capable models when metadata is available
                    modalities = getattr(m, "supported_input_modalities", None)
                    if modalities:
                        if any(str(mod).lower() == "image" for mod in modalities):
                            available_model_names.append(m.name)
                    else:
                        available_model_names.append(m.name)
            logger.info(f"Models supporting generateContent: {available_model_names[:15]}")
        except Exception as e:
            logger.warning(f"Could not list models: {e}")

        # Prefer these models in order (using full model names from the API)
        preferred_models = [
            'models/gemini-2.0-flash-001',
            'models/gemini-2.0-flash',
            'models/gemini-2.5-flash',
            'models/gemini-2.5-pro',
            'models/gemini-2.0-flash-lite',
            'models/gemini-1.5-flash-latest',
            'models/gemini-1.5-pro-latest',
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-2.0-flash-001',
        ]

        # Combine preferred models with dynamically discovered ones
        model_options = preferred_models + [m for m in available_model_names if m not in preferred_models]
        self.model_options = model_options

        self.model = None
        self.model_name = None

        for model_name in model_options:
            if "gemma" in str(model_name).lower():
                logger.info(f"Skipping non-vision model: {model_name}")
                continue
            try:
                logger.info(f"Trying to initialize model: {model_name}")
                test_model = genai.GenerativeModel(model_name)
                # Try a simple test to verify the model works
                logger.info(f"Testing model {model_name} with simple prompt...")
                test_response = test_model.generate_content("Say 'test'")
                if test_response and test_response.text:
                    logger.info(f"Model {model_name} works! Response: {test_response.text[:50]}")
                    self.model = test_model
                    self.model_name = model_name
                    break
            except Exception as e:
                logger.warning(f"Failed to use {model_name}: {e}")
                continue

        if self.model is None:
            logger.error("Could not initialize any Gemini model")
            logger.error(f"Tried models: {model_options[:10]}")
            raise VisionAnalysisError("Could not initialize any Gemini model. Check your API key and available models.")

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # seconds between requests
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _build_analysis_prompt(
        self,
        document_type: str,
        country_code: str,
        expected_side: str = "front"
    ) -> str:
        """Build the prompt for document analysis."""
        
        # Map document types to human-readable names
        doc_names = {
            "national_id": "National ID Card",
            "cnic": "CNIC (Computerized National Identity Card)",
            "passport": "Passport",
            "driving_license": "Driving License",
            "aadhaar": "Aadhaar Card",
            "pan_card": "PAN Card",
            "voter_id": "Voter ID Card",
            "emirates_id": "Emirates ID",
            "utility_bill": "Utility Bill"
        }
        
        doc_name = doc_names.get(document_type, document_type)
        
        prompt = f"""Analyze this image of what should be a {doc_name} ({expected_side} side) from {country_code}.

Provide your analysis in the following JSON format ONLY (no other text):

{{
    "detected_document_type": "type of document you see (national_id/cnic/passport/driving_license/other/unknown)",
    "detected_side": "front/back/unknown",
    "is_correct_document": true/false,
    "document_visible": true/false,
    "quality_assessment": {{
        "is_readable": true/false,
        "is_blurry": true/false,
        "has_glare": true/false,
        "is_too_dark": true/false,
        "is_too_bright": true/false,
        "all_corners_visible": true/false,
        "is_rotated": true/false,
        "has_obstructions": true/false
    }},
    "detected_elements": {{
        "has_photo": true/false,
        "has_name_field": true/false,
        "has_id_number": true/false,
        "has_date_of_birth": true/false,
        "has_expiry_date": true/false,
        "has_mrz_zone": true/false
    }},
    "extracted_data": {{
        "full_name": "extracted name or null if not readable",
        "id_number": "extracted ID/CNIC number or null",
        "date_of_birth": "extracted DOB in YYYY-MM-DD format or null",
        "gender": "M/F or null",
        "expiry_date": "extracted expiry date in YYYY-MM-DD format or null",
        "father_name": "extracted father's name or null (for CNIC)",
        "address": "extracted address or null"
    }},
    "issues_found": ["list of specific issues, e.g., 'Text is blurry in the name area'"],
    "confidence_score": 0.0-1.0,
    "additional_notes": "any other relevant observations"
}}

IMPORTANT RULES:
1. Be strict about quality - if text is not clearly readable, mark is_readable as false
2. Check all four corners are visible in the image
3. Look for common issues: glare, blur, shadows, finger covering part of document
4. Extract text data where clearly visible - this is for verification purposes
5. For ID numbers like CNIC, include the dashes (e.g., "12345-1234567-1")
6. Return ONLY valid JSON, no markdown formatting"""

        return prompt
    
    def analyze_document(
        self,
        image_base64: str,
        document_type: str,
        country_code: str,
        document_side: str = "front"
    ) -> dict:
        """
        Analyze a document image using Gemini Vision.

        Args:
            image_base64: Base64 encoded image string
            document_type: Expected document type (national_id, passport, etc.)
            country_code: ISO country code (PK, IN, etc.)
            document_side: Expected side (front/back)

        Returns:
            dict with analysis results

        Raises:
            VisionAnalysisError: If analysis fails
        """
        logger.info(f"=== Starting document analysis ===")
        logger.info(f"Document type: {document_type}")
        logger.info(f"Country code: {country_code}")
        logger.info(f"Document side: {document_side}")
        logger.info(f"Image base64 length: {len(image_base64)} chars")
        logger.info(f"Using model: {getattr(self, 'model_name', 'unknown')}")

        self._wait_for_rate_limit()

        try:
            # Build prompt
            prompt = self._build_analysis_prompt(document_type, country_code, document_side)
            logger.debug(f"Prompt built, length: {len(prompt)} chars")

            # Prepare image for Gemini
            image_part = {
                "mime_type": "image/png",
                "data": image_base64
            }
            logger.info("Image part prepared for API call")

            # Call Gemini Vision API
            logger.info("Calling Gemini Vision API...")
            start_time = time.time()

            response = self._generate_with_model(self.model, prompt, image_part)

            elapsed = time.time() - start_time
            logger.info(f"API call completed in {elapsed:.2f} seconds")
            logger.info(f"Response received, text length: {len(response.text) if response.text else 0}")
            logger.debug(f"Raw response text: {response.text[:500] if response.text else 'None'}...")

            # Parse response
            result = self._parse_response(response.text)
            logger.info(f"Response parsed successfully")
            logger.info(f"Extracted data keys: {list(result.get('extracted_data', {}).keys())}")
            logger.info(f"Quality assessment: {result.get('quality_assessment', {})}")

            # Add metadata
            result['document_type_expected'] = document_type
            result['country_code'] = country_code
            result['side_expected'] = document_side

            # Fallback: if unreadable or parse error, try a different model once
            if self._should_retry_with_fallback(result):
                logger.info("Primary model returned unreadable/invalid result. Trying fallback model...")
                fallback = self._try_fallback_model(prompt, image_part, self.model_name)
                if fallback:
                    result = fallback
                    result['document_type_expected'] = document_type
                    result['country_code'] = country_code
                    result['side_expected'] = document_side

            logger.info("=== Document analysis complete ===")
            return result

        except Exception as e:
            # Handle specific errors
            error_msg = str(e)
            logger.error(f"Vision analysis error: {error_msg}")
            logger.exception("Full exception traceback:")

            if "image input modality is not enabled" in error_msg.lower():
                logger.info("Model does not support image input. Trying fallback model...")
                fallback = self._try_fallback_model(prompt, image_part, self.model_name)
                if fallback:
                    fallback['document_type_expected'] = document_type
                    fallback['country_code'] = country_code
                    fallback['side_expected'] = document_side
                    return fallback
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                raise VisionAnalysisError("API rate limit exceeded. Please wait and try again.")
            elif "invalid" in error_msg.lower() and "key" in error_msg.lower():
                raise VisionAnalysisError("Invalid API key. Please check your GEMINI_API_KEY.")
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise VisionAnalysisError(f"Model not found (404). Try a different model. Error: {error_msg}")
            else:
                raise VisionAnalysisError(f"Vision analysis failed: {error_msg}")
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse the JSON response from Gemini."""
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response_text.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith("```"):
                # Find the end of the code block
                lines = cleaned.split('\n')
                # Remove first line (```json) and last line (```)
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = '\n'.join(lines)
            
            # Try to extract the most complete JSON object from the response
            if "{" in cleaned and "}" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                cleaned = cleaned[start:end + 1]

            # Parse JSON
            result = json.loads(cleaned)
            return result
            
        except json.JSONDecodeError as e:
            # Attempt a best-effort recovery by finding the last balanced brace
            recovered = None
            if "{" in response_text:
                text = response_text.strip()
                # Remove code fences if present
                if text.startswith("```"):
                    lines = text.split('\n')
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    text = '\n'.join(lines)

                start = text.find("{")
                if start != -1:
                    stack = 0
                    in_string = False
                    escape = False
                    last_balanced_idx = None
                    for i, ch in enumerate(text[start:], start=start):
                        if in_string:
                            if escape:
                                escape = False
                            elif ch == "\\":
                                escape = True
                            elif ch == "\"":
                                in_string = False
                            continue
                        else:
                            if ch == "\"":
                                in_string = True
                                continue
                            if ch == "{":
                                stack += 1
                            elif ch == "}":
                                stack -= 1
                                if stack == 0:
                                    last_balanced_idx = i
                    if last_balanced_idx is not None:
                        candidate = text[start:last_balanced_idx + 1]
                        try:
                            recovered = json.loads(candidate)
                        except Exception:
                            recovered = None

            if recovered is not None:
                return recovered

            # Return a default structure if parsing fails
            return {
                "detected_document_type": "unknown",
                "detected_side": "unknown",
                "is_correct_document": False,
                "document_visible": False,
                "quality_assessment": {
                    "is_readable": False,
                    "is_blurry": True,
                    "has_glare": False,
                    "is_too_dark": False,
                    "is_too_bright": False,
                    "all_corners_visible": False,
                    "is_rotated": False,
                    "has_obstructions": False
                },
                "detected_elements": {
                    "has_photo": False,
                    "has_name_field": False,
                    "has_id_number": False,
                    "has_date_of_birth": False,
                    "has_expiry_date": False,
                    "has_mrz_zone": False
                },
                "issues_found": [f"Failed to analyze image: {str(e)}"],
                "confidence_score": 0.0,
                "additional_notes": f"Raw response: {response_text[:200]}",
                "parse_error": True
            }

    def _generate_with_model(self, model, prompt: str, image_part: dict):
        """Generate content with a given model."""
        return model.generate_content(
            [prompt, image_part],
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent results
                "max_output_tokens": 2048
            }
        )

    def _should_retry_with_fallback(self, result: dict) -> bool:
        """Decide if we should retry with a fallback model."""
        quality = result.get("quality_assessment", {})
        extracted = result.get("extracted_data", {})
        is_readable = quality.get("is_readable", True)
        has_data = any(v for v in extracted.values()) if isinstance(extracted, dict) else False
        # Only retry when the model explicitly marks the image unreadable
        return (not is_readable) and (not has_data)

    def _try_fallback_model(self, prompt: str, image_part: dict, current_model: str) -> Optional[dict]:
        """Try the next available model if the primary result is unreadable."""
        for model_name in getattr(self, "model_options", []):
            if model_name == current_model:
                continue
            try:
                logger.info(f"Trying fallback model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = self._generate_with_model(model, prompt, image_part)
                candidate = self._parse_response(response.text)
                if not self._should_retry_with_fallback(candidate):
                    logger.info(f"Fallback model {model_name} produced readable result.")
                    return candidate
            except Exception as e:
                logger.warning(f"Fallback model {model_name} failed: {e}")
                continue
        return None
    
    def quick_quality_check(self, image_base64: str) -> dict:
        """
        Quick quality check without full document analysis.
        Useful for immediate feedback before detailed analysis.
        
        Args:
            image_base64: Base64 encoded image
        
        Returns:
            dict with basic quality assessment
        """
        self._wait_for_rate_limit()
        
        prompt = """Quickly assess this image quality for document verification.

Return JSON only:
{
    "is_clear": true/false,
    "main_issue": "none/blur/dark/bright/glare/not_document",
    "usable_for_kyc": true/false
}"""
        
        try:
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_base64
            }
            
            response = self.model.generate_content(
                [prompt, image_part],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 200
                }
            )
            
            return self._parse_response(response.text)
            
        except Exception as e:
            return {
                "is_clear": False,
                "main_issue": "analysis_failed",
                "usable_for_kyc": False,
                "error": str(e)
            }


# Global analyzer instance (lazy initialization)
_analyzer: Optional[GeminiVisionAnalyzer] = None


def get_vision_analyzer() -> GeminiVisionAnalyzer:
    """Get or create the global vision analyzer instance."""
    global _analyzer
    if _analyzer is None:
        logger.info("Creating new GeminiVisionAnalyzer instance")
        _analyzer = GeminiVisionAnalyzer()
    return _analyzer


def analyze_document(
    image_base64: str,
    document_type: str,
    country_code: str,
    document_side: str = "front"
) -> dict:
    """
    Convenience function to analyze a document image.

    Args:
        image_base64: Base64 encoded image
        document_type: Expected document type
        country_code: ISO country code
        document_side: Expected side (front/back)

    Returns:
        Analysis results dict
    """
    logger.info(f"analyze_document called: type={document_type}, country={country_code}, side={document_side}")
    try:
        analyzer = get_vision_analyzer()
        result = analyzer.analyze_document(image_base64, document_type, country_code, document_side)
        logger.info(f"analyze_document completed successfully")
        return result
    except Exception as e:
        logger.error(f"analyze_document failed: {e}")
        raise
