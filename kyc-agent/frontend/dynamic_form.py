"""
Dynamic Form Renderer for Country-Aware KYC Forms

Provides Streamlit components that:
- Dynamically render forms based on country schema
- Handle field-level validation in real-time
- Apply conditional logic (show/hide fields)
- Support multiple field types with proper formatting
- Track form state and validation errors
"""

import streamlit as st
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Callable
import re
import sys
from pathlib import Path

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.kyc_schema_loader import (
    KYCSchemaLoader,
    CountryKYCSchema,
    FormField,
    FormCategory,
    FieldType,
    FieldValidator,
    FormDataValidator,
    get_country_schema,
    get_supported_countries
)


# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================

def init_form_state(prefix: str = "kyc") -> None:
    """Initialize form state in session."""
    if f"{prefix}_form_data" not in st.session_state:
        st.session_state[f"{prefix}_form_data"] = {}
    if f"{prefix}_errors" not in st.session_state:
        st.session_state[f"{prefix}_errors"] = {}
    if f"{prefix}_touched" not in st.session_state:
        st.session_state[f"{prefix}_touched"] = set()
    if f"{prefix}__schema_country" not in st.session_state:
        st.session_state[f"{prefix}__schema_country"] = None


def get_form_value(field_id: str, prefix: str = "kyc") -> Any:
    """Get current value of a form field."""
    return st.session_state.get(f"{prefix}_form_data", {}).get(field_id)


def set_form_value(field_id: str, value: Any, prefix: str = "kyc") -> None:
    """Set value of a form field."""
    if f"{prefix}_form_data" not in st.session_state:
        st.session_state[f"{prefix}_form_data"] = {}
    st.session_state[f"{prefix}_form_data"][field_id] = value


def get_form_error(field_id: str, prefix: str = "kyc") -> Optional[str]:
    """Get error message for a field."""
    return st.session_state.get(f"{prefix}_errors", {}).get(field_id)


def set_form_error(field_id: str, error: Optional[str], prefix: str = "kyc") -> None:
    """Set error message for a field."""
    if f"{prefix}_errors" not in st.session_state:
        st.session_state[f"{prefix}_errors"] = {}
    if error:
        st.session_state[f"{prefix}_errors"][field_id] = error
    elif field_id in st.session_state[f"{prefix}_errors"]:
        del st.session_state[f"{prefix}_errors"][field_id]


def mark_touched(field_id: str, prefix: str = "kyc") -> None:
    """Mark a field as touched (user has interacted)."""
    if f"{prefix}_touched" not in st.session_state:
        st.session_state[f"{prefix}_touched"] = set()
    st.session_state[f"{prefix}_touched"].add(field_id)


def is_touched(field_id: str, prefix: str = "kyc") -> bool:
    """Check if field has been touched."""
    return field_id in st.session_state.get(f"{prefix}_touched", set())


