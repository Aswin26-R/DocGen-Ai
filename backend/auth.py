import streamlit as st
import hashlib
import os
from typing import Optional

def hash_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def check_authentication() -> bool:
    """Check if user is authenticated with valid API key"""
    return 'authenticated' in st.session_state and st.session_state.authenticated

def validate_gemini_key(api_key: str) -> bool:
    """Validate Gemini API key format (basic validation)"""
    if not api_key:
        return False
    
    # Basic format validation - Gemini keys typically start with certain patterns
    if len(api_key) < 20:
        return False
    
    # Additional validation could be added here
    return True

def authenticate_user(api_key: str) -> bool:
    """Authenticate user with Gemini API key"""
    if validate_gemini_key(api_key):
        st.session_state.authenticated = True
        st.session_state.gemini_api_key = api_key
        st.session_state.user_id = hash_key(api_key)[:12]  # Use first 12 chars of hash as user ID
        return True
    return False

def logout():
    """Log out user and clear session"""
    keys_to_remove = [
        'authenticated', 'gemini_api_key', 'user_id', 'documents', 
        'summaries', 'quiz_history', 'activity_log'
    ]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

def render_login():
    """Render the login interface"""
    st.title("🔐 Login to DocGen")
    st.markdown("---")
    
    st.info("""
    **Welcome to DocGen!** 
    
    To get started, please enter your Google Gemini API key. Your key is stored securely in your session and is not persisted.
    
    **Don't have an API key?** 
    1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
    2. Create a free account
    3. Generate your API key
    """)
    
    with st.form("login_form"):
        api_key = st.text_input(
            "Gemini API Key", 
            type="password",
            placeholder="Enter your Gemini API key",
            help="Your API key will be stored securely in your session only"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("🚀 Start Learning", use_container_width=True)
        
        with col2:
            if st.form_submit_button("ℹ️ How to get API key", use_container_width=True):
                st.info("""
                **Steps to get your Gemini API key:**
                1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
                2. Sign in with your Google account
                3. Click "Create API key"
                4. Copy the generated key and paste it above
                """)
    
    if submitted:
        if api_key:
            with st.spinner("Validating API key..."):
                if authenticate_user(api_key):
                    st.success("✅ Authentication successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Invalid API key. Please check your key and try again.")
        else:
            st.error("Please enter your Gemini API key.")

def render_logout_button():
    """Render logout button in sidebar"""
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
        
        # Display user info
        if 'user_id' in st.session_state:
            st.caption(f"👤 User: {st.session_state.user_id}")
