"""
Issue Prioritizer - Organizes and formats issues for user display.
Provides user-friendly issue presentation.
"""

from typing import List, Optional
from config import DetectedIssue, IssueSeverity, IssueType


def get_issue_icon(severity: IssueSeverity) -> str:
    """Get emoji icon for issue severity."""
    icons = {
        IssueSeverity.BLOCKING: "🔴",
        IssueSeverity.WARNING: "🟡",
        IssueSeverity.INFO: "🟢"
    }
    return icons.get(severity, "⚪")


def get_severity_label(severity: IssueSeverity) -> str:
    """Get human-readable label for severity."""
    labels = {
        IssueSeverity.BLOCKING: "Must Fix",
        IssueSeverity.WARNING: "Should Fix",
        IssueSeverity.INFO: "Tip"
    }
    return labels.get(severity, "Info")


def format_issue_for_display(issue: DetectedIssue) -> dict:
    """
    Format a single issue for frontend display.
    
    Returns dict with:
        - icon: Emoji icon
        - severity_label: Human-readable severity
        - title: Short issue title
        - description: Detailed description
        - suggestion: How to fix
        - affected_area: Where the issue is (optional)
    """
    # Create a short title from issue type
    title_map = {
        IssueType.MISSING_BACK: "Missing Back Side",
        IssueType.MISSING_DATE: "Bill Date Not Found",
        IssueType.BLURRY: "Image is Blurry",
        IssueType.WRONG_DOCUMENT: "Wrong Document Type",
        IssueType.EXPIRED: "Document Expired",
        IssueType.CORNERS_CUT: "Corners Not Visible",
        IssueType.GLARE: "Glare Detected",
        IssueType.TOO_DARK: "Image Too Dark",
        IssueType.TOO_BRIGHT: "Image Too Bright",
        IssueType.PHOTO_MISSING: "Photo Not Visible",
        IssueType.TEXT_UNREADABLE: "Text Not Readable",
        IssueType.ROTATED: "Document Rotated",
        IssueType.LOW_RESOLUTION: "Low Resolution",
        IssueType.WRONG_FORMAT: "Wrong File Format",
        IssueType.OBSTRUCTED: "Document Obstructed"
    }
    
    return {
        "icon": get_issue_icon(issue.severity),
        "severity": issue.severity.value,
        "severity_label": get_severity_label(issue.severity),
        "title": title_map.get(issue.issue_type, issue.issue_type.value.replace("_", " ").title()),
        "description": issue.description,
        "suggestion": issue.suggestion or "Please review and resubmit",
        "affected_area": issue.affected_area,
        "issue_type": issue.issue_type.value
    }


def format_issues_for_display(issues: List[DetectedIssue]) -> List[dict]:
    """Format all issues for frontend display."""
    return [format_issue_for_display(issue) for issue in issues]


def get_action_summary(issues: List[DetectedIssue]) -> dict:
    """
    Get a summary of required actions.
    
    Returns:
        {
            "blocking_count": int,
            "warning_count": int,
            "info_count": int,
            "primary_action": str,
            "is_ready": bool,
            "status": "success" | "warning" | "error"
        }
    """
    blocking = [i for i in issues if i.severity == IssueSeverity.BLOCKING]
    warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
    infos = [i for i in issues if i.severity == IssueSeverity.INFO]
    
    # Determine primary action
    if blocking:
        primary_action = blocking[0].suggestion or "Fix the blocking issue to continue"
        status = "error"
    elif warnings:
        primary_action = "Consider fixing the warnings for better approval chances"
        status = "warning"
    else:
        primary_action = "Document looks good!"
        status = "success"
    
    return {
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "info_count": len(infos),
        "total_count": len(issues),
        "primary_action": primary_action,
        "is_ready": len(blocking) == 0,
        "status": status
    }


def create_progress_message(
    country_code: str,
    document_type: str,
    sides_uploaded: List[str],
    requires_back: bool
) -> str:
    """
    Create a progress message for document upload.
    
    Returns human-readable progress message.
    """
    if requires_back:
        if "front" in sides_uploaded and "back" in sides_uploaded:
            return " Both sides uploaded - document complete!"
        elif "front" in sides_uploaded:
            return " Front side uploaded. Please upload the back side."
        elif "back" in sides_uploaded:
            return " Back side uploaded. Please upload the front side."
        else:
            return "📤 Please upload both front and back sides of your document."
    else:
        if sides_uploaded:
            return " Document uploaded!"
        else:
            return "📤 Please upload your document."


def get_encouragement_message(score: float, is_ready: bool) -> str:
    """
    Get an encouraging message based on document score.
    
    Args:
        score: Document score (0-100)
        is_ready: Whether document is ready for submission
    
    Returns:
        Encouraging message string
    """
    if is_ready and score >= 90:
        return " Excellent! Your document is ready for verification."
    elif is_ready and score >= 70:
        return " Good! Your document is acceptable. Consider the suggestions for better results."
    elif is_ready:
        return " Your document can be submitted, but improvements are recommended."
    elif score >= 50:
        return " Almost there! Just a few fixes needed."
    else:
        return "Let's get a better photo of your document."


def format_tips_list(issues: List[DetectedIssue]) -> List[str]:
    """
    Extract actionable tips from issues.
    
    Returns list of tip strings.
    """
    tips = []
    
    for issue in issues:
        if issue.suggestion and issue.suggestion not in tips:
            tips.append(issue.suggestion)
    
    # Add generic tips if few issues
    if len(tips) < 2:
        generic_tips = [
            "Ensure good lighting when taking the photo",
            "Place the document on a dark, contrasting background",
            "Keep the camera parallel to the document"
        ]
        for tip in generic_tips:
            if len(tips) < 3 and tip not in tips:
                tips.append(tip)
    
    return tips[:5]  # Max 5 tips
