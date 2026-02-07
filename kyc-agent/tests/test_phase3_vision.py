"""
Test script for Phase 3: Vision Analyzer components.
Tests image processing, vision analysis, and feature extraction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import io
import base64


def create_test_image(width=800, height=500, color=(200, 200, 200)):
    """Create a simple test image."""
    img = Image.new('RGB', (width, height), color)
    
    # Add some variation to make it not completely uniform
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Draw a rectangle (simulating a document)
    margin = 50
    draw.rectangle(
        [margin, margin, width - margin, height - margin],
        outline=(100, 100, 100),
        width=3
    )
    
    # Add some text-like lines
    for i in range(5):
        y = 100 + i * 50
        draw.line([(100, y), (width - 100, y)], fill=(50, 50, 50), width=2)
    
    return img


def image_to_bytes(img, format='JPEG'):
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def test_image_processor():
    """Test image processing functions."""
    print("=" * 60)
    print("TEST 1: Image Processor")
    print("=" * 60)
    
    from backend.image_processor import (
        validate_image_format,
        load_image,
        resize_for_analysis,
        convert_to_base64,
        assess_basic_quality,
        process_document_image
    )
    
    # Create test image
    test_img = create_test_image()
    test_bytes = image_to_bytes(test_img)
    
    # Test 1.1: Validate format
    print("\n1.1 Validating image format...")
    is_valid, msg = validate_image_format(test_bytes)
    print(f"    Valid: {is_valid}, Message: {msg}")
    assert is_valid, f"Expected valid image, got: {msg}"
    print("     PASSED")
    
    # Test 1.2: Load image
    print("\n1.2 Loading image...")
    loaded = load_image(test_bytes)
    print(f"    Size: {loaded.size}, Mode: {loaded.mode}")
    assert loaded.size == (800, 500)
    print("     PASSED")
    
    # Test 1.3: Resize
    print("\n1.3 Resizing image...")
    resized = resize_for_analysis(loaded, max_size=512)
    print(f"    Original: {loaded.size}, Resized: {resized.size}")
    assert max(resized.size) <= 512
    print("     PASSED")
    
    # Test 1.4: Base64 conversion
    print("\n1.4 Converting to base64...")
    b64 = convert_to_base64(resized)
    print(f"    Base64 length: {len(b64)} chars")
    assert len(b64) > 100
    print("     PASSED")
    
    # Test 1.5: Quality assessment
    print("\n1.5 Assessing quality...")
    quality = assess_basic_quality(loaded)
    print(f"    Blur score: {quality['blur_score']}")
    print(f"    Brightness: {quality['brightness']}")
    print(f"    Resolution OK: {quality['resolution_ok']}")
    print("     PASSED")
    
    # Test 1.6: Full pipeline
    print("\n1.6 Full processing pipeline...")
    b64_result, quality_result = process_document_image(test_bytes)
    print(f"    Base64 length: {len(b64_result)}")
    print(f"    Quality keys: {list(quality_result.keys())}")
    print("     PASSED")
    
    print("\n All Image Processor tests passed!")
    return True


def test_vision_analyzer_init():
    """Test vision analyzer initialization."""
    print("\n" + "=" * 60)
    print("TEST 2: Vision Analyzer Initialization")
    print("=" * 60)
    
    from backend.vision_analyzer import GeminiVisionAnalyzer, get_vision_analyzer
    
    print("\n2.1 Creating analyzer...")
    try:
        analyzer = get_vision_analyzer()
        print(f"    Model: {analyzer.model.model_name}")
        print("     PASSED - Analyzer created successfully")
        return True
    except Exception as e:
        print(f"     Could not initialize: {e}")
        print("    (This is OK if just testing without API key)")
        return False


def test_feature_extractor():
    """Test feature extraction from mock vision results."""
    print("\n" + "=" * 60)
    print("TEST 3: Feature Extractor")
    print("=" * 60)
    
    from backend.feature_extractor import (
        extract_id_features,
        extract_passport_features,
        map_features_to_deriv_requirements,
        calculate_completeness_score
    )
    
    # Mock vision result (simulating what Gemini would return)
    mock_vision_result = {
        "detected_document_type": "national_id",
        "detected_side": "front",
        "is_correct_document": True,
        "document_visible": True,
        "quality_assessment": {
            "is_readable": True,
            "is_blurry": False,
            "has_glare": False,
            "is_too_dark": False,
            "is_too_bright": False,
            "all_corners_visible": True,
            "is_rotated": False,
            "has_obstructions": False
        },
        "detected_elements": {
            "has_photo": True,
            "has_name_field": True,
            "has_id_number": True,
            "has_date_of_birth": True,
            "has_expiry_date": False,
            "has_mrz_zone": False
        },
        "issues_found": [],
        "confidence_score": 0.95
    }
    
    # Test 3.1: Extract ID features
    print("\n3.1 Extracting ID features...")
    features = extract_id_features(mock_vision_result)
    print(f"    Has photo: {features['has_photo']}")
    print(f"    Has name: {features['has_name_field']}")
    print(f"    Appears valid: {features['appears_valid']}")
    assert features['has_photo'] == True
    assert features['appears_valid'] == True
    print("     PASSED")
    
    # Test 3.2: Map to Deriv requirements
    print("\n3.2 Mapping to Deriv requirements (Pakistan CNIC)...")
    req_check = map_features_to_deriv_requirements(features, 'PK', 'national_id')
    print(f"    Meets requirements: {req_check['meets_requirements']}")
    print(f"    Missing elements: {req_check['missing_elements']}")
    print(f"    Status: {req_check['requirement_status']}")
    print("     PASSED")
    
    # Test 3.3: Calculate completeness
    print("\n3.3 Calculating completeness score...")
    score = calculate_completeness_score(features, req_check)
    print(f"    Completeness: {score}%")
    assert 0 <= score <= 100
    print("     PASSED")
    
    # Test 3.4: Test with passport
    print("\n3.4 Testing passport features...")
    mock_passport = mock_vision_result.copy()
    mock_passport['detected_elements']['has_mrz_zone'] = True
    passport_features = extract_passport_features(mock_passport)
    print(f"    Has MRZ: {passport_features['has_mrz_zone']}")
    print(f"    MRZ readable: {passport_features['mrz_readable']}")
    print("     PASSED")
    
    print("\n All Feature Extractor tests passed!")
    return True


def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "=" * 60)
    print("PHASE 3: VISION ANALYZER - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Image Processor
    try:
        results.append(("Image Processor", test_image_processor()))
    except Exception as e:
        print(f" Image Processor failed: {e}")
        results.append(("Image Processor", False))
    
    # Test 2: Vision Analyzer Init
    try:
        results.append(("Vision Analyzer Init", test_vision_analyzer_init()))
    except Exception as e:
        print(f" Vision Analyzer Init failed: {e}")
        results.append(("Vision Analyzer Init", False))
    
    # Test 3: Feature Extractor
    try:
        results.append(("Feature Extractor", test_feature_extractor()))
    except Exception as e:
        print(f" Feature Extractor failed: {e}")
        results.append(("Feature Extractor", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = " PASSED" if passed else " FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All Phase 3 tests passed!")
    else:
        print(" Some tests failed or were skipped")
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
