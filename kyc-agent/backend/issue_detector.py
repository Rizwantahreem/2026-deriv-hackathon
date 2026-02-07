"""
Issue Detector - Detects and categorizes document issues based on Deriv requirements.
Maps vision analysis results to actionable issues with severity levels.
"""

from typing import List, Optional
from datetime import date, datetime
from config import (
    IssueType,
    IssueSeverity,
    DetectedIssue,
    get_document_requirements,
    get_country_by_code,
    validate_document_completeness
)


# Issue definitions with severity and suggestions
ISSUE_DEFINITIONS = {
    IssueType.MISSING_BACK: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Back side of document is required but not uploaded",
        "suggestion": "Please upload the back side of your document"
    },
    IssueType.MISSING_DATE: {
        "severity": IssueSeverity.WARNING,
        "description": "Bill date was not detected on the document",
        "suggestion": "Please upload a bill/statement where the date is clearly visible"
    },
    IssueType.BLURRY: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Document image is too blurry to read",
        "suggestion": "Hold your camera steady and ensure good lighting. Tap to focus before taking the photo."
    },
    IssueType.WRONG_DOCUMENT: {
        "severity": IssueSeverity.BLOCKING,
        "description": "The uploaded document does not match the expected type",
        "suggestion": "Please upload the correct document type as selected"
    },
    IssueType.EXPIRED: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Document appears to be expired",
        "suggestion": "Please upload a valid, non-expired document"
    },
    IssueType.CORNERS_CUT: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Document corners are not fully visible",
        "suggestion": "Position the document so all four corners are visible in the frame"
    },
    IssueType.GLARE: {
        "severity": IssueSeverity.WARNING,
        "description": "Glare or reflection is covering part of the document",
        "suggestion": "Avoid direct lighting. Tilt the document slightly to remove reflections."
    },
    IssueType.TOO_DARK: {
        "severity": IssueSeverity.WARNING,
        "description": "Image is too dark to read clearly",
        "suggestion": "Move to a well-lit area or turn on additional lighting"
    },
    IssueType.TOO_BRIGHT: {
        "severity": IssueSeverity.WARNING,
        "description": "Image is overexposed (too bright)",
        "suggestion": "Reduce direct light or move away from bright windows"
    },
    IssueType.PHOTO_MISSING: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Photo on the ID document is not visible",
        "suggestion": "Ensure the photo portion of your ID is clearly visible"
    },
    IssueType.TEXT_UNREADABLE: {
        "severity": IssueSeverity.BLOCKING,
        "description": "Text on the document cannot be read",
        "suggestion": "Ensure the document is flat and text is in focus"
    },
    IssueType.ROTATED: {
        "severity": IssueSeverity.WARNING,
        "description": "Document appears to be rotated",
        "suggestion": "Rotate the document so text is horizontal and right-side up"
    },
    IssueType.LOW_RESOLUTION: {
        "severity": IssueSeverity.WARNING,
        "description": "Image resolution is too low",
        "suggestion": "Move camera closer or use a higher quality camera setting"
    },
    IssueType.WRONG_FORMAT: {
        "severity": IssueSeverity.BLOCKING,
        "description": "File format is not supported",
        "suggestion": "Please upload a JPEG or PNG image"
    },
    IssueType.OBSTRUCTED: {
        "severity": IssueSeverity.WARNING,
        "description": "Part of the document is covered or obstructed",
        "suggestion": "Remove any objects covering the document (fingers, shadows, etc.)"
    }
}


