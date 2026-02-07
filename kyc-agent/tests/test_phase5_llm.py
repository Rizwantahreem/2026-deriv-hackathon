"""
Test Suite for Phase 5: LLM Reasoner

Tests:
1. System prompts loading
2. Issue-specific prompts
3. Language templates
4. Encouragement messages
5. LLM Reasoner initialization
6. Fallback guidance
7. Response formatter
8. Mobile formatting
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.document_schema import DetectedIssue, IssueSeverity, IssueType


def test_system_prompts():
    """Test system prompts are loaded correctly."""
    print("\nTEST 1: System Prompts Loading")
    print("-" * 40)
    
    from backend.prompts.system_prompt import (
        SYSTEM_PROMPT,
        GUIDANCE_PROMPT_TEMPLATE,
        ISSUE_PROMPTS
    )
    
    # Check system prompt exists and has key elements
    assert SYSTEM_PROMPT is not None
    assert "friendly" in SYSTEM_PROMPT.lower()
    assert "Deriv" in SYSTEM_PROMPT
    print(f"   SYSTEM_PROMPT loaded ({len(SYSTEM_PROMPT)} chars)")
    
    # Check guidance template
    assert GUIDANCE_PROMPT_TEMPLATE is not None
    assert "{document_type}" in GUIDANCE_PROMPT_TEMPLATE
    assert "{issues_list}" in GUIDANCE_PROMPT_TEMPLATE
    print(f"   GUIDANCE_PROMPT_TEMPLATE has placeholders")
    
    # Check issue prompts
    assert len(ISSUE_PROMPTS) >= 10
    assert "BLURRY" in ISSUE_PROMPTS
    assert "GLARE" in ISSUE_PROMPTS
    print(f"   {len(ISSUE_PROMPTS)} issue-specific prompts loaded")
    
    print(" PASSED: System prompts loading")
    return True


def test_issue_specific_prompts():
    """Test getting issue-specific prompts."""
    print("\nTEST 2: Issue-Specific Prompts")
    print("-" * 40)
    
    from backend.prompts.system_prompt import get_issue_prompt
    
    # Test blurry prompt
    blurry_prompt = get_issue_prompt("BLURRY")
    assert "blurry" in blurry_prompt.lower()
    assert "focus" in blurry_prompt.lower() or "steady" in blurry_prompt.lower()
    print(f"   BLURRY prompt contains relevant guidance")
    
    # Test glare prompt
    glare_prompt = get_issue_prompt("GLARE")
    assert "glare" in glare_prompt.lower()
    assert "angle" in glare_prompt.lower() or "flash" in glare_prompt.lower()
    print(f"   GLARE prompt contains relevant guidance")
    
    # Test unknown issue falls back
    unknown_prompt = get_issue_prompt("NONEXISTENT_ISSUE")
    assert unknown_prompt is not None
    print(f"   Unknown issue returns fallback prompt")
    
    print(" PASSED: Issue-specific prompts")
    return True


def test_language_templates():
    """Test multi-language template loading."""
    print("\nTEST 3: Language Templates")
    print("-" * 40)
    
    from backend.prompts.system_prompt import get_language_template, LANGUAGE_TEMPLATES
    
    # Check we have multiple languages
    assert len(LANGUAGE_TEMPLATES) >= 5
    print(f"   {len(LANGUAGE_TEMPLATES)} languages supported")
    
    # Test English
    en = get_language_template("en")
    assert "fix_this" in en
    assert "almost_there" in en
    print(f"   English template: '{en['almost_there']}'")
    
    # Test Urdu
    ur = get_language_template("ur")
    assert ur["almost_there"] != en["almost_there"]  # Should be different
    print(f"   Urdu template: '{ur['almost_there']}'")
    
    # Test Hindi
    hi = get_language_template("hi")
    assert hi["great_job"] != en["great_job"]
    print(f"   Hindi template: '{hi['great_job']}'")
    
    # Test unknown language falls back to English
    unknown = get_language_template("xx")
    assert unknown == en
    print(f"   Unknown language falls back to English")
    
    print(" PASSED: Language templates")
    return True


def test_encouragement_messages():
    """Test encouragement message selection."""
    print("\nTEST 4: Encouragement Messages")
    print("-" * 40)
    
    from backend.prompts.system_prompt import get_encouragement
    
    # First attempt
    first = get_encouragement(1)
    assert first is not None
    print(f"   First attempt: '{first}'")
    
    # Retry attempt
    retry = get_encouragement(2)
    assert retry is not None
    print(f"   Retry attempt: '{retry}'")
    
    # Multiple retries
    multi = get_encouragement(5)
    assert multi is not None
    print(f"   Multiple retries: '{multi}'")
    
    # Success
    success = get_encouragement(1, success=True)
    assert "" in success or "" in success or "" in success
    print(f"   Success: '{success}'")
    
    print(" PASSED: Encouragement messages")
    return True


def test_reasoner_initialization():
    """Test LLM reasoner can be initialized."""
    print("\nTEST 5: LLM Reasoner Initialization")
    print("-" * 40)
    
    from backend.llm_reasoner import GeminiReasoner, get_reasoner
    
    # Test direct initialization
    reasoner = GeminiReasoner()
    assert reasoner is not None
    assert reasoner._initialized == False  # Lazy init
    print(f"   GeminiReasoner created (lazy init)")
    
    # Test singleton
    singleton1 = get_reasoner()
    singleton2 = get_reasoner()
    assert singleton1 is singleton2
    print(f"   Singleton pattern works")
    
    print(" PASSED: LLM Reasoner initialization")
    return True


def test_fallback_guidance():
    """Test fallback guidance when LLM fails."""
    print("\nTEST 6: Fallback Guidance")
    print("-" * 40)
    
    from backend.llm_reasoner import GeminiReasoner
    
    reasoner = GeminiReasoner()
    
    # Test with no issues
    result = reasoner._fallback_guidance([], 1)
    assert result["main_issue"] is None
    assert result["guidance"] is not None
    print(f"   No issues: '{result['guidance'][:50]}...'")
    
    # Test with blurry issue
    blurry_issue = DetectedIssue(
        issue_type=IssueType.BLURRY,
        severity=IssueSeverity.BLOCKING,
        description="Image is blurry",
        suggestion="Hold steady"
    )
    result = reasoner._fallback_guidance([blurry_issue], 1)
    assert result["main_issue"] == "blurry"  # lowercase enum value
    print(f"   Blurry issue: '{result['guidance'][:50]}...'")
    
    # Test with dark issue
    dark_issue = DetectedIssue(
        issue_type=IssueType.TOO_DARK,
        severity=IssueSeverity.WARNING,
        description="Image is dark",
        suggestion="More light"
    )
    result = reasoner._fallback_guidance([dark_issue], 2)
    assert "bright" in result["guidance"].lower() or "light" in result["guidance"].lower()
    print(f"   Dark issue: '{result['guidance'][:50]}...'")
    
    print(" PASSED: Fallback guidance")
    return True


def test_response_formatter():
    """Test response formatting."""
    print("\nTEST 7: Response Formatter")
    print("-" * 40)
    
    from backend.response_formatter import ResponseFormatter, format_response
    
    formatter = ResponseFormatter("en")
    
    # Create test issue
    test_issue = DetectedIssue(
        issue_type=IssueType.GLARE,
        severity=IssueSeverity.WARNING,
        description="Glare on document",
        suggestion="Tilt slightly"
    )
    
    # Test guidance card formatting
    guidance = {
        "is_success": False,
        "severity_level": "medium",
        "guidance": "Tilt the document to reduce glare",
        "quick_tip": "Angle it",
        "can_submit": True
    }
    
    card = formatter.format_guidance_card(guidance, [test_issue])
    assert card["card_type"] == "warning"
    assert card["icon"] == "🟡"
    assert "Almost" in card["header"] or "almost" in card["header"].lower()
    print(f"   Card format: {card['card_type']} with {card['icon']}")
    
    # Test issue list formatting
    issue_list = formatter.format_issue_list([test_issue])
    assert len(issue_list) == 1
    assert issue_list[0]["icon"] == "🟡"
    assert issue_list[0]["label"] == "Recommended"
    print(f"   Issue list: {issue_list[0]['title']}")
    
    # Test success response
    success_guidance = {"is_success": True, "guidance": "Great!"}
    success_card = formatter.format_guidance_card(success_guidance, [])
    assert success_card["card_type"] == "success"
    assert success_card["icon"] == ""
    print(f"   Success card: {success_card['card_type']}")
    
    print(" PASSED: Response formatter")
    return True


def test_mobile_formatting():
    """Test mobile-friendly formatting."""
    print("\nTEST 8: Mobile Formatting")
    print("-" * 40)
    
    from backend.response_formatter import ResponseFormatter
    
    formatter = ResponseFormatter("en")
    
    # Create blocking issue
    blocking = DetectedIssue(
        issue_type=IssueType.BLURRY,
        severity=IssueSeverity.BLOCKING,
        description="Too blurry",
        suggestion="Hold steady"
    )
    
    guidance = {
        "is_success": False,
        "guidance": "Hold your camera steady and ensure proper lighting for a clearer photo",
        "quick_tip": "Steady!"
    }
    
    mobile = formatter.format_mobile_friendly(guidance, [blocking])
    assert mobile["status_emoji"] == ""
    assert mobile["show_retake_button"] == True
    assert mobile["progress_percent"] < 100
    assert len(mobile["short_message"]) <= 80
    print(f"   Mobile format: {mobile['progress_percent']}% progress")
    print(f"   Short message: '{mobile['short_message'][:40]}...'")
    
    # Test success mobile format
    success_guidance = {"is_success": True, "guidance": "Perfect!"}
    success_mobile = formatter.format_mobile_friendly(success_guidance, [])
    assert success_mobile["status_emoji"] == ""
    assert success_mobile["show_retake_button"] == False
    assert success_mobile["progress_percent"] == 100
    print(f"   Success mobile: {success_mobile['progress_percent']}%")
    
    print(" PASSED: Mobile formatting")
    return True


def run_all_tests():
    """Run all Phase 5 tests."""
    print("=" * 60)
    print("PHASE 5: LLM REASONER - TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_system_prompts,
        test_issue_specific_prompts,
        test_language_templates,
        test_encouragement_messages,
        test_reasoner_initialization,
        test_fallback_guidance,
        test_response_formatter,
        test_mobile_formatting
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f" FAILED: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("All Phase 5 tests passed!")
    else:
        print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
