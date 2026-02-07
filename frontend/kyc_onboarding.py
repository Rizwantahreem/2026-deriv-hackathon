"""
KYC Onboarding Flow - Complete Multi-Step Form

A standalone Streamlit application for country-aware KYC onboarding.
Integrates:
- Dynamic form fields based on country
- Real-time validation
- Document upload with AI analysis
- Compliance declarations
- Deriv submission simulation
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import date
import time
import json
import base64
import requests
import os
import hashlib
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables BEFORE importing backend modules
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    # Debug: print to confirm loading (remove in production)
    # print(f"Loaded .env from: {env_path}")
    # print(f"GEMINI_API_KEY present: {bool(os.getenv('GEMINI_API_KEY'))}")

from frontend.dynamic_form import (
    init_form_state,
    render_country_selector,
    render_kyc_form,
    render_form_summary,
    get_all_form_data,
    clear_form_state,
    render_field
)

from config.kyc_schema_loader import (
    get_country_schema,
    get_supported_countries,
    FormDataValidator,
    CountryKYCSchema
)

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="KYC Onboarding",
    page_icon='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff444f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    layout="centered",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SVG ICONS (Professional, smooth-cornered)
# =============================================================================

ICONS = {
    "globe": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    "file": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "check_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff444f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    "alert": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
    "info": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#17a2b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>',
    "arrow_right": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>',
    "arrow_left": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>',
    "clipboard": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>',
    "lock": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
    "loader": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff444f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spin"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>'
}

# =============================================================================
# CUSTOM STYLES
# =============================================================================

st.markdown("""
<style>
    /* Base colors for consistent readability */
    .stApp {
        background: #0b0f14;
        color: #e5e7eb;
    }
    .main, .main * {
        color: #e5e7eb;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #f9fafb !important;
    }
    .stMarkdown, .stMarkdown * {
        color: #e5e7eb;
    }
    /* Reset scrollbar to page level */
    .main .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 2rem;
        overflow: visible !important;
    }
    
    /* Remove inner scrollbars */
    .stExpander, .stForm, .element-container {
        overflow: visible !important;
    }
    
    section[data-testid="stSidebar"] {
        background: #0d1117;
        border-right: 1px solid #1e2a3a;
    }
    
    /* Header */
    .kyc-header {
        text-align: center;
        padding: 24px 0;
        border-bottom: 2px solid #ff444f;
        margin-bottom: 24px;
    }
    
    .kyc-header h1 {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin: 0;
        font-weight: 600;
    }
    
    /* Step indicator - professional pills */
    .step-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .step-pill-active {
        background: #ff444f;
        color: white;
        box-shadow: 0 2px 8px rgba(255, 68, 79, 0.3);
    }
    
    .step-pill-complete {
        background: #28a745;
        color: white;
    }
    
    .step-pill-pending {
        background: #e9ecef;
        color: #6c757d;
    }
    
    /* Cards with smooth corners */
    .info-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        border-left: 4px solid #17a2b8;
        color: #212529;
    }
    
    .warning-card {
        background: #fff8e6;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        border-left: 4px solid #ffc107;
        color: #212529;
    }
    
    .success-card {
        background: #e8f5e9;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        border-left: 4px solid #28a745;
        color: #212529;
    }
    
    .error-card {
        background: #fce4e6;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        border-left: 4px solid #dc3545;
        color: #212529;
    }

    /* Ensure readable text on light backgrounds */
    .info-card *, .warning-card *, .success-card *, .error-card * {
        color: #212529 !important;
    }

    /* Darker caption text for readability */
    .stCaption {
        color: #374151 !important;
    }
    
    /* Country cards */
    .country-card {
        background: white;
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .country-card:hover {
        border-color: #ff444f;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .country-card.selected {
        border-color: #ff444f;
        background: #fff5f5;
    }
    
    .country-flag {
        font-size: 32px;
        margin-bottom: 8px;
    }
    
     /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Hide markdown header anchor (link icon) */
    .stMarkdown .anchor-link { display: none !important; }
    .stMarkdown a[aria-label="anchor"] { display: none !important; }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background-color: #ff444f;
        border-color: #ff444f;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #e03e48;
        border-color: #e03e48;
        box-shadow: 0 2px 8px rgba(255, 68, 79, 0.3);
    }
    
    /* Secondary button */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        white-space: nowrap;
        font-size: 0.9rem;
    }
    
    /* Loading spinner animation */
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .spin {
        animation: spin 1s linear infinite;
    }
    
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px;
        gap: 16px;
    }
    
    /* Form section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: #f9fafb;
        background: #111827;
        border: 1px solid #1f2937;
        padding: 8px 12px;
        border-radius: 10px;
        margin-bottom: 12px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def scroll_to_top():
    """Inject JavaScript to scroll to top of page."""
    st.markdown(
        '''<script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>''',
        unsafe_allow_html=True
    )


def get_file_signature(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    try:
        file_bytes = uploaded_file.getvalue()
        digest = hashlib.md5(file_bytes).hexdigest()
        return f"{uploaded_file.name}:{uploaded_file.size}:{digest}"
    except Exception:
        return f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 'na')}:{getattr(uploaded_file, 'type', 'na')}"


def mark_file_uploader_change(key: str):
    value = st.session_state.get(key)
    st.session_state.file_uploader_cleared[key] = value is None


# =============================================================================
# SESSION STATE
# =============================================================================

def init_onboarding_state():
    """Initialize onboarding session state."""
    if 'onboarding_step' not in st.session_state:
        st.session_state.onboarding_step = 1
    if 'selected_country' not in st.session_state:
        st.session_state.selected_country = None
    if 'form_completed' not in st.session_state:
        st.session_state.form_completed = False
    if 'documents_uploaded' not in st.session_state:
        st.session_state.documents_uploaded = {}
    if 'document_signatures' not in st.session_state:
        st.session_state.document_signatures = {}
    if 'file_uploader_cleared' not in st.session_state:
        st.session_state.file_uploader_cleared = {}
    if 'document_analysis' not in st.session_state:
        st.session_state.document_analysis = {}
    if 'ocr_extracted_data' not in st.session_state:
        st.session_state.ocr_extracted_data = {}
    if 'data_mismatches' not in st.session_state:
        st.session_state.data_mismatches = []
    if 'manual_review_required' not in st.session_state:
        st.session_state.manual_review_required = False
    if 'submission_result' not in st.session_state:
        st.session_state.submission_result = None

    # Initialize form state (but don't clear existing data)
    if "kyc_form_data" not in st.session_state:
        init_form_state("kyc")
    
    # Always sync existing form data to widgets before rendering form
    # This ensures form data persists when navigating between steps
    if "kyc_form_data" in st.session_state:
        from frontend.dynamic_form import sync_form_data_to_widgets
        sync_form_data_to_widgets("kyc")

    # Pre-populate nationality based on selected country if not already set
    if st.session_state.selected_country:
        schema = get_country_schema(st.session_state.selected_country)
        if schema:
            from frontend.dynamic_form import set_form_value, get_form_value
            # Only set if not already set
            if not get_form_value("nationality", "kyc"):
                set_form_value("nationality", schema.default_nationality, "kyc")
                st.session_state["kyc_nationality"] = schema.default_nationality
            if not get_form_value("country", "kyc"):
                set_form_value("country", schema.country_name, "kyc")
            if not get_form_value("country_of_residence", "kyc"):
                set_form_value("country_of_residence", schema.country_name, "kyc")
                st.session_state["kyc_country_of_residence"] = schema.country_name


# =============================================================================
# DOCUMENT ANALYSIS FUNCTIONS
# =============================================================================

def get_expected_ocr_fields(document_type: str, side: str, country_code: str) -> set:
    """
    Return expected OCR fields for a document side to avoid false mismatches.
    This is a pragmatic mapping for known document layouts.
    """
    doc_type = (document_type or "").lower()
    side = (side or "front").lower()
    country_code = (country_code or "").upper()

    # Base defaults (if unknown, allow all fields)
    expected = None

    # Pakistan CNIC layout
    if doc_type in {"cnic", "national_id"} and country_code == "PK":
        if side == "front":
            expected = {"full_name", "father_name", "id_number", "date_of_birth", "gender"}
        elif side == "back":
            expected = {"address"}

    # UAE Emirates ID layout
    if doc_type == "emirates_id" and country_code == "UAE":
        if side == "front":
            expected = {"full_name", "id_number", "nationality"}
        elif side == "back":
            # Back side has a different card number; don't compare ID number
            expected = {"date_of_birth", "gender"}

    # UK documents
    if country_code == "GB":
        if doc_type == "passport":
            expected = {"full_name", "id_number", "date_of_birth", "expiry_date", "nationality"}
        elif doc_type == "driving_license":
            if side == "front":
                expected = {"full_name", "id_number", "date_of_birth"}
            elif side == "back":
                expected = {"address", "expiry_date"}

    # Utility bill (all countries)
    if doc_type == "utility_bill":
        expected = {"name", "address", "bill_date", "date"}

    return expected if expected is not None else set()


def compare_extracted_with_form(
    extracted_data: dict,
    document_type: str = "",
    side: str = "front",
    country_code: str = ""
) -> dict:
    """
    Compare OCR extracted data with form data and return match score.

    Returns:
        dict with match_score (0-100) and mismatches list
    """
    from frontend.dynamic_form import get_all_form_data

    form_data = get_all_form_data("kyc")
    mismatches = []
    matched_fields = 0
    compared_fields = 0

    # Field mapping: OCR field -> form field(s)
    field_mappings = {
        "full_name": ["full_name", "first_name", "last_name"],
        "id_number": [
            "cnic_number",
            "aadhaar_number",
            "pan_number",
            "passport_number",
            "driving_license_number",
            "emirates_id_number",
            "id_number"
        ],
        "date_of_birth": ["date_of_birth", "dob"],
        "father_name": ["father_name", "fathers_name"],
        "gender": ["gender"],
        "address": [
            "address_line_1",
            "city",
            "province",
            "state",
            "postal_code",
            "postcode",
            "pin_code",
            "country",
            "country_of_residence"
        ]
    }

    for ocr_field, form_fields in field_mappings.items():
        expected_fields = get_expected_ocr_fields(document_type, side, country_code)
        if expected_fields and ocr_field not in expected_fields:
            continue
        ocr_value = extracted_data.get(ocr_field)

        if not ocr_value or ocr_value == "null" or ocr_value is None:
            continue

        # Clean OCR value
        ocr_value_clean = str(ocr_value).strip().lower()

        for form_field in form_fields:
            form_value = form_data.get(form_field)

            if not form_value:
                continue

            compared_fields += 1
            form_value_clean = str(form_value).strip().lower()

            # Handle name comparison
            if ocr_field == "full_name" and form_field in ["first_name", "last_name"]:
                first = form_data.get("first_name", "").strip().lower()
                last = form_data.get("last_name", "").strip().lower()
                full_form = f"{first} {last}".strip()

                if full_form and names_match(ocr_value_clean, full_form):
                    matched_fields += 1
                elif full_form:
                    mismatches.append({
                        "field": "Full Name",
                        "form_value": f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}".strip(),
                        "doc_value": ocr_value
                    })
                break
            elif ocr_field == "full_name" and form_field == "full_name":
                if normalize_text(ocr_value) == normalize_text(form_value):
                    matched_fields += 1
                else:
                    mismatches.append({
                        "field": "Full Name",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle ID number comparison
            elif ocr_field == "id_number":
                ocr_id_clean = ''.join(c for c in str(ocr_value) if c.isdigit())
                form_id_clean = ''.join(c for c in str(form_value) if c.isdigit())
                # Only compare if OCR looks like an actual ID number
                if len(ocr_id_clean) >= 6 and len(form_id_clean) >= 6:
                    if ocr_id_clean == form_id_clean:
                        matched_fields += 1
                    else:
                        mismatches.append({
                            "field": "ID Number",
                            "form_value": str(form_value),
                            "doc_value": ocr_value
                        })
                break

            # Handle date comparison
            elif ocr_field == "date_of_birth":
                if dates_match(ocr_value, form_value):
                    matched_fields += 1
                else:
                    mismatches.append({
                        "field": "Date of Birth",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle gender comparison (e.g., F vs Female)
            elif ocr_field == "gender":
                if normalize_gender(ocr_value) == normalize_gender(form_value):
                    matched_fields += 1
                else:
                    mismatches.append({
                        "field": "Gender",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle father name comparison
            elif ocr_field == "father_name":
                if normalize_text(ocr_value) == normalize_text(form_value):
                    matched_fields += 1
                else:
                    mismatches.append({
                        "field": "Father Name",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle address comparison (combined current address)
            if ocr_field == "address":
                # Skip address comparison if user is renting/moved
                addr_status = str(form_data.get("address_status", "") or "")
                if addr_status in ("Moved from document address", "Renting a different address"):
                    break
                # Skip address comparison if OCR address is non-Latin (needs translation)
                if has_non_latin_chars(ocr_value):
                    break
                form_addr_parts = {
                    "address_line_1": form_data.get("address_line_1", ""),
                    "city": form_data.get("city", ""),
                }
                form_address = " ".join(p for p in form_addr_parts.values() if p)
                if address_matches(ocr_value, form_addr_parts):
                    matched_fields += 1
                else:
                    mismatches.append({
                        "field": "Address",
                        "form_value": form_address.strip(),
                        "doc_value": ocr_value
                    })
                break

    # Calculate match score
    if compared_fields > 0:
        match_score = int((matched_fields / compared_fields) * 100)
    else:
        match_score = 100  # No fields to compare, assume OK

    # Flag manual review if any mismatches found
    st.session_state.manual_review_required = len(mismatches) > 0

    return {
        "match_score": match_score,
        "mismatches": mismatches,
        "matched_fields": matched_fields,
        "compared_fields": compared_fields
    }


def analyze_document_image(file, document_type: str, country_code: str, side: str = "front") -> dict:
    """
    Analyze uploaded document using the vision API.
    
    Returns analysis results including quality assessment and OCR data.
    """
    try:
        # Convert file to base64
        file.seek(0)
        image_bytes = file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        file.seek(0)  # Reset for potential re-read
        
        # Try to call the backend API
        api_url = "http://localhost:8000/analyze"
        
        payload = {
            "image_base64": image_base64,
            "document_type": document_type,
            "country_code": country_code,
            "side": side
        }
        
        try:
            response = requests.post(api_url, json=payload, timeout=120)
        except requests.exceptions.Timeout:
            # Retry once on timeout
            response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            # Ensure extracted_data is accessible at the right path for comparison
            if "extracted_data" in result and "vision_result" not in result:
                result["vision_result"] = {"extracted_data": result["extracted_data"]}
            return result
        else:
            # Fallback to direct analysis if API not available
            return analyze_document_directly(image_base64, document_type, country_code, side)
            
    except requests.exceptions.ConnectionError:
        # API not running, try direct analysis
        return analyze_document_directly(image_base64, document_type, country_code, side)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "score": 0,
            "is_ready": False,
            "issues": [{"type": "error", "severity": "high", "title": "Analysis Failed", "description": str(e), "suggestion": "Please try again"}]
        }


def analyze_document_directly(image_base64: str, document_type: str, country_code: str, side: str = "front") -> dict:
    """
    Direct document analysis using Gemini Vision (when API is not running).
    """
    import traceback

    try:
        from backend.vision_analyzer import analyze_document, VisionAnalysisError
        from backend.issue_detector import IssueDetector

        # Run vision analysis - this calls Gemini API
        vision_result = analyze_document(image_base64, document_type, country_code, side)

        # Debug: Check if we got a valid response
        if not vision_result or vision_result.get("parse_error"):
            return {
                "success": False,
                "score": 0,
                "is_ready": False,
                "issues": [{
                    "type": "API_ERROR",
                    "severity": "high",
                    "title": "Vision API Response Error",
                    "description": "The AI could not properly analyze the document",
                    "suggestion": "Please try uploading a clearer image"
                }],
                "guidance": "Document analysis returned invalid response.",
                "severity_level": "high",
                "error": "Invalid API response"
            }
        
        # Detect issues based on vision result
        detector = IssueDetector()
        quality = vision_result.get("quality_assessment", {})
        issues_list = detector.detect_issues(
            vision_result=vision_result,
            image_quality=quality,
            country_code=country_code,
            document_type=document_type,
            document_side=side,
            sides_uploaded=[side]
        )
        
        # Convert issues to dict format for JSON serialization
        issues = []
        for issue in issues_list:
            # DetectedIssue uses issue_type not type, and has no title attribute
            issue_type_val = issue.issue_type.value if hasattr(issue.issue_type, 'value') else str(issue.issue_type)
            issues.append({
                "type": issue_type_val,
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                "title": issue_type_val.replace("_", " ").title(),  # Generate title from type
                "description": issue.description,
                "suggestion": issue.suggestion or "Please review and try again"
            })
        
        # Calculate score
        base_score = 100
        
        if quality.get("is_blurry"):
            base_score -= 25
        if quality.get("has_glare"):
            base_score -= 20
        if not quality.get("all_corners_visible"):
            base_score -= 15
        if quality.get("is_too_dark") or quality.get("is_too_bright"):
            base_score -= 15
        if not quality.get("is_readable"):
            base_score -= 30
        
        # Check if OCR extracted any real data
        extracted_data = vision_result.get("extracted_data", {})
        real_values = {k: v for k, v in extracted_data.items() if v and v != "null" and v is not None}
        if not real_values:
            # No readable data extracted - likely blank or template document
            base_score -= 40
            issues.append({
                "type": "NO_DATA_EXTRACTED",
                "severity": "high",
                "title": "No Personal Information Found",
                "description": "Could not extract any personal information from this document",
                "suggestion": "Please upload a document with your actual information visible"
            })

        # Compare extracted data with form data and adjust score
        data_match_result = compare_extracted_with_form(
            extracted_data,
            document_type=document_type,
            side=side,
            country_code=country_code
        )
        data_match_score = data_match_result.get("match_score", 100)
        data_mismatches = data_match_result.get("mismatches", [])

        # Add data mismatch issues
        if data_mismatches:
            base_score -= (100 - data_match_score) // 4  # Reduce score based on mismatch severity
            for mismatch in data_mismatches[:2]:  # Limit to 2 mismatch issues
                issues.append({
                    "type": "DATA_MISMATCH",
                    "severity": "medium",
                    "title": f"Data Mismatch: {mismatch['field']}",
                    "description": f"Form shows '{mismatch['form_value']}' but document shows '{mismatch['doc_value']}'",
                    "suggestion": "Please verify your form data matches your document"
                })

        score = max(0, base_score)

        return {
            "success": True,
            "score": score,
            "is_ready": score >= 70 and bool(real_values) and data_match_score >= 50,
            "issues": issues,
            "vision_result": vision_result,
            "extracted_data": extracted_data,
            "data_match_score": data_match_score,
            "data_mismatches": data_mismatches,
            "guidance": generate_guidance(vision_result, issues),
            "severity_level": "low" if score >= 80 else "medium" if score >= 60 else "high"
        }
        
    except Exception as e:
        # Get full traceback for debugging
        error_traceback = traceback.format_exc()
        print(f"Document analysis error: {error_traceback}")  # Log to console

        # Return error result if vision analysis fails - do NOT show high score
        return {
            "success": False,
            "score": 0,
            "is_ready": False,
            "issues": [{
                "type": "ANALYSIS_ERROR",
                "severity": "high",
                "title": "Analysis Failed",
                "description": f"Could not analyze document: {str(e)}",
                "suggestion": "Please ensure you have a valid API key configured and check the console for details"
            }],
            "guidance": f"Document analysis failed: {str(e)}",
            "severity_level": "high",
            "demo_mode": False,
            "error": str(e),
            "traceback": error_traceback  # Include for debugging
        }


def generate_guidance(vision_result: dict, issues: list) -> str:
    """Generate user-friendly guidance based on analysis."""
    if not issues:
        return "Your document looks great! All quality checks passed."
    
    quality = vision_result.get("quality_assessment", {})
    
    if quality.get("is_blurry"):
        return "The image appears blurry. Please retake the photo in good lighting and hold your camera steady."
    if quality.get("has_glare"):
        return "There's glare on the document. Try taking the photo at an angle to avoid reflections."
    if not quality.get("all_corners_visible"):
        return "Some corners of the document are cut off. Please include the entire document in the frame."
    if not quality.get("is_readable"):
        return "The text is not clearly readable. Please ensure good lighting and focus."
    
    return "Please review the issues listed and consider retaking the photo."


def render_analysis_result(analysis: dict, doc_key: str, allow_expander: bool = True, show_manual_review: bool = False):
    """Render the document analysis results in the UI."""
    if not analysis:
        return

    # Check for errors first
    if analysis.get("error") or not analysis.get("success", True):
        error_msg = analysis.get("error", "Unknown error")
        st.error(f" Document analysis failed: {error_msg}")
        st.caption("Please check your API key configuration or try again.")
        return

    score = analysis.get("score", 0)
    is_ready = analysis.get("is_ready", False)
    issues = analysis.get("issues", [])
    guidance_raw = analysis.get("guidance", "")
    data_match_score = analysis.get("data_match_score", None)

    # Sanitize guidance — strip any leaked JSON regardless of format
    import json as _json
    guidance = ""
    if isinstance(guidance_raw, dict):
        guidance = str(guidance_raw.get("guidance", guidance_raw.get("message", guidance_raw.get("text", ""))))
    elif isinstance(guidance_raw, str):
        text = guidance_raw.strip()
        # Check if text contains JSON anywhere (even partial)
        if "{" in text and ("main_issue" in text or "guidance" in text):
            # Try to extract JSON object from the text
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_end > json_start:
                try:
                    parsed = _json.loads(text[json_start:json_end])
                    guidance = str(parsed.get("guidance", parsed.get("main_issue", "")))
                except Exception:
                    guidance = ""
            else:
                guidance = ""
        elif text.startswith("{") or text.startswith('"'):
            guidance = ""  # Drop any JSON-like text
        else:
            guidance = text
    # Final safety — never display anything with curly braces
    if guidance and "{" in guidance:
        guidance = ""

    # Score indicator with color
    if score >= 80:
        score_color = "#28a745"
        score_icon = ICONS["check_circle"]
    elif score >= 60:
        score_color = "#ffc107"
        score_icon = ICONS["info"]
    else:
        score_color = "#dc3545"
        score_icon = ICONS["alert"]

    # Use Streamlit native layout to avoid raw HTML rendering
    status_text = "Ready for submission" if is_ready else "Needs improvement"
    # Simple score bar (lightweight visual)
    st.progress(min(max(score, 0), 100) / 100.0, text=f"Quality {score}/100")

    if data_match_score is not None:
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            st.metric("Quality Score", score)
        with col2:
            st.metric("Data Match", f"{data_match_score}%")
        with col3:
            st.write(f"**{status_text}**")
            if guidance:
                st.markdown(f'<p style="color:#8892a4;font-size:0.85rem;margin:4px 0 0;">{guidance}</p>', unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Quality Score", score)
        with col2:
            st.write(f"**{status_text}**")
            if guidance:
                st.markdown(f'<p style="color:#8892a4;font-size:0.85rem;margin:4px 0 0;">{guidance}</p>', unsafe_allow_html=True)
    
    # Manual review badge on document card
    if show_manual_review:
        st.markdown('''
            <div style="padding:6px 10px;background:#1f2937;border:1px solid #f59e0b;border-radius:8px;display:inline-block;margin:6px 0;">
                <span style="color:#f59e0b;font-weight:600;">Manual Review Required</span>
            </div>
        ''', unsafe_allow_html=True)

    # Show issues if any
    if issues:
        for issue in issues[:3]:  # Show max 3 issues
            severity = issue.get("severity", "medium")
            border_color = "#dc3545" if severity == "high" else "#ffc107" if severity == "medium" else "#17a2b8"
            text_color = "#721c24" if severity == "high" else "#856404" if severity == "medium" else "#0c5460"
            bg_color = "#f8d7da" if severity == "high" else "#fff3cd" if severity == "medium" else "#d1ecf1"
            st.markdown(f'''
                <div style="padding:8px 12px;border-left:3px solid {border_color};background:{bg_color};margin:4px 0;border-radius:0 4px 4px 0;">
                    <strong style="color:{text_color};">{issue.get("title", "Issue")}</strong>:
                    <span style="color:{text_color};">{issue.get("description", "")}</span>
                </div>
            ''', unsafe_allow_html=True)
    
    # Check for extracted data and compare with form data
    # Handle both API response (extracted_data at top) and direct analysis (vision_result.extracted_data)
    extracted_data = analysis.get("extracted_data", {})
    if not extracted_data:
        vision_result = analysis.get("vision_result", {})
        extracted_data = vision_result.get("extracted_data", {})
    
    # Debug: Show extracted data for troubleshooting (can be removed later)
    if extracted_data:
        # Check if extracted data has any real values (not all null)
        real_values = {k: v for k, v in extracted_data.items() if v and v != "null" and v is not None}
        
        if not real_values:
            # Document was analyzed but no readable data found
            st.markdown(f'''
                <div style="padding:12px;background:#fff5f5;border-left:4px solid #dc3545;border-radius:0 8px 8px 0;margin:8px 0;">
                    <div style="font-weight:600;color:#dc3545;margin-bottom:8px;">{ICONS['alert']} No Readable Data Found</div>
                    <div style="font-size:13px;color:#721c24;">
                        The document was scanned but no personal information could be extracted. 
                        This may indicate a blank template or poor image quality.
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            # Show what was extracted (for debugging/transparency)
            if allow_expander:
                with st.expander("OCR Extracted Data", expanded=False):
                    for field, value in real_values.items():
                        st.text(f"{field}: {value}")
            else:
                st.caption("OCR Extracted Data")
                for field, value in real_values.items():
                    st.text(f"{field}: {value}")
            
            mismatches = compare_with_form_data(extracted_data, doc_key)
            if mismatches:
                st.markdown(f'''
                    <div style="padding:12px;background:#fff3cd;border-left:4px solid #ffc107;border-radius:0 8px 8px 0;margin:8px 0;">
                        <div style="font-weight:600;color:#856404;margin-bottom:8px;">{ICONS['alert']} Data Mismatch Detected</div>
                        <div style="font-size:13px;color:#856404;">
                            The information in your document doesn't match what you entered in the form:
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                for mismatch in mismatches:
                    st.markdown(f'''
                        <div style="padding:8px 12px;background:#fff;border-left:3px solid #ffc107;margin:4px 0;border-radius:0 4px 4px 0;">
                            <strong>{mismatch['field']}</strong><br/>
                            <span style="color:#dc3545;">Form: {mismatch['form_value']}</span> vs
                            <span style="color:#28a745;">Document: {mismatch['doc_value']}</span>
                        </div>
                    ''', unsafe_allow_html=True)
                
                st.warning("Please verify your form data matches your document, or re-upload a correct document.")


def compare_with_form_data(extracted_data: dict, doc_key: str) -> list:
    """
    Compare OCR extracted data with form data and return mismatches.
    """
    from frontend.dynamic_form import get_all_form_data
    
    form_data = get_all_form_data("kyc")
    mismatches = []
    
    # Field mapping: OCR field -> form field(s)
    field_mappings = {
        "full_name": ["full_name", "first_name", "last_name"],
        "id_number": [
            "cnic_number",
            "aadhaar_number",
            "pan_number",
            "passport_number",
            "driving_license_number",
            "emirates_id_number",
            "id_number"
        ],
        "date_of_birth": ["date_of_birth", "dob"],
        "father_name": ["father_name", "fathers_name"],
        "gender": ["gender"],
        "address": [
            "address_line_1",
            "city",
            "province",
            "state",
            "postal_code",
            "postcode",
            "pin_code",
            "country",
            "country_of_residence"
        ]
    }

    doc_key_lower = str(doc_key).lower()
    is_back_side = doc_key_lower.endswith("_back")
    side = "back" if is_back_side else "front"
    document_type = "unknown"
    for tag in ["cnic", "emirates_id", "driving_license", "aadhaar", "passport", "utility_bill"]:
        if tag in doc_key_lower:
            document_type = tag
            break
    country_code = st.session_state.get("selected_country", "")

    for ocr_field, form_fields in field_mappings.items():
        expected_fields = get_expected_ocr_fields(document_type, side, country_code)
        if expected_fields and ocr_field not in expected_fields:
            continue
        ocr_value = extracted_data.get(ocr_field)
        
        if not ocr_value or ocr_value == "null" or ocr_value is None:
            continue
        
        # Clean OCR value
        ocr_value_clean = str(ocr_value).strip().lower()
        
        for form_field in form_fields:
            form_value = form_data.get(form_field)
            
            if not form_value:
                continue
            
            form_value_clean = str(form_value).strip().lower()
            
            # Handle name comparison (could be first+last vs full)
            if ocr_field == "full_name" and form_field in ["first_name", "last_name"]:
                first = form_data.get("first_name", "").strip().lower()
                last = form_data.get("last_name", "").strip().lower()
                full_form = f"{first} {last}".strip()
                
                if full_form and not names_match(ocr_value_clean, full_form):
                    mismatches.append({
                        "field": "Full Name",
                        "form_value": f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}".strip(),
                        "doc_value": ocr_value
                    })
                break  # Only compare once for name
            elif ocr_field == "full_name" and form_field == "full_name":
                if normalize_text(ocr_value) != normalize_text(form_value):
                    mismatches.append({
                        "field": "Full Name",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle ID number comparison
            elif ocr_field == "id_number":
                ocr_id_clean = ''.join(c for c in str(ocr_value) if c.isdigit())
                form_id_clean = ''.join(c for c in str(form_value) if c.isdigit())
                # Only compare if OCR looks like an actual ID number
                if len(ocr_id_clean) >= 6 and len(form_id_clean) >= 6 and ocr_id_clean != form_id_clean:
                    mismatches.append({
                        "field": "ID Number",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle date comparison
            elif ocr_field == "date_of_birth":
                if not dates_match(ocr_value, form_value):
                    mismatches.append({
                        "field": "Date of Birth",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle gender comparison (e.g., F vs Female)
            elif ocr_field == "gender":
                if normalize_gender(ocr_value) != normalize_gender(form_value):
                    mismatches.append({
                        "field": "Gender",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle father name comparison
            elif ocr_field == "father_name":
                if normalize_text(ocr_value) != normalize_text(form_value):
                    mismatches.append({
                        "field": "Father Name",
                        "form_value": str(form_value),
                        "doc_value": ocr_value
                    })
                break

            # Handle address comparison (combined current address)
            if ocr_field == "address":
                # Skip address comparison if user is renting/moved
                addr_status = str(form_data.get("address_status", "") or "")
                if addr_status in ("Moved from document address", "Renting a different address"):
                    break
                # Skip address comparison if OCR address is non-Latin (needs translation)
                if has_non_latin_chars(ocr_value):
                    break
                form_addr_parts = {
                    "address_line_1": form_data.get("address_line_1", ""),
                    "city": form_data.get("city", ""),
                }
                form_address = " ".join(p for p in form_addr_parts.values() if p)
                if not address_matches(ocr_value, form_addr_parts):
                    mismatches.append({
                        "field": "Address",
                        "form_value": form_address.strip(),
                        "doc_value": ocr_value
                    })
                break

    # Store mismatches in session state for review step
    st.session_state.data_mismatches = mismatches
    st.session_state.manual_review_required = len(mismatches) > 0
    
    return mismatches


def names_match(name1: str, name2: str) -> bool:
    """Check if two names match (fuzzy comparison)."""
    # Remove extra spaces and compare
    n1_parts = set(name1.lower().split())
    n2_parts = set(name2.lower().split())
    
    # Check if most parts match
    if not n1_parts or not n2_parts:
        return True  # Can't compare empty
    
    common = n1_parts.intersection(n2_parts)
    return len(common) >= min(len(n1_parts), len(n2_parts)) * 0.5


def normalize_gender(value: str) -> str:
    """Normalize gender values for comparison."""
    v = str(value).strip().lower()
    mapping = {
        "m": "male",
        "male": "male",
        "man": "male",
        "ذكر": "male",
        "f": "female",
        "female": "female",
        "woman": "female",
        "انثى": "female",
        "أنثى": "female",
        "other": "other",
        "o": "other",
        "x": "other",
        "non-binary": "other",
        "nonbinary": "other"
    }
    return mapping.get(v, v)

def normalize_text(value: str) -> str:
    """Normalize text for comparison (case-insensitive, strip punctuation)."""
    v = str(value).casefold().strip()
    return "".join(c for c in v if c.isalnum() or c.isspace()).replace(" ", "")

def has_non_latin_chars(value: str) -> bool:
    """Detect non-Latin characters (e.g., Urdu/Arabic) for address comparison."""
    return any(ord(c) > 127 for c in str(value))


def address_matches(ocr_address: str, form_parts: dict) -> bool:
    """
    Smart address comparison — checks if key parts of the form address
    appear in the OCR-extracted address. OCR often adds extra text like
    country name, province, or postal code that the user didn't enter.

    Returns True if enough key parts match.
    """
    ocr_norm = normalize_text(ocr_address)
    if not ocr_norm:
        return True  # Can't compare empty OCR

    # Collect significant form address tokens (street, city, postal)
    significant_parts = []
    for key in ("address_line_1", "city"):
        val = form_parts.get(key, "")
        if val:
            # Split address_line_1 into tokens for partial matching
            tokens = normalize_text(val).split() if key == "address_line_1" else [normalize_text(val)]
            # Only keep tokens with 3+ chars (skip "st", "no", etc.)
            significant_parts.extend(t for t in tokens if len(t) >= 3)

    if not significant_parts:
        return True  # No form data to compare

    # Count how many significant parts appear in the OCR text
    hits = sum(1 for part in significant_parts if part in ocr_norm)
    ratio = hits / len(significant_parts) if significant_parts else 1.0

    # At least 50% of key parts must match
    return ratio >= 0.5


def dates_match(date1: str, date2: str) -> bool:
    """Check if two dates match (handles different formats)."""
    from datetime import datetime
    
    # Try to parse both dates
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
    
    d1 = None
    d2 = None
    
    for fmt in formats:
        if d1 is None:
            try:
                d1 = datetime.strptime(str(date1), fmt)
            except:
                pass
        if d2 is None:
            try:
                d2 = datetime.strptime(str(date2), fmt)
            except:
                pass
    
    if d1 and d2:
        return d1.date() == d2.date()
    
    # Fallback: compare cleaned strings
    clean1 = ''.join(c for c in str(date1) if c.isdigit())
    clean2 = ''.join(c for c in str(date2) if c.isdigit())
    
    return clean1 == clean2 if clean1 and clean2 else True


# =============================================================================
# STEP INDICATOR
# =============================================================================

def render_step_indicator(current_step: int, total_steps: int = 4):
    """Render visual step indicator with professional styling."""
    step_names = ["Country", "Personal Info", "Documents", "Review"]
    step_icons = [ICONS["globe"], ICONS["user"], ICONS["file"], ICONS["check"]]
    
    # Create step indicator HTML
    steps_html = '<div style="display:flex;justify-content:center;align-items:center;gap:8px;margin:20px 0;">'
    
    for i, (name, icon) in enumerate(zip(step_names, step_icons), 1):
        if i < current_step:
            # Completed step
            steps_html += f'''
            <div style="text-align:center;">
                <span class="step-pill step-pill-complete">{ICONS["check"]}</span>
                <div style="font-size:12px;color:#28a745;margin-top:4px;font-weight:500;">{name}</div>
            </div>
            '''
        elif i == current_step:
            # Active step
            steps_html += f'''
            <div style="text-align:center;">
                <span class="step-pill step-pill-active">{i}</span>
                <div style="font-size:12px;color:#ff444f;margin-top:4px;font-weight:600;">{name}</div>
            </div>
            '''
        else:
            # Pending step
            steps_html += f'''
            <div style="text-align:center;">
                <span class="step-pill step-pill-pending">{i}</span>
                <div style="font-size:12px;color:#6c757d;margin-top:4px;">{name}</div>
            </div>
            '''
        
        # Add connector line between steps (except after last)
        if i < total_steps:
            color = "#28a745" if i < current_step else "#e9ecef"
            steps_html += f'<div style="width:40px;height:2px;background:{color};margin:0 4px;"></div>'
    
    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)
    st.markdown("---")


# =============================================================================
# STEP 1: COUNTRY SELECTION
# =============================================================================

def render_step_country():
    """Render country selection step."""
    scroll_to_top()
    st.markdown(f'''<div class="section-header">{ICONS['globe']} Select Your Country of Residence</div>''', unsafe_allow_html=True)
    st.caption("Your KYC requirements depend on your country. Please select carefully.")

    countries = get_supported_countries()

    if not countries:
        st.error("No countries available. Please check configuration.")
        return

    # Create columns for country cards
    cols = st.columns(len(countries))

    for col, country in zip(cols, countries):
        with col:
            is_selected = st.session_state.selected_country == country['code']

            # Country card button
            button_style = "primary" if is_selected else "secondary"
            if st.button(
                f"{country['flag']}\n{country['name']}",
                key=f"country_{country['code']}",
                type=button_style,
                use_container_width=True
            ):
                # Only clear if country actually changed
                if st.session_state.selected_country != country['code']:
                    st.session_state.selected_country = country['code']
                    # Clear form when country changes
                    clear_form_state("kyc")
                    # Also clear document analysis when country changes
                    st.session_state.documents_uploaded = {}
                    st.session_state.document_analysis = {}
                    st.session_state.document_signatures = {}
                    st.session_state.file_uploader_cleared = {}
                    # Pre-populate nationality and country fields
                    schema = get_country_schema(country['code'])
                    if schema:
                        from frontend.dynamic_form import set_form_value, init_form_state
                        init_form_state("kyc")  # Re-initialize after clearing
                        set_form_value("nationality", schema.default_nationality, "kyc")
                        set_form_value("country", schema.country_name, "kyc")
                        set_form_value("country_of_residence", schema.country_name, "kyc")
                        # Also set widget keys directly for immediate display
                        st.session_state["kyc_nationality"] = schema.default_nationality
                        st.session_state["kyc_country_of_residence"] = schema.country_name
                st.rerun()

    st.markdown("---")

    # Show selected country info
    if st.session_state.selected_country:
        schema = get_country_schema(st.session_state.selected_country)
        if schema:
            st.markdown(f'''<div class="success-card">
                <div style="display:flex;align-items:center;gap:8px;">
                    {ICONS['check_circle']} <strong>Selected:</strong> {schema.flag} {schema.country_name}
                </div>
            </div>''', unsafe_allow_html=True)

            # Show requirements summary
            with st.expander("What you'll need", expanded=True):
                st.markdown(f'''<div class="section-header">{ICONS['file']} Required Documents</div>''', unsafe_allow_html=True)
                for doc_req in schema.document_requirements.values():
                    for doc in doc_req.documents:
                        sides = "front and back" if doc.requires_back else "front only"
                        st.markdown(f"- {doc.name} ({sides})")

                st.markdown(f'''<div class="section-header" style="margin-top:16px;">{ICONS['clipboard']} Required Information</div>''', unsafe_allow_html=True)
                required_count = len(schema.get_all_required_fields())
                st.markdown(f"- {required_count} form fields to complete")

                if schema.compliance_checks.fatca:
                    st.markdown("- FATCA declaration required")

            # Continue button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Continue", type="primary", use_container_width=True):
                    st.session_state.onboarding_step = 2
                    scroll_to_top()
                    st.rerun()
    else:
        st.markdown(f'''<div class="info-card">
            <div style="display:flex;align-items:center;gap:8px;">
                {ICONS['info']} Please select your country above to continue
            </div>
        </div>''', unsafe_allow_html=True)
# =============================================================================
# STEP 2: PERSONAL INFORMATION FORM
# =============================================================================

def render_step_form():
    """Render the personal information form."""
    scroll_to_top()
    country_code = st.session_state.selected_country
    schema = get_country_schema(country_code)
    
    if not schema:
        st.error("Country schema not found")
        return
    
    st.markdown(f'''<div class="section-header">{ICONS['user']} Personal Information - {schema.flag} {schema.country_name}</div>''', unsafe_allow_html=True)
    st.caption("Please fill in all required fields (*) accurately")
    
    # Render form
    result = render_kyc_form(
        country_code,
        prefix="kyc",
        show_progress=True
    )

    # Address status hint (moved/renting)
    from frontend.dynamic_form import get_form_value
    address_status = get_form_value("address_status", "kyc")
    if address_status in ["Moved from document address", "Renting a different address"]:
        st.info("You indicated a different current address. Please ensure your proof of address reflects your current residence.")
        st.checkbox(
            "Proof of address uploaded (utility bill / tenancy contract / bank statement)",
            key="address_proof_uploaded"
        )
    
    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.onboarding_step = 1
            scroll_to_top()
            st.rerun()
    
    with col3:
        if result["is_valid"]:
            if st.button("Continue", type="primary", use_container_width=True):
                st.session_state.form_completed = True
                st.session_state.onboarding_step = 3
                scroll_to_top()
                st.rerun()
        else:
            st.button("Continue", disabled=True, use_container_width=True)
            st.caption("Complete all required fields to continue")


# =============================================================================
# STEP 3: DOCUMENT UPLOAD
# =============================================================================

def render_step_documents():
    """Render document upload step."""
    scroll_to_top()
    country_code = st.session_state.selected_country
    schema = get_country_schema(country_code)
    
    if not schema:
        st.error("Country schema not found")
        return
    
    st.markdown(f'''<div class="section-header">{ICONS['upload']} Document Upload - {schema.flag} {schema.country_name}</div>''', unsafe_allow_html=True)
    st.caption("Upload clear photos of your documents for verification")

    # Note: analysis is run inline per document to keep UI aligned with the image preview
    
    all_docs_uploaded = True
    seen_labels = set()
    seen_label_normalized = set()
    seen_req_keys = set()
    
    for req_key, doc_req in schema.document_requirements.items():
        normalized_key = str(req_key).strip().lower()
        if normalized_key in seen_req_keys:
            continue
        seen_req_keys.add(normalized_key)
        # Avoid duplicate rendering if labels repeat due to state/reruns
        normalized_label = "".join(str(doc_req.label).split()).lower()
        if doc_req.label in seen_labels or normalized_label in seen_label_normalized:
            continue
        seen_labels.add(doc_req.label)
        seen_label_normalized.add(normalized_label)
        with st.expander(f"{doc_req.label} ({req_key})", expanded=True):
            
            # Handle one_of requirements (like UK passport OR driving license)
            if doc_req.one_of and len(doc_req.documents) > 1:
                st.info("Upload ONE of the following documents:")
                doc_options = [d.name for d in doc_req.documents]
                selected_doc = st.radio(
                    "Select document type:",
                    doc_options,
                    key=f"doc_select_{req_key}",
                    horizontal=True
                )
                
                # Find selected document spec
                selected_spec = next(
                    (d for d in doc_req.documents if d.name == selected_doc),
                    doc_req.documents[0]
                )
                docs_to_upload = [selected_spec]
            else:
                docs_to_upload = doc_req.documents
            
            for doc in docs_to_upload:
                st.markdown(f"**{doc.name}**")
                
                # Show tips as a collapsible help section (using caption to avoid nested expander)
                if doc.tips:
                    tips_text = " • ".join(doc.tips)
                    st.caption(f"Tips: {tips_text}")
                
                # Upload front
                front_key = f"{req_key}_{doc.type}_front"
                front_file = st.file_uploader(
                    f"Upload {doc.name} (Front)",
                    type=doc.accepted_formats,
                    key=front_key,
                    help=f"Accepted formats: {', '.join(doc.accepted_formats)}",
                    on_change=mark_file_uploader_change,
                    args=(front_key,)
                )
                explicit_clear = st.session_state.file_uploader_cleared.get(front_key, False)
                stored_front = st.session_state.documents_uploaded.get(front_key)
                # Persist file across steps only if user did not clear it
                if not explicit_clear and front_file is None and stored_front is not None:
                    front_file = stored_front

                if front_file:
                    current_sig = get_file_signature(front_file)
                    previous_sig = st.session_state.document_signatures.get(front_key)
                    if current_sig and current_sig != previous_sig:
                        analysis_key = f"{front_key}_analysis"
                        if analysis_key in st.session_state.document_analysis:
                            del st.session_state.document_analysis[analysis_key]
                        st.session_state.document_signatures[front_key] = current_sig
                    elif previous_sig is None and current_sig:
                        st.session_state.document_signatures[front_key] = current_sig
                    st.session_state.documents_uploaded[front_key] = front_file
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(front_file, caption="Front", use_column_width=True)
                    with col2:
                        # Run analysis if not already done for this file
                        analysis_key = f"{front_key}_analysis"
                        # Check if we need to run analysis (not cached or previous analysis failed)
                        cached_analysis = st.session_state.document_analysis.get(analysis_key)
                        needs_analysis = (
                            cached_analysis is None or
                            cached_analysis.get("error") or
                            not cached_analysis.get("success", True)
                        )

                        if needs_analysis:
                            with st.spinner("Analyzing document with AI..."):
                                analysis = analyze_document_image(
                                    front_file,
                                    document_type=doc.type,
                                    country_code=country_code,
                                    side="front"
                                )
                                st.session_state.document_analysis[analysis_key] = analysis
                                pass  # Analysis stored in session state

                        # Show analysis result
                        analysis = st.session_state.document_analysis.get(analysis_key, {})
                        show_manual = bool(analysis.get("data_mismatches")) or bool(analysis.get("mismatches"))
                        render_analysis_result(analysis, front_key, allow_expander=False, show_manual_review=show_manual)

                        # Reanalyze button
                        if st.button("Re-analyze", key=f"reanalyze_{front_key}", type="secondary"):
                            # Clear cached analysis first
                            if analysis_key in st.session_state.document_analysis:
                                del st.session_state.document_analysis[analysis_key]
                            with st.spinner("Re-analyzing document..."):
                                analysis = analyze_document_image(
                                    front_file,
                                    document_type=doc.type,
                                    country_code=country_code,
                                    side="front"
                                )
                                st.session_state.document_analysis[analysis_key] = analysis
                                st.rerun()
                else:
                    all_docs_uploaded = False
                    # If user explicitly cleared the file, remove cached analysis + upload state
                    if explicit_clear:
                        if front_key in st.session_state.documents_uploaded:
                            del st.session_state.documents_uploaded[front_key]
                        analysis_key = f"{front_key}_analysis"
                        if analysis_key in st.session_state.document_analysis:
                            del st.session_state.document_analysis[analysis_key]
                        if front_key in st.session_state.document_signatures:
                            del st.session_state.document_signatures[front_key]
                        st.session_state.file_uploader_cleared[front_key] = False
                
                # Upload back if required
                if doc.requires_back:
                    back_key = f"{req_key}_{doc.type}_back"
                    back_file = st.file_uploader(
                        f"Upload {doc.name} (Back)",
                        type=doc.accepted_formats,
                        key=back_key,
                        on_change=mark_file_uploader_change,
                        args=(back_key,)
                    )
                    explicit_clear = st.session_state.file_uploader_cleared.get(back_key, False)
                    stored_back = st.session_state.documents_uploaded.get(back_key)
                    # Persist file across steps only if user did not clear it
                    if not explicit_clear and back_file is None and stored_back is not None:
                        back_file = stored_back

                    if back_file:
                        current_sig = get_file_signature(back_file)
                        previous_sig = st.session_state.document_signatures.get(back_key)
                        if current_sig and current_sig != previous_sig:
                            analysis_key = f"{back_key}_analysis"
                            if analysis_key in st.session_state.document_analysis:
                                del st.session_state.document_analysis[analysis_key]
                            st.session_state.document_signatures[back_key] = current_sig
                        elif previous_sig is None and current_sig:
                            st.session_state.document_signatures[back_key] = current_sig
                        st.session_state.documents_uploaded[back_key] = back_file
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.image(back_file, caption="Back", use_column_width=True)
                        with col2:
                            # Run analysis for back
                            analysis_key = f"{back_key}_analysis"
                            # Check if we need to run analysis
                            cached_analysis = st.session_state.document_analysis.get(analysis_key)
                            needs_analysis = (
                                cached_analysis is None or
                                cached_analysis.get("error") or
                                not cached_analysis.get("success", True)
                            )

                            if needs_analysis:
                                with st.spinner("Analyzing document with AI..."):
                                    analysis = analyze_document_image(
                                        back_file,
                                        document_type=doc.type,
                                        country_code=country_code,
                                        side="back"
                                    )
                                    st.session_state.document_analysis[analysis_key] = analysis

                            # Show analysis result
                            analysis = st.session_state.document_analysis.get(analysis_key, {})
                            show_manual = bool(analysis.get("data_mismatches")) or bool(analysis.get("mismatches"))
                            render_analysis_result(analysis, back_key, allow_expander=False, show_manual_review=show_manual)

                            # Reanalyze button
                            if st.button("Re-analyze", key=f"reanalyze_{back_key}", type="secondary"):
                                if analysis_key in st.session_state.document_analysis:
                                    del st.session_state.document_analysis[analysis_key]
                                with st.spinner("Re-analyzing document..."):
                                    analysis = analyze_document_image(
                                        back_file,
                                        document_type=doc.type,
                                        country_code=country_code,
                                        side="back"
                                    )
                                    st.session_state.document_analysis[analysis_key] = analysis
                                    st.rerun()
                    else:
                        all_docs_uploaded = False
                        # If user explicitly cleared the file, remove cached analysis + upload state
                        if explicit_clear:
                            if back_key in st.session_state.documents_uploaded:
                                del st.session_state.documents_uploaded[back_key]
                            analysis_key = f"{back_key}_analysis"
                            if analysis_key in st.session_state.document_analysis:
                                del st.session_state.document_analysis[analysis_key]
                            if back_key in st.session_state.document_signatures:
                                del st.session_state.document_signatures[back_key]
                            st.session_state.file_uploader_cleared[back_key] = False
                
                st.markdown("---")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.onboarding_step = 2
            scroll_to_top()
            st.rerun()
    
    with col3:
        if all_docs_uploaded:
            if st.button("Review & Submit", type="primary", use_container_width=True):
                st.session_state.onboarding_step = 4
                scroll_to_top()
                st.rerun()
        else:
            st.button("Review & Submit", disabled=True, use_container_width=True)
            st.caption("Upload all required documents to continue")


# =============================================================================
# STEP 4: REVIEW & SUBMIT
# =============================================================================

def render_step_review():
    """Render review and submit step."""
    scroll_to_top()
    country_code = st.session_state.selected_country
    schema = get_country_schema(country_code)
    form_data = get_all_form_data("kyc")
    
    if not schema:
        st.error("Country schema not found")
        return
    
    st.markdown(f'''<div class="section-header">{ICONS['check_circle']} Review Your Application - {schema.flag} {schema.country_name}</div>''', unsafe_allow_html=True)
    st.caption("Please review your information before submitting")

    # ── Gather ALL issues & mismatches from every document analysis ──
    all_mismatches = list(st.session_state.data_mismatches or [])
    all_issues = []
    has_unresolved_issues = False

    for key, analysis in st.session_state.document_analysis.items():
        if not isinstance(analysis, dict):
            continue
        # Collect mismatches from each analysis result
        doc_mismatches = analysis.get("data_mismatches", [])
        for mm in doc_mismatches:
            if mm not in all_mismatches:
                all_mismatches.append(mm)
        # Collect blocking issues
        for issue in analysis.get("issues", []):
            if issue.get("severity") == "high":
                has_unresolved_issues = True
                all_issues.append(issue)
        # Low quality score
        if analysis.get("score", 100) < 50:
            has_unresolved_issues = True

    needs_manual_review = st.session_state.manual_review_required or bool(all_mismatches) or has_unresolved_issues

    # ── Show warnings ──
    if needs_manual_review:
        st.markdown(f'''
            <div style="padding:14px 18px;background:#1f1510;border:1px solid #f59e0b;border-radius:10px;margin:12px 0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    {ICONS['alert']} <strong style="color:#f59e0b;">Manual Review Required</strong>
                </div>
                <p style="color:#d4a054;margin:0;font-size:0.9rem;">
                    Your application will be sent for manual verification by the compliance team.
                    This may add 1-2 business days to the review time.
                </p>
            </div>
        ''', unsafe_allow_html=True)

    if all_mismatches:
        st.markdown(f'''
            <div style="padding:14px 18px;background:#1a1020;border:1px solid #ff4d6a;border-radius:10px;margin:12px 0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    {ICONS['alert']} <strong style="color:#ff4d6a;">Data Mismatches Detected ({len(all_mismatches)})</strong>
                </div>
                <p style="color:#cc8899;margin:0 0 8px;font-size:0.88rem;">
                    The following information in your documents doesn't match your form entries.
                    Go back to fix them, or submit for manual review.
                </p>
            </div>
        ''', unsafe_allow_html=True)

        for mismatch in all_mismatches:
            field = mismatch.get("field", "?")
            form_val = mismatch.get("form_value", mismatch.get("form", "?"))
            doc_val = mismatch.get("doc_value", mismatch.get("document", "?"))
            st.markdown(f'''
                <div style="padding:10px 14px;background:#141928;border-left:3px solid #ff4d6a;margin:4px 0;border-radius:0 6px 6px 0;">
                    <strong style="color:#e0e4eb;">{field}</strong><br/>
                    <span style="color:#ff4d6a;">Form: {form_val}</span>
                    <span style="color:#6c757d;margin:0 6px;">vs</span>
                    <span style="color:#00d084;">Document: {doc_val}</span>
                </div>
            ''', unsafe_allow_html=True)
        st.markdown("")

    if has_unresolved_issues:
        st.markdown(f'''
            <div style="padding:14px 18px;background:#1a1020;border:1px solid #ffb347;border-radius:10px;margin:12px 0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    {ICONS['alert']} <strong style="color:#ffb347;">Document Quality Issues</strong>
                </div>
                <p style="color:#d4a054;margin:0;font-size:0.88rem;">
                    Some documents have quality issues that may delay verification. Consider going back to re-upload clearer images.
                </p>
            </div>
        ''', unsafe_allow_html=True)
        for issue in all_issues[:3]:
            st.markdown(f'''
                <div style="padding:8px 14px;background:#141928;border-left:3px solid #ffb347;margin:4px 0;border-radius:0 6px 6px 0;">
                    <strong style="color:#ffb347;">{issue.get("title", "Issue")}</strong>:
                    <span style="color:#d0d5de;">{issue.get("description", "")}</span>
                </div>
            ''', unsafe_allow_html=True)
        st.markdown("")
    
    # Show summary
    render_form_summary(country_code, form_data, "kyc")
    
    # Documents summary
    st.markdown(f'''<div class="section-header" style="margin-top:24px;">{ICONS['file']} Uploaded Documents</div>''', unsafe_allow_html=True)
    for key, file in st.session_state.documents_uploaded.items():
        st.markdown(f"• {key}: {file.name}")
    
    st.markdown("---")
    
    # Final declarations
    st.markdown(f'''<div class="section-header">{ICONS['clipboard']} Final Declarations</div>''', unsafe_allow_html=True)
    
    declaration_1 = st.checkbox(
        "I confirm that all information provided is accurate and complete",
        key="declaration_1"
    )
    
    declaration_2 = st.checkbox(
        "I understand that providing false information may result in account termination",
        key="declaration_2"
    )
    
    declaration_3 = st.checkbox(
        "I consent to the processing of my personal data for verification purposes",
        key="declaration_3"
    )
    
    all_declared = declaration_1 and declaration_2 and declaration_3

    # Address proof requirement if moved/renting
    from frontend.dynamic_form import get_form_value
    address_status = get_form_value("address_status", "kyc")
    address_proof_required = address_status in ["Moved from document address", "Renting a different address"]
    address_proof_ok = True
    if address_proof_required:
        address_proof_ok = bool(st.session_state.get("address_proof_uploaded"))
        if not address_proof_ok:
            st.warning("Proof of address is required because your current address differs from your document address.")
    
    st.markdown("---")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.onboarding_step = 3
            scroll_to_top()
            st.rerun()
    
    with col3:
        if all_declared and address_proof_ok:
            if st.button("Submit Application", type="primary", use_container_width=True):
                submit_application(schema, form_data)
        else:
            st.button("Submit Application", disabled=True, use_container_width=True)
            if not all_declared:
                st.caption("Please accept all declarations to submit")
            elif not address_proof_ok:
                st.caption("Please confirm proof of address to submit")


def submit_application(schema: CountryKYCSchema, form_data: dict):
    """Simulate application submission."""
    with st.spinner("Submitting your application..."):
        # Simulate API call
        time.sleep(2)
        
        # Create submission result
        st.session_state.submission_result = {
            "success": True,
            "reference_id": f"KYC-{schema.country_code}-{int(time.time())}",
            "status": "pending_review",
            "estimated_time": "24-48 hours",
            "country": schema.country_name
        }
        
        st.session_state.onboarding_step = 5
        st.rerun()


# =============================================================================
# STEP 5: CONFIRMATION
# =============================================================================

def render_step_confirmation():
    """Render submission confirmation."""
    result = st.session_state.submission_result
    
    if not result:
        st.session_state.onboarding_step = 1
        st.rerun()
        return
    
    # Tiny round confetti dots falling animation
    st.markdown("""
    <style>
    @keyframes confetti-fall {
        0% { transform: translateY(-10px) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(360deg); opacity: 0; }
    }
    .confetti-container {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none; overflow: hidden; z-index: 9999;
    }
    .confetti-dot {
        position: absolute; top: -10px; border-radius: 50%;
        animation: confetti-fall linear forwards;
    }
    </style>
    <div class="confetti-container">""" + "".join([
        f'<div class="confetti-dot" style="left:{i*4.3:.0f}%; width:{s}px; height:{s}px; '
        f'background:{c}; animation-duration:{d}s; animation-delay:{dl}s;"></div>'
        for i, (s, c, d, dl) in enumerate([
            (5, "#ff444f", 3.0, 0.0), (4, "#00d084", 3.5, 0.2), (6, "#4da6ff", 2.8, 0.4),
            (3, "#ffb347", 3.2, 0.1), (5, "#ff444f", 3.6, 0.5), (4, "#00d084", 2.9, 0.3),
            (6, "#ffd700", 3.1, 0.6), (3, "#4da6ff", 3.4, 0.15), (5, "#ffb347", 2.7, 0.45),
            (4, "#ff444f", 3.3, 0.25), (6, "#00d084", 3.0, 0.55), (3, "#ffd700", 3.7, 0.35),
            (5, "#4da6ff", 2.9, 0.1), (4, "#ff444f", 3.2, 0.7), (6, "#ffb347", 3.5, 0.05),
            (3, "#00d084", 2.8, 0.6), (5, "#ffd700", 3.4, 0.3), (4, "#4da6ff", 3.1, 0.5),
            (6, "#ff444f", 2.6, 0.2), (3, "#00d084", 3.3, 0.4), (5, "#ffb347", 3.0, 0.15),
            (4, "#ffd700", 3.6, 0.55), (6, "#4da6ff", 2.7, 0.35), (3, "#ff444f", 3.2, 0.65),
        ])
    ]) + "</div>", unsafe_allow_html=True)

    st.markdown(f'''<div style="text-align:center;padding:40px 0;">
        <div style="margin-bottom:16px;">{ICONS['check_circle'].replace('width="20" height="20"', 'width="64" height="64"')}</div>
        <h1 style="color:#28a745;margin:0;">Application Submitted!</h1>
    </div>''', unsafe_allow_html=True)
    
    st.markdown(f'''
    <div class="success-card">
        <h3 style="color:#155724;margin:0 0 12px 0;">Thank you for completing your KYC verification!</h3>
        <p style="color:#155724;margin:4px 0;"><strong>Reference ID:</strong> {result['reference_id']}</p>
        <p style="color:#155724;margin:4px 0;"><strong>Status:</strong> {result['status'].replace('_', ' ').title()}</p>
        <p style="color:#155724;margin:4px 0;"><strong>Estimated Review Time:</strong> {result['estimated_time']}</p>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("### What happens next")
    st.markdown("""
    1. You'll receive a confirmation email shortly
    2. Our team will review your documents
    3. You'll be notified once verification is complete
    4. Start trading on Deriv!
    """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start New Application", use_container_width=True):
            # Reset everything
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application entry point."""
    init_onboarding_state()

    # ── Sidebar Navigation ──
    ADMIN_PASSWORD = "deriv2026"  # Change for production

    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0 20px;">
            {ICONS['shield']}
            <h3 style="margin:8px 0 0;color:#ff444f;">KYC Agent</h3>
            <p style="color:#888;font-size:0.8rem;margin:2px 0 0;">Powered by Deriv AI</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Admin Access ──
        st.markdown("---")
        if not st.session_state.get("admin_authenticated", False):
            with st.expander("Admin Access"):
                pwd = st.text_input("Password", type="password", key="admin_pwd")
                if st.button("Login", key="admin_login_btn"):
                    if pwd == ADMIN_PASSWORD:
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else:
                        st.error("Incorrect password")
        else:
            page = st.radio(
                "Navigation",
                ["Client KYC Portal", "Compliance Dashboard"],
                key="nav_page",
                label_visibility="collapsed",
            )
            st.markdown("---")
            from backend.deriv_api import get_submission_manager
            _mgr = get_submission_manager()
            _stats = _mgr.get_analytics()
            st.markdown("**Session Stats**")
            st.caption(f"Submissions: {_stats.get('total', 0)}")
            st.caption(f"Pending Review: {_stats.get('pending_review', 0)}")
            st.caption(f"High Risk: {_stats.get('high_risk_count', 0)}")
            st.markdown("---")
            if st.button("Logout", key="admin_logout_btn"):
                st.session_state.admin_authenticated = False
                st.rerun()

    # ── Compliance Dashboard View (admin only) ──
    if st.session_state.get("admin_authenticated") and st.session_state.get("nav_page") == "Compliance Dashboard":
        from frontend.compliance_dashboard import render_compliance_dashboard
        from backend.deriv_api import get_submission_manager
        render_compliance_dashboard(get_submission_manager())
        return

    # ── Client KYC Portal View (default) ──

    # Auto-scroll to top when navigating between steps
    if "prev_onboarding_step" not in st.session_state:
        st.session_state.prev_onboarding_step = st.session_state.onboarding_step
    elif st.session_state.prev_onboarding_step != st.session_state.onboarding_step:
        scroll_to_top()
        st.session_state.prev_onboarding_step = st.session_state.onboarding_step

    # Header with professional icon
    st.markdown(f'''
    <div class="kyc-header">
        <h1>{ICONS['shield']} KYC Verification</h1>
        <p style="color: #6c757d;">Secure identity verification for Deriv</p>
    </div>
    ''', unsafe_allow_html=True)

    # Render step indicator (except for confirmation)
    if st.session_state.onboarding_step < 5:
        render_step_indicator(st.session_state.onboarding_step)

    # Render current step
    if st.session_state.onboarding_step == 1:
        render_step_country()
    elif st.session_state.onboarding_step == 2:
        render_step_form()
    elif st.session_state.onboarding_step == 3:
        render_step_documents()
    elif st.session_state.onboarding_step == 4:
        render_step_review()
    elif st.session_state.onboarding_step == 5:
        render_step_confirmation()

    # Footer
    st.markdown("---")
    st.caption("Your data is encrypted and secure | Powered by Deriv AI")


if __name__ == "__main__":
    main()