def create_issue(
    issue_type: IssueType,
    affected_area: Optional[str] = None,
    custom_description: Optional[str] = None
) -> DetectedIssue:
    """
    Create a DetectedIssue with predefined severity and suggestions.
    
    Args:
        issue_type: Type of issue
        affected_area: Specific area affected (optional)
        custom_description: Override default description (optional)
    
    Returns:
        DetectedIssue object
    """
    definition = ISSUE_DEFINITIONS.get(issue_type, {
        "severity": IssueSeverity.INFO,
        "description": f"Issue detected: {issue_type.value}",
        "suggestion": "Please review and resubmit"
    })
    
    return DetectedIssue(
        issue_type=issue_type,
        severity=definition["severity"],
        description=custom_description or definition["description"],
        affected_area=affected_area,
        suggestion=definition["suggestion"]
    )


class IssueDetector:
    """
    Detects issues in documents based on vision analysis and Deriv requirements.
    """
    
    def __init__(self):
        """Initialize the issue detector."""
        pass
    
    def detect_issues(
        self,
        vision_result: dict,
        image_quality: dict,
        country_code: str,
        document_type: str,
        document_side: str,
        sides_uploaded: List[str]
    ) -> List[DetectedIssue]:
        """
        Detect all issues in a document based on analysis results.
        
        Args:
            vision_result: Result from GeminiVisionAnalyzer
            image_quality: Result from assess_basic_quality
            country_code: ISO country code
            document_type: Type of document
            document_side: Which side was uploaded (front/back)
            sides_uploaded: List of all sides uploaded so far
        
        Returns:
            List of DetectedIssue objects
        """
        issues = []
        
        # 1. Check completeness (missing sides)
        # Only flag missing sides when both sides have been attempted.
        # This avoids showing "missing back/front" during single-side uploads.
        if len(sides_uploaded) > 1:
            completeness = validate_document_completeness(
                country_code, document_type, sides_uploaded
            )
            if not completeness['is_complete']:
                for missing_side in completeness['missing_sides']:
                    issues.append(create_issue(
                        IssueType.MISSING_BACK,
                        affected_area=f"{missing_side} side",
                        custom_description=f"The {missing_side} side of your document is required"
                    ))
        
        # 2. Check image quality issues (from preprocessing)
        issues.extend(self._detect_quality_issues(image_quality))
        
        # 3. Check AI-detected issues
        issues.extend(self._detect_vision_issues(vision_result))

        # If blur is present, suppress corner/text unreadable to avoid stacking
        has_blur = any(i.issue_type == IssueType.BLURRY for i in issues)
        if has_blur:
            issues = [
                i for i in issues
                if i.issue_type not in (IssueType.CORNERS_CUT, IssueType.TEXT_UNREADABLE)
            ]
        
        # 4. Check document type mismatch
        if vision_result.get('is_correct_document') == False:
            detected = vision_result.get('detected_document_type', 'unknown')
            # Only flag wrong document if detected type actually differs
            if str(detected).lower() != str(document_type).lower():
                issues.append(create_issue(
                    IssueType.WRONG_DOCUMENT,
                    custom_description=f"Expected {document_type}, but detected: {detected}"
                ))

        # 5. Check required elements
        issues.extend(self._detect_missing_elements(
            vision_result, country_code, document_type, document_side
        ))

        # 6. Utility bill age check (must be within allowed months)
        if document_type == "utility_bill":
            issues.extend(self._detect_utility_bill_age(vision_result, country_code))
        
        return issues

    def _detect_utility_bill_age(
        self,
        vision_result: dict,
        country_code: str
    ) -> List[DetectedIssue]:
        """Detect if utility bill date is older than allowed max age."""
        issues = []
        extracted = vision_result.get("extracted_data", {}) if vision_result else {}

        bill_date_value = (
            extracted.get("bill_date")
            or extracted.get("date")
            or extracted.get("billDate")
            or extracted.get("statement_date")
        )
        if not bill_date_value:
            issues.append(create_issue(
                IssueType.MISSING_DATE,
                affected_area="bill date"
            ))
            return issues

        parsed_date = self._parse_date(bill_date_value)
        if not parsed_date:
            return issues

        max_months = 3
        country = get_country_by_code(country_code)
        if country:
            reqs = country.get("utility_bill_requirements", {})
            max_months = reqs.get("max_age_months") or max_months

        cutoff = self._subtract_months(date.today(), max_months)
        if parsed_date < cutoff:
            issues.append(create_issue(
                IssueType.EXPIRED,
                custom_description=f"Bill date {parsed_date.isoformat()} is older than {max_months} months",
                affected_area="bill date"
            ))

        return issues

    def _parse_date(self, value: str) -> Optional[date]:
        """Parse date from OCR in common formats."""
        if not value:
            return None
        text = str(value).strip().replace(",", "")
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
            "%b %d %Y",
            "%B %d %Y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except Exception:
                continue
        # Fallback: extract digits and try YYYYMMDD or DDMMYYYY
        digits = "".join(c for c in text if c.isdigit())
        if len(digits) == 8:
            for fmt in ("%Y%m%d", "%d%m%Y", "%m%d%Y"):
                try:
                    return datetime.strptime(digits, fmt).date()
                except Exception:
                    continue
        return None

    def _subtract_months(self, source: date, months: int) -> date:
        """Subtract N months from a date, preserving day when possible."""
        year = source.year
        month = source.month - months
        while month <= 0:
            month += 12
            year -= 1
        day = min(source.day, self._days_in_month(year, month))
        return date(year, month, day)

    def _days_in_month(self, year: int, month: int) -> int:
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return (next_month - date(year, month, 1)).days
    
    def _detect_quality_issues(self, image_quality: dict) -> List[DetectedIssue]:
        """Detect issues from basic image quality assessment."""
        issues = []
        
        if image_quality.get('is_blurry', False):
            issues.append(create_issue(
                IssueType.BLURRY,
                custom_description=f"Image blur score: {image_quality.get('blur_score', 'N/A')}"
            ))
        
        if image_quality.get('is_too_dark', False):
            issues.append(create_issue(
                IssueType.TOO_DARK,
                custom_description=f"Image brightness: {image_quality.get('brightness', 'N/A')}/255"
            ))
        
        if image_quality.get('is_too_bright', False):
            issues.append(create_issue(
                IssueType.TOO_BRIGHT,
                custom_description=f"Image brightness: {image_quality.get('brightness', 'N/A')}/255"
            ))
        
        if not image_quality.get('resolution_ok', True):
            issues.append(create_issue(
                IssueType.LOW_RESOLUTION,
                custom_description=f"Image size: {image_quality.get('width', '?')}x{image_quality.get('height', '?')}"
            ))
        
        return issues
    
    def _detect_vision_issues(self, vision_result: dict) -> List[DetectedIssue]:
        """Detect issues from AI vision analysis."""
        issues = []
        quality = vision_result.get('quality_assessment', {})
        is_blurry = quality.get('is_blurry', False)
        is_readable = quality.get('is_readable', True)
        
        # Check each quality flag
        if is_blurry:
            issues.append(create_issue(IssueType.BLURRY))
        
        if quality.get('has_glare', False):
            issues.append(create_issue(IssueType.GLARE))
        
        if quality.get('is_too_dark', False):
            issues.append(create_issue(IssueType.TOO_DARK))
        
        if quality.get('is_too_bright', False):
            issues.append(create_issue(IssueType.TOO_BRIGHT))
        
        # If image is blurry, don't add corners/text issues to avoid stacking
        if not is_blurry and not quality.get('all_corners_visible', True):
            issues.append(create_issue(IssueType.CORNERS_CUT))
        
        if quality.get('is_rotated', False):
            issues.append(create_issue(IssueType.ROTATED))
        
        if quality.get('has_obstructions', False):
            issues.append(create_issue(IssueType.OBSTRUCTED))
        
        if not is_blurry and not is_readable:
            issues.append(create_issue(IssueType.TEXT_UNREADABLE))
        
        # Add AI-specific issues
        for issue_text in vision_result.get('issues_found', []):
            # Only add if it's not already covered
            if issue_text and len(issues) < 5:  # Limit to avoid overwhelming
                # Try to map to known issue type, otherwise skip
                pass
        
        return issues
    
    def _detect_missing_elements(
        self,
        vision_result: dict,
        country_code: str,
        document_type: str,
        document_side: str
    ) -> List[DetectedIssue]:
        """Detect missing required elements."""
        issues = []
        
        detected = vision_result.get('detected_elements', {})
        requirements = get_document_requirements(country_code, document_type)
        
        if not requirements:
            return issues
        
        # Check for missing photo (critical for ID documents)
        if document_side != "back" and document_type != 'utility_bill' and not detected.get('has_photo', False):
            issues.append(create_issue(
                IssueType.PHOTO_MISSING,
                affected_area="photo area"
            ))
        
        return issues


