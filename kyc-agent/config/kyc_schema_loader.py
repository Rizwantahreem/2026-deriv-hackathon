"""
KYC Schema Loader and Validator

Provides:
- Pydantic models for KYC form schemas
- Functions to load and validate country-specific schemas
- Dynamic field requirement resolution
- Conditional logic evaluation
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import date, datetime
import re


# =============================================================================
# ENUMS
# =============================================================================

class FieldType(str, Enum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    DATE = "date"
    SELECT = "select"
    BOOLEAN = "boolean"
    CHECKBOX = "checkbox"
    ID = "id"  # Special type for ID numbers with masks


class ActionType(str, Enum):
    SHOW_FIELD = "show_field"
    SHOW_FIELDS = "show_fields"
    HIDE_FIELD = "hide_field"
    REQUIRE_FIELD = "require_field"
    DISABLE_FIELD = "disable_field"


# =============================================================================
# VALIDATION MODELS
# =============================================================================

class FieldValidation(BaseModel):
    """Validation rules for a form field."""
    pattern: Optional[str] = None
    length: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    checksum: Optional[str] = None  # e.g., "verhoeff" for Aadhaar
    error: str = "Invalid value"


class FormField(BaseModel):
    """Definition of a single form field."""
    id: str
    label: str
    type: FieldType
    required: bool = False
    placeholder: Optional[str] = None
    help: Optional[str] = None
    default: Optional[Any] = None
    readonly: bool = False
    options: Optional[List[str]] = None  # For select fields
    mask: Optional[str] = None  # For ID fields
    prefix: Optional[str] = None  # For phone fields
    validation: Optional[FieldValidation] = None
    must_be_true: bool = False  # For checkbox fields
    ocr_field: bool = False  # Can be extracted via OCR
    error: Optional[str] = None


class DocumentSpec(BaseModel):
    """Specification for a required document."""
    type: str
    name: str
    requires_front: bool = True
    requires_back: bool = False
    accepted_formats: List[str] = ["jpg", "jpeg", "png"]
    max_size_mb: int = 5
    max_age_months: Optional[int] = None
    ocr_fields: List[str] = []
    tips: List[str] = []


class DocumentRequirement(BaseModel):
    """A document requirement category (e.g., Proof of Identity)."""
    label: str
    required: bool = True
    one_of: bool = False  # If true, user needs only ONE document from the list
    documents: List[DocumentSpec]


class IDOption(BaseModel):
    """An option for government ID (when one_of is true)."""
    id: str
    label: str
    fields: List[FormField]
    document: DocumentSpec


class FormCategory(BaseModel):
    """A category of form fields (e.g., Identity, Contact, Address)."""
    label: str
    order: int = 0
    description: Optional[str] = None
    required_fields: List[FormField] = []
    optional_fields: List[FormField] = []
    one_of: bool = False
    options: Optional[List[IDOption]] = None  # For one_of categories like GB gov ID


class ConditionalTrigger(BaseModel):
    """Trigger condition for conditional logic."""
    field: str
    value: Any


class ConditionalLogic(BaseModel):
    """Conditional logic rule."""
    trigger: ConditionalTrigger
    action: ActionType
    target: Optional[str] = None
    targets: Optional[List[str]] = None


class ValidationRules(BaseModel):
    """Country-specific validation rules."""
    cnic_checksum: bool = False
    aadhaar_verhoeff: bool = False
    pan_format: bool = False
    passport_format: bool = False
    driving_license_format: bool = False
    postcode_format: bool = False
    age_verification: bool = True
    address_matching: bool = True
    name_matching: bool = True


class ComplianceChecks(BaseModel):
    """Compliance checks to perform."""
    aml_screening: bool = True
    pep_check: bool = True
    sanctions_check: bool = True
    fatca: bool = False
    fca_appropriateness: bool = False


# =============================================================================
# COUNTRY SCHEMA MODEL
# =============================================================================

class CountryKYCSchema(BaseModel):
    """Complete KYC schema for a country."""
    country_code: str
    country_name: str
    flag: str
    default_nationality: str
    supported_languages: List[str]
    categories: Dict[str, FormCategory]
    document_requirements: Dict[str, DocumentRequirement]
    validation_rules: ValidationRules
    compliance_checks: ComplianceChecks
    conditional_logic: List[ConditionalLogic] = []

    def get_all_required_fields(self) -> List[FormField]:
        """Get all required fields across all categories."""
        fields = []
        for category in self.categories.values():
            fields.extend(category.required_fields)
        return fields

    def get_all_optional_fields(self) -> List[FormField]:
        """Get all optional fields across all categories."""
        fields = []
        for category in self.categories.values():
            fields.extend(category.optional_fields)
        return fields

    def get_category(self, category_name: str) -> Optional[FormCategory]:
        """Get a specific category by name."""
        return self.categories.get(category_name)

    def get_document_requirements_list(self) -> List[DocumentRequirement]:
        """Get list of all document requirements."""
        return list(self.document_requirements.values())


# =============================================================================
# GLOBAL SETTINGS MODEL
# =============================================================================

class GlobalSettings(BaseModel):
    """Global settings for the KYC system."""
    supported_countries: List[str]
    default_country: str
    session_timeout_minutes: int = 30
    max_upload_size_mb: int = 5
    accepted_image_formats: List[str] = ["jpg", "jpeg", "png"]
    enable_ocr_validation: bool = True
    enable_liveness_check: bool = False


# =============================================================================
# SCHEMA LOADER CLASS
# =============================================================================

class KYCSchemaLoader:
    """Loads and manages KYC schemas for different countries."""
    
    _instance = None
    _schemas: Dict[str, CountryKYCSchema] = {}
    _global_settings: Optional[GlobalSettings] = None
    _loaded = False
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_schemas(self, config_path: Optional[str] = None) -> None:
        """Load all country schemas from JSON config file."""
        if self._loaded:
            return
            
        if config_path is None:
            # Default path relative to this file
            config_path = Path(__file__).parent / "kyc_schemas.json"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"KYC schema config not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Load global settings
        if "global_settings" in data:
            self._global_settings = GlobalSettings(**data["global_settings"])
        
        # Load country schemas
        for country_code, country_data in data.get("countries", {}).items():
            try:
                schema = CountryKYCSchema(**country_data)
                self._schemas[country_code] = schema
            except Exception as e:
                print(f"Warning: Failed to load schema for {country_code}: {e}")
        
        self._loaded = True
    
    def get_schema(self, country_code: str) -> Optional[CountryKYCSchema]:
        """Get schema for a specific country."""
        self.load_schemas()
        return self._schemas.get(country_code.upper())
    
    def get_all_countries(self) -> List[Dict[str, str]]:
        """Get list of all supported countries."""
        self.load_schemas()
        return [
            {
                "code": schema.country_code,
                "name": schema.country_name,
                "flag": schema.flag
            }
            for schema in self._schemas.values()
        ]
    
    def get_global_settings(self) -> Optional[GlobalSettings]:
        """Get global settings."""
        self.load_schemas()
        return self._global_settings
    
    def is_country_supported(self, country_code: str) -> bool:
        """Check if a country is supported."""
        self.load_schemas()
        return country_code.upper() in self._schemas


# =============================================================================
# FIELD VALIDATOR CLASS
# =============================================================================

class FieldValidator:
    """Validates form field values against their schemas."""
    
    @staticmethod
    def validate_field(field: FormField, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a single field value.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required
        if field.required and (value is None or value == ""):
            return False, f"{field.label} is required"
        
        # Empty optional fields are valid
        if value is None or value == "":
            return True, None
        
        # Type-specific validation
        if field.type == FieldType.EMAIL:
            return FieldValidator._validate_email(value, field)
        elif field.type == FieldType.TEL:
            return FieldValidator._validate_phone(value, field)
        elif field.type == FieldType.DATE:
            return FieldValidator._validate_date(value, field)
        elif field.type == FieldType.CHECKBOX:
            return FieldValidator._validate_checkbox(value, field)
        elif field.type == FieldType.BOOLEAN:
            return FieldValidator._validate_boolean(value, field)
        elif field.type in [FieldType.TEXT, FieldType.ID]:
            return FieldValidator._validate_text(value, field)
        elif field.type == FieldType.SELECT:
            return FieldValidator._validate_select(value, field)
        
        return True, None
    
    @staticmethod
    def _validate_email(value: str, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if field.validation and field.validation.pattern:
            pattern = field.validation.pattern
        
        if not re.match(pattern, value):
            error = field.validation.error if field.validation else "Invalid email format"
            return False, error
        return True, None
    
    @staticmethod
    def _validate_phone(value: str, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate phone number format."""
        if not field.validation:
            return True, None
        
        if field.validation.pattern:
            if not re.match(field.validation.pattern, value):
                return False, field.validation.error
        
        return True, None
    
    @staticmethod
    def _validate_date(value: Any, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate date and age requirements."""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return False, "Invalid date format"
        
        if not isinstance(value, date):
            return False, "Invalid date"
        
        if field.validation:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            
            if field.validation.min_age and age < field.validation.min_age:
                return False, field.validation.error or f"Must be at least {field.validation.min_age} years old"
            
            if field.validation.max_age and age > field.validation.max_age:
                return False, field.validation.error or f"Age cannot exceed {field.validation.max_age} years"
        
        return True, None
    
    @staticmethod
    def _validate_checkbox(value: Any, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate checkbox field."""
        if field.must_be_true and value != True:
            return False, field.error or "This field must be checked"
        return True, None
    
    @staticmethod
    def _validate_boolean(value: Any, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate boolean field."""
        if not isinstance(value, bool):
            return False, "Must be true or false"
        return True, None
    
    @staticmethod
    def _validate_text(value: str, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate text and ID fields."""
        if not field.validation:
            return True, None
        
        val = field.validation
        
        # Check length
        if val.length and len(value) != val.length:
            return False, val.error or f"Must be exactly {val.length} characters"
        
        if val.min_length and len(value) < val.min_length:
            return False, val.error or f"Must be at least {val.min_length} characters"
        
        if val.max_length and len(value) > val.max_length:
            return False, val.error or f"Must be at most {val.max_length} characters"
        
        # Check pattern
        if val.pattern:
            # Handle the case where value might have spaces (like Aadhaar)
            if not re.match(val.pattern, value, re.IGNORECASE):
                return False, val.error
        
        # Special checksum validations
        if val.checksum == "verhoeff":
            if not FieldValidator._validate_verhoeff(value.replace(" ", "")):
                return False, val.error or "Invalid checksum"
        
        return True, None
    
    @staticmethod
    def _validate_select(value: str, field: FormField) -> tuple[bool, Optional[str]]:
        """Validate select field."""
        if field.options and value not in field.options:
            return False, f"Invalid selection. Must be one of: {', '.join(field.options)}"
        return True, None
    
    @staticmethod
    def _validate_verhoeff(number: str) -> bool:
        """Validate Aadhaar number using Verhoeff algorithm."""
        # Verhoeff multiplication table
        d = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        ]
        
        # Permutation table
        p = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
        ]
        
        try:
            c = 0
            for i, char in enumerate(reversed(number)):
                c = d[c][p[i % 8][int(char)]]
            return c == 0
        except (ValueError, IndexError):
            return False


