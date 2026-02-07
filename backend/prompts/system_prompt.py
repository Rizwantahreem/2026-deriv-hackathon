"""
System Prompts for KYC Document Analysis Agent

These prompts guide Gemini LLM to generate user-friendly guidance
for fixing document issues during KYC verification.
"""

# ============================================================================
# MAIN SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are a friendly KYC document verification assistant for Deriv, 
a leading online trading platform. Your job is to help users fix issues with their 
identity document uploads so they can complete their account verification successfully.

## Your Personality
- Friendly and encouraging, never judgmental
- Clear and concise, avoid technical jargon
- Patient and supportive, even for repeated issues
- Culturally aware and respectful

## Your Goals
1. Help users understand what's wrong with their document photo
2. Give specific, actionable steps to fix the issue
3. Explain WHY the fix is needed (Deriv needs to verify identity)
4. Keep users motivated to complete their KYC

## Important Context
- Users are uploading identity documents (national ID, passport, driver's license)
- Deriv needs clear, readable documents for regulatory compliance
- Many users are on mobile devices with varying camera quality
- Users may be frustrated after multiple upload attempts

## Response Guidelines
- Keep responses SHORT (2-3 sentences max for main guidance)
- Use simple language (assume non-native English speakers)
- Be specific about the problem and solution
- Include emojis sparingly to make guidance feel friendly
- Never mention "AI" or "system" - speak as a helpful assistant

## What NOT to Do
- Don't repeat the same advice multiple times
- Don't give long lists of tips (focus on the ONE main issue)
- Don't be vague ("improve your photo" - HOW?)
- Don't blame the user ("your photo is bad")
"""

# ============================================================================
# GUIDANCE GENERATION PROMPT
# ============================================================================

GUIDANCE_PROMPT_TEMPLATE = """Analyze these document issues and generate helpful guidance.

## Document Information
- Document Type: {document_type}
- Country: {country_name}
- Side: {document_side}
- Upload Attempt: {attempt_number}

## Issues Found
{issues_list}

## Image Quality Metrics
- Blurry: {is_blurry}
- Brightness: {brightness}
- Resolution: {resolution}

## Your Task
Generate a SHORT, friendly response that:
1. Acknowledges the main problem (1 sentence)
2. Gives ONE specific action to fix it (1-2 sentences)
3. Optionally adds encouragement if this is a retry

## Response Format
Return a JSON object with:
{{
    "main_issue": "Brief description of the primary problem",
    "guidance": "The short, friendly guidance message for the user",
    "quick_tip": "A 5-word max actionable tip",
    "confidence": 0.0-1.0 (how confident you are in this guidance)
}}
"""

# ============================================================================
# ISSUE-SPECIFIC PROMPTS
# ============================================================================

ISSUE_PROMPTS = {
    "BLURRY": """The document is too blurry to read.
    
Guidance focus:
- Stable hands or rest phone on surface
- Good lighting (natural light is best)
- Wait for camera to focus before capturing
- Clean camera lens""",

    "TOO_DARK": """The image is too dark.

Guidance focus:
- Move to brighter location
- Face toward a window or light source
- Don't cast shadow over document
- Use flash if needed (but watch for glare)""",

    "TOO_BRIGHT": """The image is overexposed.

Guidance focus:
- Move away from direct sunlight
- Reduce flash intensity
- Find even, diffused lighting
- Avoid reflective surfaces""",

    "GLARE": """There's glare or reflection on the document.

Guidance focus:
- Angle the document slightly
- Turn off flash
- Move away from bright lights
- Use matte surface underneath""",

    "CORNERS_CUT": """The document corners are not visible.

Guidance focus:
- Include entire document in frame
- Keep some margin around edges
- Don't zoom in too much
- Hold phone directly above document""",

    "ROTATED": """The document is rotated or tilted.

Guidance focus:
- Hold phone level with document
- Align document edges with screen
- Use grid lines if available
- Place document on flat surface""",

    "MISSING_BACK": """The back side of the document is required.

Guidance focus:
- National IDs typically have info on both sides
- Flip the document over
- Same quality standards apply to back
- Upload in the correct section""",

    "WRONG_DOCUMENT": """This doesn't appear to be the expected document type.

Guidance focus:
- Verify document type matches selection
- Check if document is valid/not expired
- Make sure it's an accepted document type
- Contact support if unsure what to upload""",

    "PHOTO_MISSING": """The photo on the ID is not visible.

Guidance focus:
- Ensure the ID photo is clear and visible
- Check for glare covering the photo
- Photo is used for identity verification
- Try different angle if photo is covered""",

    "TEXT_UNREADABLE": """The text on the document cannot be read.

Guidance focus:
- Improve lighting
- Hold camera steady
- Ensure document is flat
- Higher resolution if possible""",

    "LOW_RESOLUTION": """The image resolution is too low.

Guidance focus:
- Move closer to document
- Use rear camera (better quality)
- Check camera settings for quality
- Avoid digital zoom""",

    "OBSTRUCTED": """Part of the document is covered or obstructed.

Guidance focus:
- Remove fingers from document
- Remove any clips or holders
- Ensure nothing covers important info
- Move objects from around document"""
}

# ============================================================================
# MULTI-LANGUAGE TEMPLATES
# ============================================================================

LANGUAGE_TEMPLATES = {
    "en": {
        "fix_this": "Fix this",
        "almost_there": "Almost there!",
        "great_job": "Great job!",
        "try_again": "Let's try again",
        "ready": "Ready to submit!",
        "issue_found": "We found an issue",
        "tip": "Quick tip"
    },
    "ur": {  # Urdu (Pakistan)
        "fix_this": "اسے ٹھیک کریں",
        "almost_there": "تقریباً ہو گیا!",
        "great_job": "شاباش!",
        "try_again": "دوبارہ کوشش کریں",
        "ready": "جمع کرانے کے لیے تیار!",
        "issue_found": "ایک مسئلہ ملا",
        "tip": "فوری ٹپ"
    },
    "hi": {  # Hindi (India)
        "fix_this": "इसे ठीक करें",
        "almost_there": "लगभग हो गया!",
        "great_job": "बहुत बढ़िया!",
        "try_again": "फिर से कोशिश करें",
        "ready": "जमा करने के लिए तैयार!",
        "issue_found": "एक समस्या मिली",
        "tip": "त्वरित सुझाव"
    },
    "sw": {  # Swahili (Kenya)
        "fix_this": "Rekebisha hii",
        "almost_there": "Karibu kumaliza!",
        "great_job": "Vizuri sana!",
        "try_again": "Jaribu tena",
        "ready": "Tayari kuwasilisha!",
        "issue_found": "Tatizo limegunduliwa",
        "tip": "Kidokezo"
    },
    "de": {  # German
        "fix_this": "Beheben Sie dies",
        "almost_there": "Fast geschafft!",
        "great_job": "Gut gemacht!",
        "try_again": "Versuchen wir es noch einmal",
        "ready": "Bereit zum Einreichen!",
        "issue_found": "Problem gefunden",
        "tip": "Schneller Tipp"
    },
    "ar": {  # Arabic (UAE)
        "fix_this": "أصلح هذا",
        "almost_there": "اوشكت!",
        "great_job": "عمل رائع!",
        "try_again": "لنحاول مرة أخرى",
        "ready": "جاهز للإرسال!",
        "issue_found": "تم العثور على مشكلة",
        "tip": "نصيحة سريعة"
    }
}

# ============================================================================
# ENCOURAGEMENT MESSAGES
# ============================================================================

ENCOURAGEMENT_MESSAGES = {
    "first_attempt": [
        "Let's make sure your document is clear and readable. ",
        "Just a quick fix and you'll be ready to go!",
        "One small adjustment will help verify your identity."
    ],
    "retry_attempt": [
        "You're getting closer! Just one more adjustment.",
        "Almost there! This small fix will help.",
        "Good effort! Let's try one more time."
    ],
    "multiple_retries": [
        "Don't worry, we'll get this right together!",
        "You're doing great - document verification can be tricky.",
        "Hang in there! Clear documents help keep your account secure."
    ],
    "success": [
        "Perfect! Your document looks great!",
        "Excellent! Ready for verification.",
        "Document quality is acceptable and readable."
    ]
}

# ============================================================================
# FALLBACK GUIDANCE
# ============================================================================

FALLBACK_GUIDANCE = {
    "generic": "Please ensure your document is well-lit, in focus, and all corners are visible.",
    "blurry": "Hold your camera steady and make sure the document is in focus before capturing.",
    "dark": "Move to a brighter area or turn on more lights.",
    "glare": "Tilt the document slightly to avoid reflections.",
    "quality": "Try using your phone's rear camera for better quality."
}


def get_issue_prompt(issue_type: str) -> str:
    """Get specific guidance prompt for an issue type."""
    return ISSUE_PROMPTS.get(issue_type.upper(), ISSUE_PROMPTS.get("TEXT_UNREADABLE"))


def get_language_template(language: str = "en") -> dict:
    """Get language-specific template strings."""
    return LANGUAGE_TEMPLATES.get(language.lower(), LANGUAGE_TEMPLATES["en"])


def get_encouragement(attempt: int, success: bool = False) -> str:
    """Get appropriate encouragement message based on attempt number."""
    import random
    
    if success:
        return random.choice(ENCOURAGEMENT_MESSAGES["success"])
    elif attempt == 1:
        return random.choice(ENCOURAGEMENT_MESSAGES["first_attempt"])
    elif attempt <= 3:
        return random.choice(ENCOURAGEMENT_MESSAGES["retry_attempt"])
    else:
        return random.choice(ENCOURAGEMENT_MESSAGES["multiple_retries"])


def format_guidance_prompt(
    document_type: str,
    country_name: str,
    document_side: str,
    issues: list,
    is_blurry: bool,
    brightness: str,
    resolution: str,
    attempt_number: int = 1
) -> str:
    """Format the guidance prompt with actual values."""
    issues_text = "\n".join([
        f"- {issue.issue_type.value}: {issue.description}"
        for issue in issues
    ]) if issues else "- No issues detected"
    
    return GUIDANCE_PROMPT_TEMPLATE.format(
        document_type=document_type,
        country_name=country_name,
        document_side=document_side,
        attempt_number=attempt_number,
        issues_list=issues_text,
        is_blurry=is_blurry,
        brightness=brightness,
        resolution=resolution
    )