def prioritize_issues(issues: List[DetectedIssue]) -> List[DetectedIssue]:
    """
    Prioritize issues by severity and remove duplicates.
    
    Args:
        issues: List of detected issues
    
    Returns:
        Sorted, deduplicated list (BLOCKING first, max 3 actionable)
    """
    if not issues:
        return []
    
    # Remove duplicates by issue type
    seen_types = set()
    unique_issues = []
    for issue in issues:
        if issue.issue_type not in seen_types:
            seen_types.add(issue.issue_type)
            unique_issues.append(issue)
    
    # Sort by severity (BLOCKING > WARNING > INFO)
    severity_order = {
        IssueSeverity.BLOCKING: 0,
        IssueSeverity.WARNING: 1,
        IssueSeverity.INFO: 2
    }
    
    sorted_issues = sorted(
        unique_issues,
        key=lambda x: severity_order.get(x.severity, 3)
    )
    
    # Limit to top 3 actionable issues to avoid overwhelming user
    return sorted_issues[:3]


def get_primary_blocking_issue(issues: List[DetectedIssue]) -> Optional[DetectedIssue]:
    """
    Get the single most important blocking issue.
    
    Args:
        issues: List of detected issues
    
    Returns:
        Most important blocking issue, or None if no blocking issues
    """
    blocking = [i for i in issues if i.severity == IssueSeverity.BLOCKING]
    if blocking:
        return blocking[0]
    return None