def clear_form_state(prefix: str = "kyc") -> None:
    """Clear all form state including widget keys."""
    keys_to_clear = [
        f"{prefix}_form_data",
        f"{prefix}_errors",
        f"{prefix}_touched",
        f"{prefix}__schema_country"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Also clear widget keys that start with the prefix
    widget_keys_to_clear = [k for k in st.session_state.keys() if k.startswith(f"{prefix}_") and k not in keys_to_clear]
    for key in widget_keys_to_clear:
        del st.session_state[key]


def get_all_form_data(prefix: str = "kyc") -> Dict[str, Any]:
    """Get all form data."""
    return st.session_state.get(f"{prefix}_form_data", {})


def sync_form_data_to_widgets(prefix: str = "kyc") -> None:
    """
    Sync form data to widget keys to ensure data persists across navigation.
    Call this before rendering the form to restore any previously entered data.
    """
    form_data = st.session_state.get(f"{prefix}_form_data", {})
    for field_id, value in form_data.items():
        widget_key = f"{prefix}_{field_id}"
        # Always sync form data to widget keys if widget key doesn't exist
        # This ensures data persistence when navigating between steps
        if widget_key not in st.session_state and value is not None:
            # Handle different value types appropriately
            if isinstance(value, str) and value.strip() != "":
                st.session_state[widget_key] = value
            elif isinstance(value, bool):
                st.session_state[widget_key] = value
            elif value not in [None, "", 0]:  # Don't sync empty/zero values
                st.session_state[widget_key] = value


# =============================================================================
# FIELD RENDERERS
# =============================================================================

def render_text_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a text input field."""
    key = f"{prefix}_{field.id}"

    # For readonly fields, ensure the value is set BEFORE rendering
    if field.readonly:
        form_value = get_form_value(field.id, prefix)
        if form_value:
            if key not in st.session_state or st.session_state[key] != form_value:
                st.session_state[key] = form_value
        elif field.default:
            set_form_value(field.id, field.default, prefix)
            st.session_state[key] = field.default

    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        current_value = st.session_state[key]
    else:
        current_value = get_form_value(field.id, prefix) or field.default or ""

    # Build label with required indicator
    label = f"{field.label} *" if field.required else field.label

    # Render input - avoid passing default value if key already exists in session_state
    if key in st.session_state:
        value = st.text_input(
            label,
            key=key,
            placeholder=field.placeholder or "",
            help=field.help,
            disabled=disabled or field.readonly
        )
    else:
        value = st.text_input(
            label,
            value=current_value,
            key=key,
            placeholder=field.placeholder or "",
            help=field.help,
            disabled=disabled or field.readonly
        )

    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)

    # Update touched state if value changed
    if value != current_value:
        mark_touched(field.id, prefix)

    # Validate if touched
    error = None
    if is_touched(field.id, prefix) and value:
        is_valid, error = FieldValidator.validate_field(field, value)
        set_form_error(field.id, error, prefix)

    # Show error
    if error:
        st.error(error)

    return value, error


def render_email_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render an email input field."""
    # Email uses same renderer as text with different validation
    return render_text_field(field, prefix, disabled)


def render_phone_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a phone input field with optional prefix."""
    key = f"{prefix}_{field.id}"
    
    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        current_value = st.session_state[key]
    else:
        current_value = get_form_value(field.id, prefix) or ""
        
    label = f"{field.label} *" if field.required else field.label
    
    # Add prefix info to help
    help_text = field.help or ""
    if field.prefix:
        help_text = f"Country code: {field.prefix}. {help_text}"
    
    # Render input - avoid passing default value if key already exists in session_state
    if key in st.session_state:
        value = st.text_input(
            label,
            key=key,
            placeholder=field.placeholder or "",
            help=help_text,
            disabled=disabled
        )
    else:
        value = st.text_input(
            label,
            value=current_value,
            key=key,
            placeholder=field.placeholder or "",
            help=help_text,
            disabled=disabled
        )
    
    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)
    
    if value != current_value:
        mark_touched(field.id, prefix)
    
    error = None
    if is_touched(field.id, prefix) and value:
        is_valid, error = FieldValidator.validate_field(field, value)
        set_form_error(field.id, error, prefix)
    
    if error:
        st.error(error)
    
    return value, error


def render_id_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render an ID number field with auto-formatting for CNIC/Aadhaar."""
    key = f"{prefix}_{field.id}"
    
    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        current_value = st.session_state[key]
    else:
        current_value = get_form_value(field.id, prefix) or ""
        
    label = f"{field.label} *" if field.required else field.label
    
    # Check if this is a CNIC field (Pakistan) - auto-format with dashes
    is_cnic = field.id == "cnic" or (field.mask and "XXXXX-XXXXXXX-X" in field.mask)
    
    # Format placeholder for better UX
    placeholder = field.placeholder or ""
    if is_cnic and not placeholder:
        placeholder = "12345-1234567-1"
    
    help_text = field.help or ""
    
    # Render input - avoid passing default value if key already exists in session_state
    if key in st.session_state:
        value = st.text_input(
            label,
            key=key,
            placeholder=placeholder,
            help=help_text if help_text else None,
            disabled=disabled,
            max_chars=15 if is_cnic else None
        )
    else:
        value = st.text_input(
            label,
            value=current_value,
            key=key,
            placeholder=placeholder,
            help=help_text if help_text else None,
            disabled=disabled,
            max_chars=15 if is_cnic else None
        )
    
    # Auto-format CNIC as user types: XXXXX-XXXXXXX-X
    if is_cnic and value:
        # Remove existing dashes and non-digits
        digits_only = ''.join(c for c in value if c.isdigit())
        
        # Format with dashes: 5-7-1 pattern
        if len(digits_only) > 0:
            formatted = digits_only[:5]
            if len(digits_only) > 5:
                formatted += "-" + digits_only[5:12]
            if len(digits_only) > 12:
                formatted += "-" + digits_only[12:13]
            
            if formatted != value:
                value = formatted
                st.session_state[key] = value
                set_form_value(field.id, value, prefix)
                st.rerun()
    
    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)
    
    if value != current_value:
        mark_touched(field.id, prefix)
    
    error = None
    if is_touched(field.id, prefix) and value:
        is_valid, error = FieldValidator.validate_field(field, value)
        set_form_error(field.id, error, prefix)
    
    if error:
        st.error(error)
    
    return value, error


