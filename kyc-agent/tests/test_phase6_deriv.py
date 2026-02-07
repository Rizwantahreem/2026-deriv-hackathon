"""
Test Suite for Phase 6: Deriv API Bridge

Tests:
1. Mock client initialization
2. Document submission (high score)
3. Document submission (low score - rejected)
4. Document status check
5. Document type validation
6. Submission manager workflow
7. Error simulation
8. Can submit check
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.document_schema import DocumentType, DocumentSide


def test_mock_client_init():
    """Test mock Deriv client initialization."""
    print("\nTEST 1: Mock Client Initialization")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient, get_deriv_client
    
    # Test direct initialization
    client = MockDerivClient(simulate_delay=False)
    assert client is not None
    assert client.simulate_delay == False
    print(f"   MockDerivClient created (no delay)")
    
    # Test with delay
    client_delay = MockDerivClient(simulate_delay=True)
    assert client_delay.simulate_delay == True
    print(f"   MockDerivClient created (with delay)")
    
    # Test singleton
    singleton = get_deriv_client()
    assert singleton is not None
    print(f"   Singleton client accessible")
    
    print(" PASSED: Mock client initialization")
    return True


def test_document_submission_accepted():
    """Test document submission with high score (accepted)."""
    print("\nTEST 2: Document Submission (Accepted)")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient, DerivStatus, DocumentSubmission
    
    client = MockDerivClient(simulate_delay=False)
    
    # Create payload
    payload = DocumentSubmission(
        document_type="national_id",
        side="front",
        image_data="base64_image_data_here",
        checksum="abc123",
        country_code="PK"
    )
    
    # Submit with high score
    response = client.submit_document(payload, issue_score=95)
    
    assert response.status == DerivStatus.ACCEPTED
    assert response.document_id.startswith("DOC_")
    assert "accepted" in response.message.lower()
    print(f"   Document ID: {response.document_id}")
    print(f"   Status: {response.status.value}")
    print(f"   Message: {response.message}")
    
    print(" PASSED: Document submission (accepted)")
    return True


def test_document_submission_rejected():
    """Test document submission with low score (rejected)."""
    print("\nTEST 3: Document Submission (Rejected)")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient, DerivStatus, DocumentSubmission
    
    client = MockDerivClient(simulate_delay=False)
    
    # Create payload
    payload = DocumentSubmission(
        document_type="national_id",
        side="front",
        image_data="blurry_image_data",
        checksum="xyz789",
        country_code="PK"
    )
    
    # Submit with low score
    response = client.submit_document(payload, issue_score=30)
    
    assert response.status == DerivStatus.REJECTED
    assert response.document_id.startswith("DOC_")
    assert response.details.get("can_retry") == True
    print(f"   Document ID: {response.document_id}")
    print(f"   Status: {response.status.value}")
    print(f"   Can retry: {response.details.get('can_retry')}")
    
    print(" PASSED: Document submission (rejected)")
    return True


def test_document_status_check():
    """Test checking document status."""
    print("\nTEST 4: Document Status Check")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient, DerivAPIError, DocumentSubmission
    
    client = MockDerivClient(simulate_delay=False)
    
    # Submit a document first
    payload = DocumentSubmission(
        document_type="passport",
        side="front",
        image_data="passport_image",
        checksum="pass123",
        country_code="GB"
    )
    
    response = client.submit_document(payload, issue_score=85)
    doc_id = response.document_id
    
    # Check status
    status = client.check_document_status(doc_id)
    assert status.document_id == doc_id
    print(f"   Status retrieved for {doc_id}")
    
    # Check non-existent document
    try:
        client.check_document_status("DOC_NONEXISTENT")
        assert False, "Should have raised error"
    except DerivAPIError as e:
        assert e.code == "DOC_NOT_FOUND"
        print(f"   Correctly raised error for missing doc: {e.code}")
    
    print(" PASSED: Document status check")
    return True


def test_document_type_validation():
    """Test document type validation for country."""
    print("\nTEST 5: Document Type Validation")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient
    
    client = MockDerivClient(simulate_delay=False)
    
    # Test valid document for Pakistan
    result = client.validate_document_type(DocumentType.NATIONAL_ID, "PK")
    assert result["valid"] == True
    assert result["country"] == "PK"
    print(f"   NATIONAL_ID valid for PK: {result['valid']}")
    
    # Test passport for UK
    result = client.validate_document_type(DocumentType.PASSPORT, "GB")
    assert result["valid"] == True
    print(f"   PASSPORT valid for GB: {result['valid']}")
    
    # Get accepted documents for India
    accepted = client.get_accepted_documents("IN")
    # May be empty list if country not configured - that's ok for mock
    print(f"   India document types retrieved: {len(accepted)}")
    
    print(" PASSED: Document type validation")
    return True


def test_submission_manager():
    """Test submission manager workflow."""
    print("\nTEST 6: Submission Manager Workflow")
    print("-" * 40)
    
    from backend.deriv_api import DerivSubmissionManager
    
    manager = DerivSubmissionManager()
    manager.client.simulate_delay = False
    
    # Submit document
    result = manager.prepare_and_submit(
        document_type="national_id",
        side="front",
        image_data="test_image",
        checksum="test_checksum",
        country_code="PK",
        issue_score=90
    )
    
    assert result["success"] == True
    assert result["can_proceed"] == True
    assert result["document_id"].startswith("DOC_")
    print(f"   Submitted: {result['document_id']}")
    print(f"   Status: {result['status']}")
    
    # Check history
    history = manager.get_history()
    assert len(history) == 1
    assert history[0]["document_type"] == "national_id"
    print(f"   History tracked: {len(history)} submissions")
    
    # Get status
    status = manager.get_submission_status(result["document_id"])
    assert status["found"] == True
    print(f"   Status lookup works")
    
    print(" PASSED: Submission manager workflow")
    return True


def test_error_simulation():
    """Test error simulation for testing."""
    print("\nTEST 7: Error Simulation")
    print("-" * 40)
    
    from backend.deriv_api import MockDerivClient, DerivAPIError
    
    client = MockDerivClient(simulate_delay=False)
    
    # Test network error
    try:
        client.simulate_error("network")
        assert False, "Should have raised error"
    except DerivAPIError as e:
        assert e.code == "NETWORK_ERROR"
        print(f"   Network error: {e.code}")
    
    # Test rate limit
    try:
        client.simulate_error("rate_limit")
        assert False, "Should have raised error"
    except DerivAPIError as e:
        assert e.code == "RATE_LIMIT"
        print(f"   Rate limit error: {e.code}")
    
    # Test auth error
    try:
        client.simulate_error("auth")
        assert False, "Should have raised error"
    except DerivAPIError as e:
        assert e.code == "UNAUTHORIZED"
        print(f"   Auth error: {e.code}")
    
    print(" PASSED: Error simulation")
    return True


def test_can_submit_check():
    """Test submission readiness check."""
    print("\nTEST 8: Can Submit Check")
    print("-" * 40)
    
    from backend.deriv_api import DerivSubmissionManager
    
    manager = DerivSubmissionManager()
    
    # High score - ready
    result = manager.can_submit(85)
    assert result["ready"] == True
    assert result["recommendation"] == "submit"
    print(f"   Score 85: {result['recommendation']} - {result['message'][:40]}...")
    
    # Medium score - ready with review
    result = manager.can_submit(60)
    assert result["ready"] == True
    assert result["recommendation"] == "review"
    print(f"   Score 60: {result['recommendation']}")
    
    # Low score - not ready
    result = manager.can_submit(30)
    assert result["ready"] == False
    assert result["recommendation"] == "fix"
    print(f"   Score 30: {result['recommendation']}")
    
    print(" PASSED: Can submit check")
    return True


def run_all_tests():
    """Run all Phase 6 tests."""
    print("=" * 60)
    print("PHASE 6: DERIV API BRIDGE - TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_mock_client_init,
        test_document_submission_accepted,
        test_document_submission_rejected,
        test_document_status_check,
        test_document_type_validation,
        test_submission_manager,
        test_error_simulation,
        test_can_submit_check
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
        print("All Phase 6 tests passed!")
    else:
        print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
