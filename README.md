# 🧪 Potassium Dichromate Concentration Predictor

**[中文](./README_CN.md) | English**

---

An intelligent solution concentration detection tool based on image color analysis and machine learning.

---

## 🌐 Live Demo

- **Frontend**: https://k2cr2o7-predictor.vercel.app
- **API Docs**: https://k2cr2o7-api.onrender.com/docs

---

## ✨ Features

- 📷 Upload cuvette photo for concentration prediction
- 🎨 Automatic extraction of RGB/HSV/Lab color features
- 📊 Real-time prediction results with confidence scores
- 🔬 Supports pH 2-12, concentration 1-8 mM range
- 📱 Responsive web design
- 💯 Completely free deployment

---

## 🚀 Quick Start

### Use Online Version

Simply visit https://k2cr2o7-predictor.vercel.app to use, no installation required.

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/k2cr2o7-predictor.git
cd k2cr2o7-predictor

# Install dependencies and start backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Install dependencies and start frontend (new terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Visit: http://localhost:8501

---

## 📖 Usage Instructions

1. Open the web page, upload a cropped cuvette photo
2. Enter the solution pH value (2-12)
3. Click the "Predict" button
4. View concentration results, confidence, and species distribution

**⚠️ Note**: Please use solutions with concentration 1-8 mM and pH 2-12

### Photography Tips

- Use uniform natural or white light
- White background (e.g., white paper)
- Ensure cuvette is clearly visible
- Avoid shadows and reflections
- Crop to cuvette area before uploading

---

## 🏗️ Technical Architecture

```
Frontend (Streamlit) ←→ Backend (FastAPI) ←→ ML Model (Random Forest)
     Vercel              Render              Joblib
```

### Model Information

- **Type**: Random Forest Regressor
- **Features**: 16-dimensional (pH + RGB + HSV + Lab + ratios)
- **Training Data**: 30 potassium dichromate solution samples
- **Accuracy**: MAE = 0.37 mM, 93.3% samples with error < 1mM
- **Applicable Range**: pH 2-12, concentration 1-8 mM

---

## 🆓 Free Deployment

This project can be deployed completely free:

- **Frontend**: [Vercel](https://vercel.com) (Free tier)
- **Backend**: [Render](https://render.com) (Free tier)
- **Storage**: [GitHub](https://github.com) (Free tier)

Detailed deployment steps: [DEPLOY_CLOUD.md](./DEPLOY_CLOUD.md)

---

## 📁 Project Structure

```
.
├── backend/              # Backend
│   ├── main.py           # API entry
│   ├── image_processor.py # Image preprocessing
│   ├── model.py          # Model wrapper
│   ├── requirements.txt  # Dependencies
│   └── models/
│       └── RF_model.joblib  # Trained model
├── frontend/             # Frontend
│   ├── app.py            # Web interface
│   └── requirements.txt  # Dependencies
├── docker/               # Docker config
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── README.md             # This file (English)
├── README_CN.md          # Chinese version
├── LICENSE               # License
├── render.yaml           # Render config
└── vercel.json           # Vercel config
```

---

## 🔬 Chemical Principles

The potassium dichromate system has acid-base equilibrium:

```
2CrO₄²⁻ (yellow) + 2H⁺ ⇌ Cr₂O₇²⁻ (orange) + H₂O
```

Solution color changes with pH. Machine learning is used to establish a color-concentration relationship model.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, OpenCV, scikit-learn, NumPy
- **Frontend**: Streamlit, Pillow, Requests
- **Deployment**: Vercel, Render, Docker

---

## 📄 License

MIT License

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 🙏 Acknowledgments

- ML Model: [scikit-learn](https://scikit-learn.org)
- Web Framework: [FastAPI](https://fastapi.tiangolo.com), [Streamlit](https://streamlit.io)
- Deployment: [Vercel](https://vercel.com), [Render](https://render.com)

---

## 📧 Contact

For questions or suggestions, please contact us via GitHub Issues.
