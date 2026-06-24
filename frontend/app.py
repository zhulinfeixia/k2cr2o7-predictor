"""
Streamlit frontend for chromium(VI) species prediction.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from streamlit_cropper import st_cropper


st.set_page_config(
    page_title="K2Cr2O7 Species Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
CONTENT_DIR = Path(__file__).parent / "content"
INTRODUCTION_FILE = CONTENT_DIR / "knowledge_summary.md"

PH_COLOR_POINTS = [
    {"ph": 3.0, "rgb": [177.93, 136.34, 50.14]},
    {"ph": 4.0, "rgb": [178.10, 136.61, 52.91]},
    {"ph": 5.0, "rgb": [183.09, 139.77, 49.16]},
    {"ph": 6.0, "rgb": [178.09, 139.62, 50.24]},
    {"ph": 7.0, "rgb": [182.19, 155.29, 59.58]},
    {"ph": 8.0, "rgb": [175.57, 159.75, 64.82]},
    {"ph": 9.0, "rgb": [173.19, 159.16, 65.06]},
    {"ph": 10.0, "rgb": [169.85, 156.63, 65.59]},
    {"ph": 11.0, "rgb": [168.15, 156.63, 67.19]},
    {"ph": 12.0, "rgb": [174.60, 161.99, 69.92]},
]


def init_state() -> None:
    defaults = {
        "history": [],
        "cropped_image": None,
        "original_image": None,
        "roi_selected": False,
        "last_prediction": None,
        "query_messages": [],
        "analysis_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def check_api() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def image_mimetype(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith((".tif", ".tiff")):
        return "image/tiff"
    if lowered.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def predict(image_bytes: bytes, ph: float, filename: str) -> Dict[str, Any]:
    try:
        files = {"image": (filename, image_bytes, image_mimetype(filename))}
        data = {"ph": ph}
        response = requests.post(
            f"{API_BASE_URL}/predict",
            files=files,
            data=data,
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        return {"error": f"API Error ({response.status_code}): {detail}"}
    except requests.RequestException as exc:
        return {"error": str(exc)}


def ask_llm(
    prompt: str,
    messages: List[Dict[str, str]],
    mode: str,
    prediction_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "prompt": prompt,
        "messages": messages,
        "mode": mode,
        "prediction_context": prediction_context or {},
    }
    try:
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        return {"reply": f"Chat API error ({response.status_code}): {detail}", "configured": False}
    except requests.RequestException as exc:
        return {"reply": f"Chat API unavailable: {exc}", "configured": False}


def render_chat_panel(
    title: str,
    state_key: str,
    mode: str,
    placeholder: str,
    prediction_context: Optional[Dict[str, Any]] = None,
) -> None:
    st.subheader(title)

    messages = st.session_state[state_key]
    if not messages:
        st.caption("大模型接口已预留，填入后端环境变量后即可使用。")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form(f"{state_key}_form", clear_on_submit=True):
        prompt = st.text_area("Message", placeholder=placeholder, label_visibility="collapsed", height=110)
        submitted = st.form_submit_button("Send")

    if submitted and prompt.strip():
        user_message = {"role": "user", "content": prompt.strip()}
        messages.append(user_message)
        with st.spinner("Waiting for model response..."):
            result = ask_llm(prompt.strip(), messages[:-1], mode, prediction_context)
        messages.append({"role": "assistant", "content": result.get("reply", "")})
        st.rerun()


def render_ph_equilibrium_simulator() -> None:
    color_points_js = PH_COLOR_POINTS
    html = f"""
    <div id="cr-sim-root">
      <style>
        #cr-sim-root {{
          --ink: #17202a;
          --muted: #667085;
          --line: #d0d5dd;
          font-family: Arial, sans-serif;
          color: var(--ink);
          border: 1px solid #e4e7ec;
          border-radius: 8px;
          padding: 18px;
          background: #ffffff;
          overflow: hidden;
        }}
        .sim-title {{
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 14px;
        }}
        .sim-title h3 {{
          margin: 0;
          font-size: 20px;
          line-height: 1.2;
        }}
        .sim-title span {{
          color: var(--muted);
          font-size: 13px;
        }}
        .sim-stage {{
          display: grid;
          grid-template-columns: 150px minmax(280px, 1fr) minmax(260px, 330px);
          gap: 22px;
          align-items: center;
          min-height: 430px;
        }}
        .ph-panel {{
          height: 360px;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }}
        .ph-scale {{
          width: 34px;
          height: 310px;
          border: 3px solid var(--ink);
          border-radius: 12px;
          background: linear-gradient(to top, #4caf50 0%, #c6d93b 42%, #f6c343 55%, #db4b3f 100%);
          position: relative;
          box-shadow: inset 0 0 0 4px rgba(255,255,255,.45);
        }}
        .ph-tick {{
          position: absolute;
          left: 46px;
          transform: translateY(50%);
          font-weight: 700;
          font-size: 16px;
        }}
        .ph-tick.one {{ bottom: 0%; }}
        .ph-tick.seven {{ bottom: 46.15%; }}
        .ph-tick.fourteen {{ bottom: 100%; }}
        .ph-label {{
          position: absolute;
          left: 0;
          top: 50%;
          transform: rotate(-90deg) translateX(-50%);
          transform-origin: left center;
          font-size: 24px;
          font-weight: 700;
        }}
        .probe-line {{
          position: absolute;
          left: 72px;
          width: 54px;
          height: 3px;
          background: var(--ink);
          bottom: calc(var(--ph-pos) * 1%);
        }}
        .probe-tip {{
          position: absolute;
          left: 124px;
          width: 0;
          height: 0;
          border-top: 10px solid transparent;
          border-bottom: 10px solid transparent;
          border-right: 18px solid var(--ink);
          bottom: calc(var(--ph-pos) * 1% - 9px);
        }}
        .acid-basic {{
          position: absolute;
          left: 6px;
          font-size: 12px;
          color: var(--ink);
          writing-mode: vertical-rl;
          text-orientation: mixed;
          letter-spacing: .04em;
        }}
        .acid-basic.acid {{ top: 42px; }}
        .acid-basic.basic {{ bottom: 42px; }}
        .center-scene {{
          min-height: 420px;
          position: relative;
          display: grid;
          grid-template-rows: 92px 1fr;
        }}
        .drop-controls {{
          display: flex;
          gap: 18px;
          justify-content: center;
          align-items: start;
        }}
        .drop-button {{
          border: 2px solid var(--ink);
          background: #fff;
          color: var(--ink);
          border-radius: 6px;
          padding: 10px 26px;
          font-size: 18px;
          font-weight: 700;
          cursor: pointer;
          box-shadow: 0 2px 0 var(--ink);
        }}
        .drop-button:active {{
          transform: translateY(2px);
          box-shadow: none;
        }}
        .drop {{
          position: absolute;
          top: 70px;
          left: 50%;
          width: 14px;
          height: 20px;
          border-radius: 55% 55% 55% 0;
          transform: rotate(-45deg);
          opacity: 0;
          background: #2f80ed;
        }}
        .drop.falling {{
          animation: fall 560ms ease-in;
        }}
        @keyframes fall {{
          0% {{ top: 70px; opacity: 0; }}
          10% {{ opacity: 1; }}
          100% {{ top: 265px; opacity: 0; }}
        }}
        .beaker-wrap {{
          position: relative;
          display: flex;
          justify-content: center;
          align-items: center;
          height: 320px;
        }}
        .beaker {{
          width: 142px;
          height: 248px;
          border: 4px solid var(--ink);
          border-top: 0;
          border-radius: 0 0 44px 44px;
          position: relative;
          overflow: hidden;
          background: rgba(255,255,255,.5);
        }}
        .beaker::before {{
          content: "";
          position: absolute;
          top: 0;
          left: -4px;
          width: 150px;
          height: 24px;
          border: 4px solid var(--ink);
          border-bottom: 0;
          border-radius: 50%;
          background: #fff;
          z-index: 3;
        }}
        .solution {{
          position: absolute;
          left: 7px;
          right: 7px;
          bottom: 9px;
          height: 175px;
          background: rgb(182,155,60);
          border-radius: 0 0 35px 35px;
          opacity: .82;
          transition: background 280ms ease;
        }}
        .solution::before {{
          content: "";
          position: absolute;
          top: -11px;
          left: 0;
          width: 100%;
          height: 22px;
          border-radius: 50%;
          background: inherit;
          filter: brightness(1.12);
        }}
        .volume-label {{
          position: absolute;
          bottom: 22px;
          font-size: 13px;
          color: rgba(23,32,42,.72);
          z-index: 4;
        }}
        .probe {{
          position: absolute;
          width: 10px;
          height: 210px;
          border: 3px solid var(--ink);
          border-radius: 8px;
          background: #f2f4f7;
          top: 24px;
          left: calc(50% - 6px);
          transform: translateX(-78px) rotate(-7deg);
          z-index: 5;
        }}
        .probe::after {{
          content: "";
          position: absolute;
          bottom: -16px;
          left: -5px;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #101828;
        }}
        .magnifier {{
          position: relative;
          height: 420px;
        }}
        .lens {{
          width: 258px;
          height: 258px;
          border: 8px solid var(--ink);
          border-radius: 50%;
          position: relative;
          margin: 20px auto 0;
          background: radial-gradient(circle at 40% 35%, #ffffff 0%, #f8fafc 52%, #eef2f6 100%);
          box-shadow: inset 0 0 0 9px #fff;
        }}
        .handle {{
          position: absolute;
          width: 28px;
          height: 180px;
          background: #fff;
          border: 7px solid var(--ink);
          border-radius: 18px;
          transform: rotate(34deg);
          left: 46px;
          top: 232px;
        }}
        .ion-orbit {{
          position: absolute;
          inset: 54px;
          border: 3px solid var(--ink);
          border-radius: 50%;
        }}
        .ion {{
          position: absolute;
          display: grid;
          place-items: center;
          border: 3px solid var(--ink);
          background: #fff;
          border-radius: 50%;
          width: 34px;
          height: 34px;
          font-size: 20px;
          font-weight: 700;
        }}
        .ion.center {{ left: 111px; top: 111px; }}
        .ion.top {{ left: 112px; top: 45px; }}
        .ion.left {{ left: 62px; top: 155px; }}
        .ion.right {{ right: 62px; top: 155px; }}
        .ion-caption {{
          position: absolute;
          top: -20px;
          left: 105px;
          font-weight: 700;
        }}
        .conc-table {{
          margin: 16px auto 0;
          width: min(100%, 320px);
          border-collapse: collapse;
          font-size: 13px;
        }}
        .conc-table th, .conc-table td {{
          border-bottom: 1px solid #eaecf0;
          padding: 6px 4px;
          text-align: right;
          white-space: nowrap;
        }}
        .conc-table th:first-child, .conc-table td:first-child {{
          text-align: left;
        }}
        .sim-footer {{
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-top: 14px;
        }}
        .readout {{
          border: 1px solid #eaecf0;
          border-radius: 8px;
          padding: 10px 12px;
          background: #fcfcfd;
        }}
        .readout b {{
          display: block;
          font-size: 20px;
          margin-top: 4px;
        }}
        .readout span {{
          color: var(--muted);
          font-size: 12px;
        }}
        @media (max-width: 820px) {{
          .sim-stage {{
            grid-template-columns: 1fr;
          }}
          .sim-footer {{
            grid-template-columns: repeat(2, 1fr);
          }}
        }}
      </style>

      <div class="sim-title">
        <h3>Interactive chromium(VI) equilibrium simulator</h3>
        <span>Initial solution: 5 mM K2Cr2O7, about 50 mL</span>
      </div>
      <div class="sim-stage" style="--ph-pos: 46.15;">
        <div class="ph-panel">
          <div class="ph-label">pH</div>
          <div class="acid-basic acid">acid</div>
          <div class="acid-basic basic">basic</div>
          <div class="ph-scale">
            <div class="ph-tick fourteen">14</div>
            <div class="ph-tick seven">7</div>
            <div class="ph-tick one">1</div>
          </div>
          <div class="probe-line"></div>
          <div class="probe-tip"></div>
        </div>

        <div class="center-scene">
          <div class="drop-controls">
            <button class="drop-button" id="acidBtn" type="button">acid</button>
            <button class="drop-button" id="baseBtn" type="button">alkaline</button>
          </div>
          <div class="drop" id="drop"></div>
          <div class="beaker-wrap">
            <div class="probe"></div>
            <div class="beaker">
              <div class="solution" id="solution"></div>
              <div class="volume-label">about 50 mL</div>
            </div>
          </div>
        </div>

        <div class="magnifier">
          <div class="handle"></div>
          <div class="lens">
            <div class="ion-caption">ions</div>
            <div class="ion-orbit"></div>
            <div class="ion center">+</div>
            <div class="ion top">-</div>
            <div class="ion left">-</div>
            <div class="ion right">-</div>
          </div>
          <table class="conc-table">
            <thead>
              <tr><th>species</th><th>mM</th><th>Cr share</th></tr>
            </thead>
            <tbody>
              <tr><td>H+</td><td id="hConc"></td><td>-</td></tr>
              <tr><td>HCrO4-</td><td id="hcro4Conc"></td><td id="hcro4Share"></td></tr>
              <tr><td>CrO4^2-</td><td id="cro4Conc"></td><td id="cro4Share"></td></tr>
              <tr><td>Cr2O7^2-</td><td id="cr2o7Conc"></td><td id="cr2o7Share"></td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="sim-footer">
        <div class="readout"><span>Current pH</span><b id="phReadout">7.0</b></div>
        <div class="readout"><span>Color source</span><b id="colorSource">pH 7.0</b></div>
        <div class="readout"><span>Total Cr(VI)</span><b>5.000 mM</b></div>
        <div class="readout"><span>Drop step</span><b>0.5 pH</b></div>
      </div>

      <script>
        const colorPoints = {color_points_js};
        const totalCr = 5.0;
        const ka2 = 1.26e-6;
        const kDimer = 15.8;
        let ph = 7.0;

        const root = document.getElementById('cr-sim-root');
        const stage = root.querySelector('.sim-stage');
        const solution = root.querySelector('#solution');
        const drop = root.querySelector('#drop');

        function clamp(value, min, max) {{
          return Math.max(min, Math.min(max, value));
        }}

        function interpolateColor(value) {{
          if (value <= colorPoints[0].ph) {{
            return {{ rgb: colorPoints[0].rgb, source: 'pH <= 3.0' }};
          }}
          const last = colorPoints[colorPoints.length - 1];
          if (value >= last.ph) {{
            return {{ rgb: last.rgb, source: 'pH >= 12.0' }};
          }}
          for (let i = 0; i < colorPoints.length - 1; i++) {{
            const left = colorPoints[i];
            const right = colorPoints[i + 1];
            if (value >= left.ph && value <= right.ph) {{
              const t = (value - left.ph) / (right.ph - left.ph);
              const rgb = left.rgb.map((c, idx) => c + (right.rgb[idx] - c) * t);
              return {{ rgb, source: `pH ${{value.toFixed(1)}}` }};
            }}
          }}
        }}

        function solveSpecies(value) {{
          const hM = Math.pow(10, -value);
          const chromateFactor = ka2 / hM;
          const a = 2 * kDimer / 1000;
          const b = 1 + chromateFactor;
          const c = -totalCr;
          const hcro4 = (-b + Math.sqrt(b * b - 4 * a * c)) / (2 * a);
          const cro4 = chromateFactor * hcro4;
          const cr2o7 = kDimer * hcro4 * hcro4 / 1000;
          const h = hM * 1000;
          return {{ h, hcro4, cro4, cr2o7 }};
        }}

        function fmt(value) {{
          if (value >= 1) return value.toFixed(3);
          if (value >= 0.01) return value.toFixed(4);
          return value.toExponential(2);
        }}

        function update() {{
          const phPos = ((ph - 1) / 13) * 100;
          stage.style.setProperty('--ph-pos', phPos.toFixed(2));
          root.querySelector('#phReadout').textContent = ph.toFixed(1);

          const color = interpolateColor(ph);
          const rgb = color.rgb.map(v => Math.round(v));
          solution.style.background = `rgb(${{rgb[0]}}, ${{rgb[1]}}, ${{rgb[2]}})`;
          root.querySelector('#colorSource').textContent = color.source;

          const s = solveSpecies(ph);
          const hcro4Share = s.hcro4 / totalCr * 100;
          const cro4Share = s.cro4 / totalCr * 100;
          const cr2o7Share = 2 * s.cr2o7 / totalCr * 100;

          root.querySelector('#hConc').textContent = fmt(s.h);
          root.querySelector('#hcro4Conc').textContent = fmt(s.hcro4);
          root.querySelector('#cro4Conc').textContent = fmt(s.cro4);
          root.querySelector('#cr2o7Conc').textContent = fmt(s.cr2o7);
          root.querySelector('#hcro4Share').textContent = hcro4Share.toFixed(1) + '%';
          root.querySelector('#cro4Share').textContent = cro4Share.toFixed(1) + '%';
          root.querySelector('#cr2o7Share').textContent = cr2o7Share.toFixed(1) + '%';
        }}

        function addDrop(delta, color) {{
          ph = clamp(Math.round((ph + delta) * 2) / 2, 1, 14);
          drop.style.background = color;
          drop.classList.remove('falling');
          void drop.offsetWidth;
          drop.classList.add('falling');
          update();
        }}

        root.querySelector('#acidBtn').addEventListener('click', () => addDrop(-0.5, '#db4b3f'));
        root.querySelector('#baseBtn').addEventListener('click', () => addDrop(0.5, '#2f80ed'));
        update();
      </script>
    </div>
    """
    components.html(html, height=620, scrolling=False)


def render_introduction() -> None:
    st.title("Introduction")
    if INTRODUCTION_FILE.exists():
        st.markdown(INTRODUCTION_FILE.read_text(encoding="utf-8"))
    else:
        st.warning("Introduction content is missing.")
    render_ph_equilibrium_simulator()


def render_query(api_ok: bool) -> None:
    st.title("Query")
    st.caption(f"Backend: {API_BASE_URL} · {'online' if api_ok else 'offline'}")
    render_chat_panel(
        "General chemistry query",
        "query_messages",
        "query",
        "Ask about dichromate equilibrium, experimental design, or model interpretation...",
    )


def save_crop_for_prediction(cropped: Image.Image, original_name: str) -> bytes:
    image_buffer = io.BytesIO()
    if cropped.mode == "RGBA":
        cropped = cropped.convert("RGB")
    if original_name.lower().endswith((".tif", ".tiff")):
        cropped.save(image_buffer, format="TIFF")
    else:
        cropped.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return image_buffer.getvalue()


def render_prediction_results(result: Dict[str, Any], ph: float) -> None:
    species = result.get("species_concentrations") or {}
    total_cr = float(species.get("estimated_total_cr_mM", result.get("concentration", 0.0)))
    hcro4 = float(species.get("HCrO4_mM", 0.0))
    cr2o7 = float(species.get("Cr2O7_mM", 0.0))
    cro4 = float(species.get("CrO4_mM", 0.0))
    residual = float(species.get("dimer_residual_mM", 0.0))

    st.session_state.history.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ph": ph,
            "total_cr": total_cr,
            "hcro4": hcro4,
            "cr2o7": cr2o7,
            "cro4": cro4,
        }
    )
    st.session_state.last_prediction = {
        "pH": ph,
        "HCrO4_mM": hcro4,
        "Cr2O7_mM": cr2o7,
        "CrO4_mM": cro4,
        "estimated_total_cr_mM": total_cr,
        "dimer_residual_mM": residual,
        "confidence": result.get("confidence"),
        "warnings": result.get("warnings", []),
        "features_used": result.get("features_used", {}),
    }

    st.success("Prediction completed.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("HCrO4-", f"{hcro4:.4f} mM")
    c2.metric("Cr2O7^2-", f"{cr2o7:.4f} mM")
    c3.metric("CrO4^2-", f"{cro4:.4f} mM")
    c4.metric("Estimated total Cr(VI)", f"{total_cr:.4f} mM")

    d1, d2, d3 = st.columns(3)
    d1.metric("Confidence", f"{float(result.get('confidence', 0.0)):.1%}")
    d2.metric("Dimer residual", f"{residual:.4f} mM")
    d3.metric("pH", f"{ph:.1f}")

    for warning in result.get("warnings", []):
        st.warning(warning)


def render_model_prediction(api_ok: bool) -> None:
    st.title("Model Prediction")
    st.caption("Workflow: upload ROI image and pH, standardize illumination, extract color features, predict HCrO4- and Cr2O7^2-, then compute CrO4^2-.")

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Sample image")
        uploaded = st.file_uploader("Select photo", type=["jpg", "jpeg", "png", "tif", "tiff"])
        if uploaded:
            image = Image.open(uploaded)
            st.session_state.original_image = image
            st.session_state.cropped_image = st_cropper(
                image,
                realtime_update=True,
                box_color="#D92D20",
                aspect_ratio=None,
                return_type="image",
            )
            st.session_state.roi_selected = True

        ph = st.slider("pH", 3.0, 8.0, 6.0, 0.1)
        st.caption("The deployed model is trained for pH 3-8. pH 7-8 may amplify CrO4^2- uncertainty.")

        can_predict = bool(uploaded and api_ok and st.session_state.cropped_image)
        if st.button("Predict", disabled=not can_predict, type="primary"):
            with st.spinner("Analyzing ROI image..."):
                image_bytes = save_crop_for_prediction(st.session_state.cropped_image, uploaded.name)
                result = predict(image_bytes, ph, uploaded.name)
            if "error" in result:
                st.error(result["error"])
            else:
                render_prediction_results(result, ph)

    with right:
        st.subheader("ROI preview")
        if st.session_state.cropped_image:
            st.image(st.session_state.cropped_image, caption="Selected ROI", use_container_width=True)
        elif uploaded:
            st.info("Draw a box around the cuvette region.")
        else:
            st.info("Upload a photo, then select the cuvette region.")

        st.markdown("---")
        st.subheader("Equilibrium basis")
        st.latex(r"Cr_2O_7^{2-} + H_2O \rightleftharpoons 2HCrO_4^-")
        st.latex(r"HCrO_4^- \rightleftharpoons H^+ + CrO_4^{2-}")
        st.latex(r"[CrO_4^{2-}] = K_{a2}[HCrO_4^-]/[H^+]")
        st.latex(r"C_{Cr(VI)} = [HCrO_4^-] + [CrO_4^{2-}] + 2[Cr_2O_7^{2-}]")

    st.markdown("---")
    render_chat_panel(
        "Result analysis assistant",
        "analysis_messages",
        "prediction_analysis",
        "Ask the model to summarize this result, discuss reliability, or suggest experimental checks...",
        st.session_state.last_prediction,
    )


def render_sidebar(api_ok: bool) -> str:
    with st.sidebar:
        st.title("K2Cr2O7")
        st.caption("Chromium(VI) species predictor")
        if api_ok:
            st.success("Backend online")
        else:
            st.error("Backend offline")

        module = st.radio(
            "Module",
            ["Introduction", "Query", "Model Prediction"],
            index=2,
        )

        if st.session_state.history:
            st.markdown("---")
            st.subheader("Recent predictions")
            for item in st.session_state.history[-5:]:
                st.write(
                    f"{item['time']} · pH {item['ph']:.1f} · "
                    f"CrO4^2- {item['cro4']:.3f} mM"
                )
    return module


def main() -> None:
    init_state()
    api_ok = check_api()
    module = render_sidebar(api_ok)

    if module == "Introduction":
        render_introduction()
    elif module == "Query":
        render_query(api_ok)
    else:
        render_model_prediction(api_ok)

    st.markdown("---")
    st.caption("K2Cr2O7 Prediction System · ML species prediction with equilibrium calculation")


if __name__ == "__main__":
    main()
