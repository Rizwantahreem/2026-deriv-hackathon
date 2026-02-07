"""
Reusable Form Field Components for KYC Forms

Provides Streamlit-based field renderers that:
- Support different field types (text, date, select, ID with mask)
- Apply real-time validation
- Show field-specific help and error messages
- Track field state in session
"""

import streamlit as st
import re
from datetime import date, timedelta
from typing import Optional, List, Dict, Any, Callable


def get_field_key(field_id: str, prefix: str = "form") -> str:
    """Generate unique session state key for a field."""
    return f"{prefix}_{field_id}"


def render_text_field(
    field_id: str,
    label: str,
    required: bool = False,
    placeholder: str = "",
    help_text: str = "",
    validation: Optional[Dict] = None,
    prefix: str = "form"
) -> tuple[str, Optional[str]]:
    """
    Render a text input field with validation.
    
    Returns:
        Tuple of (value, error_message)
    """
    key = get_field_key(field_id, prefix)
    
    # Add required indicator
    display_label = f"{label} *" if required else label
    
    value = st.text_input(
        display_label,
        key=key,
        placeholder=placeholder,
        help=help_text
    )
    
    # Validate
    error = None
    if value:
        if validation:
            pattern = validation.get("pattern")
            if pattern:
                if not re.match(pattern, value, re.IGNORECASE):
                    error = validation.get("error", "Invalid format")
            
            min_len = validation.get("min_length")
            if min_len and len(value) < min_len:
                error = f"Must be at least {min_len} characters"
            
            max_len = validation.get("max_length")
            if max_len and len(value) > max_len:
                error = f"Must be at most {max_len} characters"
    elif required:
        # Don't show error until user interacts
        pass
    
    if error:
        st.error(error)
    
    return value, error


def render_date_field(
    field_id: str,
    label: str,
    required: bool = False,
    min_age: int = 0,
    max_age: int = 120,
    help_text: str = "",
    prefix: str = "form"
) -> tuple[Optional[date], Optional[str]]:
    """
    Render a date input field with age validation.
    
    Returns:
        Tuple of (date_value, error_message)
    """
    key = get_field_key(field_id, prefix)
    
    display_label = f"{label} *" if required else label
    
    # Calculate date bounds
    today = date.today()
    max_date = today - timedelta(days=min_age * 365)  # Must be at least min_age
    min_date = today - timedelta(days=max_age * 365)  # Cannot be older than max_age
    
    value = st.date_input(
        display_label,
        key=key,
        min_value=min_date,
        max_value=max_date,
        value=None,
        help=help_text or f"You must be between {min_age} and {max_age} years old"
    )
    
    error = None
    if value:
        age = (today - value).days // 365
        if age < min_age:
            error = f"You must be at least {min_age} years old"
        elif age > max_age:
            error = f"Age cannot exceed {max_age} years"
    
    if error:
        st.error(error)
    
    return value, error


def render_select_field(
    field_id: str,
    label: str,
    options: List[str],
    required: bool = False,
    help_text: str = "",
    prefix: str = "form"
) -> tuple[Optional[str], Optional[str]]:
    """
    Render a dropdown select field.
    
    Returns:
        Tuple of (selected_value, error_message)
    """
    key = get_field_key(field_id, prefix)
    
    display_label = f"{label} *" if required else label
    
    value = st.selectbox(
        display_label,
        options=[""] + options,  # Add empty option
        key=key,
        help=help_text
    )
    
    error = None
    # Empty string means no selection
    if value == "":
        value = None
    
    return value, error


def render_id_field(
    field_id: str,
    label: str,
    required: bool = False,
    placeholder: str = "",
    format_hint: str = "",
    validation: Optional[Dict] = None,
    help_text: str = "",
    prefix: str = "form"
) -> tuple[str, Optional[str]]:
    """
    Render an ID field with format mask and validation.
    Shows format hint and applies real-time validation.
    
    Returns:
        Tuple of (value, error_message)
    """
    key = get_field_key(field_id, prefix)
    
    display_label = f"{label} *" if required else label
    
    # Show format hint
    if format_hint:
        st.caption(f"Format: {format_hint}")
    
    value = st.text_input(
        display_label,
        key=key,
        placeholder=placeholder,
        help=help_text
    )
    
    error = None
    if value:
        if validation:
            pattern = validation.get("pattern")
            if pattern:
                # Clean value for validation (remove extra spaces)
                clean_value = value.strip()
                if not re.match(pattern, clean_value, re.IGNORECASE):
                    error = validation.get("error", "Invalid format")
    
    if error:
        st.error(error)
    
    return value, error


