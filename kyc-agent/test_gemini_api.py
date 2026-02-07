"""
Quick test script to verify Gemini API connectivity and model availability.
Run this to debug API issues.

Usage: python test_gemini_api.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {env_path}")
else:
    print(f"✗ No .env file found at: {env_path}")

# Check API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"✓ GEMINI_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
else:
    print("✗ GEMINI_API_KEY not found in environment")
    sys.exit(1)

# Test Gemini API
print("\n--- Testing Gemini API ---")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    print("✓ Gemini API configured")
except Exception as e:
    print(f"✗ Failed to configure Gemini: {e}")
    sys.exit(1)

# List available models
print("\n--- Available Models ---")
try:
    models = list(genai.list_models())
    for model in models:
        supported = "generateContent" in [m.name for m in model.supported_generation_methods] if hasattr(model, 'supported_generation_methods') else "unknown"
        print(f"  - {model.name}")
except Exception as e:
    print(f"✗ Failed to list models: {e}")

# Test each model
print("\n--- Testing Models ---")
test_models = [
    'models/gemini-2.5-flash',
    'models/gemini-2.0-flash',
    'models/gemini-2.0-flash-001',
    'models/gemini-2.5-pro',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
]

working_model = None
for model_name in test_models:
    try:
        print(f"\nTesting {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Reply with just 'OK'")
        if response and response.text:
            print(f"  ✓ {model_name} works! Response: {response.text.strip()}")
            if working_model is None:
                working_model = model_name
        else:
            print(f"  ? {model_name} returned empty response")
    except Exception as e:
        print(f"  ✗ {model_name} failed: {str(e)[:100]}")

if working_model:
    print(f"\n✓ SUCCESS: Use model '{working_model}' for your application")
else:
    print("\n✗ FAILED: No working model found. Check your API key and quota.")

# Test with an image (if a test image exists)
print("\n--- Testing Vision Capability ---")
test_image_path = project_root / "test_image.jpg"
if test_image_path.exists():
    try:
        import base64
        with open(test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        model = genai.GenerativeModel(working_model or 'gemini-1.5-flash')
        response = model.generate_content([
            "What do you see in this image? Reply briefly.",
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        print(f"  ✓ Vision test successful: {response.text[:100]}...")
    except Exception as e:
        print(f"  ✗ Vision test failed: {e}")
else:
    print(f"  - No test image at {test_image_path}, skipping vision test")

print("\n--- Test Complete ---")
