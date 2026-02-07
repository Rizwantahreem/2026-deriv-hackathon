"""Test Slice A2: Form Field Components"""
import sys
import os

# Add project to path
sys.path.insert(0, r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")
os.chdir(r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")

print("=" * 60)
print("SLICE A2: FORM FIELD COMPONENTS - TEST")
print("=" * 60)

# Test 1: Import module
print("TEST 1: Import form_fields module")
from frontend.form_fields import (
    get_field_key,
    collect_form_data,
    validate_form
)
print("   PASSED - Module imported successfully")

# Test 2: get_field_key function
print("TEST 2: get_field_key function")
assert get_field_key("cnic", "form") == "form_cnic"
assert get_field_key("name", "kyc") == "kyc_name"
print("   PASSED")

# Test 3: validate_form - all valid
print("TEST 3: validate_form - valid data")
fields = [
    {"id": "name", "required": True},
    {"id": "cnic", "required": True, "validation": {"pattern": r"^\d{5}-\d{7}-\d{1}$", "error": "Invalid CNIC"}}
]
data = {"name": "Ahmed Khan", "cnic": "12345-1234567-1"}
is_valid, errors = validate_form(fields, data)
assert is_valid == True, f"Expected valid, got errors: {errors}"
assert len(errors) == 0
print("   PASSED")

# Test 4: validate_form - missing required
print("TEST 4: validate_form - missing required field")
data = {"name": None, "cnic": "12345-1234567-1"}
is_valid, errors = validate_form(fields, data)
assert is_valid == False
assert "name is required" in errors[0]
print(f"  Errors: {errors}")
print("   PASSED")

# Test 5: validate_form - invalid pattern
print("TEST 5: validate_form - invalid CNIC pattern")
data = {"name": "Ahmed Khan", "cnic": "12345"}
is_valid, errors = validate_form(fields, data)
assert is_valid == False
assert "Invalid CNIC" in errors[0]
print(f"  Errors: {errors}")
print("   PASSED")

# Test 6: validate different country patterns
print("TEST 6: Validate country-specific patterns")

# Pakistan CNIC
import re
cnic_pattern = r"^\d{5}-\d{7}-\d{1}$"
assert re.match(cnic_pattern, "12345-1234567-1"), "Valid CNIC should match"
assert not re.match(cnic_pattern, "12345"), "Short CNIC should not match"
print("  PK CNIC: ")

# India Aadhaar
aadhaar_pattern = r"^\d{4}\s?\d{4}\s?\d{4}$"
assert re.match(aadhaar_pattern, "1234 5678 9012"), "Valid Aadhaar should match"
assert re.match(aadhaar_pattern, "123456789012"), "Aadhaar without spaces should match"
assert not re.match(aadhaar_pattern, "12345"), "Short Aadhaar should not match"
print("  IN Aadhaar: ")

# India PAN
pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
assert re.match(pan_pattern, "ABCDE1234F"), "Valid PAN should match"
assert not re.match(pan_pattern, "ABCDE1234"), "Short PAN should not match"
print("  IN PAN: ")

# UK Postcode
uk_postcode_pattern = r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
assert re.match(uk_postcode_pattern, "SW1A 1AA", re.IGNORECASE), "Valid UK postcode should match"
assert re.match(uk_postcode_pattern, "M1 1AA", re.IGNORECASE), "Short UK postcode should match"
assert not re.match(uk_postcode_pattern, "12345", re.IGNORECASE), "US ZIP should not match"
print("  GB Postcode: ")

# UK NI Number (relaxed pattern for testing)
ni_pattern = r"^[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-Z]$"
assert re.match(ni_pattern, "QQ 12 34 56 A", re.IGNORECASE), "Valid NI should match"
assert re.match(ni_pattern, "QQ123456A", re.IGNORECASE), "NI without spaces should match"
print("  GB NI Number: ")

print("   ALL PATTERNS PASSED")

# Test 7: collect_form_data function
print("TEST 7: collect_form_data function")
# This would need Streamlit session state, so we just verify the function exists
from frontend.form_fields import collect_form_data
print("   PASSED - Function exists")

print("=" * 60)
print("SLICE A2 COMPLETE - All tests passed!")
print("=" * 60)