def render_phone_field(
    field_id: str,
    label: str,
    country_code: str,
    required: bool = False,
    validation: Optional[Dict] = None,
    prefix: str = "form"
) -> tuple[str, Optional[str]]:
    """
    Render a phone number field with country-specific validation.
    
    Returns:
        Tuple of (value, error_message)
    """
    key = get_field_key(field_id, prefix)
    
    display_label = f"{label} *" if required else label
    
    # Country-specific placeholders
    placeholders = {
        "PK": "03001234567",
        "IN": "9876543210",
        "GB": "07700900123"
    }
    
    value = st.text_input(
        display_label,
        key=key,
        placeholder=placeholders.get(country_code, ""),
        help="Enter your mobile number without country code"
    )
    
    error = None
    if value:
        if validation:
            pattern = validation.get("pattern")
            if pattern and not re.match(pattern, value):
                error = validation.get("error", "Invalid phone number")
    
    if error:
        st.error(error)
    
    return value, error


def render_field(
    field: Dict[str, Any],
    country_code: str = "",
    prefix: str = "form"
) -> tuple[Any, Optional[str]]:
    """
    Render a field based on its type from country_forms.json schema.
    
    Args:
        field: Field definition dict from schema
        country_code: ISO country code for country-specific logic
        prefix: Session state key prefix
    
    Returns:
        Tuple of (value, error_message)
    """
    field_type = field.get("type", "text")
    field_id = field["id"]
    label = field.get("label", field_id)
    required = field.get("required", False)
    placeholder = field.get("placeholder", "")
    help_text = field.get("help", "")
    validation = field.get("validation")
    
    if field_type == "text":
        return render_text_field(
            field_id=field_id,
            label=label,
            required=required,
            placeholder=placeholder,
            help_text=help_text,
            validation=validation,
            prefix=prefix
        )
    
    elif field_type == "date":
        return render_date_field(
            field_id=field_id,
            label=label,
            required=required,
            min_age=field.get("min_age", 0),
            max_age=field.get("max_age", 120),
            help_text=help_text,
            prefix=prefix
        )
    
    elif field_type == "select":
        return render_select_field(
            field_id=field_id,
            label=label,
            options=field.get("options", []),
            required=required,
            help_text=help_text,
            prefix=prefix
        )
    
    elif field_type == "id":
        return render_id_field(
            field_id=field_id,
            label=label,
            required=required,
            placeholder=placeholder,
            format_hint=field.get("format", ""),
            validation=validation,
            help_text=help_text,
            prefix=prefix
        )
    
    elif field_type == "phone":
        return render_phone_field(
            field_id=field_id,
            label=label,
            country_code=country_code,
            required=required,
            validation=validation,
            prefix=prefix
        )
    
    else:
        # Default to text
        return render_text_field(
            field_id=field_id,
            label=label,
            required=required,
            placeholder=placeholder,
            help_text=help_text,
            validation=validation,
            prefix=prefix
        )


def collect_form_data(
    fields: List[Dict[str, Any]],
    prefix: str = "form"
) -> Dict[str, Any]:
    """
    Collect all form field values from session state.
    
    Args:
        fields: List of field definitions
        prefix: Session state key prefix
    
    Returns:
        Dict of field_id -> value
    """
    data = {}
    for field in fields:
        key = get_field_key(field["id"], prefix)
        if key in st.session_state:
            value = st.session_state[key]
            # Handle empty strings and None
            if value == "" or value is None:
                data[field["id"]] = None
            else:
                data[field["id"]] = value
    return data


def validate_form(
    fields: List[Dict[str, Any]],
    data: Dict[str, Any]
) -> tuple[bool, List[str]]:
    """
    Validate all form fields.
    
    Args:
        fields: List of field definitions
        data: Dict of field values
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    for field in fields:
        field_id = field["id"]
        value = data.get(field_id)
        required = field.get("required", False)
        validation = field.get("validation")
        
        # Check required
        if required and (value is None or value == ""):
            errors.append(f"{field.get('label', field_id)} is required")
            continue
        
        # Check pattern
        if value and validation:
            pattern = validation.get("pattern")
            if pattern:
                if not re.match(pattern, str(value), re.IGNORECASE):
                    errors.append(validation.get("error", f"Invalid {field.get('label', field_id)}"))
    
    return len(errors) == 0, errors


def render_form_section(
    title: str,
    fields: List[Dict[str, Any]],
    country_code: str = "",
    prefix: str = "form",
    columns: int = 2
) -> Dict[str, tuple[Any, Optional[str]]]:
    """
    Render a section of form fields with title.
    
    Args:
        title: Section title
        fields: List of field definitions
        country_code: ISO country code
        prefix: Session state key prefix
        columns: Number of columns for layout
    
    Returns:
        Dict of field_id -> (value, error)
    """
    st.markdown(f"### {title}")
    
    results = {}
    
    # Render fields in columns
    cols = st.columns(columns)
    for i, field in enumerate(fields):
        with cols[i % columns]:
            value, error = render_field(field, country_code, prefix)
            results[field["id"]] = (value, error)
    
    return results
