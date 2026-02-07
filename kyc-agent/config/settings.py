"""
Configuration settings for the KYC Agent application.
Uses pydantic-settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key (required)")
    GROQ_API_KEY: Optional[str] = Field(None, description="Groq API Key (optional backup)")
    
    # Application Mode
    DEBUG: bool = Field(True, description="Enable debug mode")
    DEMO_MODE: bool = Field(True, description="Use mock Deriv responses (no real account needed)")
    
    # Deriv Configuration
    DERIV_APP_ID: int = Field(1089, description="Deriv API app_id (1089 = public demo)")
    DERIV_API_TOKEN: Optional[str] = Field(None, description="Deriv API token for authenticated calls")
    DERIV_WS_URL: str = Field(
        "wss://ws.derivws.com/websockets/v3",
        description="Deriv WebSocket URL"
    )
    DERIV_API_URL: str = Field(
        "https://api.deriv.com",
        description="Deriv REST API URL"
    )
    
    # Server Configuration
    HOST: str = Field("0.0.0.0", description="Server host")
    PORT: int = Field(8000, description="Server port")
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB: int = Field(10, description="Maximum file upload size in MB")
    ALLOWED_IMAGE_TYPES: list = Field(
        default=["image/jpeg", "image/png", "image/jpg"],
        description="Allowed image MIME types"
    )
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES: int = Field(30, description="Session timeout in minutes")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def validate_settings() -> tuple[bool, list[str]]:
    """
    Validate that all required settings are present.
    Returns (is_valid, list of missing/invalid settings).
    """
    issues = []
    
    try:
        s = settings
        
        # Check required API key
        if not s.GEMINI_API_KEY or s.GEMINI_API_KEY == "your_gemini_api_key_here":
            issues.append("GEMINI_API_KEY is missing or not configured")
        
        # Warn about optional keys
        if not s.GROQ_API_KEY:
            issues.append("GROQ_API_KEY not set (optional - used as backup)")
        
    except Exception as e:
        issues.append(f"Configuration error: {str(e)}")
    
    return len(issues) == 0 or (len(issues) == 1 and "optional" in issues[0].lower()), issues


# Load .env from project root
env_path = get_project_root() / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# On Streamlit Cloud, secrets are in .streamlit/secrets.toml
# Load them into os.environ so pydantic-settings can find them
try:
    import streamlit as st
    for key, value in st.secrets.items():
        if isinstance(value, str) and key not in os.environ:
            os.environ[key] = value
except Exception:
    pass

# Global settings instance
settings = Settings()
