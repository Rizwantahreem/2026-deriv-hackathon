"""
LLM Reasoner Module

Uses Gemini LLM to generate user-friendly guidance based on detected issues.
Provides smart, contextual advice that helps users fix document problems.
"""

import json
import time
from typing import Optional
import google.generativeai as genai

from config.settings import settings
from config.document_schema import DetectedIssue, IssueSeverity
from backend.prompts.system_prompt import (
    SYSTEM_PROMPT,
    get_issue_prompt,
    get_encouragement,
    format_guidance_prompt,
    FALLBACK_GUIDANCE
)


class GeminiReasoner:
    """
    LLM Reasoner using Google Gemini for generating user guidance.
    
    This class takes detected issues and generates helpful, friendly
    guidance that helps users understand and fix their document problems.
    """
    
    def __init__(self):
        """Initialize the Gemini reasoner."""
        self.api_key = settings.GEMINI_API_KEY
        self.model = None
        self._initialized = False
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Rate limiting
        
    def _ensure_initialized(self):
        """Initialize Gemini client if not already done."""
        if not self._initialized:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                generation_config={
                    'temperature': 0.7,  # More creative for friendly responses
                    'top_p': 0.9,
                    'max_output_tokens': 500,
                }
            )
            self._initialized = True
            
    def _rate_limit(self):
        """Ensure we don't exceed API rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
        
    def generate_guidance(
        self,
        issues: list[DetectedIssue],
        document_type: str,
        country_name: str,
        document_side: str,
        is_blurry: bool = False,
        brightness: str = "normal",
        resolution: str = "adequate",
        attempt_number: int = 1,
        language: str = "en"
    ) -> dict:
        """
        Generate user-friendly guidance based on detected issues.
        
        Args:
            issues: List of detected issues from IssueDetector
            document_type: Type of document being analyzed
            country_name: User's country name
            document_side: 'front' or 'back'
            is_blurry: Whether image was detected as blurry
            brightness: 'dark', 'normal', or 'bright'
            resolution: 'low', 'adequate', or 'high'
            attempt_number: Which upload attempt this is
            language: Language code for response
            
        Returns:
            dict with: main_issue, guidance, quick_tip, confidence, encouragement
        """
        # If no issues, return success message
        if not issues:
            return {
                "main_issue": None,
                "guidance": get_encouragement(attempt_number, success=True),
                "quick_tip": "All good!",
                "confidence": 1.0,
                "encouragement": "Your document is ready for verification! ",
                "is_success": True
            }
            
        try:
            self._ensure_initialized()
            self._rate_limit()
            
            # Format the prompt
            prompt = format_guidance_prompt(
                document_type=document_type,
                country_name=country_name,
                document_side=document_side,
                issues=issues,
                is_blurry=is_blurry,
                brightness=brightness,
                resolution=resolution,
                attempt_number=attempt_number
            )
            
            # Include issue-specific context
            primary_issue = issues[0]
            issue_context = get_issue_prompt(primary_issue.issue_type.value)
            
            full_prompt = f"{SYSTEM_PROMPT}\n\n{issue_context}\n\n{prompt}"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            # Parse JSON response
            result = self._parse_response(response.text, issues, attempt_number)
            return result
            
        except Exception as e:
            # Fallback to rule-based guidance
            return self._fallback_guidance(issues, attempt_number)
            
    def _parse_response(
        self,
        response_text: str,
        issues: list[DetectedIssue],
        attempt_number: int
    ) -> dict:
        """Parse the LLM response into structured guidance."""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)

                # Ensure guidance fields are plain text strings, not dicts/JSON
                for key in ("main_issue", "guidance", "quick_tip"):
                    val = result.get(key)
                    if isinstance(val, dict):
                        result[key] = val.get("message", val.get("text", str(val)))
                    elif val is None:
                        result[key] = ""

                # Add encouragement
                result["encouragement"] = get_encouragement(attempt_number)
                result["is_success"] = False
                return result
                
        except json.JSONDecodeError:
            pass
            
        # If JSON parsing fails, extract text directly
        # Strip any leading JSON artifacts from guidance text
        guidance_text = response_text[:200]
        if guidance_text.strip().startswith("{"):
            guidance_text = issues[0].suggestion if issues and issues[0].suggestion else "Please retake the photo with better lighting and focus."
        return {
            "main_issue": issues[0].issue_type.value if issues else "UNKNOWN",
            "guidance": guidance_text,
            "quick_tip": issues[0].suggestion[:30] if issues else "Retake photo",
            "confidence": 0.6,
            "encouragement": get_encouragement(attempt_number),
            "is_success": False
        }
        
    def _fallback_guidance(
        self,
        issues: list[DetectedIssue],
        attempt_number: int
    ) -> dict:
        """Generate rule-based fallback guidance when LLM fails."""
        if not issues:
            return {
                "main_issue": None,
                "guidance": FALLBACK_GUIDANCE["generic"],
                "quick_tip": "Check lighting",
                "confidence": 0.5,
                "encouragement": get_encouragement(attempt_number),
                "is_success": False
            }
            
        primary = issues[0]
        issue_key = primary.issue_type.value.lower()
        
        # Map issue types to fallback guidance
        guidance_map = {
            "blurry": FALLBACK_GUIDANCE["blurry"],
            "too_dark": FALLBACK_GUIDANCE["dark"],
            "too_bright": FALLBACK_GUIDANCE["generic"],
            "glare": FALLBACK_GUIDANCE["glare"],
            "low_resolution": FALLBACK_GUIDANCE["quality"],
        }
        
        guidance = guidance_map.get(issue_key, primary.suggestion)
        
        return {
            "main_issue": primary.issue_type.value,
            "guidance": guidance,
            "quick_tip": primary.suggestion[:30] if primary.suggestion else "Retake photo",
            "confidence": 0.7,
            "encouragement": get_encouragement(attempt_number),
            "is_success": False
        }


class GuidanceGenerator:
    """
    High-level guidance generator that combines issue detection with LLM reasoning.
    """
    
    def __init__(self):
        self.reasoner = GeminiReasoner()
        
    def generate(
        self,
        issues: list[DetectedIssue],
        context: dict,
        attempt: int = 1
    ) -> dict:
        """
        Generate complete guidance package for the user.
        
        Args:
            issues: Detected issues
            context: Dict with document_type, country_name, side, image_quality
            attempt: Upload attempt number
            
        Returns:
            Complete guidance dict with messages and formatting
        """
        # Extract context
        document_type = context.get("document_type", "identity document")
        country_name = context.get("country_name", "Unknown")
        document_side = context.get("side", "front")
        image_quality = context.get("image_quality", {})
        
        # Generate LLM guidance
        guidance = self.reasoner.generate_guidance(
            issues=issues,
            document_type=document_type,
            country_name=country_name,
            document_side=document_side,
            is_blurry=image_quality.get("is_blurry", False),
            brightness=self._get_brightness_level(image_quality),
            resolution=self._get_resolution_level(image_quality),
            attempt_number=attempt
        )
        
        # Add issue summary
        blocking_count = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKING)
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        
        guidance["issue_summary"] = {
            "blocking": blocking_count,
            "warnings": warning_count,
            "total": len(issues)
        }
        
        # Add severity level
        if blocking_count > 0:
            guidance["severity_level"] = "high"
            guidance["can_submit"] = False
        elif warning_count > 0:
            guidance["severity_level"] = "medium"
            guidance["can_submit"] = True
        else:
            guidance["severity_level"] = "low"
            guidance["can_submit"] = True
            
        return guidance
        
    def _get_brightness_level(self, quality: dict) -> str:
        """Convert brightness value to category."""
        brightness = quality.get("brightness", 128)
        if brightness < 60:
            return "dark"
        elif brightness > 200:
            return "bright"
        return "normal"
        
    def _get_resolution_level(self, quality: dict) -> str:
        """Assess resolution level."""
        # This would be based on actual image dimensions
        return "adequate"


# ============================================================================
# MODULE-LEVEL INSTANCES
# ============================================================================

_reasoner = None
_guidance_generator = None


def get_reasoner() -> GeminiReasoner:
    """Get singleton reasoner instance."""
    global _reasoner
    if _reasoner is None:
        _reasoner = GeminiReasoner()
    return _reasoner


def get_guidance_generator() -> GuidanceGenerator:
    """Get singleton guidance generator instance."""
    global _guidance_generator
    if _guidance_generator is None:
        _guidance_generator = GuidanceGenerator()
    return _guidance_generator


def generate_guidance(
    issues: list[DetectedIssue],
    document_type: str,
    country_name: str,
    document_side: str = "front",
    attempt: int = 1
) -> dict:
    """
    Convenience function to generate guidance.
    
    Args:
        issues: List of detected issues
        document_type: Type of document
        country_name: User's country
        document_side: 'front' or 'back'
        attempt: Upload attempt number
        
    Returns:
        Guidance dict with messages and formatting
    """
    generator = get_guidance_generator()
    
    context = {
        "document_type": document_type,
        "country_name": country_name,
        "side": document_side,
        "image_quality": {}
    }
    
    return generator.generate(issues, context, attempt)
