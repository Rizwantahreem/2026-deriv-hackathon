"""
Response Formatter Module

Formats LLM guidance into user-friendly display formats.
Supports multiple output formats and languages.
"""

from typing import Optional
from config.document_schema import DetectedIssue, IssueSeverity
from backend.prompts.system_prompt import get_language_template


class ResponseFormatter:
    """
    Formats guidance responses for display to users.
    
    Handles:
    - Multi-language support
    - UI-ready formatting
    - Different output formats (web, mobile, API)
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize formatter with language.
        
        Args:
            language: Language code (en, ur, hi, sw, de, ar)
        """
        self.language = language
        self.templates = get_language_template(language)
        
    def format_guidance_card(
        self,
        guidance: dict,
        issues: list[DetectedIssue]
    ) -> dict:
        """
        Format guidance into a UI-ready card format.
        
        Args:
            guidance: Guidance dict from LLM reasoner
            issues: Detected issues list
            
        Returns:
            Card-formatted dict for UI display
        """
        # Determine card type and styling
        if guidance.get("is_success"):
            card_type = "success"
            icon = ""
            header = self.templates.get("ready", "Ready to submit!")
            color = "green"
        elif guidance.get("severity_level") == "high":
            card_type = "error"
            icon = "🔴"
            header = self.templates.get("issue_found", "Issue found")
            color = "red"
        elif guidance.get("severity_level") == "medium":
            card_type = "warning"
            icon = "🟡"
            header = self.templates.get("almost_there", "Almost there!")
            color = "yellow"
        else:
            card_type = "info"
            icon = "ℹ️"
            header = self.templates.get("tip", "Quick tip")
            color = "blue"
            
        return {
            "card_type": card_type,
            "icon": icon,
            "header": header,
            "color": color,
            "main_message": guidance.get("guidance", ""),
            "quick_tip": guidance.get("quick_tip", ""),
            "encouragement": guidance.get("encouragement", ""),
            "can_submit": guidance.get("can_submit", False),
            "issue_count": guidance.get("issue_summary", {}).get("total", 0)
        }
        
    def format_issue_list(
        self,
        issues: list[DetectedIssue],
        max_display: int = 3
    ) -> list[dict]:
        """
        Format issues into a display list.
        
        Args:
            issues: Detected issues
            max_display: Maximum issues to show
            
        Returns:
            List of formatted issue dicts
        """
        formatted = []
        
        for issue in issues[:max_display]:
            severity_icons = {
                IssueSeverity.BLOCKING: "🔴",
                IssueSeverity.WARNING: "🟡",
                IssueSeverity.INFO: "🟢"
            }
            
            severity_labels = {
                IssueSeverity.BLOCKING: "Must Fix",
                IssueSeverity.WARNING: "Recommended",
                IssueSeverity.INFO: "Tip"
            }
            
            formatted.append({
                "icon": severity_icons.get(issue.severity, "⚪"),
                "label": severity_labels.get(issue.severity, "Info"),
                "title": self._format_issue_title(issue.issue_type.value),
                "description": issue.description,
                "suggestion": issue.suggestion,
                "severity": issue.severity.value
            })
            
        return formatted
        
    def format_step_by_step(
        self,
        issues: list[DetectedIssue],
        guidance: dict
    ) -> list[dict]:
        """
        Create step-by-step fix instructions.
        
        Args:
            issues: Detected issues
            guidance: LLM guidance
            
        Returns:
            List of steps with numbers and instructions
        """
        if not issues:
            return [{
                "step": 1,
                "instruction": guidance.get("guidance", "Your document is ready!"),
                "icon": ""
            }]
            
        steps = []
        
        # Primary fix step
        steps.append({
            "step": 1,
            "instruction": guidance.get("guidance", issues[0].suggestion),
            "icon": ""
        })
        
        # Additional tips from other issues
        for i, issue in enumerate(issues[1:3], start=2):
            steps.append({
                "step": i,
                "instruction": issue.suggestion,
                "icon": "💡"
            })
            
        # Final verification step
        steps.append({
            "step": len(steps) + 1,
            "instruction": "Check that all document corners are visible and text is readable",
            "icon": "🔍"
        })
        
        return steps
        
    def format_for_api(
        self,
        guidance: dict,
        issues: list[DetectedIssue]
    ) -> dict:
        """
        Format response for API consumption.
        
        Args:
            guidance: LLM guidance
            issues: Detected issues
            
        Returns:
            API-formatted response
        """
        return {
            "success": guidance.get("is_success", False),
            "can_proceed": guidance.get("can_submit", False),
            "severity": guidance.get("severity_level", "unknown"),
            "message": guidance.get("guidance", ""),
            "quick_tip": guidance.get("quick_tip", ""),
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "severity": issue.severity.value,
                    "message": issue.description,
                    "fix": issue.suggestion
                }
                for issue in issues
            ],
            "counts": guidance.get("issue_summary", {}),
            "confidence": guidance.get("confidence", 0.0)
        }
        
    def format_mobile_friendly(
        self,
        guidance: dict,
        issues: list[DetectedIssue]
    ) -> dict:
        """
        Format for mobile display (shorter messages).
        
        Args:
            guidance: LLM guidance
            issues: Detected issues
            
        Returns:
            Mobile-optimized response
        """
        # Shorter messages for mobile
        main_message = guidance.get("guidance", "")
        if len(main_message) > 80:
            main_message = main_message[:77] + "..."
            
        return {
            "status_emoji": "" if guidance.get("is_success") else "",
            "short_message": main_message,
            "action_text": guidance.get("quick_tip", "Retake"),
            "show_retake_button": not guidance.get("is_success", False),
            "progress_percent": self._calculate_progress(issues)
        }
        
    def _format_issue_title(self, issue_type: str) -> str:
        """Convert issue type to readable title."""
        titles = {
            "BLURRY": "Image is Blurry",
            "TOO_DARK": "Image is Too Dark",
            "TOO_BRIGHT": "Image is Too Bright",
            "GLARE": "Glare Detected",
            "CORNERS_CUT": "Corners Not Visible",
            "ROTATED": "Document is Rotated",
            "MISSING_BACK": "Back Side Required",
            "WRONG_DOCUMENT": "Wrong Document Type",
            "PHOTO_MISSING": "Photo Not Visible",
            "TEXT_UNREADABLE": "Text is Unreadable",
            "LOW_RESOLUTION": "Low Image Quality",
            "OBSTRUCTED": "Part of Document Covered",
            "EXPIRED": "Document Appears Expired"
        }
        return titles.get(issue_type.upper(), issue_type.replace("_", " ").title())
        
    def _calculate_progress(self, issues: list[DetectedIssue]) -> int:
        """Calculate completion progress based on issues."""
        if not issues:
            return 100
            
        blocking = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKING)
        warnings = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        
        # Deduct points for issues
        progress = 100 - (blocking * 25) - (warnings * 10)
        return max(0, min(100, progress))


