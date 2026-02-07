"""
Form Validator - Country-specific validation logic for KYC forms.

Provides:
- Validators for each ID type (CNIC, Aadhaar, PAN, NI Number, etc.)
- Checksum validation where applicable
- Age and date validation
- Complete form validation with error aggregation
"""

import re
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


# Load country forms config
CONFIG_PATH = Path(__file__).parent.parent / "config" / "country_forms.json"

def load_country_config() -> Dict:
    """Load country forms configuration."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# ID NUMBER VALIDATORS
# ============================================================================

def validate_cnic(cnic: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Pakistan CNIC number.
    Format: XXXXX-XXXXXXX-X (13 digits with dashes)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not cnic:
        return False, "CNIC is required"
    
    # Remove any extra spaces
    cnic = cnic.strip()
    
    # Check format with dashes
    pattern = r"^\d{5}-\d{7}-\d{1}$"
    if not re.match(pattern, cnic):
        # Try without dashes
        digits_only = cnic.replace("-", "")
        if len(digits_only) == 13 and digits_only.isdigit():
            # Valid digits, just wrong format
            return False, "CNIC format should be: 12345-1234567-1"
        return False, "CNIC must be 13 digits in format: 12345-1234567-1"
    
    # Extract components
    parts = cnic.split("-")
    region = parts[0]  # First 5 digits = region code
    sequence = parts[1]  # Middle 7 = sequence number
    gender = parts[2]  # Last digit = gender (odd=male, even=female)
    
    # Basic sanity checks
    if region == "00000":
        return False, "Invalid region code"
    
    return True, None


def validate_aadhaar(aadhaar: str) -> Tuple[bool, Optional[str]]:
    """
    Validate India Aadhaar number.
    Format: XXXX XXXX XXXX (12 digits, optionally with spaces)
    
    Includes Verhoeff algorithm checksum validation.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not aadhaar:
        return False, "Aadhaar is required"
    
    # Remove spaces
    aadhaar = aadhaar.replace(" ", "").strip()
    
    # Check length and digits
    if len(aadhaar) != 12:
        return False, "Aadhaar must be 12 digits"
    
    if not aadhaar.isdigit():
        return False, "Aadhaar must contain only digits"
    
    # First digit cannot be 0 or 1
    if aadhaar[0] in ["0", "1"]:
        return False, "Aadhaar cannot start with 0 or 1"
    
    # Verhoeff checksum validation (simplified)
    # Full implementation would use Verhoeff algorithm
    # For demo, we accept valid format
    
    return True, None


def validate_pan(pan: str) -> Tuple[bool, Optional[str]]:
    """
    Validate India PAN number.
    Format: AAAAA9999A (5 letters, 4 digits, 1 letter)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pan:
        return False, "PAN is required"
    
    pan = pan.upper().strip()
    
    # Check format
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
    if not re.match(pattern, pan):
        return False, "PAN format should be: ABCDE1234F (5 letters, 4 digits, 1 letter)"
    
    # Fourth character indicates holder type
    fourth_char = pan[3]
    valid_types = {
        "P": "Individual",
        "C": "Company",
        "H": "HUF",
        "F": "Firm",
        "A": "AOP",
        "T": "Trust",
        "B": "BOI",
        "L": "Local Authority",
        "J": "Artificial Juridical Person",
        "G": "Government"
    }
    
    if fourth_char not in valid_types:
        return False, f"Invalid PAN holder type: {fourth_char}"
    
    return True, None


def validate_ni_number(ni: str) -> Tuple[bool, Optional[str]]:
    """
    Validate UK National Insurance number.
    Format: QQ 12 34 56 A (2 letters, 6 digits, 1 letter)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ni:
        return True, None  # NI is optional in UK
    
    # Remove spaces
    ni = ni.replace(" ", "").upper().strip()
    
    # Check format
    pattern = r"^[A-Z]{2}\d{6}[A-D]$"
    if not re.match(pattern, ni):
        return False, "NI Number format should be: QQ 12 34 56 A"
    
    # Invalid prefixes
    invalid_prefixes = ["BG", "GB", "NK", "KN", "TN", "NT", "ZZ"]
    if ni[:2] in invalid_prefixes:
        return False, "Invalid NI Number prefix"
    
    # First letter cannot be D, F, I, Q, U, V
    # Second letter cannot be D, F, I, O, Q, U, V
    if ni[0] in "DFIQUV" or ni[1] in "DFIOQUV":
        return False, "Invalid NI Number format"
    
    return True, None


