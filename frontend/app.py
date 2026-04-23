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


def predict(image_bytes, ph, skip_preprocessing=False, filename="image.png"):
    """Call API"""
    try:
        # 根据文件名确定MIME类型
        if filename.lower().endswith(('.tif', '.tiff')):
            mimetype = "image/tiff"
        elif filename.lower().endswith('.png'):
            mimetype = "image/png"
        else:
            mimetype = "image/jpeg"
        
        files = {"image": (filename, image_bytes, mimetype)}
        data = {"ph": ph, "skip_preprocessing": skip_preprocessing}
        response = requests.post(
            f"{API_BASE_URL}/predict",
            files=files,
            data=data,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            # 返回详细错误信息
            try:
                error_detail = response.json().get('detail', response.text)
            except:
                error_detail = response.text or f"HTTP {response.status_code}"
            return {"error": f"API Error ({response.status_code}): {error_detail}"}
    except Exception as e:
        return {"error": str(e)}


def calculate_species_exact(C_total, pH, Ka1=0.0294, Ka2=1.26e-6):
    """
    精确计算铬物种浓度（基于化学平衡常数）
    
    反应体系：
    1) H2CrO4 ⇌ H+ + HCrO4-     Ka1 = 2.94×10^-2
    2) HCrO4- ⇌ H+ + CrO4^2-    Ka2 = 1.26×10^-6
    3) 2HCrO4- ⇌ Cr2O7^2- + H2O  K_dimer = 10^2.2 = 1.58×10^1
    
    物料平衡：
    C_total = [H2CrO4] + [HCrO4-] + [CrO4^2-] + 2[Cr2O7^2-]
    """
    import math
    
    H = 10**(-pH)
    
    # 平衡常数（科学计数法表示）
    Ka1 = 2.94e-2      # H2CrO4 ⇌ H+ + HCrO4-
    Ka2 = 1.26e-6      # HCrO4- ⇌ H+ + CrO4^2-
    K_dimer = 1.58e1   # 2HCrO4- ⇌ Cr2O7^2- + H2O (10^2.2)
    
    # 通过平衡常数建立方程组求解
    # 设 [HCrO4-] = x，则：
    # [Cr2O7^2-] = K_dimer * x^2 / [H2O] ≈ K_dimer * x^2 (水活度≈1)
    # [CrO4^2-] = Ka2 * x / [H+]
    # [H2CrO4] = x * [H+] / Ka1
    
    # 物料平衡方程：
    # C_total = [H2CrO4] + [HCrO4-] + [CrO4^2-] + 2[Cr2O7^2-]
    # C_total = x*[H+]/Ka1 + x + Ka2*x/[H+] + 2*K_dimer*x^2
    
    # 整理为关于 x 的二次方程：a*x^2 + b*x + c = 0
    a = 2 * K_dimer
    b = 1 + H/Ka1 + Ka2/H
    c = -C_total
    
    # 求解二次方程
    discriminant = b**2 - 4*a*c
    if discriminant >= 0:
        x = (-b + math.sqrt(discriminant)) / (2*a)  # [HCrO4-]
    else:
        # 退化为线性方程求解
        x = C_total / b
    
    # 通过平衡常数计算各组分浓度（科学计数法形式）
    HCrO4 = x                                          # [HCrO4-]
    Cr2O7 = K_dimer * x**2                            # [Cr2O7^2-]
    CrO4 = Ka2 * x / H                                # [CrO4^2-]
    H2CrO4 = x * H / Ka1                              # [H2CrO4]
    
    return {
        'HCrO4-': HCrO4,
        'CrO4^2-': CrO4,
        'Cr2O7^2-': Cr2O7,
        'H2CrO4': H2CrO4
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
        
        st.info("📋 Please use the solutions with concentrations between 1 mM and 8 mM and pH values between 2 and 12.")
        
        if uploaded:
            # 直接读取上传的图片（假设已裁剪好）
            image = Image.open(uploaded)
            
            st.markdown("### 📷 Selected Image")
            st.image(image, caption="Uploaded image (already cropped)", use_container_width=True)
            
            # 直接使用上传的图片
            st.session_state.cropped_image = image
            
            # DEBUG: 打印图片信息
            print(f"DEBUG - 上传图片尺寸: {image.size}")
            print(f"DEBUG - 上传图片模式: {image.mode}")
        
        ph = st.slider("pH", 2.0, 12.0, 7.0, 0.1)
        
        # 默认跳过自动预处理（用户已手动裁剪）
        skip_preprocessing = True
        
        # Predict button
        predict_clicked = st.button("🔮 Predict", disabled=not (uploaded and api_ok))
        
        if predict_clicked and uploaded and st.session_state.cropped_image:
            with st.spinner("Analyzing... (may take up to 60s on first request)"):
                # Use cropped image
                img_byte_arr = io.BytesIO()
                cropped = st.session_state.cropped_image
                
                # 获取原始文件格式
                original_name = uploaded.name.lower()
                
                # 根据原始格式保存，避免格式转换导致颜色失真
                if original_name.endswith('.tif') or original_name.endswith('.tiff'):
                    # TIF格式：保持原样或转换为PNG（TIF可能包含特殊信息）
                    if cropped.mode == 'RGBA':
                        cropped = cropped.convert('RGB')
                    cropped.save(img_byte_arr, format='TIFF')
                    img_format = 'TIFF'
                else:
                    # 其他格式：转换为PNG
                    if cropped.mode == 'RGBA':
                        cropped = cropped.convert('RGB')
                    cropped.save(img_byte_arr, format='PNG')
                    img_format = 'PNG'
                
                img_byte_arr.seek(0)
                
                # DEBUG: 打印图片信息
                print(f"DEBUG - 原始格式: {original_name}")
                print(f"DEBUG - 发送格式: {img_format}")
                print(f"DEBUG - 图片模式: {cropped.mode}")
                print(f"DEBUG - 图片尺寸: {cropped.size}")
                print(f"DEBUG - 发送图片大小: {len(img_byte_arr.getvalue())} bytes")
                
                result = predict(img_byte_arr.getvalue(), ph, skip_preprocessing, uploaded.name)
            
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
                
                # 显示使用的pH子模型
                ph_model_used = result.get('ph_model_used')
                if ph_model_used:
                    st.caption(f"使用 pH={ph_model_used} 专属模型")
                
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