# =============================================================================
# FORM DATA VALIDATOR
# =============================================================================

class FormDataValidator:
    """Validates complete form submissions against country schemas."""
    
    def __init__(self, schema: CountryKYCSchema):
        self.schema = schema
        self.field_validator = FieldValidator()
    
    def validate_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete form data.
        
        Returns:
            Dict with:
                - is_valid: bool
                - errors: Dict[field_id, error_message]
                - warnings: List[str]
                - missing_required: List[str]
        """
        errors = {}
        warnings = []
        missing_required = []
        
        # Validate all required fields
        for field in self.schema.get_all_required_fields():
            # Skip readonly fields that have a default value - they're auto-populated
            if field.readonly and field.default is not None:
                continue
            
            value = form_data.get(field.id)
            
            if value is None or value == "":
                missing_required.append(field.id)
                errors[field.id] = f"{field.label} is required"
            else:
                is_valid, error = self.field_validator.validate_field(field, value)
                if not is_valid:
                    errors[field.id] = error
        
        # Validate optional fields that have values
        for field in self.schema.get_all_optional_fields():
            value = form_data.get(field.id)
            if value is not None and value != "":
                is_valid, error = self.field_validator.validate_field(field, value)
                if not is_valid:
                    errors[field.id] = error
        
        # Check conditional logic for additional requirements
        for condition in self.schema.conditional_logic:
            trigger_value = form_data.get(condition.trigger.field)
            if trigger_value == condition.trigger.value:
                if condition.action == ActionType.REQUIRE_FIELD:
                    if condition.target and not form_data.get(condition.target):
                        errors[condition.target] = "This field is required based on your selections"
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "missing_required": missing_required
        }
    
    def get_visible_fields(self, form_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Determine which fields should be visible based on conditional logic.
        
        Returns:
            Dict with category_name -> list of visible field IDs
        """
        visible = {}
        hidden = set()
        shown = set()
        
        # Evaluate conditional logic
        for condition in self.schema.conditional_logic:
            trigger_value = form_data.get(condition.trigger.field)
            
            if trigger_value == condition.trigger.value:
                if condition.action == ActionType.SHOW_FIELD and condition.target:
                    shown.add(condition.target)
                elif condition.action == ActionType.SHOW_FIELDS and condition.targets:
                    shown.update(condition.targets)
                elif condition.action == ActionType.HIDE_FIELD and condition.target:
                    hidden.add(condition.target)
        
        # Build visible fields per category
        for cat_name, category in self.schema.categories.items():
            visible[cat_name] = []
            
            for field in category.required_fields + category.optional_fields:
                # Field is visible if:
                # 1. Not in hidden set, AND
                # 2. Either in shown set OR is a base field (not conditional)
                if field.id not in hidden:
                    visible[cat_name].append(field.id)
            
            # Add conditionally shown fields
            for field_id in shown:
                if field_id not in visible[cat_name]:
                    visible[cat_name].append(field_id)
        
        return visible


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_schema_loader() -> KYCSchemaLoader:
    """Get the singleton schema loader instance."""
    return KYCSchemaLoader()


