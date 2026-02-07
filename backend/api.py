"""
FastAPI Backend for KYC Document Analysis

Provides REST API endpoints for:
- Document analysis
- Issue detection
- Guidance generation
- Document submission to Deriv (mock)
"""

import time
import base64
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from config.document_schema import DocumentType, DocumentSide, IssueSeverity


# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI(
    title="KYC Document Analysis API",
    description="AI-powered document verification for Deriv onboarding",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request for document analysis with base64 image."""
    image_base64: str
    document_type: str
    country_code: str
    side: str = "front"
    attempt: int = 1


class IssueResponse(BaseModel):
    """Single issue in response."""
    type: str
    severity: str
    title: str
    description: str
    suggestion: str


class AnalysisResponse(BaseModel):
    """Full analysis response."""
    success: bool
    score: int
    is_ready: bool
    issues: list[IssueResponse]
    guidance: str
    quick_tip: str
    encouragement: str
    severity_level: str
    processing_time_ms: int
    extracted_data: dict = {}  # OCR extracted data for form comparison


class SubmitRequest(BaseModel):
    """Request to submit document to Deriv."""
    document_type: str
    side: str
    image_base64: str
    country_code: str
    issue_score: int = 100


class SubmitResponse(BaseModel):
    """Response from document submission."""
    success: bool
    document_id: str
    status: str
    message: str
    can_proceed: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    api_version: str
    gemini_configured: bool


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        api_version="1.0.0",
        gemini_configured=bool(settings.GEMINI_API_KEY)
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        api_version="1.0.0",
        gemini_configured=bool(settings.GEMINI_API_KEY)
    )


@app.get("/countries")
async def get_countries():
    """Get list of supported countries."""
    from config.deriv_context import get_supported_countries
    
    countries = get_supported_countries()
    return {
        "success": True,
        "countries": countries
    }


@app.get("/documents/{country_code}")
async def get_documents(country_code: str):
    """Get supported documents for a country."""
    from config.deriv_context import DerivContextResolver
    
    resolver = DerivContextResolver()
    documents = resolver.get_documents(country_code)
    
    if not documents:
        raise HTTPException(status_code=404, detail=f"Country {country_code} not found")
        
    return {
        "success": True,
        "country_code": country_code,
        "documents": documents
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(request: AnalyzeRequest):
    """
    Analyze a document image and return issues/guidance.
    
    This is the main endpoint that:
    1. Processes the image
    2. Runs vision analysis
    3. Detects issues
    4. Generates guidance
    """
    start_time = time.time()
    
    try:
        # Import modules
        from backend.image_processor import process_document_image
        from backend.vision_analyzer import analyze_document as vision_analyze
        from backend.issue_detector import (
            IssueDetector,
            prioritize_issues,
            calculate_issue_score,
            is_deriv_ready
        )
        from backend.llm_reasoner import generate_guidance
        from backend.issue_prioritizer import format_issues_for_display
        from config.deriv_context import get_document_requirements
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(request.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
            
        # Process image
        processed_image, image_quality = process_document_image(image_bytes)
        
        if processed_image is None:
            return AnalysisResponse(
                success=False,
                score=0,
                is_ready=False,
                issues=[IssueResponse(
                    type="INVALID_IMAGE",
                    severity="blocking",
                    title="Invalid Image",
                    description="Could not process the uploaded image",
                    suggestion="Please upload a valid JPEG or PNG image"
                )],
                guidance="The image could not be processed. Please try again with a different photo.",
                quick_tip="Use JPEG or PNG",
                encouragement="Let's try again!",
                severity_level="high",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
        # Run vision analysis
        vision_result = await vision_analyze_async(
            processed_image,
            request.document_type,
            request.country_code
        )
        
        # Detect issues
        detector = IssueDetector()
        issues = detector.detect_issues(
            vision_result=vision_result,
            image_quality=image_quality,
            country_code=request.country_code,
            document_type=request.document_type,
            document_side=request.side,
            sides_uploaded=[request.side]
        )
        
        # Check if OCR extracted any real data
        extracted_data = vision_result.get("extracted_data", {}) if vision_result else {}
        real_values = {k: v for k, v in extracted_data.items() if v and v != "null" and v is not None}
        
        if not real_values:
            # No readable data extracted - add blocking issue
            from config import IssueType, IssueSeverity, DetectedIssue
            issues.append(DetectedIssue(
                issue_type=IssueType.TEXT_UNREADABLE,
                severity=IssueSeverity.BLOCKING,
                description="No personal information could be extracted from this document",
                suggestion="Please upload a document with your actual information visible, not a blank template",
                title="No Data Found"
            ))
        
        # Prioritize issues
        prioritized = prioritize_issues(issues)
        
        # Calculate score
        score = calculate_issue_score(prioritized)
        is_ready = is_deriv_ready(prioritized)
        
        # Generate guidance
        country_name = get_country_name(request.country_code)
        guidance_result = generate_guidance(
            issues=prioritized,
            document_type=request.document_type,
            country_name=country_name,
            document_side=request.side,
            attempt=request.attempt
        )
        
        # Format issues for response
        formatted_issues = format_issues_for_display(prioritized)
        
        # Build response
        issue_responses = [
            IssueResponse(
                type=issue.issue_type.value,
                severity=issue.severity.value,
                title=formatted["title"],
                description=issue.description,
                suggestion=issue.suggestion
            )
            for issue, formatted in zip(prioritized, formatted_issues)
        ]
        
        return AnalysisResponse(
            success=True,
            score=score,
            is_ready=is_ready,
            issues=issue_responses,
            guidance=guidance_result.get("guidance", ""),
            quick_tip=guidance_result.get("quick_tip", ""),
            encouragement=guidance_result.get("encouragement", ""),
            severity_level=guidance_result.get("severity_level", "medium"),
            processing_time_ms=int((time.time() - start_time) * 1000),
            extracted_data=vision_result.get("extracted_data", {}) if vision_result else {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return AnalysisResponse(
            success=False,
            score=0,
            is_ready=False,
            issues=[IssueResponse(
                type="PROCESSING_ERROR",
                severity="blocking",
                title="Processing Error",
                description=str(e),
                suggestion="Please try again"
            )],
            guidance="An error occurred during analysis. Please try again.",
            quick_tip="Try again",
            encouragement="Let's try again!",
            severity_level="high",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/analyze/upload")
async def analyze_document_upload(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    country_code: str = Form(...),
    side: str = Form("front"),
    attempt: int = Form(1)
):
    """
    Analyze document from file upload.
    Alternative to base64 for direct file upload.
    """
    # Read file content
    contents = await file.read()
    
    # Convert to base64
    image_base64 = base64.b64encode(contents).decode()
    
    # Create request
    request = AnalyzeRequest(
        image_base64=image_base64,
        document_type=document_type,
        country_code=country_code,
        side=side,
        attempt=attempt
    )
    
    return await analyze_document(request)


@app.post("/submit", response_model=SubmitResponse)
async def submit_document(request: SubmitRequest):
    """
    Submit document to Deriv (mock).
    
    In production, this would send to actual Deriv API.
    """
    from backend.deriv_api import submit_document as deriv_submit
    from backend.image_processor import calculate_md5_checksum
    
    try:
        # Calculate checksum
        image_bytes = base64.b64decode(request.image_base64)
        checksum = calculate_md5_checksum(image_bytes)
        
        # Submit to mock Deriv API
        result = deriv_submit(
            document_type=request.document_type,
            side=request.side,
            image_data=request.image_base64,
            checksum=checksum,
            country_code=request.country_code,
            issue_score=request.issue_score
        )
        
        return SubmitResponse(
            success=result["success"],
            document_id=result["document_id"],
            status=result["status"],
            message=result["message"],
            can_proceed=result["can_proceed"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/submission/{document_id}")
async def get_submission_status(document_id: str):
    """Check status of a submitted document."""
    from backend.deriv_api import get_submission_manager
    
    manager = get_submission_manager()
    status = manager.get_submission_status(document_id)
    
    if not status.get("found"):
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
    return status


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def vision_analyze_async(image_base64: str, document_type: str, country_code: str) -> dict:
    """
    Wrapper for vision analysis (would be async in production).
    Returns mock result for now to avoid blocking.
    """
    # In production, this would call the actual vision analyzer
    # For now, return a simulated result to avoid API calls during testing
    
    try:
        from backend.vision_analyzer import analyze_document
        result = analyze_document(image_base64, document_type, country_code)
        return result
    except Exception:
        # Fallback mock result
        return {
            "detected_document_type": document_type,
            "quality_assessment": {
                "overall_quality": "good",
                "is_blurry": False,
                "has_glare": False,
                "is_dark": False,
                "is_bright": False,
                "corners_visible": True
            },
            "detected_elements": ["photo", "name", "id_number"],
            "issues_found": []
        }


def get_country_name(country_code: str) -> str:
    """Get country name from code."""
    country_names = {
        "PK": "Pakistan",
        "IN": "India",
        "NG": "Nigeria",
        "KE": "Kenya",
        "GB": "United Kingdom",
        "DE": "Germany",
        "UAE": "United Arab Emirates"
    }
    return country_names.get(country_code, country_code)


# ============================================================================
# KYC FORM SCHEMA ENDPOINTS
# ============================================================================

class KYCFormValidationRequest(BaseModel):
    """Request for KYC form validation."""
    country_code: str
    form_data: dict


class KYCValidationResponse(BaseModel):
    """Response from KYC form validation."""
    is_valid: bool
    errors: dict
    warnings: list
    missing_required: list


class KYCSchemaResponse(BaseModel):
    """Full KYC schema for a country."""
    country_code: str
    country_name: str
    flag: str
    categories: dict
    document_requirements: dict
    validation_rules: dict
    compliance_checks: dict


@app.get("/api/kyc/countries")
async def get_kyc_countries():
    """Get list of countries with KYC schema support."""
    try:
        from config.kyc_schema_loader import get_supported_countries
        countries = get_supported_countries()
        return {
            "success": True,
            "countries": countries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load countries: {str(e)}")


@app.get("/api/kyc/schema/{country_code}")
async def get_kyc_schema(country_code: str):
    """
    Get complete KYC form schema for a country.
    
    Returns all required fields, optional fields, validation rules,
    document requirements, and conditional logic.
    """
    try:
        from config.kyc_schema_loader import get_country_schema, export_schema_json
        
        schema = get_country_schema(country_code.upper())
        if not schema:
            raise HTTPException(
                status_code=404, 
                detail=f"KYC schema not found for country: {country_code}"
            )
        
        # Export as JSON-serializable dict
        schema_json = export_schema_json(country_code.upper())
        
        return {
            "success": True,
            "schema": schema_json
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load schema: {str(e)}")


@app.get("/api/kyc/schema/{country_code}/fields")
async def get_kyc_fields(country_code: str, category: Optional[str] = None):
    """
    Get form fields for a country, optionally filtered by category.
    
    Categories: identity, contact, address, government_id, compliance
    """
    try:
        from config.kyc_schema_loader import get_country_schema
        
        schema = get_country_schema(country_code.upper())
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"KYC schema not found for country: {country_code}"
            )
        
        if category:
            cat = schema.get_category(category)
            if not cat:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category not found: {category}"
                )
            return {
                "success": True,
                "country_code": country_code.upper(),
                "category": category,
                "required_fields": [f.model_dump() for f in cat.required_fields],
                "optional_fields": [f.model_dump() for f in cat.optional_fields]
            }
        
        # Return all fields
        return {
            "success": True,
            "country_code": country_code.upper(),
            "required_fields": [f.model_dump() for f in schema.get_all_required_fields()],
            "optional_fields": [f.model_dump() for f in schema.get_all_optional_fields()]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load fields: {str(e)}")


@app.get("/api/kyc/schema/{country_code}/documents")
async def get_kyc_documents(country_code: str):
    """Get document requirements for a country."""
    try:
        from config.kyc_schema_loader import get_country_schema
        
        schema = get_country_schema(country_code.upper())
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"KYC schema not found for country: {country_code}"
            )
        
        return {
            "success": True,
            "country_code": country_code.upper(),
            "document_requirements": {
                k: v.model_dump() for k, v in schema.document_requirements.items()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {str(e)}")


@app.post("/api/kyc/validate", response_model=KYCValidationResponse)
async def validate_kyc_form(request: KYCFormValidationRequest):
    """
    Validate KYC form data against country-specific schema.
    
    Returns validation errors, warnings, and list of missing required fields.
    """
    try:
        from config.kyc_schema_loader import validate_kyc_form
        
        result = validate_kyc_form(request.country_code.upper(), request.form_data)
        
        return KYCValidationResponse(
            is_valid=result["is_valid"],
            errors=result["errors"],
            warnings=result["warnings"],
            missing_required=result["missing_required"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.post("/api/kyc/validate-field")
async def validate_single_field(
    country_code: str = Form(...),
    field_id: str = Form(...),
    value: str = Form(...)
):
    """Validate a single field value in real-time."""
    try:
        from config.kyc_schema_loader import get_country_schema, FieldValidator
        
        schema = get_country_schema(country_code.upper())
        if not schema:
            raise HTTPException(
                status_code=404,
                detail=f"Country not supported: {country_code}"
            )
        
        # Find the field
        field = None
        for f in schema.get_all_required_fields() + schema.get_all_optional_fields():
            if f.id == field_id:
                field = f
                break
        
        if not field:
            raise HTTPException(
                status_code=404,
                detail=f"Field not found: {field_id}"
            )
        
        is_valid, error = FieldValidator.validate_field(field, value)
        
        return {
            "success": True,
            "field_id": field_id,
            "is_valid": is_valid,
            "error": error
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Field validation failed: {str(e)}")


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
