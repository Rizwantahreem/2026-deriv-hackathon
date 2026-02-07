"""
Feature Extractor - Extracts specific features from vision analysis results.
Maps detected elements to Deriv's KYC requirements.
"""

from typing import Optional
from config import get_document_requirements


def extract_id_features(vision_result: dict) -> dict:
    """
    Extract ID document features from vision analysis result.
    
    Identifies presence of key elements without storing actual values.
    This is important for privacy - we only confirm field presence.
    
    Args:
        vision_result: Result from GeminiVisionAnalyzer
    
    Returns:
        dict with feature presence flags
    """
    detected = vision_result.get('detected_elements', {})
    quality = vision_result.get('quality_assessment', {})
    
    # Determine document orientation
    orientation = 'correct'
    if quality.get('is_rotated', False):
        # Try to determine rotation direction
        orientation = 'rotated'
    
    return {
        # Required elements for ID documents
        "has_photo": detected.get('has_photo', False),
        "has_name_field": detected.get('has_name_field', False),
        "has_date_of_birth": detected.get('has_date_of_birth', False),
        "has_document_number": detected.get('has_id_number', False),
        "has_expiry_date": detected.get('has_expiry_date', False),
        
        # Document state
        "document_orientation": orientation,
        "is_readable": quality.get('is_readable', False),
        "all_corners_visible": quality.get('all_corners_visible', False),
        
        # Quality flags
        "has_quality_issues": (
            quality.get('is_blurry', False) or
            quality.get('has_glare', False) or
            quality.get('is_too_dark', False) or
            quality.get('is_too_bright', False) or
            quality.get('has_obstructions', False)
        ),
        
        # Overall assessment
        "appears_valid": (
            detected.get('has_photo', False) and
            detected.get('has_name_field', False) and
            quality.get('is_readable', False) and
            not quality.get('is_blurry', False)
        )
    }


def extract_passport_features(vision_result: dict) -> dict:
    """
    Extract passport-specific features from vision analysis.
    
    Args:
        vision_result: Result from GeminiVisionAnalyzer
    
    Returns:
        dict with passport feature presence flags
    """
    detected = vision_result.get('detected_elements', {})
    quality = vision_result.get('quality_assessment', {})
    
    return {
        # Passport-specific elements
        "has_photo": detected.get('has_photo', False),
        "has_name_field": detected.get('has_name_field', False),
        "has_passport_number": detected.get('has_id_number', False),
        "has_date_of_birth": detected.get('has_date_of_birth', False),
        "has_expiry_date": detected.get('has_expiry_date', False),
        "has_mrz_zone": detected.get('has_mrz_zone', False),
        
        # MRZ is critical for passports
        "mrz_readable": (
            detected.get('has_mrz_zone', False) and
            quality.get('is_readable', False)
        ),
        
        # Document state
        "is_readable": quality.get('is_readable', False),
        "all_corners_visible": quality.get('all_corners_visible', False),
        
        # Overall assessment
        "appears_valid": (
            detected.get('has_photo', False) and
            detected.get('has_mrz_zone', False) and
            quality.get('is_readable', False)
        )
    }


def extract_utility_bill_features(vision_result: dict) -> dict:
    """
    Extract utility bill features for address verification.
    
    Args:
        vision_result: Result from GeminiVisionAnalyzer
    
    Returns:
        dict with utility bill feature presence flags
    """
    detected = vision_result.get('detected_elements', {})
    quality = vision_result.get('quality_assessment', {})
    
    # Note: These would need custom detection in the vision prompt
    # For now, using generic detection
    return {
        "has_address": detected.get('has_name_field', False),  # Approximation
        "has_date": detected.get('has_date_of_birth', False),  # Could be bill date
        "has_company_name": True,  # Assume visible if document detected
        
        # Quality
        "is_readable": quality.get('is_readable', False),
        "all_corners_visible": quality.get('all_corners_visible', False),
        
        # Bills don't have photos
        "appears_valid": quality.get('is_readable', False)
    }


def extract_features_by_type(
    vision_result: dict,
    document_type: str
) -> dict:
    """
    Extract features based on document type.
    
    Args:
        vision_result: Result from vision analyzer
        document_type: Type of document (national_id, passport, etc.)
    
    Returns:
        Extracted features dict
    """
    if document_type == 'passport':
        return extract_passport_features(vision_result)
    elif document_type == 'utility_bill':
        return extract_utility_bill_features(vision_result)
    else:
        # All ID types (national_id, aadhaar, pan_card, etc.)
        return extract_id_features(vision_result)


def map_features_to_deriv_requirements(
    features: dict,
    country_code: str,
    document_type: str
) -> dict:
    """
    Map extracted features against Deriv's requirements for the document.
    
    Args:
        features: Extracted features from document
        country_code: ISO country code
        document_type: Type of document
    
    Returns:
        dict with requirement compliance status
    """
    requirements = get_document_requirements(country_code, document_type)
    
    if not requirements:
        return {
            "meets_requirements": False,
            "missing_elements": ["Unknown document type or country"],
            "requirement_status": {}
        }
    
    required_fields = requirements.get('required_fields', [])
    
    # Map feature names to requirement names
    field_mapping = {
        "full_name": "has_name_field",
        "cnic_number": "has_document_number",
        "aadhaar_number": "has_document_number",
        "pan_number": "has_document_number",
        "id_number": "has_document_number",
        "passport_number": "has_passport_number",
        "nin_number": "has_document_number",
        "vin_number": "has_document_number",
        "licence_number": "has_document_number",
        "emirates_id_number": "has_document_number",
        "date_of_birth": "has_date_of_birth",
        "photo": "has_photo",
        "expiry_date": "has_expiry_date"
    }
    
    requirement_status = {}
    missing_elements = []
    
    for req_field in required_fields:
        feature_key = field_mapping.get(req_field, f"has_{req_field}")
        
        if feature_key in features:
            is_present = features[feature_key]
            requirement_status[req_field] = is_present
            if not is_present:
                missing_elements.append(req_field)
        else:
            # Unknown field, assume not present
            requirement_status[req_field] = False
            missing_elements.append(req_field)
    
    # Check overall quality requirements
    quality_ok = features.get('is_readable', False) and features.get('all_corners_visible', False)
    requirement_status['quality_acceptable'] = quality_ok
    
    if not quality_ok:
        missing_elements.append('acceptable_quality')
    
    return {
        "meets_requirements": len(missing_elements) == 0,
        "missing_elements": missing_elements,
        "requirement_status": requirement_status,
        "required_fields": required_fields
    }


def calculate_completeness_score(
    features: dict,
    requirements_check: dict
) -> float:
    """
    Calculate a completeness score (0-100) for the document.
    
    Args:
        features: Extracted features
        requirements_check: Result from map_features_to_deriv_requirements
    
    Returns:
        Completeness percentage (0-100)
    """
    status = requirements_check.get('requirement_status', {})
    
    if not status:
        return 0.0
    
    total = len(status)
    passed = sum(1 for v in status.values() if v)
    
    return round((passed / total) * 100, 1)