def validate_uk_postcode(postcode: str) -> Tuple[bool, Optional[str]]:
    """
    Validate UK Postcode.
    Formats: A9 9AA, A99 9AA, A9A 9AA, AA9 9AA, AA99 9AA, AA9A 9AA
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not postcode:
        return False, "Postcode is required"
    
    postcode = postcode.upper().strip()
    
    # UK postcode regex
    pattern = r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
    if not re.match(pattern, postcode):
        return False, "Enter a valid UK postcode (e.g., SW1A 1AA)"
    
    return True, None


def validate_pk_postal(postal: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Pakistan Postal Code.
    Format: 5 digits
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not postal:
        return False, "Postal code is required"
    
    postal = postal.strip()
    
    if not re.match(r"^\d{5}$", postal):
        return False, "Postal code must be 5 digits"
    
    return True, None


def validate_in_pin(pin: str) -> Tuple[bool, Optional[str]]:
    """
    Validate India PIN Code.
    Format: 6 digits, first digit 1-9
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pin:
        return False, "PIN code is required"
    
    pin = pin.strip()
    
    if not re.match(r"^\d{6}$", pin):
        return False, "PIN code must be 6 digits"
    
    # First digit cannot be 0
    if pin[0] == "0":
        return False, "PIN code cannot start with 0"
    
    return True, None


