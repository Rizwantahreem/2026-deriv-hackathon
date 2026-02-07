"""
KYC Document Verification - Streamlit Frontend

A multi-step KYC wizard supporting:
- Country selection with dynamic form fields
- Real Gemini OCR document analysis  
- Usage tracking with retry limits
- Professional UI with feedback cards
"""

import streamlit as st
import json
import base64
import os
import sys
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables BEFORE any other imports
from dotenv import load_dotenv
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

# Debug: Verify API key is loaded
_api_key = os.getenv("GEMINI_API_KEY", "")
if _api_key:
    print(f"[DEBUG] GEMINI_API_KEY loaded: {_api_key[:10]}...{_api_key[-4:]}")
else:
    print("[WARNING] GEMINI_API_KEY not found in environment!")

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
# IMPORTS (after path setup)
# ============================================================================

from backend.ocr_service import GeminiOCR, OCRResult, DocumentQuality
from backend.usage_tracker import UsageTracker, UsageLevel
from backend.form_validator import validate_form_data, validate_cnic, validate_aadhaar, validate_pan


# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Card styling - ensure dark text on all cards */
    .info-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #007bff;
        color: #212529 !important;
    }
    
    .info-card * {
        color: #212529 !important;
    }
    
    .success-card {
        background: #d4edda;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #28a745;
        color: #155724 !important;
    }
    
    .success-card * {
        color: #155724 !important;
    }
    
    .warning-card {
        background: #fff3cd;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #ffc107;
        color: #856404 !important;
    }
    
    .warning-card * {
        color: #856404 !important;
    }
    
    .error-card {
        background: #f8d7da;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #dc3545;
        color: #721c24 !important;
    }
    
    .error-card * {
        color: #721c24 !important;
    }
    
    /* Issue cards - dark text */
    .issue-blocking {
        background: #fff;
        border-left: 4px solid #dc3545;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
        color: #212529 !important;
    }
    
    .issue-blocking * {
        color: #212529 !important;
    }
    
    .issue-warning {
        background: #fff;
        border-left: 4px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
        color: #212529 !important;
    }
    
    .issue-warning * {
        color: #212529 !important;
    }
    
    .issue-info {
        background: #fff;
        border-left: 4px solid #17a2b8;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
        color: #212529 !important;
    }
    
    .issue-info * {
        color: #212529 !important;
    }
    
    /* File info display */
    .file-info {
        background: #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Progress steps */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    
    /* Usage banner */
    .usage-banner-green {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .usage-banner-yellow {
        background: linear-gradient(90deg, #ffc107 0%, #fd7e14 100%);
        color: #212529;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .usage-banner-red {
        background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'step': 1,  # 1: Country, 2: Form, 3: Documents, 4: Review
        'country_code': None,
        'country_name': None,
        'form_data': {},
        'documents': {},  # {doc_type: {side: {result, file_info}}}
        'ocr_results': {},
        'usage_tracker': None,
        'submitted': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize usage tracker
    if st.session_state.usage_tracker is None:
        st.session_state.usage_tracker = UsageTracker()


def get_tracker() -> UsageTracker:
    """Get usage tracker from session state."""
    if st.session_state.usage_tracker is None:
        st.session_state.usage_tracker = UsageTracker()
    return st.session_state.usage_tracker


# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_country_config() -> Dict:
    """Load country forms configuration."""
    config_path = Path(__file__).parent.parent / "config" / "country_forms.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_countries() -> List[Dict]:
    """Get list of supported countries."""
    config = load_country_config()
    countries = []
    for code, data in config["countries"].items():
        countries.append({
            "code": code,
            "name": data["name"],
            "flag": data.get("flag", "🌍")
        })
    return countries


def get_country_fields(country_code: str) -> List[Dict]:
    """Get form fields for a country."""
    config = load_country_config()
    return config["countries"].get(country_code, {}).get("personal_fields", [])


def get_country_documents(country_code: str) -> Dict:
    """Get document requirements for a country."""
    config = load_country_config()
    return config["countries"].get(country_code, {}).get("documents", {})


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_usage_banner():
    """Render API usage status banner."""
    tracker = get_tracker()
    level, message, color = tracker.get_status_message()
    
    if level == "ok":
        css_class = "usage-banner-green"
    elif level == "warning":
        css_class = "usage-banner-yellow"
    else:
        css_class = "usage-banner-red"
    
    st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)


def render_progress_indicator():
    """Render step progress indicator."""
    steps = ["🌍 Country", "📝 Personal Info", "📄 Documents", " Review"]
    current = st.session_state.step
    
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps), 1):
        with col:
            if i < current:
                st.markdown(f" ~~{step.split()[1]}~~")
            elif i == current:
                st.markdown(f"**🔵 {step.split()[1]}**")
            else:
                st.markdown(f"⚪ {step.split()[1]}")


def render_file_info(file) -> Dict:
    """Render file info card (not the image itself)."""
    file_size_kb = len(file.getvalue()) / 1024
    file_size_mb = file_size_kb / 1024
    
    info = {
        "name": file.name,
        "size_kb": round(file_size_kb, 1),
        "size_mb": round(file_size_mb, 2),
        "type": file.type
    }
    
    size_display = f"{info['size_mb']:.2f} MB" if file_size_mb >= 1 else f"{info['size_kb']:.1f} KB"
    
    st.markdown(f"""
    <div style="background-color: #e9ecef; border-radius: 8px; padding: 15px; margin: 10px 0; color: #212529;">
        <strong style="color: #212529;">📎 {info['name']}</strong><br>
        <small style="color: #495057;">Size: {size_display} | Type: {info['type']}</small>
    </div>
    """, unsafe_allow_html=True)
    
    return info


def render_ocr_result(result: OCRResult, form_data: Optional[Dict] = None, country_code: Optional[str] = None, is_success: bool = False, side: str = "", has_mismatches: bool = False):
    """Render OCR analysis result with form data comparison - Clean UX."""
    # Check for rate limit error first
    if result.error_message and ("rate limit" in result.error_message.lower() or "quota" in result.error_message.lower()):
        st.error("### API Rate Limit Exceeded")
        st.warning("Please wait 1-2 minutes and try again. This is a temporary limit on the free API tier.")
        return

    score = result.quality_score
    quality = result.quality.value

    # === MAIN STATUS CARD ===
    if is_success:
        st.markdown(f"""
        <div class="success-card">
            <h3> {side.title()} Accepted</h3>
            <p><strong>Quality: {score}/100</strong> • This document meets requirements</p>
        </div>
        """, unsafe_allow_html=True)
    elif has_mismatches and score >= 50:
        # High quality image but mismatches with form - show special message
        st.markdown(f"""
        <div class="warning-card">
            <h3> {side.title()} - Form Data Mismatch</h3>
            <p><strong>Image Quality: {score}/100</strong> (Good quality)</p>
            <p style="margin-top: 10px;"><strong>Issue:</strong> Document data doesn't match your form entries.</p>
            <p>👉 <strong>Go back to Step 2</strong> and correct your form data to match your document, then return here.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Get top 2 most critical issues for main card
        main_issues = []
        if result.issues:
            blocking = [i for i in result.issues if i.get("severity") == "blocking"]
            main_issues = blocking[:2] if blocking else result.issues[:2]

        issues_text = ""
        if main_issues:
            issues_text = "<br>".join([f"• {issue.get('message', '')[:80]}..." for issue in main_issues])

        st.markdown(f"""
        <div class="error-card">
            <h3> {side.title()} Rejected - Retake Required</h3>
            <p><strong>Quality: {score}/100</strong> (minimum 50 required)</p>
            <p style="margin-top: 10px;"><strong>Main Issues:</strong><br>{issues_text}</p>
        </div>
        """, unsafe_allow_html=True)

    # === FORM DATA VERIFICATION ===
    if form_data and country_code and result.extracted_fields:
        from backend.ocr_service import ocr_service
        all_match, mismatches = ocr_service.compare_with_form(
            result.extracted_fields,
            form_data,
            country_code
        )

        if all_match and mismatches == []:
            st.success(" **Document data matches your form**")
        elif mismatches:
            st.error(f" **{len(mismatches)} field(s) don't match your form**")
            st.info("💡 **Tip:** Go back to **Step 2 (Personal Info)** and correct your entries to match your document. The data will be saved and your document will be re-validated automatically.")

            with st.expander("📋 View Mismatches", expanded=True):
                for mismatch in mismatches:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**{mismatch['field'].replace('_', ' ').title()}**")
                        st.caption(f"📝 You entered: `{mismatch['form_value']}`")
                    with col2:
                        st.markdown("&nbsp;")
                        st.caption(f"📄 Document shows: `{mismatch['document_value']}`")
                    st.markdown("---")

    # === COLLAPSIBLE DETAILS ===
    # Extracted Fields
    if result.extracted_fields:
        with st.expander("📄 Extracted Data"):
            for key, value in result.extracted_fields.items():
                if value:
                    st.text(f"{key.replace('_', ' ').title()}: {value}")

    # Issues (if not successful)
    if not is_success and result.issues:
        with st.expander(f" All Issues ({len(result.issues)})", expanded=False):
            for issue in result.issues:
                severity = issue.get("severity", "info")
                icon = "🔴" if severity == "blocking" else "🟡"
                st.markdown(f"{icon} **{issue.get('type', 'Issue').replace('_', ' ').title()}**")
                st.caption(issue.get('message', ''))
                if issue.get('suggestion'):
                    st.info(f"💡 {issue.get('suggestion')}")
                st.markdown("---")

    # Tips (if not successful)
    if not is_success and result.suggestions:
        with st.expander("💡 Tips for Better Photo", expanded=True):
            for i, tip in enumerate(result.suggestions[:3], 1):
                st.markdown(f"{i}. {tip}")


def render_retry_status(document_type: str, side: str):
    """Render retry status for a document."""
    tracker = get_tracker()
    status = tracker.get_field_status(document_type, side)
    
    remaining = status["remaining"]
    attempts = status["attempts"]
    
    if remaining == 0:
        st.error(f" Maximum retries reached ({attempts}/{status['max_attempts']})")
    elif remaining == 1:
        st.warning(f" Last retry remaining ({attempts}/{status['max_attempts']})")
    else:
        st.info(f"📊 Attempts: {attempts}/{status['max_attempts']}")


# ============================================================================
# STEP 1: COUNTRY SELECTION
# ============================================================================

def render_step1_country():
    """Render country selection step."""
    st.header("🌍 Step 1: Select Your Country")
    st.markdown("Choose your country to see the required documents and form fields.")
    
    countries = get_countries()
    
    # Create selection options
    options = {f"{c['flag']} {c['name']}": c for c in countries}
    
    selected = st.selectbox(
        "Country",
        options=["Select a country..."] + list(options.keys()),
        key="country_select"
    )
    
    if selected and selected != "Select a country...":
        country = options[selected]
        st.session_state.country_code = country["code"]
        st.session_state.country_name = country["name"]
        
        # Show what's required
        docs = get_country_documents(country["code"])
        fields = get_country_fields(country["code"])
        
        st.markdown("---")
        st.markdown(f"### Requirements for {country['flag']} {country['name']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📝 Personal Information**")
            required_fields = [f["label"] for f in fields if f.get("required")]
            for field in required_fields[:5]:
                st.markdown(f"- {field}")
            if len(required_fields) > 5:
                st.markdown(f"- _...and {len(required_fields) - 5} more_")
        
        with col2:
            st.markdown("**📄 Documents Required**")
            for doc_key, doc in docs.items():
                sides = doc.get("sides", ["front"])
                st.markdown(f"- {doc['name']} ({', '.join(sides)})")
        
        st.markdown("---")
        
        if st.button("Continue →", type="primary"):
            st.session_state.step = 2
            st.rerun()


# ============================================================================
# STEP 2: PERSONAL INFORMATION FORM
# ============================================================================

def render_step2_form():
    """Render personal information form."""
    st.header("📝 Step 2: Personal Information")
    
    country_code = st.session_state.country_code
    country_name = st.session_state.country_name
    
    st.markdown(f"**Country:** {country_name}")
    
    fields = get_country_fields(country_code)
    
    # Group fields into sections
    id_fields = [f for f in fields if f["type"] == "id"]
    personal_fields = [f for f in fields if f["id"] in ["full_name", "first_name", "last_name", "middle_name", "title", "date_of_birth", "gender"]]
    address_fields = [f for f in fields if "address" in f["id"] or f["id"] in ["city", "state", "province", "county", "postal_code", "postcode", "pin_code"]]
    contact_fields = [f for f in fields if f["id"] == "phone"]
    
    # Render sections
    st.markdown("### 👤 Personal Details")
    render_form_fields(personal_fields, country_code)
    
    if id_fields:
        st.markdown("### 🆔 Identification Numbers")
        render_form_fields(id_fields, country_code)
    
    st.markdown("### 🏠 Address")
    render_form_fields(address_fields, country_code)
    
    if contact_fields:
        st.markdown("### 📱 Contact")
        render_form_fields(contact_fields, country_code)
    
    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back"):
            # Save current form data before going back
            form_data = collect_form_data(fields)
            st.session_state.form_data = form_data
            st.session_state.step = 1
            st.rerun()
    
    with col2:
        if st.button("Continue to Documents →", type="primary"):
            # Collect and validate form data
            form_data = collect_form_data(fields)
            is_valid, errors, field_errors = validate_form_data(form_data, country_code, fields)
            
            if is_valid:
                st.session_state.form_data = form_data
                st.session_state.step = 3
                st.rerun()
            else:
                # Still save the form data even if invalid (for retention)
                st.session_state.form_data = form_data
                st.error("Please fix the following errors:")
                for error in errors[:5]:
                    st.markdown(f"- {error}")


def render_form_fields(fields: List[Dict], country_code: str):
    """Render a list of form fields."""
    cols = st.columns(2)
    
    for i, field in enumerate(fields):
        with cols[i % 2]:
            render_single_field(field, country_code)


def render_single_field(field: Dict, country_code: str):
    """Render a single form field."""
    field_id = field["id"]
    label = field.get("label", field_id)
    required = field.get("required", False)
    field_type = field.get("type", "text")
    placeholder = field.get("placeholder", "")
    help_text = field.get("help", "")
    options = field.get("options", [])
    validation = field.get("validation", {})
    
    display_label = f"{label} *" if required else label
    key = f"form_{field_id}"
    
    # Get existing value from form_data (for data retention when navigating back)
    existing = st.session_state.form_data.get(field_id, "")
    
    # Pre-populate session state if not already set but we have stored data
    if key not in st.session_state and existing:
        st.session_state[key] = existing
    
    if field_type == "select":
        # Find index of existing value
        all_options = [""] + options
        default_index = 0
        if existing and existing in all_options:
            default_index = all_options.index(existing)
        
        st.selectbox(
            display_label,
            options=all_options,
            index=default_index,
            key=key,
            help=help_text
        )
    
    elif field_type == "date":
        min_age = field.get("min_age", 18)
        max_age = field.get("max_age", 100)
        today = date.today()
        max_date = date(today.year - min_age, today.month, today.day)
        min_date = date(today.year - max_age, today.month, today.day)
        
        # Use existing date value if available
        default_date = None
        if existing:
            if isinstance(existing, date):
                default_date = existing
            elif isinstance(existing, str):
                try:
                    from datetime import datetime
                    default_date = datetime.strptime(existing, "%Y-%m-%d").date()
                except:
                    pass
        
        st.date_input(
            display_label,
            key=key,
            min_value=min_date,
            max_value=max_date,
            value=default_date,
            help=help_text or f"You must be between {min_age} and {max_age} years old"
        )
    
    elif field_type == "id":
        format_hint = field.get("format", "")
        if format_hint:
            st.caption(f"Format: {format_hint}")
        
        value = st.text_input(
            display_label,
            key=key,
            placeholder=placeholder,
            help=help_text
        )
        
        # Real-time validation for ID fields
        if value:
            error = None
            if field_id == "cnic":
                _, error = validate_cnic(value)
            elif field_id == "aadhaar":
                _, error = validate_aadhaar(value)
            elif field_id == "pan":
                _, error = validate_pan(value)
            
            if error:
                st.error(error)
    
    else:  # text
        st.text_input(
            display_label,
            key=key,
            placeholder=placeholder,
            help=help_text
        )


def collect_form_data(fields: List[Dict]) -> Dict:
    """Collect all form data from session state."""
    data = {}
    for field in fields:
        key = f"form_{field['id']}"
        if key in st.session_state:
            value = st.session_state[key]
            if value == "" or value is None:
                data[field["id"]] = None
            else:
                data[field["id"]] = value
    return data


# ============================================================================
# STEP 3: DOCUMENT UPLOAD
# ============================================================================

def render_step3_documents():
    """Render document upload step."""
    st.header("📄 Step 3: Upload Documents")
    
    country_code = st.session_state.country_code
    docs = get_country_documents(country_code)
    
    # Render usage banner
    render_usage_banner()
    
    # Track completion
    all_complete = True
    
    for doc_key, doc_config in docs.items():
        st.markdown(f"### {doc_config['name']}")
        st.markdown(f"_{doc_config.get('description', '')}_")
        
        # Tips expander
        tips = doc_config.get("tips", [])
        if tips:
            with st.expander(" Photo Tips"):
                for tip in tips:
                    st.markdown(f"- {tip}")
        
        # Render each side
        sides = doc_config.get("sides", ["front"])
        for side in sides:
            doc_complete = render_document_upload(
                doc_key=doc_key,
                doc_type=doc_config["type"],
                doc_name=doc_config["name"],
                side=side,
                country_code=country_code
            )
            if not doc_complete:
                all_complete = False
        
        st.markdown("---")
    
    # Navigation
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Form"):
            st.session_state.step = 2
            st.rerun()
    
    with col2:
        if all_complete:
            if st.button("Review & Submit →", type="primary"):
                st.session_state.step = 4
                st.rerun()
        else:
            st.button("Review & Submit →", type="primary", disabled=True)
            st.caption("Upload all required documents to continue")


def render_document_upload(
    doc_key: str,
    doc_type: str,
    doc_name: str,
    side: str,
    country_code: str
) -> bool:
    """Render upload UI for a single document side. Returns True if complete."""
    
    tracker = get_tracker()
    storage_key = f"{doc_key}_{side}"
    
    st.markdown(f"**{side.title()} Side**")
    
    # Check if already analyzed (show results whether success or failure)
    existing_result = st.session_state.documents.get(storage_key)
    if existing_result:
        ocr_result = existing_result["ocr_result"]
        raw_score = existing_result.get("raw_quality_score", ocr_result.quality_score)
        
        # DYNAMIC SUCCESS CALCULATION based on current form data
        # Check for mismatches with current form data
        form_data = st.session_state.get("form_data", {})
        has_mismatches = False
        
        if form_data and ocr_result.extracted_fields:
            from backend.ocr_service import ocr_service
            all_match, mismatches = ocr_service.compare_with_form(
                ocr_result.extracted_fields,
                form_data,
                country_code
            )
            has_mismatches = len(mismatches) > 0
        
        # Document is successful only if:
        # 1. OCR was successful
        # 2. Quality score >= 50
        # 3. No mismatches with form data
        is_success = (
            ocr_result.success and 
            raw_score >= 50 and 
            not has_mismatches
        )
        
        # Calculate effective score for display
        # If there are mismatches, cap the displayed score at 49
        effective_score = raw_score if not has_mismatches else min(raw_score, 49)
        
        # Update the OCR result's quality_score for display purposes
        # Create a modified result for display
        display_result = ocr_result
        if has_mismatches and raw_score >= 50:
            # We need to show a lower score when there are mismatches
            # But keep the original data intact
            pass  # The render function will show mismatch info

        # Always show OCR results (whether success or failure)
        render_ocr_result(
            ocr_result,
            form_data=form_data,
            country_code=country_code,
            is_success=is_success,
            side=side,
            has_mismatches=has_mismatches  # Pass mismatch info
        )

        # Show re-upload button
        if st.button(f"🔄 Re-upload {side.title()}", key=f"reupload_{storage_key}", use_container_width=True):
            del st.session_state.documents[storage_key]
            st.rerun()

        st.markdown("---")

        # Only return True if successful (for progress tracking)
        return is_success
    
    # Check retry limit
    can_retry, remaining = tracker.can_retry_field(doc_type, side)
    
    if not can_retry:
        st.error(" Maximum upload attempts reached for this document.")
        st.markdown("Please contact support if you need assistance.")
        return False
    
    # Show retry status
    render_retry_status(doc_type, side)
    
    # File uploader
    uploaded_file = st.file_uploader(
        f"Upload {side} side",
        type=["jpg", "jpeg", "png"],
        key=f"upload_{storage_key}",
        help="Supported formats: JPEG, PNG (max 5MB)"
    )
    
    if uploaded_file:
        # Show file info (not the image)
        file_info = render_file_info(uploaded_file)
        
        # Check file size
        if file_info["size_mb"] > 5:
            st.error("File too large. Maximum size is 5MB.")
            return False
        
        # Analyze button
        if st.button(f"🔍 Analyze {side.title()}", key=f"analyze_{storage_key}", type="primary"):
            # Check API limits
            if not tracker.can_make_call:
                st.error("API limit reached. Please try again tomorrow.")
                return False

            # Record attempt
            success, msg = tracker.record_field_attempt(doc_type, side)

            if not success:
                st.error(msg)
                return False

            if msg:
                st.info(msg)

            # Analyze with Gemini OCR
            with st.spinner("Analyzing document with AI..."):
                ocr = GeminiOCR()

                if not ocr.is_configured():
                    st.error("Gemini API not configured. Please set GEMINI_API_KEY in .env file.")
                    st.warning("API Key not found. Check terminal logs for details.")
                    return False

                # Real OCR - always use real API when configured
                tracker.record_call()
                result = ocr.analyze_document(
                    image_bytes=uploaded_file.getvalue(),
                    document_type=doc_type,
                    country_code=country_code,
                    side=side
                )

                # Store result with raw OCR data
                # Success will be recalculated dynamically based on form data matching
                st.session_state.documents[storage_key] = {
                    "ocr_result": result,
                    "file_info": file_info,
                    "raw_quality_score": result.quality_score,  # Store original score
                    "image_bytes": uploaded_file.getvalue()  # Store for potential re-analysis
                }

                st.rerun()
    
    return False


def create_mock_ocr_result(doc_type: str, side: str) -> OCRResult:
    """Create mock OCR result for demo when API is not configured."""
    from backend.ocr_service import OCRResult, DocumentQuality
    
    mock_fields = {
        "cnic": {"cnic_number": "12345-1234567-1", "name": "Demo User", "father_name": "Demo Father"},
        "aadhaar": {"aadhaar_number": "2345 6789 0123", "name": "Demo User"},
        "passport": {"passport_number": "AB1234567", "surname": "USER", "given_names": "DEMO"}
    }
    
    return OCRResult(
        success=True,
        document_type=doc_type,
        quality=DocumentQuality.GOOD,
        quality_score=85,
        extracted_fields=mock_fields.get(doc_type, {}),
        issues=[],
        suggestions=["Demo mode - using mock data"],
        raw_response="{}"
    )


# ============================================================================
# STEP 4: REVIEW & SUBMIT
# ============================================================================

def render_step4_review():
    """Render review and submit step."""
    st.header(" Step 4: Review & Submit")
    
    # Summary
    st.markdown("### 📋 Application Summary")
    
    # Personal Info
    st.markdown("**Personal Information:**")
    form_data = st.session_state.form_data
    for key, value in form_data.items():
        if value:
            label = key.replace("_", " ").title()
            st.markdown(f"- **{label}:** {value}")
    
    st.markdown("---")
    
    # Documents
    st.markdown("**Documents Uploaded:**")
    for key, doc_info in st.session_state.documents.items():
        if doc_info.get("success"):
            result = doc_info["ocr_result"]
            file_info = doc_info["file_info"]
            st.markdown(f"-  **{key}** - {file_info['name']} (Score: {result.quality_score}/100)")
    
    st.markdown("---")
    
    # Confirmation
    confirm = st.checkbox("I confirm that all information provided is accurate and the documents are genuine.")
    
    # Navigation
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Documents"):
            st.session_state.step = 3
            st.rerun()
    
    with col2:
        if confirm:
            if st.button(" Submit Application", type="primary"):
                with st.spinner("Submitting application..."):
                    # Mock submission
                    import time
                    time.sleep(1)
                    st.session_state.submitted = True
                    st.rerun()
        else:
            st.button(" Submit Application", type="primary", disabled=True)


def render_success():
    """Render success message after submission."""
    st.balloons()
    
    st.markdown("""
    <div class="success-card">
        <h2>Application Submitted Successfully!</h2>
        <p>Your KYC documents have been submitted for verification.</p>
        <p><strong>What happens next:</strong></p>
        <ul>
            <li>Our team will review your documents within 24-48 hours</li>
            <li>You'll receive an email confirmation shortly</li>
            <li>If any issues are found, we'll contact you</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Start New Application"):
        # Reset state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    init_session_state()
    
    # Header
    st.title("📄 KYC Document Verification")
    st.markdown("Complete your identity verification in a few simple steps.")
    
    # Check if submitted
    if st.session_state.submitted:
        render_success()
        return
    
    # Progress indicator
    render_progress_indicator()
    
    st.markdown("---")
    
    # Render current step
    if st.session_state.step == 1:
        render_step1_country()
    elif st.session_state.step == 2:
        render_step2_form()
    elif st.session_state.step == 3:
        render_step3_documents()
    elif st.session_state.step == 4:
        render_step4_review()
    
    # Footer
    st.markdown("---")
    st.caption("KYC Document Verification Agent | Powered by AI")


if __name__ == "__main__":
    main()