def group_issues_by_severity(
    issues: List[DetectedIssue]
) -> dict[IssueSeverity, List[DetectedIssue]]:
    """
    Group issues by their severity level.
    
    Args:
        issues: List of detected issues
    
    Returns:
        Dict mapping severity to list of issues
    """
    grouped = {
        IssueSeverity.BLOCKING: [],
        IssueSeverity.WARNING: [],
        IssueSeverity.INFO: []
    }
    
    for issue in issues:
        if issue.severity in grouped:
            grouped[issue.severity].append(issue)
    
    return grouped


def calculate_issue_score(issues: List[DetectedIssue]) -> float:
    """
    Calculate a score (0-100) based on issues found.
    100 = no issues, 0 = many blocking issues.
    
    Args:
        issues: List of detected issues
    
    Returns:
        Score from 0-100
    """
    if not issues:
        return 100.0
    
    # Penalty points per issue type
    penalties = {
        IssueSeverity.BLOCKING: 30,
        IssueSeverity.WARNING: 10,
        IssueSeverity.INFO: 2
    }
    
    total_penalty = sum(
        penalties.get(issue.severity, 0)
        for issue in issues
    )
    
    # Cap at 100
    score = max(0, 100 - total_penalty)
    return float(score)


def is_deriv_ready(issues: List[DetectedIssue]) -> bool:
    """
    Check if document is ready for Deriv submission (no blocking issues).
    
    Args:
        issues: List of detected issues
    
    Returns:
        True if no blocking issues
    """
    return not any(
        issue.severity == IssueSeverity.BLOCKING
        for issue in issues
    )


# Global detector instance
detector = IssueDetector()
