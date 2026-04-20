"""
Streamlit Frontend with Mouse Cropper
"""

import io
from datetime import datetime
from PIL import Image

import requests
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="K2Cr2O7 Concentration Predictor",
    page_icon="🧪",
    layout="wide"
)

# API configuration
import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'cropped_image' not in st.session_state:
    st.session_state.cropped_image = None


def check_api():
    """Check API status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=60)
        return response.status_code == 200
    except:
        return False


def predict(image_bytes, ph):
    """Call API"""
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


def calculate_species_exact(C_total, pH, Ka1=0.0294, Ka2=1.26e-6):
    """
    精确计算铬物种浓度（基于化学平衡常数）
    """
    import math
    
    H = 10**(-pH)
    
    # 基于 H2CrO4 的解离，计算各单体物种的分布系数
    denom = H**2 + Ka1*H + Ka1*Ka2
    
    alpha_H2CrO4 = H**2 / denom
    alpha_HCrO4 = Ka1 * H / denom
    alpha_CrO4 = Ka1 * Ka2 / denom
    
    # 二聚平衡常数
    K_dimer = 10**2.2
    
    if pH <= 4:
        C_monomer = C_total * (alpha_HCrO4 + alpha_CrO4)
        a = 2 * K_dimer
        b = 1
        c = -C_monomer
        
        discriminant = b**2 - 4*a*c
        if discriminant >= 0:
            x = (-b + math.sqrt(discriminant)) / (2*a)
            y = K_dimer * x**2
        else:
            x = C_monomer
            y = 0
        
        HCrO4 = x
        Cr2O7 = y
        CrO4 = C_total * alpha_CrO4 * 0.1
        
    elif pH >= 8:
        HCrO4 = C_total * alpha_HCrO4
        CrO4 = C_total * alpha_CrO4
        Cr2O7 = 0
        
    else:
        f_dimer = (8 - pH) / 4
        C_monomer = C_total * (alpha_HCrO4 + alpha_CrO4)
        
        if f_dimer > 0:
            a = 2 * K_dimer * f_dimer
            b = 1
            c = -C_monomer
            
            discriminant = b**2 - 4*a*c
            if discriminant >= 0:
                x = (-b + math.sqrt(discriminant)) / (2*a)
                y = K_dimer * f_dimer * x**2
            else:
                x = C_monomer
                y = 0
            
            HCrO4 = x
            Cr2O7 = y
            CrO4 = C_total * alpha_CrO4 * (1 - f_dimer*0.5)
        else:
            HCrO4 = C_total * alpha_HCrO4
            CrO4 = C_total * alpha_CrO4
            Cr2O7 = 0
    
    return {
        'HCrO4-': HCrO4,
        'CrO4^2-': CrO4,
        'Cr2O7^2-': Cr2O7
    }


def main():
    # Sidebar
    with st.sidebar:
        st.title("🧪 K2Cr2O7 Predictor")
        
        st.markdown("### API Status")
        
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
        st.markdown("2. Draw box around cuvette")
        st.markdown("3. Enter pH")
        st.markdown("4. Click Predict")
        
        if st.session_state.history:
            st.markdown("---")
            st.markdown("### History")
            for h in st.session_state.history[-5:]:
                st.write(f"{h['time']}: {h['conc']:.3f} mM")
    
    # Main
    st.title("🧪 Potassium Dichromate Concentration Prediction")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📷 Upload & Crop")
        
        uploaded = st.file_uploader(
            "Select photo",
            type=["jpg", "jpeg", "png", "tif"]
        )
        
        if uploaded:
            # Load image
            image = Image.open(uploaded)
            
            # Try to use streamlit-cropper
            try:
                from streamlit_cropper import st_cropper
                
                st.markdown("### ✂️ Draw a box around the cuvette")
                
                # Show cropper
                cropped_image = st_cropper(
                    image,
                    aspect_ratio=None,  # Free aspect ratio
                    box_color='#FF0000',
                    return_type='image'
                )
                
                # Save to session state
                st.session_state.cropped_image = cropped_image
                
            except ImportError:
                # Fallback to simple center crop
                st.warning("streamlit-cropper not installed. Using center crop.")
                
                # Center crop 50%
                width, height = image.size
                left = width // 4
                top = height // 4
                right = 3 * width // 4
                bottom = 3 * height // 4
                
                cropped_image = image.crop((left, top, right, bottom))
                st.session_state.cropped_image = cropped_image
        
        ph = st.slider("pH", 0.0, 14.0, 7.0, 0.1)
        
        # Predict button
        predict_clicked = st.button("🔮 Predict", disabled=not (uploaded and api_ok))
        
        if predict_clicked and uploaded and st.session_state.cropped_image:
            with st.spinner("Analyzing... (may take up to 60s on first request)"):
                # Use cropped image
                img_byte_arr = io.BytesIO()
                # Convert RGBA to RGB if necessary
                cropped = st.session_state.cropped_image
                if cropped.mode == 'RGBA':
                    cropped = cropped.convert('RGB')
                cropped.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)
                
                result = predict(img_byte_arr.getvalue(), ph)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
                if "timeout" in result['error'].lower():
                    st.info("The backend is waking up from sleep. Please wait a moment and try again.")
            else:
                concentration = result['concentration']
                
                st.session_state.history.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'conc': concentration,
                    'ph': ph
                })
                
                st.success("Done!")
                
                # Display results
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Concentration", f"{concentration:.4f} mM")
                with c2:
                    st.metric("Confidence", f"{result['confidence']:.1%}")
                with c3:
                    rel = "High" if result['confidence'] > 0.8 else "Medium" if result['confidence'] > 0.5 else "Low"
                    st.metric("Reliability", rel)
                
                # Species calculation
                st.markdown("---")
                st.subheader("🧪 Species Concentration")
                
                species = calculate_species_exact(concentration / 1000, ph)
                
                sp_col1, sp_col2, sp_col3 = st.columns(3)
                with sp_col1:
                    st.metric("Cr₂O₇²⁻", f"{species['Cr2O7^2-']*1000:.4f} mM")
                with sp_col2:
                    st.metric("CrO₄²⁻", f"{species['CrO4^2-']*1000:.4f} mM")
                with sp_col3:
                    st.metric("HCrO₄⁻", f"{species['HCrO4-']*1000:.4f} mM")
                
                if result.get('warnings'):
                    for w in result['warnings']:
                        st.warning(w)
    
    with col2:
        st.subheader("📊 Preview")
        if uploaded and st.session_state.cropped_image:
            st.image(st.session_state.cropped_image, caption="Selected Region", use_container_width=True)
        else:
            st.info("Upload a photo and draw a box around the cuvette")
        
        # Reaction equations and formulas
        st.markdown("---")
        st.subheader("⚗️ Reaction Equations (Hydrolysis)")
        
        st.markdown("**Step 1: Cr₂O₇²⁻ hydrolysis**")
        st.latex(r"Cr_2O_7^{2-} + H_2O \rightleftharpoons 2HCrO_4^- \quad K_1 = 10^{-2.2}")
        
        st.markdown("**Step 2: HCrO₄⁻ hydrolysis**")
        st.latex(r"HCrO_4^- \rightleftharpoons H^+ + CrO_4^{2-} \quad K_2 = 1.26 \times 10^{-6}")
        
        st.markdown("---")
        st.subheader("📐 Calculation Formulas")
        
        st.markdown("**Equilibrium constants (25°C):**")
        st.latex(r"K_1 = \frac{[HCrO_4^-]^2}{[Cr_2O_7^{2-}]} = 10^{-2.2}")
        st.latex(r"K_2 = \frac{[H^+][CrO_4^{2-}]}{[HCrO_4^-]} = 1.26 \times 10^{-6}")
        
        st.markdown("**Mass balance:**")
        st.latex(r"C_{total} = 2[Cr_2O_7^{2-}] + [HCrO_4^-] + [CrO_4^{2-}]")
        
        st.markdown("**Species distribution:**")
        st.latex(r"[Cr_2O_7^{2-}] = \frac{[HCrO_4^-]^2}{K_1}")
        st.latex(r"[CrO_4^{2-}] = \frac{K_2[HCrO_4^-]}{[H^+]}")
    
    st.markdown("---")
    st.caption("K2Cr2O7 Prediction System | ML-based with Equilibrium Calculation")


if __name__ == "__main__":
    main()
