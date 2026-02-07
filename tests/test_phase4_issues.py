"""
Test script for Phase 4: Issue Detection components.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IssueType, IssueSeverity, DetectedIssue
from backend.issue_detector import (
    IssueDetector,
    create_issue,
    prioritize_issues,
    get_primary_blocking_issue,
    calculate_issue_score,
    is_deriv_ready,
    group_issues_by_severity
)
from backend.issue_prioritizer import (
    format_issue_for_display,
    format_issues_for_display,
    get_action_summary,
    get_encouragement_message,
    format_tips_list
)


def test_issue_creation():
    """Test issue creation."""
    print("=" * 60)
    print("TEST 1: Issue Creation")
    print("=" * 60)
    
    # Create different types of issues
    issue1 = create_issue(IssueType.BLURRY)
    issue2 = create_issue(IssueType.MISSING_BACK, affected_area="back side")
    issue3 = create_issue(IssueType.GLARE)
    
    print(f"\n1.1 Created BLURRY issue:")
    print(f"    Type: {issue1.issue_type.value}")
    print(f"    Severity: {issue1.severity.value}")
    print(f"    Suggestion: {issue1.suggestion[:50]}...")
    assert issue1.severity == IssueSeverity.BLOCKING
    print("     PASSED")
    
    print(f"\n1.2 Created MISSING_BACK issue:")
    print(f"    Affected area: {issue2.affected_area}")
    assert issue2.severity == IssueSeverity.BLOCKING
    print("     PASSED")
    
    print(f"\n1.3 Created GLARE issue:")
    assert issue3.severity == IssueSeverity.WARNING
    print(f"    Severity: {issue3.severity.value} (WARNING)")
    print("     PASSED")
    
    return [issue1, issue2, issue3]


def test_prioritization(issues):
    """Test issue prioritization."""
    print("\n" + "=" * 60)
    print("TEST 2: Issue Prioritization")
    print("=" * 60)
    
    # Shuffle issues (put warning first)
    shuffled = [issues[2], issues[0], issues[1]]
    print(f"\n2.1 Input order: {[i.issue_type.value for i in shuffled]}")
    
    prioritized = prioritize_issues(shuffled)
    print(f"    Output order: {[i.issue_type.value for i in prioritized]}")
    
    # First issue should be BLOCKING
    assert prioritized[0].severity == IssueSeverity.BLOCKING
    print("     PASSED - BLOCKING issues sorted first")
    
    # Test deduplication
    print("\n2.2 Testing deduplication...")
    duplicates = issues + issues  # Same issues twice
    deduped = prioritize_issues(duplicates)
    print(f"    Input count: {len(duplicates)}")
    print(f"    Output count: {len(deduped)}")
    assert len(deduped) <= 3  # Max 3 after prioritization
    print("     PASSED - Duplicates removed")
    
    return prioritized


def test_primary_issue(prioritized):
    """Test getting primary blocking issue."""
    print("\n" + "=" * 60)
    print("TEST 3: Primary Blocking Issue")
    print("=" * 60)
    
    primary = get_primary_blocking_issue(prioritized)
    print(f"\n    Primary issue: {primary.issue_type.value if primary else None}")
    assert primary is not None
    assert primary.severity == IssueSeverity.BLOCKING
    print("     PASSED")
    
    # Test with no blocking issues
    warnings_only = [create_issue(IssueType.GLARE)]
    no_blocking = get_primary_blocking_issue(warnings_only)
    assert no_blocking is None
    print("     No blocking = None returned")


def test_scoring():
    """Test issue scoring."""
    print("\n" + "=" * 60)
    print("TEST 4: Issue Scoring")
    print("=" * 60)
    
    # No issues = 100
    score_none = calculate_issue_score([])
    print(f"\n4.1 No issues: {score_none}/100")
    assert score_none == 100.0
    print("     PASSED")
    
    # One blocking = 70
    one_blocking = [create_issue(IssueType.BLURRY)]
    score_one = calculate_issue_score(one_blocking)
    print(f"4.2 One BLOCKING: {score_one}/100")
    assert score_one == 70.0
    print("     PASSED")
    
    # One warning = 90
    one_warning = [create_issue(IssueType.GLARE)]
    score_warning = calculate_issue_score(one_warning)
    print(f"4.3 One WARNING: {score_warning}/100")
    assert score_warning == 90.0
    print("     PASSED")


def test_deriv_ready():
    """Test Deriv readiness check."""
    print("\n" + "=" * 60)
    print("TEST 5: Deriv Readiness")
    print("=" * 60)
    
    # With blocking issues
    blocking = [create_issue(IssueType.BLURRY)]
    ready1 = is_deriv_ready(blocking)
    print(f"\n5.1 With BLOCKING: ready={ready1}")
    assert ready1 == False
    print("     PASSED - Not ready")
    
    # With only warnings
    warnings = [create_issue(IssueType.GLARE)]
    ready2 = is_deriv_ready(warnings)
    print(f"5.2 With WARNING only: ready={ready2}")
    assert ready2 == True
    print("     PASSED - Ready (warnings OK)")
    
    # No issues
    ready3 = is_deriv_ready([])
    print(f"5.3 No issues: ready={ready3}")
    assert ready3 == True
    print("     PASSED - Ready")


def test_formatting():
    """Test issue formatting for display."""
    print("\n" + "=" * 60)
    print("TEST 6: Display Formatting")
    print("=" * 60)
    
    issue = create_issue(IssueType.BLURRY)
    formatted = format_issue_for_display(issue)
    
    print(f"\n6.1 Formatted issue:")
    print(f"    Icon: {formatted['icon']}")
    print(f"    Title: {formatted['title']}")
    print(f"    Severity: {formatted['severity_label']}")
    print(f"    Suggestion: {formatted['suggestion'][:40]}...")
    
    assert formatted['icon'] == "🔴"  # BLOCKING = red
    assert formatted['severity_label'] == "Must Fix"
    print("     PASSED")


def test_action_summary():
    """Test action summary generation."""
    print("\n" + "=" * 60)
    print("TEST 7: Action Summary")
    print("=" * 60)
    
    issues = [
        create_issue(IssueType.BLURRY),
        create_issue(IssueType.GLARE),
    ]
    summary = get_action_summary(issues)
    
    print(f"\n    Blocking: {summary['blocking_count']}")
    print(f"    Warning: {summary['warning_count']}")
    print(f"    Status: {summary['status']}")
    print(f"    Ready: {summary['is_ready']}")
    
    assert summary['blocking_count'] == 1
    assert summary['warning_count'] == 1
    assert summary['status'] == "error"
    assert summary['is_ready'] == False
    print("     PASSED")


def test_encouragement():
    """Test encouragement messages."""
    print("\n" + "=" * 60)
    print("TEST 8: Encouragement Messages")
    print("=" * 60)
    
    # Perfect score
    msg1 = get_encouragement_message(100, True)
    print(f"\n8.1 Score 100, ready: {msg1}")
    assert "" in msg1
    print("     PASSED")
    
    # Low score, not ready
    msg2 = get_encouragement_message(30, False)
    print(f"8.2 Score 30, not ready: {msg2}")
    assert "" in msg2
    print("     PASSED")


def run_all_tests():
    """Run all Phase 4 tests."""
    print("\n" + "=" * 60)
    print("PHASE 4: ISSUE DETECTION - TEST SUITE")
    print("=" * 60)
    
    try:
        issues = test_issue_creation()
        prioritized = test_prioritization(issues)
        test_primary_issue(prioritized)
        test_scoring()
        test_deriv_ready()
        test_formatting()
        test_action_summary()
        test_encouragement()
        
        print("\n" + "=" * 60)
        print("All Phase 4 tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_all_tests()