def get_country_schema(country_code: str) -> Optional[CountryKYCSchema]:
    """Get schema for a specific country."""
    return get_schema_loader().get_schema(country_code)


def validate_kyc_form(country_code: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate KYC form data for a country."""
    schema = get_country_schema(country_code)
    if not schema:
        return {
            "is_valid": False,
            "errors": {"_form": f"Unsupported country: {country_code}"},
            "warnings": [],
            "missing_required": []
        }
    
    validator = FormDataValidator(schema)
    return validator.validate_form(form_data)


def get_supported_countries() -> List[Dict[str, str]]:
    """Get list of supported countries."""
    return get_schema_loader().get_all_countries()


# =============================================================================
# EXPORT SCHEMA AS JSON (for API responses)
# =============================================================================

def export_schema_json(country_code: str) -> Optional[Dict[str, Any]]:
    """Export country schema as JSON-serializable dict."""
    schema = get_country_schema(country_code)
    if not schema:
        return None
    
    return {
        "country_code": schema.country_code,
        "country_name": schema.country_name,
        "flag": schema.flag,
        "required_fields": [f.model_dump() for f in schema.get_all_required_fields()],
        "optional_fields": [f.model_dump() for f in schema.get_all_optional_fields()],
        "document_requirements": {
            k: v.model_dump() for k, v in schema.document_requirements.items()
        },
        "validation_rules": schema.validation_rules.model_dump(),
        "compliance_checks": schema.compliance_checks.model_dump(),
        "conditional_logic": [c.model_dump() for c in schema.conditional_logic]
    }