def render_date_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a date input field with age validation."""
    key = f"{prefix}_{field.id}"
    
    label = f"{field.label} *" if field.required else field.label
    
    # Calculate date bounds based on age requirements
    today = date.today()
    min_age = field.validation.min_age if field.validation else 18
    max_age = field.validation.max_age if field.validation else 100
    
    max_date = today - timedelta(days=min_age * 365)
    min_date = today - timedelta(days=max_age * 365)
    
    # Get current value - check widget first, then form data
    current_value = None
    if key in st.session_state:
        current_value = st.session_state[key]
        # Normalize stored widget value to a date object
        if isinstance(current_value, str):
            try:
                parsed = date.fromisoformat(current_value)
                current_value = parsed
                st.session_state[key] = parsed
            except Exception:
                current_value = None
                # Drop invalid value to avoid Streamlit API errors
                del st.session_state[key]
        elif hasattr(current_value, "date"):
            # Handles datetime values
            current_value = current_value.date() if not isinstance(current_value, date) else current_value
            st.session_state[key] = current_value
    else:
        current_form_value = get_form_value(field.id, prefix)
        if current_form_value is not None:
            if isinstance(current_form_value, str):
                try:
                    current_value = date.fromisoformat(current_form_value)
                except:
                    current_value = None
            elif isinstance(current_form_value, date):
                current_value = current_form_value
    
    # Validate that current_value is within bounds, otherwise reset to None
    if current_value and isinstance(current_value, date):
        if current_value < min_date or current_value > max_date:
            current_value = None
            set_form_value(field.id, None, prefix)
    
    help_text = field.help if field.help else None
    
    # Render date input - let Streamlit manage state via key
    value = st.date_input(
        label,
        value=current_value,
        min_value=min_date,
        max_value=max_date,
        key=key,
        help=help_text,
        disabled=disabled
    )
    
    # Sync the current widget value to form data storage
    value_str = value.isoformat() if value else None
    set_form_value(field.id, value_str, prefix)
    
    if value != current_value:
        mark_touched(field.id, prefix)
    
    error = None
    if is_touched(field.id, prefix) and value:
        is_valid, error = FieldValidator.validate_field(field, value)
        set_form_error(field.id, error, prefix)
    
    if error:
        st.error(error)
    
    return value, error


def render_select_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a select/dropdown field."""
    key = f"{prefix}_{field.id}"
    
    label = f"{field.label} *" if field.required else field.label
    options = field.options or []
    
    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        current_value = st.session_state[key]
    else:
        current_value = get_form_value(field.id, prefix) or field.default
    
    # Find index of current value
    try:
        index = options.index(current_value) if current_value in options else 0
    except (ValueError, TypeError):
        index = 0
    
    # Render select - let Streamlit manage the state via key
    value = st.selectbox(
        label,
        options=options,
        index=index,
        key=key,
        help=field.help,
        disabled=disabled or field.readonly
    )
    
    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)
    
    # Mark as touched if value changed
    if value != current_value:
        mark_touched(field.id, prefix)
    
    return value, None