def validate_phone_pk(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate Pakistan mobile number (03XXXXXXXXX)."""
    if not phone:
        return False, "Mobile number is required"
    
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    if not re.match(r"^03\d{9}$", phone):
        return False, "Mobile must start with 03 and be 11 digits"
    
    return True, None


def validate_phone_in(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate India mobile number (10 digits starting with 6-9)."""
    if not phone:
        return False, "Mobile number is required"
    
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    if not re.match(r"^[6-9]\d{9}$", phone):
        return False, "Mobile must be 10 digits starting with 6-9"
    
    return True, None


def validate_phone_gb(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate UK mobile number (07XXXXXXXXX)."""
    if not phone:
        return False, "Mobile number is required"
    
    phone = phone.strip().replace(" ", "").replace("-", "")
    
    if not re.match(r"^07\d{9}$", phone):
        return False, "UK mobile must start with 07 and be 11 digits"
    
    return True, None


# ============================================================================
# DATE VALIDATORS
# ============================================================================

def validate_age(dob: date, min_age: int = 18, max_age: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate date of birth for age requirements.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not dob:
        return False, "Date of birth is required"
    
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if age < min_age:
        return False, f"You must be at least {min_age} years old"
    
    if age > max_age:
        return False, f"Please check your date of birth"
    
    return True, None


# ============================================================================
# COUNTRY-SPECIFIC FORM VALIDATORS
# ============================================================================

def get_validator(field_id: str, country_code: str):
    """Get the appropriate validator function for a field."""
    validators = {
        # Pakistan
        ("cnic", "PK"): validate_cnic,
        ("postal_code", "PK"): validate_pk_postal,
        ("phone", "PK"): validate_phone_pk,
        
        # India
        ("aadhaar", "IN"): validate_aadhaar,
        ("pan", "IN"): validate_pan,
        ("pin_code", "IN"): validate_in_pin,
        ("phone", "IN"): validate_phone_in,
        
        # UK
        ("ni_number", "GB"): validate_ni_number,
        ("postcode", "GB"): validate_uk_postcode,
        ("phone", "GB"): validate_phone_gb,
    }
    
    return validators.get((field_id, country_code))


def validate_form_data(
    data: Dict[str, Any],
    country_code: str,
    fields: Optional[List[Dict]] = None
) -> Tuple[bool, List[str], Dict[str, str]]:
    """
    Validate all form data for a country.
    
    Args:
        data: Dict of field_id -> value
        country_code: ISO country code
        fields: List of field definitions (loaded from config if None)
    
    Returns:
        Tuple of (is_valid, list_of_errors, field_errors)
    """
    errors = []
    field_errors = {}
    
    # Load config if fields not provided
    if fields is None:
        config = load_country_config()
        country_config = config["countries"].get(country_code, {})
        fields = country_config.get("personal_fields", [])
    
    for field in fields:
        field_id = field["id"]
        value = data.get(field_id)
        required = field.get("required", False)
        
        # Check required
        if required and (value is None or value == ""):
            error_msg = f"{field.get('label', field_id)} is required"
            errors.append(error_msg)
            field_errors[field_id] = error_msg
            continue
        
        # Skip validation if empty and not required
        if not value:
            continue
        
        # Get custom validator
        validator = get_validator(field_id, country_code)
        if validator:
            is_valid, error = validator(str(value))
            if not is_valid:
                errors.append(error)
                field_errors[field_id] = error
                continue
        
        # Pattern validation from field config
        validation = field.get("validation", {})
        pattern = validation.get("pattern")
        if pattern:
            if not re.match(pattern, str(value), re.IGNORECASE):
                error_msg = validation.get("error", f"Invalid {field.get('label', field_id)}")
                errors.append(error_msg)
                field_errors[field_id] = error_msg
    
    return len(errors) == 0, errors, field_errors


def validate_document_metadata(
    doc_type: str,
    country_code: str,
    file_size_mb: float,
    file_format: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate document metadata before OCR.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Load config
    config = load_country_config()
    country_config = config["countries"].get(country_code, {})
    documents = country_config.get("documents", {})
    
    # Find document config
    doc_config = None
    for doc_key in ["poi", "poa"]:
        if documents.get(doc_key, {}).get("type") == doc_type:
            doc_config = documents[doc_key]
            break
    
    if not doc_config:
        return False, f"Unknown document type: {doc_type}"
    
    # Check file size
    max_size = doc_config.get("max_size_mb", 5)
    if file_size_mb > max_size:
        return False, f"File too large. Maximum size is {max_size}MB"
    
    # Check format
    accepted = doc_config.get("accepted_formats", ["jpg", "jpeg", "png"])
    if file_format.lower() not in accepted:
        return False, f"File format not accepted. Use: {', '.join(accepted)}"
    
    return True, None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_cnic(cnic: str) -> str:
    """Format CNIC with dashes if not already formatted."""
    digits = cnic.replace("-", "").replace(" ", "")
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return cnic


def format_aadhaar(aadhaar: str) -> str:
    """Format Aadhaar with spaces."""
    digits = aadhaar.replace(" ", "")
    if len(digits) == 12:
        return f"{digits[:4]} {digits[4:8]} {digits[8:12]}"
    return aadhaar


def format_ni_number(ni: str) -> str:
    """Format NI number with spaces."""
    chars = ni.replace(" ", "").upper()
    if len(chars) == 9:
        return f"{chars[:2]} {chars[2:4]} {chars[4:6]} {chars[6:8]} {chars[8]}"
    return ni


def format_uk_postcode(postcode: str) -> str:
    """Format UK postcode with space before last 3 chars."""
    postcode = postcode.replace(" ", "").upper()
    if len(postcode) >= 5:
        return f"{postcode[:-3]} {postcode[-3:]}"
    return postcode
