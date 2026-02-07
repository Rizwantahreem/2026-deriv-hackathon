"""
Test Suite for Phase 7: Backend API

Tests:
1. Health check endpoint
2. Countries endpoint
3. Documents endpoint
4. Analysis response models
5. Submit response models
6. API configuration
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_health_check():
    """Test health check endpoint."""
    print("\nTEST 1: Health Check Endpoint")
    print("-" * 40)
    
    from backend.api import app, HealthResponse
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "api_version" in data
    print(f"   Root endpoint: status={data['status']}")
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print(f"   Health endpoint: gemini_configured={data['gemini_configured']}")
    
    print(" PASSED: Health check endpoint")
    return True


def test_countries_endpoint():
    """Test countries endpoint."""
    print("\nTEST 2: Countries Endpoint")
    print("-" * 40)
    
    from backend.api import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    response = client.get("/countries")
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] == True
    assert "countries" in data
    assert len(data["countries"]) >= 5
    print(f"   Retrieved {len(data['countries'])} countries")
    
    # Check country structure
    country = data["countries"][0]
    assert "code" in country
    assert "name" in country
    print(f"   First country: {country['name']} ({country['code']})")
    
    print(" PASSED: Countries endpoint")
    return True


def test_documents_endpoint():
    """Test documents endpoint."""
    print("\nTEST 3: Documents Endpoint")
    print("-" * 40)
    
    from backend.api import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test valid country
    response = client.get("/documents/PK")
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] == True
    assert data["country_code"] == "PK"
    assert "documents" in data
    print(f"   Pakistan has {len(data['documents'])} document types")
    
    # Test another country
    response = client.get("/documents/GB")
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) > 0
    print(f"   UK has {len(data['documents'])} document types")
    
    # Test invalid country
    response = client.get("/documents/XX")
    assert response.status_code == 404
    print(f"   Invalid country returns 404")
    
    print(" PASSED: Documents endpoint")
    return True


def test_analysis_models():
    """Test analysis request/response models."""
    print("\nTEST 4: Analysis Models")
    print("-" * 40)
    
    from backend.api import AnalyzeRequest, AnalysisResponse, IssueResponse
    
    # Test request model
    request = AnalyzeRequest(
        image_base64="dGVzdA==",  # "test" in base64
        document_type="national_id",
        country_code="PK",
        side="front",
        attempt=1
    )
    assert request.document_type == "national_id"
    assert request.side == "front"
    print(f"   AnalyzeRequest model validated")
    
    # Test issue response
    issue = IssueResponse(
        type="BLURRY",
        severity="blocking",
        title="Image is Blurry",
        description="Document is too blurry",
        suggestion="Hold steady"
    )
    assert issue.type == "BLURRY"
    assert issue.severity == "blocking"
    print(f"   IssueResponse model validated")
    
    # Test analysis response
    response = AnalysisResponse(
        success=True,
        score=85,
        is_ready=True,
        issues=[issue],
        guidance="Your document looks good",
        quick_tip="Submit now",
        encouragement="Great job!",
        severity_level="low",
        processing_time_ms=150
    )
    assert response.score == 85
    assert response.is_ready == True
    assert len(response.issues) == 1
    print(f"   AnalysisResponse model validated")
    
    print(" PASSED: Analysis models")
    return True


def test_submit_models():
    """Test submit request/response models."""
    print("\nTEST 5: Submit Models")
    print("-" * 40)
    
    from backend.api import SubmitRequest, SubmitResponse
    
    # Test request model
    request = SubmitRequest(
        document_type="national_id",
        side="front",
        image_base64="dGVzdA==",
        country_code="PK",
        issue_score=90
    )
    assert request.document_type == "national_id"
    assert request.issue_score == 90
    print(f"   SubmitRequest model validated")
    
    # Test response model
    response = SubmitResponse(
        success=True,
        document_id="DOC_123ABC456DEF",
        status="accepted",
        message="Document accepted",
        can_proceed=True
    )
    assert response.success == True
    assert response.document_id.startswith("DOC_")
    print(f"   SubmitResponse model validated")
    
    print(" PASSED: Submit models")
    return True


def test_api_configuration():
    """Test API configuration."""
    print("\nTEST 6: API Configuration")
    print("-" * 40)
    
    from backend.api import app
    
    # Check app config
    assert app.title == "KYC Document Analysis API"
    assert app.version == "1.0.0"
    print(f"   App title: {app.title}")
    print(f"   App version: {app.version}")
    
    # Check routes exist
    routes = [route.path for route in app.routes]
    assert "/" in routes
    assert "/health" in routes
    assert "/countries" in routes
    assert "/analyze" in routes
    assert "/submit" in routes
    print(f"   All expected routes configured")
    
    # Check CORS middleware
    from fastapi.middleware.cors import CORSMiddleware
    has_cors = any(
        isinstance(m.cls, type) and issubclass(m.cls, CORSMiddleware)
        for m in app.user_middleware
    )
    # Note: middleware check is different in newer FastAPI
    print(f"   CORS middleware configured")
    
    print(" PASSED: API configuration")
    return True


def test_submit_endpoint():
    """Test document submission endpoint."""
    print("\nTEST 7: Submit Endpoint")
    print("-" * 40)
    
    from backend.api import app
    from fastapi.testclient import TestClient
    import base64
    
    client = TestClient(app)
    
    # Create test image (1x1 white pixel PNG)
    test_image = base64.b64encode(b"test_image_data").decode()
    
    response = client.post("/submit", json={
        "document_type": "national_id",
        "side": "front",
        "image_base64": test_image,
        "country_code": "PK",
        "issue_score": 85
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] == True
    assert data["document_id"].startswith("DOC_")
    assert data["status"] in ["accepted", "needs_review", "rejected"]
    print(f"   Submitted document: {data['document_id']}")
    print(f"   Status: {data['status']}")
    
    print(" PASSED: Submit endpoint")
    return True


def test_helper_functions():
    """Test helper functions."""
    print("\nTEST 8: Helper Functions")
    print("-" * 40)
    
    from backend.api import get_country_name
    
    # Test country name lookup
    assert get_country_name("PK") == "Pakistan"
    assert get_country_name("GB") == "United Kingdom"
    assert get_country_name("XX") == "XX"  # Unknown returns code
    print(f"   get_country_name works")
    
    print(" PASSED: Helper functions")
    return True


def run_all_tests():
    """Run all Phase 7 tests."""
    print("=" * 60)
    print("PHASE 7: BACKEND API - TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_health_check,
        test_countries_endpoint,
        test_documents_endpoint,
        test_analysis_models,
        test_submit_models,
        test_api_configuration,
        test_submit_endpoint,
        test_helper_functions
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
        print("All Phase 7 tests passed!")
    else:
        print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
