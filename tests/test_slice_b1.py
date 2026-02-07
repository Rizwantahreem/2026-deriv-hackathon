"""Test Slice B1: Gemini OCR Service"""
import sys
import os

sys.path.insert(0, r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")
os.chdir(r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")

print("=" * 60)
print("SLICE B1: GEMINI OCR SERVICE - TEST")
print("=" * 60)

# Test 1: Import module
print("TEST 1: Import ocr_service module")
from backend.ocr_service import (
    GeminiOCR,
    OCRResult,
    DocumentQuality,
    analyze_document,
    get_call_count,
    load_ocr_prompts
)
print("   PASSED - Module imported successfully")

# Test 2: Load OCR prompts
print("TEST 2: Load OCR prompts from config")
prompts = load_ocr_prompts()
print(f"  Prompts loaded: {list(prompts.keys())}")
assert "cnic" in prompts, "Should have CNIC prompt"
assert "aadhaar" in prompts, "Should have Aadhaar prompt"
assert "passport" in prompts, "Should have passport prompt"
print("   PASSED")

# Test 3: GeminiOCR instantiation
print("TEST 3: GeminiOCR class instantiation")
ocr = GeminiOCR()
print(f"  Configured: {ocr.is_configured()}")
print(f"  Model: {ocr.model_name}")
print(f"  Call count: {ocr.call_count}")
print("   PASSED")

# Test 4: OCRResult dataclass
print("TEST 4: OCRResult dataclass")
result = OCRResult(
    success=True,
    document_type="cnic",
    quality=DocumentQuality.GOOD,
    quality_score=80,
    extracted_fields={"cnic_number": "12345-1234567-1", "name": "Ahmed Khan"},
    issues=[],
    suggestions=[],
    raw_response="{}"
)
assert result.success == True
assert result.quality == DocumentQuality.GOOD
assert result.quality_score == 80
assert result.extracted_fields["cnic_number"] == "12345-1234567-1"
print("   PASSED")

# Test 5: DocumentQuality enum
print("TEST 5: DocumentQuality enum values")
assert DocumentQuality.EXCELLENT.value == "excellent"
assert DocumentQuality.GOOD.value == "good"
assert DocumentQuality.ACCEPTABLE.value == "acceptable"
assert DocumentQuality.POOR.value == "poor"
assert DocumentQuality.UNREADABLE.value == "unreadable"
print("   PASSED")

# Test 6: extract_field_value method
print("TEST 6: extract_field_value method")
extracted = {"cnic_number": "12345-1234567-1", "name": "Ahmed Khan"}
value, valid = ocr.extract_field_value(extracted, "cnic_number", r"^\d{5}-\d{7}-\d{1}$")
assert value == "12345-1234567-1"
assert valid == True
print(f"  CNIC extracted: {value}, valid: {valid} ")

value, valid = ocr.extract_field_value(extracted, "missing_field")
assert value is None
assert valid == False
print(f"  Missing field: {value}, valid: {valid} ")

# Test 7: compare_with_form method
print("TEST 7: compare_with_form method")
extracted_fields = {
    "cnic_number": "12345-1234567-1",
    "name": "Ahmed Khan",
    "date_of_birth": "1990-01-15"
}
form_data = {
    "cnic": "12345-1234567-1",
    "full_name": "Ahmed Khan",
    "date_of_birth": "1990-01-15"
}
all_match, mismatches = ocr.compare_with_form(extracted_fields, form_data, "PK")
print(f"  All match: {all_match}, Mismatches: {len(mismatches)}")
assert all_match == True
print("   PASSED")

# Test 8: compare_with_form - mismatch detection
print("TEST 8: compare_with_form - mismatch detection")
form_data_wrong = {
    "cnic": "99999-9999999-9",  # Different CNIC
    "full_name": "Ahmed Khan",
    "date_of_birth": "1990-01-15"
}
all_match, mismatches = ocr.compare_with_form(extracted_fields, form_data_wrong, "PK")
print(f"  All match: {all_match}, Mismatches: {len(mismatches)}")
assert all_match == False
assert len(mismatches) >= 1
print(f"  Mismatch: {mismatches[0]['field']} - {mismatches[0]['message']} ")

# Test 9: Prompt building
print("TEST 9: Prompt building")
prompt = ocr._build_prompt("cnic", "PK", "front")
assert "cnic" in prompt.lower()
assert "PK" in prompt
assert "JSON" in prompt
print(f"  Prompt length: {len(prompt)} chars ")

# Test 10: Parse unstructured response
print("TEST 10: Parse unstructured response fallback")
response_text = "The document is blurry and the text is not readable. Please retake the photo."
result = ocr._parse_unstructured_response(response_text, "cnic")
assert result.quality == DocumentQuality.POOR
assert result.quality_score < 50
assert len(result.issues) > 0
print(f"  Quality: {result.quality.value}, Score: {result.quality_score} ")
print(f"  Issues: {[i['type'] for i in result.issues]} ")

# Test 11: API not configured handling
print("TEST 11: API not configured handling")
ocr_no_key = GeminiOCR(api_key="")
assert ocr_no_key.is_configured() == False
result = ocr_no_key.analyze_document(b"test", "cnic", "PK", "front")
assert result.success == False
assert "not configured" in result.error_message.lower()
print(f"  Error: {result.error_message} ")

print("=" * 60)
print("SLICE B1 COMPLETE - All tests passed!")
print("=" * 60)
