"""
Streamlit Frontend for KYC Document Analysis

Provides an interactive UI for:
- Selecting country and document type
- Uploading document images
- Viewing analysis results
- Getting guidance on fixing issues
- Submitting documents to Deriv (mock)
"""

import streamlit as st
import base64
import time
import requests
from io import BytesIO
from PIL import Image, ImageFilter, ImageStat

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="KYC Document Verification",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 1rem;
    }
    
    /* Card styling */
    .stCard {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Issue cards */
    .issue-blocking {
        border-left: 4px solid #ff4444;
        padding-left: 15px;
        margin: 10px 0;
    }
    
    .issue-warning {
        border-left: 4px solid #ffbb33;
        padding-left: 15px;
        margin: 10px 0;
    }
    
    .issue-info {
        border-left: 4px solid #33b5e5;
        padding-left: 15px;
        margin: 10px 0;
    }
    
    /* Success message */
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Progress indicator */
    .progress-step {
        display: inline-block;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        text-align: center;
        line-height: 30px;
        margin: 0 5px;
    }
    
    .step-complete {
        background: #28a745;
        color: white;
    }
    
    .step-current {
        background: #007bff;
        color: white;
    }
    
    .step-pending {
        background: #e9ecef;
        color: #6c757d;
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'step' not in st.session_state:
    st.session_state.step = 1  # 1: Select, 2: Upload, 3: Review, 4: Submit

if 'country' not in st.session_state:
    st.session_state.country = None

if 'document_type' not in st.session_state:
    st.session_state.document_type = None

if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

if 'attempt' not in st.session_state:
    st.session_state.attempt = 1

if 'submitted' not in st.session_state:
    st.session_state.submitted = False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_api_base():
    """Get API base URL."""
    return "http://localhost:8000"


def get_countries():
    """Fetch countries from API."""
    # Fallback data if API not available
    return [
        {"code": "PK", "name": "Pakistan"},
        {"code": "IN", "name": "India"},
        {"code": "NG", "name": "Nigeria"},
        {"code": "KE", "name": "Kenya"},
        {"code": "GB", "name": "United Kingdom"},
        {"code": "DE", "name": "Germany"},
        {"code": "UAE", "name": "United Arab Emirates"}
    ]


def get_documents(country_code):
    """Get documents for a country."""
    # Fallback data
    documents = {
        "PK": [
            {"doc_type": "national_id", "name": "CNIC (National ID)", "requires_back": True},
            {"doc_type": "passport", "name": "Passport", "requires_back": False}
        ],
        "IN": [
            {"doc_type": "national_id", "name": "Aadhaar Card", "requires_back": True},
            {"doc_type": "passport", "name": "Passport", "requires_back": False},
            {"doc_type": "driving_license", "name": "Driving License", "requires_back": True}
        ],
        "NG": [
            {"doc_type": "national_id", "name": "National ID Card", "requires_back": True},
            {"doc_type": "passport", "name": "International Passport", "requires_back": False}
        ],
        "KE": [
            {"doc_type": "national_id", "name": "National ID Card", "requires_back": True},
            {"doc_type": "passport", "name": "Kenyan Passport", "requires_back": False}
        ],
        "GB": [
            {"doc_type": "passport", "name": "UK Passport", "requires_back": False},
            {"doc_type": "driving_license", "name": "UK Driving Licence", "requires_back": True}
        ],
        "DE": [
            {"doc_type": "national_id", "name": "Personalausweis (ID Card)", "requires_back": True},
            {"doc_type": "passport", "name": "Reisepass (Passport)", "requires_back": False}
        ],
        "UAE": [
            {"doc_type": "national_id", "name": "Emirates ID", "requires_back": True},
            {"doc_type": "passport", "name": "Passport", "requires_back": False}
        ]
    }
    return documents.get(country_code, [])


def estimate_quality(image_bytes):
    """Estimate basic image quality using PIL (brightness + edge strength).
    Returns a dict with keys: is_blurry (bool), brightness (0-255).
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("L")
        brightness = int(ImageStat.Stat(img).mean[0])
        edges = img.filter(ImageFilter.FIND_EDGES)
        edge_strength = ImageStat.Stat(edges).mean[0]
        # Heuristic threshold: lower edge strength implies blur
        is_blurry = edge_strength < 12
        return {"is_blurry": is_blurry, "brightness": brightness}
    except Exception:
        # Fallback neutral values
        return {"is_blurry": False, "brightness": 128}


def analyze_document_local(image_bytes, document_type, country_code, side, attempt):
    """Analyze document using local modules (no API call)."""
    try:
        from backend.image_processor import process_document_image
        from backend.issue_detector import IssueDetector, prioritize_issues, calculate_issue_score, is_deriv_ready
        from backend.llm_reasoner import generate_guidance
        from backend.issue_prioritizer import format_issues_for_display
        
        # Process image
        processed_image, image_quality = process_document_image(image_bytes)
        
        if processed_image is None:
            return {
                "success": False,
                "score": 0,
                "is_ready": False,
                "issues": [{
                    "type": "INVALID_IMAGE",
                    "severity": "blocking",
                    "title": "Invalid Image",
                    "description": "Could not process the image",
                    "suggestion": "Please upload a valid JPEG or PNG image"
                }],
                "guidance": "We couldn't process your image. Please try a different photo.",
                "quick_tip": "Use JPEG/PNG",
                "encouragement": "Let's try again!",
                "severity_level": "high"
            }
        
        # Normalize image quality (handle unexpected list formats)
        quality = image_quality if isinstance(image_quality, dict) else estimate_quality(image_bytes)

        # Derive readability and content heuristics
        is_blurry = bool(quality.get("is_blurry", False))
        is_too_dark = bool(quality.get("is_too_dark", quality.get("brightness", 128) < 60))
        is_too_bright = bool(quality.get("is_too_bright", quality.get("brightness", 128) > 220))
        low_contrast = bool(quality.get("low_contrast", False))
        resolution_ok = bool(quality.get("resolution_ok", True))
        is_readable = (not is_blurry) and (not is_too_dark) and (not is_too_bright) and (not low_contrast) and resolution_ok

        # Create mock vision result aligned to IssueDetector expectations
        vision_result = {
            "detected_document_type": document_type,
            "is_correct_document": True,
            "quality_assessment": {
                "overall_quality": "good" if is_readable else "needs_improvement",
                "is_blurry": is_blurry,
                "has_glare": False,
                "is_too_dark": is_too_dark,
                "is_too_bright": is_too_bright,
                "all_corners_visible": True,
                "is_rotated": False,
                "has_obstructions": False,
                "is_readable": is_readable
            },
            # Detected elements should be a dict per IssueDetector
            "detected_elements": {
                "has_photo": is_readable,
                "has_name": is_readable,
                "has_id_number": is_readable
            },
            "issues_found": []
        }
        
        # Add issues based on quality
        if is_blurry:
            vision_result["issues_found"].append("blurry")
        if is_too_dark:
            vision_result["issues_found"].append("too_dark")
        if low_contrast and not is_blurry:
            # Treat very low content as unreadable
            vision_result["issues_found"].append("low_content")
        
        # Detect issues
        detector = IssueDetector()
        issues = detector.detect_issues(
            vision_result=vision_result,
            image_quality=quality,
            country_code=country_code,
            document_type=document_type,
            document_side=side,
            sides_uploaded=[side]
        )
        
        # Prioritize
        prioritized = prioritize_issues(issues)
        score = calculate_issue_score(prioritized)
        is_ready = is_deriv_ready(prioritized)
        
        # Get country name
        country_names = {
            "PK": "Pakistan", "IN": "India", "NG": "Nigeria",
            "KE": "Kenya", "GB": "United Kingdom", "DE": "Germany", "UAE": "UAE"
        }
        country_name = country_names.get(country_code, country_code)
        
        # Generate guidance
        guidance_result = generate_guidance(
            issues=prioritized,
            document_type=document_type,
            country_name=country_name,
            document_side=side,
            attempt=attempt
        )
        
        # Format issues
        formatted = format_issues_for_display(prioritized)
        
        return {
            "success": True,
            "score": score,
            "is_ready": is_ready,
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "severity": issue.severity.value,
                    "title": fmt["title"],
                    "description": issue.description,
                    "suggestion": issue.suggestion
                }
                for issue, fmt in zip(prioritized, formatted)
            ],
            "guidance": guidance_result.get("guidance", ""),
            "quick_tip": guidance_result.get("quick_tip", ""),
            "encouragement": guidance_result.get("encouragement", ""),
            "severity_level": guidance_result.get("severity_level", "medium")
        }
        
    except Exception as e:
        return {
            "success": False,
            "score": 0,
            "is_ready": False,
            "issues": [{
                "type": "ERROR",
                "severity": "blocking",
                "title": "Analysis Error",
                "description": "We couldn't analyze the photo due to a technical issue.",
                "suggestion": "Retake the photo with better focus and lighting, then try again."
            }],
            "guidance": "Please retake the photo with steady hands and good lighting.",
            "quick_tip": "Use natural light, hold camera steady",
            "encouragement": "Let's try again!",
            "severity_level": "high"
        }


def submit_document_local(image_bytes, document_type, country_code, side, score):
    """Submit document using local mock API."""
    try:
        from backend.deriv_api import submit_document
        from backend.image_processor import calculate_md5_checksum
        
        image_b64 = base64.b64encode(image_bytes).decode()
        checksum = calculate_md5_checksum(image_bytes)
        
        result = submit_document(
            document_type=document_type,
            side=side,
            image_data=image_b64,
            checksum=checksum,
            country_code=country_code,
            issue_score=score
        )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "document_id": None,
            "status": "error",
            "message": str(e),
            "can_proceed": False
        }


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render page header."""
    st.markdown("""
    # 📄 KYC Document Verification
    
    Upload your identity document for verification. Our AI will help you 
    ensure your document meets all requirements.
    """)
    
    # Progress indicator
    steps = ["Select", "Upload", "Review", "Submit"]
    cols = st.columns(len(steps))
    
    for i, (col, step) in enumerate(zip(cols, steps), 1):
        with col:
            if i < st.session_state.step:
                st.markdown(f" {step}")
            elif i == st.session_state.step:
                st.markdown(f"🔵 **{step}**")
            else:
                st.markdown(f"⚪ {step}")


def render_step1_select():
    """Render country and document selection."""
    st.subheader("Step 1: Select Your Country & Document")
    
    countries = get_countries()
    country_options = {c["name"]: c["code"] for c in countries}
    
    selected_country_name = st.selectbox(
        "Select your country",
        options=list(country_options.keys()),
        index=None,
        placeholder="Choose a country..."
    )
    
    if selected_country_name:
        country_code = country_options[selected_country_name]
        st.session_state.country = country_code
        
        documents = get_documents(country_code)
        doc_options = {d["name"]: d for d in documents}
        
        selected_doc_name = st.selectbox(
            "Select document type",
            options=list(doc_options.keys()),
            index=None,
            placeholder="Choose a document type..."
        )
        
        if selected_doc_name:
            st.session_state.document_type = doc_options[selected_doc_name]["doc_type"]
            st.session_state.requires_back = doc_options[selected_doc_name].get("requires_back", False)
            
            # Show requirements
            st.info(f"""
            📋 **Document Requirements:**
            - Upload a clear, well-lit photo
            - All corners must be visible
            - Text must be readable
            {"- Both front AND back sides required" if doc_options[selected_doc_name].get("requires_back") else "- Only front side needed"}
            """)
            
            if st.button("Continue →", type="primary"):
                st.session_state.step = 2
                st.rerun()


def render_step2_upload():
    """Render document upload."""
    st.subheader("Step 2: Upload Document Photo")
    
    st.markdown(f"""
    **Selected:** {st.session_state.document_type.replace('_', ' ').title()} 
    ({st.session_state.country})
    """)
    
    # Upload tips and uploader
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    with st.expander(" Photo Tips", expanded=True):
        st.markdown("""
        - Use good lighting (natural light works best)
        - Place document on a dark, flat surface
        - Hold camera directly above the document
        - Ensure all four corners are visible
        - Avoid shadows and reflections
        """)

    uploaded_file = st.file_uploader(
        "Upload front side of document",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPEG, PNG"
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    
    with col2:
        if uploaded_file is not None:
            # Show preview
            image = Image.open(uploaded_file)
            st.image(image, caption="Document Preview", use_column_width=True)
            
            if st.button("Analyze Document →", type="primary"):
                with st.spinner("Analyzing your document..."):
                    # Read image bytes
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    
                    # Analyze
                    result = analyze_document_local(
                        image_bytes=image_bytes,
                        document_type=st.session_state.document_type,
                        country_code=st.session_state.country,
                        side="front",
                        attempt=st.session_state.attempt
                    )
                    
                    st.session_state.analysis_result = result
                    st.session_state.image_bytes = image_bytes
                    st.session_state.step = 3
                    st.rerun()


def render_step3_review():
    """Render analysis results and review."""
    st.subheader("Step 3: Review Analysis")
    
    result = st.session_state.analysis_result
    
    if result is None:
        st.error("No analysis result. Please upload a document first.")
        if st.button("← Back to Upload"):
            st.session_state.step = 2
            st.rerun()
        return
    
    # Score display
    score = result.get("score", 0)
    is_ready = result.get("is_ready", False)
    
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        # Score meter
        if score >= 80:
            st.success(f"##  {score}/100")
        elif score >= 50:
            st.warning(f"##  {score}/100")
        else:
            st.error(f"##  {score}/100")
    with col2:
        # Main guidance
        st.markdown(f"### {result.get('guidance', 'Analyzing...')}")
        if result.get("quick_tip"):
            st.markdown(f"💡 **Quick Tip:** {result['quick_tip']}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Issues
    issues = result.get("issues", [])
    if issues:
        st.markdown("### Issues Found")
        with st.container():
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            for issue in issues:
                severity = issue.get("severity", "info")
                icon = "🔴" if severity == "blocking" else "🟡" if severity == "warning" else "🟢"
                st.markdown(f"""
                <div class="issue-{severity}">
                    {icon} **{issue['title']}**
                    <div style="margin-top:6px;">{issue['description']}</div>
                    <div style="margin-top:6px;">➡️ {issue['suggestion']}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success(" No issues found! Your document looks great.")
    
    # Encouragement
    st.info(f" {result.get('encouragement', 'Keep going!')}")
    
    # Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("← Back"):
            st.session_state.step = 2
            st.rerun()
    
    with col2:
        if st.button(" Retake Photo"):
            st.session_state.attempt += 1
            st.session_state.step = 2
            st.session_state.analysis_result = None
            st.rerun()
    
    with col3:
        if is_ready:
            if st.button("Submit Document →", type="primary"):
                st.session_state.step = 4
                st.rerun()
        else:
            st.button("Submit Document →", type="primary", disabled=True)
            st.caption("Fix blocking issues first")


def render_step4_submit():
    """Render document submission."""
    st.subheader("Step 4: Submit to Deriv")
    
    if st.session_state.submitted:
        st.success("""
        ## Document Submitted Successfully!
        
        Your document has been submitted for verification.
        
        **What happens next:**
        - Our team will review your document
        - You'll receive confirmation within 24-48 hours
        - Keep an eye on your email for updates
        """)
        
        if st.button("Submit Another Document"):
            # Reset state
            st.session_state.step = 1
            st.session_state.country = None
            st.session_state.document_type = None
            st.session_state.analysis_result = None
            st.session_state.attempt = 1
            st.session_state.submitted = False
            st.rerun()
        return
    
    # Confirmation
    st.markdown("""
    ### Ready to Submit
    
    Please confirm the following:
    """)
    
    result = st.session_state.analysis_result
    
    st.markdown(f"""
    - **Country:** {st.session_state.country}
    - **Document:** {st.session_state.document_type.replace('_', ' ').title()}
    - **Quality Score:** {result.get('score', 0)}/100
    """)
    
    confirm = st.checkbox("I confirm this is my valid identity document")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Review"):
            st.session_state.step = 3
            st.rerun()
    
    with col2:
        if confirm:
            if st.button(" Submit Document", type="primary"):
                with st.spinner("Submitting document..."):
                    # Submit
                    submit_result = submit_document_local(
                        image_bytes=st.session_state.image_bytes,
                        document_type=st.session_state.document_type,
                        country_code=st.session_state.country,
                        side="front",
                        score=result.get("score", 0)
                    )
                    
                    if submit_result.get("success"):
                        st.session_state.submitted = True
                        st.session_state.submission_id = submit_result.get("document_id")
                        st.rerun()
                    else:
                        st.error(f"Submission failed: {submit_result.get('message')}")
        else:
            st.button(" Submit Document", type="primary", disabled=True)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point."""
    render_header()
    
    st.markdown("---")
    
    if st.session_state.step == 1:
        render_step1_select()
    elif st.session_state.step == 2:
        render_step2_upload()
    elif st.session_state.step == 3:
        render_step3_review()
    elif st.session_state.step == 4:
        render_step4_submit()
    
    # Footer
    st.markdown("---")
    st.caption("KYC Document Verification Agent - Powered by AI")


if __name__ == "__main__":
    main()
