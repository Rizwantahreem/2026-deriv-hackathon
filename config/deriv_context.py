"""
Deriv Context Resolver - Handles country-specific KYC requirements.
This module loads and provides access to Deriv's document validation rules.
"""

import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

from .document_schema import DocumentType, DocumentSide


def get_config_path() -> Path:
    """Get the path to the config directory."""
    return Path(__file__).parent


@lru_cache(maxsize=1)
def load_country_config() -> dict:
    """
    Load the country configuration from JSON file.
    Cached for performance.
    """
    config_path = get_config_path() / "deriv_countries.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Country config not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_supported_countries() -> list[dict]:
    """Get list of all supported countries with basic info."""
    config = load_country_config()
    return [
        {
            "code": country["country_code"],
            "name": country["country_name"],
            "languages": country["languages"]
        }
        for country in config["countries"]
    ]


def get_country_by_code(country_code: str) -> Optional[dict]:
    """Get full country configuration by country code."""
    config = load_country_config()
    for country in config["countries"]:
        if country["country_code"].upper() == country_code.upper():
            return country
    return None


def get_document_types_for_country(country_code: str) -> list[dict]:
    """
    Get list of supported document types for a specific country.
    Returns simplified list for UI display.
    """
    country = get_country_by_code(country_code)
    if not country:
        return []
    
    return [
        {
            "type": doc["doc_type"],
            "name": doc["doc_name"],
            "requires_back": doc["requires_back"]
        }
        for doc in country["supported_documents"]
    ]


def get_document_requirements(country_code: str, document_type: str) -> Optional[dict]:
    """
    Get detailed requirements for a specific document type in a country.
    
    Returns:
        dict with: requires_front, requires_back, common_issues, required_fields, etc.
    """
    country = get_country_by_code(country_code)
    if not country:
        return None
    
    for doc in country["supported_documents"]:
        if doc["doc_type"] == document_type:
            return {
                "requires_front": doc["requires_front"],
                "requires_back": doc["requires_back"],
                "common_issues": doc["common_issues"],
                "required_fields": doc["required_fields"],
                "validity_check": doc.get("validity_check", False),
                "max_age_years": doc.get("max_age_years"),
                "doc_name": doc["doc_name"]
            }
    
    return None


def validate_document_completeness(
    country_code: str,
    document_type: str,
    sides_uploaded: list[str]
) -> dict:
    """
    Check if all required document sides have been uploaded.
    
    Args:
        country_code: ISO country code
        document_type: Type of document
        sides_uploaded: List of sides that have been uploaded ("front", "back")
    
    Returns:
        dict with: is_complete, missing_sides, message
    """
    requirements = get_document_requirements(country_code, document_type)
    
    if not requirements:
        return {
            "is_complete": False,
            "missing_sides": [],
            "message": f"Unknown document type '{document_type}' for country '{country_code}'"
        }
    
    missing_sides = []
    
    if requirements["requires_front"] and "front" not in sides_uploaded:
        missing_sides.append("front")
    
    if requirements["requires_back"] and "back" not in sides_uploaded:
        missing_sides.append("back")
    
    is_complete = len(missing_sides) == 0
    
    if is_complete:
        message = "All required document sides have been uploaded."
    else:
        sides_text = " and ".join(missing_sides)
        message = f"Please upload the {sides_text} side of your {requirements['doc_name']}."
    
    return {
        "is_complete": is_complete,
        "missing_sides": missing_sides,
        "message": message
    }


def get_common_issues_for_document(country_code: str, document_type: str) -> list[str]:
    """Get list of common issues for a specific document type."""
    requirements = get_document_requirements(country_code, document_type)
    if requirements:
        return requirements.get("common_issues", [])
    return []


def get_supported_languages() -> dict:
    """Get dictionary of supported languages."""
    config = load_country_config()
    return config.get("supported_languages", {"en": "English"})


class DerivContextResolver:
    """
    Main class for resolving Deriv-specific KYC context.
    Provides a clean interface for all country/document lookups.
    """
    
    def __init__(self):
        """Initialize the resolver and load config."""
        self._config = load_country_config()
    
    def get_countries(self) -> list[dict]:
        """Get list of supported countries."""
        return get_supported_countries()
    
    def get_country(self, country_code: str) -> Optional[dict]:
        """Get country details by code."""
        return get_country_by_code(country_code)
    
    def get_documents(self, country_code: str) -> list[dict]:
        """Get supported documents for a country."""
        return get_document_types_for_country(country_code)
    
    def get_requirements(self, country_code: str, doc_type: str) -> Optional[dict]:
        """Get document requirements."""
        return get_document_requirements(country_code, doc_type)
    
    def check_completeness(
        self,
        country_code: str,
        doc_type: str,
        sides: list[str]
    ) -> dict:
        """Check if document upload is complete."""
        return validate_document_completeness(country_code, doc_type, sides)
    
    def get_languages(self) -> dict:
        """Get supported languages."""
        return get_supported_languages()
    
    def is_country_supported(self, country_code: str) -> bool:
        """Check if a country is supported."""
        return get_country_by_code(country_code) is not None
    
    def is_document_supported(self, country_code: str, doc_type: str) -> bool:
        """Check if a document type is supported for a country."""
        return get_document_requirements(country_code, doc_type) is not None


# Global resolver instance
resolver = DerivContextResolver()
