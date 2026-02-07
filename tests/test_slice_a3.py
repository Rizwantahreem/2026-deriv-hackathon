"""Test Slice A3: Form Validation Logic"""
import sys
import os

sys.path.insert(0, r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")
os.chdir(r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")

print("=" * 60)
print("SLICE A3: FORM VALIDATION LOGIC - TEST")
print("=" * 60)

# Test 1: Import module
print("TEST 1: Import form_validator module")
from backend.form_validator import (
    validate_cnic,
    validate_aadhaar,
    validate_pan,
    validate_ni_number,
    validate_uk_postcode,
    validate_pk_postal,
    validate_in_pin,
    validate_phone_pk,
    validate_phone_in,
    validate_phone_gb,
    validate_form_data,
    format_cnic,
    format_aadhaar
)
print("   PASSED - Module imported successfully")

# Test 2: Pakistan CNIC validation
print("TEST 2: Pakistan CNIC validation")
valid, err = validate_cnic("12345-1234567-1")
assert valid == True, f"Valid CNIC failed: {err}"
print("  Valid CNIC: ")

valid, err = validate_cnic("12345")
assert valid == False
print(f"  Invalid CNIC rejected: {err} ")

valid, err = validate_cnic("00000-1234567-1")
assert valid == False
print(f"  Invalid region rejected: {err} ")

# Test 3: India Aadhaar validation
print("TEST 3: India Aadhaar validation")
valid, err = validate_aadhaar("2345 6789 0123")
assert valid == True, f"Valid Aadhaar failed: {err}"
print("  Valid Aadhaar: ")

valid, err = validate_aadhaar("0123 4567 8901")
assert valid == False
print(f"  Invalid Aadhaar (starts with 0) rejected: {err} ")

valid, err = validate_aadhaar("12345")
assert valid == False
print(f"  Invalid Aadhaar (short) rejected: {err} ")

# Test 4: India PAN validation
print("TEST 4: India PAN validation")
valid, err = validate_pan("ABCPE1234F")
assert valid == True, f"Valid PAN failed: {err}"
print("  Valid PAN (Individual): ")

valid, err = validate_pan("ABCXE1234F")
assert valid == False
print(f"  Invalid PAN type rejected: {err} ")

valid, err = validate_pan("ABC123")
assert valid == False
print(f"  Invalid PAN format rejected: {err} ")

# Test 5: UK NI Number validation
print("TEST 5: UK NI Number validation")
valid, err = validate_ni_number("AB123456C")
assert valid == True, f"Valid NI failed: {err}"
print("  Valid NI Number: ")

valid, err = validate_ni_number("BG123456A")
assert valid == False
print(f"  Invalid NI prefix rejected: {err} ")

valid, err = validate_ni_number("")  # Optional field
assert valid == True
print("  Empty NI accepted (optional): ")

# Test 6: UK Postcode validation
print("TEST 6: UK Postcode validation")
valid, err = validate_uk_postcode("SW1A 1AA")
assert valid == True, f"Valid postcode failed: {err}"
print("  Valid postcode (SW1A 1AA): ")

valid, err = validate_uk_postcode("M1 1AA")
assert valid == True, f"Valid short postcode failed: {err}"
print("  Valid postcode (M1 1AA): ")

valid, err = validate_uk_postcode("12345")
assert valid == False
print(f"  Invalid postcode rejected: {err} ")

# Test 7: Pakistan postal code
print("TEST 7: Pakistan Postal Code validation")
valid, err = validate_pk_postal("44000")
assert valid == True, f"Valid postal failed: {err}"
print("  Valid postal: ")

valid, err = validate_pk_postal("4400")
assert valid == False
print(f"  Invalid postal rejected: {err} ")

# Test 8: India PIN code
print("TEST 8: India PIN Code validation")
valid, err = validate_in_pin("400001")
assert valid == True, f"Valid PIN failed: {err}"
print("  Valid PIN: ")

valid, err = validate_in_pin("012345")
assert valid == False
print(f"  Invalid PIN (starts with 0) rejected: {err} ")

# Test 9: Phone validations
print("TEST 9: Phone number validations")
valid, err = validate_phone_pk("03001234567")
assert valid == True, f"Valid PK phone failed: {err}"
print("  Valid PK phone: ")

valid, err = validate_phone_in("9876543210")
assert valid == True, f"Valid IN phone failed: {err}"
print("  Valid IN phone: ")

valid, err = validate_phone_gb("07700900123")
assert valid == True, f"Valid GB phone failed: {err}"
print("  Valid GB phone: ")

# Test 10: Formatting functions
print("TEST 10: Formatting functions")
assert format_cnic("1234512345671") == "12345-1234567-1"
print("  format_cnic: ")

assert format_aadhaar("234567890123") == "2345 6789 0123"
print("  format_aadhaar: ")

# Test 11: Full form validation
print("TEST 11: Full form validation - Pakistan")
pk_data = {
    "full_name": "Ahmed Khan",
    "date_of_birth": "1990-01-15",
    "gender": "Male",
    "cnic": "12345-1234567-1",
    "address_line1": "House 123, Street 5",
    "city": "Karachi",
    "province": "Sindh",
    "postal_code": "75500",
    "phone": "03001234567"
}
is_valid, errors, field_errors = validate_form_data(pk_data, "PK")
print(f"  Valid: {is_valid}, Errors: {len(errors)}")
if not is_valid:
    print(f"  Errors: {errors}")
assert is_valid == True, f"PK form should be valid: {errors}"
print("   PASSED")

# Test 12: Invalid form validation
print("TEST 12: Full form validation - Invalid data")
invalid_data = {
    "full_name": "",  # Required
    "cnic": "12345",  # Invalid format
    "phone": "123"  # Invalid phone
}
is_valid, errors, field_errors = validate_form_data(invalid_data, "PK")
print(f"  Valid: {is_valid}, Errors: {len(errors)}")
assert is_valid == False
assert len(errors) >= 2
print(f"  Field errors: {list(field_errors.keys())}")
print("   PASSED - Invalid data rejected")

print("=" * 60)
print("SLICE A3 COMPLETE - All tests passed!")
print("=" * 60)
