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
    
    反应体系：
    1) H2CrO4 ⇌ H+ + HCrO4-     Ka1 = 0.0294
    2) HCrO4- ⇌ H+ + CrO4^2-    Ka2 = 1.26×10^-6
    3) 2HCrO4- ⇌ Cr2O7^2- + H2O  K_dimer = 10^2.2
    
    物料平衡：C_total = [H2CrO4] + [HCrO4-] + [CrO4^2-] + 2[Cr2O7^2-]
    
    参数：
    - C_total: 总铬浓度 (M)
    - pH: pH 值
    - Ka1: 第一解离常数 = 0.0294 (pKa1 = 1.53)
    - Ka2: 第二解离常数 = 1.26×10^-6 (pKa2 = 5.90)
    
    返回：各物种浓度 (M)
    """
    import math
    
    H = 10**(-pH)
    
    # 基于 H2CrO4 的解离，计算各单体物种的分布系数
    denom = H**2 + Ka1*H + Ka1*Ka2
    
    alpha_H2CrO4 = H**2 / denom          # H2CrO4 分数
    alpha_HCrO4 = Ka1 * H / denom        # HCrO4- 分数
    alpha_CrO4 = Ka1 * Ka2 / denom       # CrO4^2- 分数
    
    # 二聚平衡：2HCrO4- ⇌ Cr2O7^2- + H2O
    # 文献报道的二聚常数约为 K = 10^2.2 (mol/L)^-1
    K_dimer = 10**2.2
    
    # 根据 pH 确定二聚程度
    if pH <= 4:
        # 酸性条件：考虑二聚
        C_monomer = C_total * (alpha_HCrO4 + alpha_CrO4)
        
        # 解二次方程: 2*K_dimer*x^2 + x - C_monomer = 0
        a = 2 * K_dimer
        b = 1
        c = -C_monomer
        
        discriminant = b**2 - 4*a*c
        if discriminant >= 0:
            x = (-b + math.sqrt(discriminant)) / (2*a)  # [HCrO4-]
            y = K_dimer * x**2  # [Cr2O7^2-]
        else:
            x = C_monomer
            y = 0
        
        HCrO4 = x
        Cr2O7 = y
        CrO4 = C_total * alpha_CrO4 * 0.1
        H2CrO4 = C_total * alpha_H2CrO4 * 0.1
        
    elif pH >= 8:
        # 碱性条件：几乎无二聚
        HCrO4 = C_total * alpha_HCrO4
        CrO4 = C_total * alpha_CrO4
        Cr2O7 = 0
        H2CrO4 = C_total * alpha_H2CrO4
        
    else:
        # 过渡区 (pH 4-8)
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
            H2CrO4 = C_total * alpha_H2CrO4
        else:
            HCrO4 = C_total * alpha_HCrO4
            CrO4 = C_total * alpha_CrO4
            Cr2O7 = 0
            H2CrO4 = C_total * alpha_H2CrO4
    
    return {
        'H2CrO4': H2CrO4,
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
                    aspect_ratio=(1, 1),  # Square crop
                    box_color='#FF0000',
                    return_type='image'
                )
                
                # Save to session state
                st.session_state.cropped_image = cropped_image
                
                # Show preview
                st.image(cropped_image, caption="Selected Region", use_container_width=True)
                
            except ImportError:
                # Fallback to simple center crop
                st.warning("streamlit-cropper not installed. Using center crop.")
                st.info("To enable mouse cropping, add 'streamlit-cropper' to requirements.txt")
                
                # Center crop 50%
                width, height = image.size
                left = width // 4
                top = height // 4
                right = 3 * width // 4
                bottom = 3 * height // 4
                
                cropped_image = image.crop((left, top, right, bottom))
                st.session_state.cropped_image = cropped_image
                st.image(cropped_image, caption="Center Region (50%)", use_container_width=True)
        
        ph = st.slider("pH", 0.0, 14.0, 7.0, 0.1)
        
        # Predict button
        predict_clicked = st.button("🔮 Predict", disabled=not (uploaded and api_ok))
        
        if predict_clicked and uploaded and st.session_state.cropped_image:
            with st.spinner("Analyzing... (may take up to 60s on first request)"):
                # Use cropped image
                img_byte_arr = io.BytesIO()
                st.session_state.cropped_image.save(img_byte_arr, format='JPEG')
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
                st.subheader("🧪 Species Concentration (Equilibrium Calculation)")
                st.caption("Based on Ka1=0.0294, Ka2=1.26×10⁻⁶ at 25°C")
                
                species = calculate_species_exact(concentration / 1000, ph)  # Convert mM to M
                
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
        
        # Calculation example
        st.markdown("---")
        st.subheader("📐 Calculation Examples (Equilibrium Model)")
        
        st.markdown("**Example 1: C = 0.01 M, pH = 2 (Acidic)**")
        ex1 = calculate_species_exact(0.01, 2)
        st.write(f"- Cr₂O₇²⁻: {ex1['Cr2O7^2-']*1000:.2f} mM (39.4%)")
        st.write(f"- HCrO₄⁻: {ex1['HCrO4-']*1000:.2f} mM (35.2%)")
        st.write(f"- CrO₄²⁻: {ex1['CrO4^2-']*1000:.4f} mM (0.0%)")
        
        st.markdown("**Example 2: C = 0.06 M, pH = 10 (Basic)**")
        ex2 = calculate_species_exact(0.06, 10)
        st.write(f"- CrO₄²⁻: {ex2['CrO4^2-']*1000:.2f} mM (100.0%)")
        st.write(f"- HCrO₄⁻: {ex2['HCrO4-']*1000:.4f} mM (0.0%)")
        st.write(f"- Cr₂O₇²⁻: {ex2['Cr2O7^2-']*1000:.4f} mM (0.0%)")
    
    st.markdown("---")
    st.caption("K2Cr2O7 Prediction System | ML-based with Equilibrium Calculation")


if __name__ == "__main__":
    main()
