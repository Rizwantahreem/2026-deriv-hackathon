"""Test Slice A1: Country Forms Schema"""
import json
import os

os.chdir(r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")

with open("config/country_forms.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 60)
print("SLICE A1: COUNTRY FORMS SCHEMA - TEST")
print("=" * 60)

# Test 1: Countries loaded
countries = list(data["countries"].keys())
print(f"TEST 1: Countries loaded: {countries}")
assert countries == ["PK", "IN", "GB"], "Expected PK, IN, GB"
print("   PASSED")

# Test 2: PK fields
pk_fields = data["countries"]["PK"]["personal_fields"]
pk_field_ids = [f["id"] for f in pk_fields]
print(f"TEST 2: PK has {len(pk_fields)} fields: {pk_field_ids}")
assert "cnic" in pk_field_ids, "PK must have CNIC field"
assert "province" in pk_field_ids, "PK must have province field"
print("   PASSED")

# Test 3: IN fields
in_fields = data["countries"]["IN"]["personal_fields"]
in_field_ids = [f["id"] for f in in_fields]
print(f"TEST 3: IN has {len(in_fields)} fields: {in_field_ids}")
assert "aadhaar" in in_field_ids, "IN must have Aadhaar field"
assert "pan" in in_field_ids, "IN must have PAN field"
assert "state" in in_field_ids, "IN must have state field"
print("   PASSED")

# Test 4: GB fields
gb_fields = data["countries"]["GB"]["personal_fields"]
gb_field_ids = [f["id"] for f in gb_fields]
print(f"TEST 4: GB has {len(gb_fields)} fields: {gb_field_ids}")
assert "postcode" in gb_field_ids, "GB must have postcode field"
assert "ni_number" in gb_field_ids, "GB must have NI number field"
print("   PASSED")

# Test 5: Documents defined
for cc in ["PK", "IN", "GB"]:
    docs = data["countries"][cc]["documents"]
    assert "poi" in docs, f"{cc} must have POI document"
    assert "poa" in docs, f"{cc} must have POA document"
    print(f"TEST 5: {cc} documents: POI={docs['poi']['name']}, POA={docs['poa']['name']}")
print("   PASSED")

# Test 6: Validation rules
rules = list(data["validation_rules"].keys())
print(f"TEST 6: Validation rules: {rules}")
assert "cnic" in rules, "Must have CNIC rule"
assert "aadhaar" in rules, "Must have Aadhaar rule"
assert "uk_postcode" in rules, "Must have UK postcode rule"
print("   PASSED")

# Test 7: OCR prompts
prompts = list(data["ocr_prompts"].keys())
print(f"TEST 7: OCR prompts: {prompts}")
assert "cnic" in prompts, "Must have CNIC OCR prompt"
assert "passport" in prompts, "Must have passport OCR prompt"
print("   PASSED")

print("=" * 60)
print("SLICE A1 COMPLETE - All tests passed!")
print("=" * 60)
