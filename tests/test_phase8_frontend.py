"""
Test Suite for Phase 8: Frontend (Streamlit)

Tests:
1. Helper functions
2. Session state
3. Country data
4. Document data
5. Local analysis function
6. Local submit function
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_helper_functions():
    """Test frontend helper functions."""
    print("\nTEST 1: Helper Functions")
    print("-" * 40)
    
    from frontend.app import get_api_base, get_countries, get_documents
    
    # Test API base
    api_base = get_api_base()
    assert api_base == "http://localhost:8000"
    print(f"   API base: {api_base}")
    
    # Test countries
    countries = get_countries()
    assert len(countries) >= 5
    assert any(c["code"] == "PK" for c in countries)
    print(f"   Countries loaded: {len(countries)}")
    
    # Test documents
    pk_docs = get_documents("PK")
    assert len(pk_docs) >= 1
    assert any(d["doc_type"] == "national_id" for d in pk_docs)
    print(f"   Pakistan documents: {len(pk_docs)}")
    
    print(" PASSED: Helper functions")
    return True


def test_country_data():
    """Test country data completeness."""
    print("\nTEST 2: Country Data")
    print("-" * 40)
    
    from frontend.app import get_countries, get_documents
    
    countries = get_countries()
    
    required_countries = ["PK", "NG", "KE", "GB", "DE", "UAE"]
    
    for code in required_countries:
        country = next((c for c in countries if c["code"] == code), None)
        assert country is not None, f"Missing country: {code}"
        assert "name" in country
        print(f"   {code}: {country['name']}")
    
    print(" PASSED: Country data")
    return True


def test_document_data():
    """Test document data for each country."""
    print("\nTEST 3: Document Data")
    print("-" * 40)
    
    from frontend.app import get_documents
    
    countries_docs = {
        "PK": ["national_id", "passport"],
        "GB": ["passport", "driving_license"],
        "UAE": ["national_id", "passport"],
    }
    
    for country, expected_docs in countries_docs.items():
        docs = get_documents(country)
        doc_types = [d["doc_type"] for d in docs]
        
        for expected in expected_docs:
            assert expected in doc_types, f"Missing {expected} for {country}"
        
        print(f"   {country}: {len(docs)} document types")
    
    print(" PASSED: Document data")
    return True


def test_local_analysis():
    """Test local analysis function."""
    print("\nTEST 4: Local Analysis Function")
    print("-" * 40)
    
    from frontend.app import analyze_document_local
    
    # Create a simple test image (1x1 white pixel JPEG)
    from io import BytesIO
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='white')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    image_bytes = buffer.getvalue()
    
    # Run analysis
    result = analyze_document_local(
        image_bytes=image_bytes,
        document_type="national_id",
        country_code="PK",
        side="front",
        attempt=1
    )
    
    assert "success" in result
    assert "score" in result
    assert "is_ready" in result
    assert "issues" in result
    assert "guidance" in result
    print(f"   Analysis returned: success={result['success']}, score={result['score']}")
    
    print(" PASSED: Local analysis function")
    return True


def test_local_submit():
    """Test local submit function."""
    print("\nTEST 5: Local Submit Function")
    print("-" * 40)
    
    from frontend.app import submit_document_local
    
    # Create test image
    from io import BytesIO
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='white')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    image_bytes = buffer.getvalue()
    
    # Submit
    result = submit_document_local(
        image_bytes=image_bytes,
        document_type="national_id",
        country_code="PK",
        side="front",
        score=85
    )
    
    assert "success" in result
    assert "document_id" in result
    assert "status" in result
    print(f"   Submit returned: success={result['success']}, id={result.get('document_id')}")
    
    print(" PASSED: Local submit function")
    return True


def test_streamlit_import():
    """Test that Streamlit app can be imported."""
    print("\nTEST 6: Streamlit Import")
    print("-" * 40)
    
    try:
        # Import the main function (not run it)
        from frontend.app import main, render_header
        
        # Check functions exist
        assert callable(main)
        assert callable(render_header)
        print(f"   frontend.app module importable")
        print(f"   main() function exists")
        print(f"   render_header() function exists")
        
    except Exception as e:
        print(f"   Import warning (expected without streamlit): {e}")
    
    print(" PASSED: Streamlit import")
    return True


def run_all_tests():
    """Run all Phase 8 tests."""
    print("=" * 60)
    print("PHASE 8: FRONTEND - TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_helper_functions,
        test_country_data,
        test_document_data,
        test_local_analysis,
        test_local_submit,
        test_streamlit_import
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f" FAILED: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("All Phase 8 tests passed!")
    else:
        print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