class MessageBuilder:
    """
    Builds custom messages by combining templates and dynamic content.
    """
    
    def __init__(self, language: str = "en"):
        self.language = language
        self.templates = get_language_template(language)
        
    def build_header(self, is_success: bool, severity: str) -> str:
        """Build header message."""
        if is_success:
            return f" {self.templates.get('great_job', 'Great job!')}"
        elif severity == "high":
            return f"🔴 {self.templates.get('fix_this', 'Fix this')}"
        elif severity == "medium":
            return f"🟡 {self.templates.get('almost_there', 'Almost there!')}"
        else:
            return f"💡 {self.templates.get('tip', 'Quick tip')}"
            
    def build_action_button(
        self,
        is_success: bool,
        has_back: bool = False
    ) -> dict:
        """Build action button config."""
        if is_success:
            return {
                "text": "Submit Document",
                "style": "primary",
                "action": "submit"
            }
        else:
            return {
                "text": self.templates.get("try_again", "Try Again"),
                "style": "default",
                "action": "retake"
            }
            
    def build_progress_indicator(
        self,
        front_uploaded: bool,
        back_uploaded: bool,
        requires_back: bool
    ) -> dict:
        """Build document upload progress indicator."""
        if requires_back:
            steps = [
                {"label": "Front", "complete": front_uploaded},
                {"label": "Back", "complete": back_uploaded},
                {"label": "Submit", "complete": False}
            ]
            current = 0 if not front_uploaded else (1 if not back_uploaded else 2)
        else:
            steps = [
                {"label": "Document", "complete": front_uploaded},
                {"label": "Submit", "complete": False}
            ]
            current = 0 if not front_uploaded else 1
            
        return {
            "steps": steps,
            "current_step": current,
            "total_steps": len(steps)
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def format_response(
    guidance: dict,
    issues: list[DetectedIssue],
    language: str = "en",
    output_format: str = "card"
) -> dict:
    """
    Format guidance response for display.
    
    Args:
        guidance: LLM guidance dict
        issues: List of detected issues
        language: Language code
        output_format: 'card', 'list', 'steps', 'api', 'mobile'
        
    Returns:
        Formatted response dict
    """
    formatter = ResponseFormatter(language)
    
    if output_format == "card":
        return formatter.format_guidance_card(guidance, issues)
    elif output_format == "list":
        return formatter.format_issue_list(issues)
    elif output_format == "steps":
        return formatter.format_step_by_step(issues, guidance)
    elif output_format == "api":
        return formatter.format_for_api(guidance, issues)
    elif output_format == "mobile":
        return formatter.format_mobile_friendly(guidance, issues)
    else:
        return formatter.format_guidance_card(guidance, issues)


def create_success_response(language: str = "en") -> dict:
    """Create a success response when no issues found."""
    templates = get_language_template(language)
    
    return {
        "card_type": "success",
        "icon": "",
        "header": templates.get("ready", "Ready to submit!"),
        "color": "green",
        "main_message": templates.get("great_job", "Great job!") + " Your document is clear and ready for verification.",
        "quick_tip": "Submit now",
        "encouragement": "You did it!",
        "can_submit": True,
        "issue_count": 0
    }
