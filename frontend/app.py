"""
Streamlit Frontend - Fixed Timeout Version
"""

import json
from datetime import datetime

import requests
import streamlit as st
from PIL import Image
import os

# Page configuration
st.set_page_config(
    page_title="K2Cr2O7 Concentration Predictor",
    page_icon="🧪",
    layout="wide"
)

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []


def check_api():
    """Check API status with longer timeout for Render cold start"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=60)
        return response.status_code == 200
    except:
        return False


def predict(image_bytes, ph):
    """Call API with longer timeout"""
    try:
        files = {"image": ("image.jpg", image_bytes, "image/jpeg")}
        data = {"ph": ph}
        response = requests.post(
            f"{API_BASE_URL}/predict",
            files=files,
            data=data,
            timeout=60
        )
        return response.json() if response.status_code == 200 else {"error": "API error"}
    except Exception as e:
        return {"error": str(e)}


def main():
    # Sidebar
    with st.sidebar:
        st.title("🧪 K2Cr2O7 Predictor")
        
        st.markdown("### API Status")
        
        # Check API with loading indicator
        with st.spinner("Connecting to API..."):
            api_ok = check_api()
        
        if api_ok:
            st.success("✅ API Online")
        else:
            st.error("❌ API Offline")
            st.info("The backend may be waking up from sleep. Please wait 30-60 seconds and refresh the page.")
        
        st.markdown("---")
        st.markdown("### Instructions")
        st.markdown("1. Upload photo")
        st.markdown("2. Enter pH")
        st.markdown("3. Click Predict")
        
        if st.session_state.history:
            st.markdown("---")
            st.markdown("### History")
            for h in st.session_state.history[-5:]:
                st.write(f"{h['time']}: {h['conc']:.3f} mM")
    
    # Main
    st.title("🧪 Potassium Dichromate Concentration Prediction")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 Upload")
        
        uploaded = st.file_uploader(
            "Select photo",
            type=["jpg", "jpeg", "png", "tif"]
        )
        
        ph = st.slider("pH", 0.0, 14.0, 7.0, 0.1)
        
        # Always allow button, but show warning if API is offline
        predict_clicked = st.button("🔮 Predict", disabled=not uploaded)
        
        if predict_clicked and uploaded:
            if not api_ok:
                st.warning("API is offline. Attempting to wake up the backend (this may take 30-60 seconds)...")
            
            with st.spinner("Analyzing... (may take up to 60s on first request)"):
                image_bytes = uploaded.read()
                result = predict(image_bytes, ph)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
                if "timeout" in result['error'].lower():
                    st.info("The backend is waking up from sleep. Please wait a moment and try again.")
            else:
                st.session_state.history.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'conc': result['concentration'],
                    'ph': ph
                })
                
                st.success("Done!")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Concentration", f"{result['concentration']:.4f} mM")
                with c2:
                    st.metric("Confidence", f"{result['confidence']:.1%}")
                with c3:
                    rel = "High" if result['confidence'] > 0.8 else "Medium" if result['confidence'] > 0.5 else "Low"
                    st.metric("Reliability", rel)
                
                if result.get('warnings'):
                    for w in result['warnings']:
                        st.warning(w)
    
    with col2:
        st.subheader("📊 Preview")
        if uploaded:
            st.image(uploaded, caption="Uploaded", use_container_width=True)
        else:
            st.info("Upload a photo")
    
    st.markdown("---")
    st.caption("K2Cr2O7 Prediction System | ML-based")


if __name__ == "__main__":
    main()