def render_boolean_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a boolean (yes/no) field."""
    key = f"{prefix}_{field.id}"
    
    label = f"{field.label} *" if field.required else field.label
    
    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        # Normalize stored value to radio options
        if isinstance(st.session_state[key], bool):
            st.session_state[key] = "Yes" if st.session_state[key] else "No"
        elif st.session_state[key] not in ["Yes", "No"]:
            del st.session_state[key]
        # Convert radio selection back to boolean
        current_value = st.session_state.get(key) == "Yes"
    else:
        current_value = get_form_value(field.id, prefix)
        if current_value is None:
            current_value = field.default if field.default is not None else False
    
    # Use radio for boolean questions
    options = ["No", "Yes"]
    index = 1 if current_value else 0
    
    value_str = st.radio(
        label,
        options=options,
        index=index,
        key=key,
        help=field.help,
        horizontal=True,
        disabled=disabled
    )
    
    value = value_str == "Yes"
    
    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)
    
    # Mark as touched if value changed
    if value != current_value:
        mark_touched(field.id, prefix)
    
    return value, None


def render_checkbox_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a checkbox field."""
    key = f"{prefix}_{field.id}"
    
    # Get current value - check widget first, then form data, then default
    if key in st.session_state:
        current_value = st.session_state[key]
    else:
        current_value = get_form_value(field.id, prefix)
        if current_value is None:
            current_value = field.default if field.default is not None else False
    
    # Render checkbox - let Streamlit manage the state via key
    value = st.checkbox(
        field.label,
        value=bool(current_value),
        key=key,
        help=field.help,
        disabled=disabled
    )
    
    # Sync the current widget value to form data storage
    set_form_value(field.id, value, prefix)
    
    # Mark as touched if value changed
    if value != current_value:
        mark_touched(field.id, prefix)

    # Validate if must be true (only after touch to avoid premature errors)
    error = None
    if field.must_be_true and not value and is_touched(field.id, prefix):
        error = field.error or "This field is required"
        set_form_error(field.id, error, prefix)
    else:
        set_form_error(field.id, None, prefix)
    
    if error:
        st.error(error)
    
    return value, error


# =============================================================================
# FIELD RENDERER DISPATCHER
# =============================================================================

def render_field(
    field: FormField,
    prefix: str = "kyc",
    disabled: bool = False
) -> tuple[Any, Optional[str]]:
    """Render a field based on its type."""
    key = f"{prefix}_{field.id}"

    # If field is readonly, always disable it and ensure default value is set
    if field.readonly:
        disabled = True
        # Ensure the default value is set in BOTH form_data AND widget key
        if field.default is not None:
            current = get_form_value(field.id, prefix)
            if current is None or current == "":
                set_form_value(field.id, field.default, prefix)
                # Also set widget key so text_input shows the value
                st.session_state[key] = field.default
            elif key not in st.session_state:
                # Form data exists but widget key doesn't - sync it
                st.session_state[key] = current
    
    renderers = {
        FieldType.TEXT: render_text_field,
        FieldType.EMAIL: render_email_field,
        FieldType.TEL: render_phone_field,
        FieldType.ID: render_id_field,
        FieldType.DATE: render_date_field,
        FieldType.SELECT: render_select_field,
        FieldType.BOOLEAN: render_boolean_field,
        FieldType.CHECKBOX: render_checkbox_field,
    }
    
    renderer = renderers.get(field.type, render_text_field)
    return renderer(field, prefix, disabled)


