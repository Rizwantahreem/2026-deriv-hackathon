"""
Test script to verify form fixes

This script helps verify that the form data persistence issues have been resolved.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from frontend.dynamic_form import (
    init_form_state,
    get_all_form_data,
    set_form_value,
    get_form_value,
    sync_form_data_to_widgets
)

def test_form_persistence():
    """Test form data persistence"""
    
    # Initialize form state
    init_form_state("test")
    
    # Test data to simulate form input
    test_data = {
        "nationality": "Pakistani",
        "country_of_residence": "Pakistan", 
        "gender": "Female",
        "city": "Lahore",
        "province": "Punjab",
        "country": "Pakistan",
        "source_of_funds": "Business/Self-Employed",
        "politically_exposed_person": True,
        "terms_and_conditions_accepted": True
    }
    
    # Set form values
    for field_id, value in test_data.items():
        set_form_value(field_id, value, "test")
    
    # Verify data was stored
    stored_data = get_all_form_data("test")
    
    st.write("## Form Persistence Test")
    st.write("### Original Test Data:")
    st.json(test_data)
    
    st.write("### Stored Form Data:")
    st.json(stored_data)
    
    # Check if all data matches
    all_match = all(stored_data.get(k) == v for k, v in test_data.items())
    
    if all_match:
        st.success(" All form data persisted correctly!")
    else:
        st.error(" Form data persistence has issues")
        
        # Show differences
        for key, original_value in test_data.items():
            stored_value = stored_data.get(key)
            if stored_value != original_value:
                st.error(f"Mismatch for {key}: Expected {original_value}, Got {stored_value}")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Form Fixes Test",
        page_icon="🔧",
        layout="centered"
    )
    
    st.title("🔧 Form Data Persistence Test")
    
    test_form_persistence()