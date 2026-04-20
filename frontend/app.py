"""
Streamlit Frontend - Enhanced Version
Provides user-friendly interface for dichromate concentration prediction
"""

import base64
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageDraw

# Page configuration
st.set_page_config(
    page_title="K2Cr2O7 Concentration Predictor",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration - Use environment variable or default to localhost
import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Initialize session state
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []
if 'last_result' not in st.session_state:
    st.session_state.last_result = None


def check_api_health():
    """Check API service status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_model_info():
    """Get model information"""
    try:
        response = requests.get(f"{API_BASE_URL}/model/info", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def predict_concentration(image_bytes, ph):
    """Call API for prediction"""
    try:
        files = {"image": ("image.jpg", image_bytes, "image/jpeg")}
        data = {"ph": ph}
        
        response = requests.post(
            f"{API_BASE_URL}/predict",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Unknown error")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend service. Please ensure API is running."}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


def draw_roi_on_image(image, roi_info=None):
    """Draw ROI rectangle on image for visualization"""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    width, height = img_copy.size
    # Draw center region as ROI (40% of image)
    cx, cy = width // 2, height // 2
    rw, rh = int(width * 0.4), int(height * 0.6)
    x1, y1 = cx - rw // 2, cy - rh // 2
    x2, y2 = cx + rw // 2, cy + rh // 2
    
    draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
    return img_copy


def display_color_visualization(rgb_values):
    """Display color visualization"""
    r, g, b = rgb_values
    # Normalize to 0-1 range for display
    color_hex = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    
    st.markdown(f"""
    <div style="
        background-color: {color_hex};
        width: 100%;
        height: 60px;
        border-radius: 8px;
        border: 2px solid #ddd;
        margin: 10px 0;
    "></div>
    """, unsafe_allow_html=True)


def main():
    # Sidebar
    with st.sidebar:
        st.title("🧪 K2Cr2O7 Predictor")
        st.markdown("---")
        
        # API status
        api_healthy = check_api_health()
        if api_healthy:
            st.success("✅ API Service Online")
        else:
            st.error("❌ API Service Offline")
            st.info("Start backend:\n```\ncd backend\nuvicorn main:app --reload\n```")
        
        # Model info
        model_info = get_model_info() if api_healthy else None
        if model_info:
            with st.expander("📊 Model Info"):
                st.write(f"**Type:** {model_info.get('model_type', 'N/A')}")
                st.write(f"**Features:** {model_info.get('feature_count', 'N/A')}")
                st.write(f"**Trees:** {model_info.get('n_estimators', 'N/A')}")
                ph_range = model_info.get('valid_ph_range', (2, 12))
                st.write(f"**pH Range:** {ph_range[0]} - {ph_range[1]}")
        
        st.markdown("---")
        st.markdown("### 📖 Instructions")
        st.markdown("""
        1. Upload cuvette photo
        2. Enter solution pH value
        3. Click Predict button
        4. View results
        """)
        
        st.markdown("---")
        st.markdown("### ⚠️ Tips")
        st.markdown("""
        - Use uniform lighting
        - White background recommended
        - Ensure cuvette is clear
        - pH range: 2-12
        """)
        
        # Prediction history
        if st.session_state.prediction_history:
            st.markdown("---")
            st.markdown("### 📜 History")
            for i, record in enumerate(reversed(st.session_state.prediction_history[-5:])):
                st.write(f"{i+1}. {record['time']}: {record['conc']:.3f} mM (pH {record['ph']})")
    
    # Main content
    st.title("🧪 Potassium Dichromate Concentration Prediction")
    st.markdown("Intelligent chemical concentration detection based on machine learning")
    
    # Create tabs
    tab1, tab2 = st.tabs(["🔮 Prediction", "📚 Batch Processing"])
    
    with tab1:
        # Two column layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📷 Upload Image")
            
            # Image upload
            uploaded_file = st.file_uploader(
                "Select cuvette photo",
                type=["jpg", "jpeg", "png", "tif", "tiff"],
                help="Supports JPG, PNG, TIF formats"
            )
            
            # pH input with slider and number
            st.markdown("**pH Value**")
            ph_col1, ph_col2 = st.columns([3, 1])
            with ph_col1:
                ph_slider = st.slider("pH", 0.0, 14.0, 7.0, 0.1, label_visibility="collapsed")
            with ph_col2:
                ph_value = st.number_input("pH", 0.0, 14.0, ph_slider, 0.1, label_visibility="collapsed")
            
            # Sync slider and number input
            ph_value = ph_slider
            
            # Advanced options
            with st.expander("⚙️ Advanced Options"):
                show_roi = st.checkbox("Show ROI Region", value=True)
                show_features = st.checkbox("Show Feature Details", value=True)
            
            # Predict button
            predict_button = st.button(
                "🔮 Start Prediction",
                type="primary",
                disabled=uploaded_file is None or not api_healthy,
                use_container_width=True
            )
        
        with col2:
            st.subheader("📊 Results")
            
            if uploaded_file is not None:
                # Display uploaded image
                image = Image.open(uploaded_file)
                
                if show_roi:
                    display_image = draw_roi_on_image(image)
                    st.image(display_image, caption="Uploaded Image (ROI marked in red)", use_container_width=True)
                else:
                    st.image(image, caption="Uploaded Image", use_container_width=True)
                
                # Reset file pointer
                uploaded_file.seek(0)
            else:
                st.info("👈 Please upload a cuvette photo first")
        
        # Execute prediction
        if predict_button and uploaded_file is not None:
            with st.spinner("Analyzing image and predicting concentration..."):
                image_bytes = uploaded_file.read()
                result = predict_concentration(image_bytes, ph_value)
            
            if "error" in result:
                st.error(f"❌ {result['error']}")
            else:
                # Store result
                st.session_state.last_result = result
                st.session_state.prediction_history.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'conc': result['concentration'],
                    'ph': ph_value,
                    'conf': result['confidence']
                })
                
                # Display results
                st.success("✅ Prediction Complete!")
                
                # Result cards
                st.markdown("---")
                
                concentration = result.get("concentration", 0)
                confidence = result.get("confidence", 0)
                
                # Main metrics
                rcol1, rcol2, rcol3, rcol4 = st.columns(4)
                
                with rcol1:
                    st.metric(
                        label="Concentration",
                        value=f"{concentration:.4f} mM"
                    )
                
                with rcol2:
                    conf_pct = f"{confidence:.1%}"
                    st.metric(label="Confidence", value=conf_pct)
                
                with rcol3:
                    if confidence > 0.8 and not result.get("warnings"):
                        reliability = "High"
                    elif confidence > 0.5:
                        reliability = "Medium"
                    else:
                        reliability = "Low"
                    st.metric(label="Reliability", value=reliability)
                
                with rcol4:
                    # Calculate approximate absorbance (simplified)
                    features = result.get("features_used", {})
                    if features and "rgb" in features:
                        rgb = features["rgb"]
                        avg_intensity = sum(rgb) / 3
                        st.metric(label="Avg Intensity", value=f"{avg_intensity:.1f}")
                
                # Warnings
                warnings = result.get("warnings", [])
                if warnings:
                    st.markdown("---")
                    st.warning("⚠️ Warnings")
                    for warning in warnings:
                        st.markdown(f"- {warning}")
                
                # Feature details
                if show_features:
                    st.markdown("---")
                    with st.expander("🔍 Feature Details", expanded=True):
                        features = result.get("features_used", {})
                        
                        if features:
                            feat_col1, feat_col2, feat_col3 = st.columns(3)
                            
                            with feat_col1:
                                st.markdown("**RGB Features**")
                                rgb = features.get("rgb", [0, 0, 0])
                                display_color_visualization(rgb)
                                st.write(f"R: {rgb[0]:.1f}")
                                st.write(f"G: {rgb[1]:.1f}")
                                st.write(f"B: {rgb[2]:.1f}")
                            
                            with feat_col2:
                                st.markdown("**HSV Features**")
                                hsv = features.get("hsv", [0, 0, 0])
                                st.write(f"H: {hsv[0]:.1f}")
                                st.write(f"S: {hsv[1]:.1f}")
                                st.write(f"V: {hsv[2]:.1f}")
                            
                            with feat_col3:
                                st.markdown("**Lab Features**")
                                lab = features.get("lab", [0, 0, 0])
                                st.write(f"L: {lab[0]:.1f}")
                                st.write(f"a: {lab[1]:.1f}")
                                st.write(f"b: {lab[2]:.1f}")
                            
                            st.markdown(f"**pH:** {features.get('ph', 'N/A')}")
                
                # Export option
                st.markdown("---")
                result_json = json.dumps(result, indent=2)
                st.download_button(
                    label="📥 Download Result (JSON)",
                    data=result_json,
                    file_name=f"prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with tab2:
        st.subheader("📚 Batch Processing")
        st.info("Upload multiple images for batch prediction (coming soon)")
        
        batch_files = st.file_uploader(
            "Select multiple images",
            type=["jpg", "jpeg", "png", "tif"],
            accept_multiple_files=True
        )
        
        if batch_files:
            st.write(f"Selected {len(batch_files)} files")
            
            batch_ph = st.number_input("pH value for all samples", 0.0, 14.0, 7.0, 0.1)
            
            if st.button("Process Batch", disabled=not api_healthy):
                progress_bar = st.progress(0)
                batch_results = []
                
                for i, file in enumerate(batch_files):
                    progress_bar.progress((i + 1) / len(batch_files))
                    
                    image_bytes = file.read()
                    result = predict_concentration(image_bytes, batch_ph)
                    
                    if "error" not in result:
                        batch_results.append({
                            "File": file.name,
                            "Concentration (mM)": result["concentration"],
                            "Confidence": result["confidence"]
                        })
                
                if batch_results:
                    df = pd.DataFrame(batch_results)
                    st.dataframe(df)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="batch_results.csv",
                        mime="text/csv"
                    )
    
    # Footer
    st.markdown("---")
    st.caption("🔬 K2Cr2O7 Concentration Prediction System | Based on Random Forest Machine Learning Model")


if __name__ == "__main__":
    main()