# =============================================================================
# CATEGORY RENDERER
# =============================================================================

def render_category(
    category: FormCategory,
    prefix: str = "kyc",
    expanded: bool = True,
    show_optional: bool = True
) -> Dict[str, tuple[Any, Optional[str]]]:
    """
    Render all fields in a category.
    
    Returns:
        Dict mapping field_id to (value, error) tuples
    """
    results = {}
    
    with st.expander(category.label, expanded=expanded):
        if category.description:
            st.caption(category.description)
        
        # Required fields
        if category.required_fields:
            for field in category.required_fields:
                results[field.id] = render_field(field, prefix)
                st.markdown("---")
        
        # Optional fields
        if show_optional and category.optional_fields:
            st.markdown("**Optional Information**")
            for field in category.optional_fields:
                results[field.id] = render_field(field, prefix)
    
    return results


# =============================================================================
# FULL FORM RENDERER
# =============================================================================

def render_kyc_form(
    country_code: str,
    prefix: str = "kyc",
    show_progress: bool = True,
    on_submit: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Render complete KYC form for a country.

    Args:
        country_code: ISO country code (PK, IN, GB)
        prefix: Session state prefix
        show_progress: Show progress bar
        on_submit: Callback when form is submitted

    Returns:
        Dict with form_data, is_valid, errors
    """
    init_form_state(prefix)

    # Load schema
    schema = get_country_schema(country_code)
    if not schema:
        st.error(f" Country not supported: {country_code}")
        return {"form_data": {}, "is_valid": False, "errors": {"_form": "Unsupported country"}}

    # Check if country changed - only clear if ACTUALLY changed (not just on page revisit)
    current_country = st.session_state.get(f"{prefix}__schema_country")
    if current_country is not None and current_country != country_code:
        # Country actually changed, clear and reinitialize
        clear_form_state(prefix)
        init_form_state(prefix)

    # Always update the current country marker
    st.session_state[f"{prefix}__schema_country"] = country_code

    # Sync any existing form data to widget keys (for data persistence on navigation)
    sync_form_data_to_widgets(prefix)
    
    # Header
    st.markdown(f"## {schema.flag} {schema.country_name} KYC Form")
    st.caption(f"Complete the form below to verify your identity for trading")
    
    # Progress bar
    if show_progress:
        form_data = get_all_form_data(prefix)
        required_fields = schema.get_all_required_fields()
        filled = sum(1 for f in required_fields if form_data.get(f.id))
        progress = filled / len(required_fields) if required_fields else 0
        st.progress(progress, text=f"Progress: {filled}/{len(required_fields)} required fields completed")
    
    st.markdown("---")
    
    # Render categories in order
    sorted_categories = sorted(
        schema.categories.items(),
        key=lambda x: x[1].order
    )
    
    all_results = {}
    for cat_name, category in sorted_categories:
        # Handle special one_of categories (like GB government ID)
        if category.one_of and category.options:
            render_one_of_category(category, prefix)
        else:
            results = render_category(category, prefix, expanded=True)
            all_results.update(results)
    
    st.markdown("---")
    
    # Validate form
    form_data = get_all_form_data(prefix)
    validator = FormDataValidator(schema)
    validation_result = validator.validate_form(form_data)
    
    # Debug: Always show form data and errors for troubleshooting
    # with st.expander("Debug: Form Data & Validation", expanded=False):
    #     st.write("**Form Data:**")
    #     st.json(form_data)
    #     st.write("**Validation Errors:**")
    #     st.json(validation_result["errors"])
    #     st.write(f"**Is Valid:** {validation_result['is_valid']}")
    
    # Show status (no button - navigation is in kyc_onboarding.py)
    if validation_result["is_valid"]:
        st.success("All required fields are valid. You can proceed.")
    else:
        errors = validation_result["errors"]
        if errors:
            error_lines = []
            for field_id, msg in errors.items():
                error_lines.append(
                    f'<p style="color:#d0d5de;margin:2px 0;font-size:0.82rem;">'
                    f'<strong>{field_id.replace("_", " ").title()}</strong>: {msg}</p>'
                )
            st.markdown(
                '<div style="padding:12px 16px;background:#1a1020;border:1px solid #ff4d6a;border-radius:8px;">'
                '<p style="color:#ff4d6a;font-weight:600;margin:0 0 6px;font-size:0.85rem;">Please fix the following fields:</p>'
                + "".join(error_lines[:6])
                + (f'<p style="color:#8892a4;margin:4px 0 0;font-size:0.78rem;">...and {len(error_lines) - 6} more</p>' if len(error_lines) > 6 else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    return {
        "form_data": form_data,
        "is_valid": validation_result["is_valid"],
        "errors": validation_result["errors"]
    }


def render_one_of_category(
    category: FormCategory,
    prefix: str = "kyc"
) -> None:
    """Render a category where user selects ONE of several options."""
    with st.expander(category.label, expanded=True):
        if category.description:
            st.caption(category.description)
        
        st.info("Please select ONE of the following options:")
        
        # Get current selection
        selection_key = f"{prefix}_{category.label}_selection"
        options = [opt.label for opt in (category.options or [])]
        
        current_selection = st.session_state.get(selection_key, options[0] if options else None)
        
        selected = st.radio(
            "Choose your document type:",
            options=options,
            key=selection_key,
            horizontal=True
        )
        
        st.markdown("---")
        
        # Render fields for selected option
        for option in (category.options or []):
            if option.label == selected:
                for field in option.fields:
                    render_field(field, prefix)
                
                # Show document requirement
                if option.document:
                    st.markdown(f"**📄 Required Document:** {option.document.name}")
                    if option.document.requires_back:
                        st.caption("Both front and back sides required")
                    else:
                        st.caption("Photo page only")


# =============================================================================
# COUNTRY SELECTOR
# =============================================================================

def render_country_selector(
    prefix: str = "kyc",
    on_change: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Render country selector dropdown."""
    countries = get_supported_countries()
    
    if not countries:
        st.error("No countries configured")
        return None
    
    options = [f"{c['flag']} {c['name']}" for c in countries]
    codes = [c['code'] for c in countries]
    
    selected_display = st.selectbox(
        "🌍 Select Your Country",
        options=options,
        key=f"{prefix}_country_selector",
        help="Your KYC requirements depend on your country of residence"
    )
    
    # Extract code from selection
    selected_index = options.index(selected_display)
    selected_code = codes[selected_index]
    
    # Handle change
    if st.session_state.get(f"{prefix}__schema_country") != selected_code:
        if on_change:
            on_change(selected_code)
    
    return selected_code


# =============================================================================
# FORM SUMMARY VIEW
# =============================================================================

def render_form_summary(
    country_code: str,
    form_data: Dict[str, Any],
    prefix: str = "kyc"
) -> None:
    """Render a summary of submitted form data."""
    schema = get_country_schema(country_code)
    if not schema:
        return
    
    st.markdown("### Form Summary")
    st.markdown(f"**Country:** {schema.flag} {schema.country_name}")
    st.markdown("---")
    
    sorted_categories = sorted(
        schema.categories.items(),
        key=lambda x: x[1].order
    )
    
    for cat_name, category in sorted_categories:
        st.markdown(f"**{category.label}**")
        
        for field in category.required_fields + category.optional_fields:
            value = form_data.get(field.id)
            if value is not None and value != "":
                # Mask sensitive fields
                display_value = value
                if field.type == FieldType.ID and len(str(value)) > 4:
                    display_value = str(value)[:4] + "*" * (len(str(value)) - 4)
                
                st.text(f"  {field.label}: {display_value}")
        
        st.markdown("")
