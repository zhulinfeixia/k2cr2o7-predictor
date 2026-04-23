# 🧪 重铬酸钾浓度预测系统 | Potassium Dichromate Concentration Predictor

**基于图像颜色分析与机器学习的溶液浓度智能检测工具**

**An intelligent solution concentration detection tool based on image color analysis and machine learning**

---

## 🌐 在线演示 | Live Demo

- **前端界面 | Frontend**: https://k2cr2o7-predictor.vercel.app
- **API 文档 | API Docs**: https://k2cr2o7-api.onrender.com/docs

---

## ✨ 功能特点 | Features

**中文**
- 📷 上传比色皿照片即可预测浓度
- 🎨 自动提取 RGB/HSV/Lab 颜色特征
- 📊 实时显示预测结果与置信度
- 🔬 支持 pH 2-12, 浓度 1-8 mM 范围
- 📱 响应式网页设计
- 💯 完全免费部署

**English**
- 📷 Upload cuvette photo for concentration prediction
- 🎨 Automatic extraction of RGB/HSV/Lab color features
- 📊 Real-time prediction results with confidence scores
- 🔬 Supports pH 2-12, concentration 1-8 mM range
- 📱 Responsive web design
- 💯 Completely free deployment

---

## 🚀 快速开始 | Quick Start

### 使用在线版本 | Use Online Version

**中文**: 直接访问 https://k2cr2o7-predictor.vercel.app 即可使用，无需安装任何软件。

**English**: Simply visit https://k2cr2o7-predictor.vercel.app to use, no installation required.

### 本地运行 | Local Development

```bash
# 克隆仓库 | Clone repository
git clone https://github.com/yourusername/k2cr2o7-predictor.git
cd k2cr2o7-predictor

# 安装依赖并启动后端 | Install dependencies and start backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 安装依赖并启动前端（新终端）| Install dependencies and start frontend (new terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

访问 | Visit: http://localhost:8501

---

## 📖 使用说明 | Usage Instructions

### 中文
1. 打开网页，上传已裁剪好的比色皿照片
2. 输入溶液的 pH 值（2-12）
3. 点击"预测"按钮
4. 查看浓度结果、置信度和各组分浓度

**⚠️ 注意**: 请使用浓度在 1mM-8mM，pH 在 2-12 范围内的溶液

### English
1. Open the web page, upload a cropped cuvette photo
2. Enter the solution pH value (2-12)
3. Click the "Predict" button
4. View concentration results, confidence, and species distribution

**⚠️ Note**: Please use solutions with concentration 1-8 mM and pH 2-12

### 拍摄建议 | Photography Tips

**中文**
- 使用均匀的自然光或白光
- 白色背景（如白纸）
- 确保比色皿清晰可见
- 避免阴影和反光
- 上传前裁剪至比色皿区域

**English**
- Use uniform natural or white light
- White background (e.g., white paper)
- Ensure cuvette is clearly visible
- Avoid shadows and reflections
- Crop to cuvette area before uploading

---

## 🏗️ 技术架构 | Technical Architecture

```
前端 (Streamlit) ←→ 后端 (FastAPI) ←→ 机器学习模型 (Random Forest)
Frontend           ←→  Backend        ←→  ML Model
     Vercel              Render              Joblib
```

### 模型信息 | Model Information

**中文**
- **类型**: Random Forest Regressor
- **特征**: 16维 (pH + RGB + HSV + Lab + 比值)
- **训练数据**: 30个重铬酸钾溶液样本
- **准确度**: MAE = 0.37 mM, 93.3% 样本误差 < 1mM
- **适用范围**: pH 2-12, 浓度 1-8 mM

**English**
- **Type**: Random Forest Regressor
- **Features**: 16-dimensional (pH + RGB + HSV + Lab + ratios)
- **Training Data**: 30 potassium dichromate solution samples
- **Accuracy**: MAE = 0.37 mM, 93.3% samples with error < 1mM
- **Applicable Range**: pH 2-12, concentration 1-8 mM

---

## 🆓 免费部署 | Free Deployment

**中文**: 本项目可以完全免费部署

**English**: This project can be deployed completely free

- **前端 | Frontend**: [Vercel](https://vercel.com) (免费版 | Free tier)
- **后端 | Backend**: [Render](https://render.com) (免费版 | Free tier)
- **存储 | Storage**: [GitHub](https://github.com) (免费版 | Free tier)

详细部署步骤请参考 | Detailed deployment steps: [DEPLOY_CLOUD.md](./DEPLOY_CLOUD.md)

---

## 📁 项目结构 | Project Structure

```
.
├── backend/              # FastAPI 后端 | Backend
│   ├── main.py           # API 主入口 | API entry
│   ├── image_processor.py # 图像预处理 | Image preprocessing
│   ├── model.py          # 模型封装 | Model wrapper
│   ├── requirements.txt  # Python 依赖 | Dependencies
│   └── models/
│       └── RF_model.joblib  # 训练好的模型 | Trained model
├── frontend/             # Streamlit 前端 | Frontend
│   ├── app.py            # Web 界面 | Web interface
│   └── requirements.txt  # Python 依赖 | Dependencies
├── docker/               # Docker 配置 | Docker config
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── vercel.json           # Vercel 部署配置 | Vercel config
├── render.yaml           # Render 部署配置 | Render config
└── README.md             # 项目说明 | Project documentation
```

---

## 🔬 化学原理 | Chemical Principles

**中文**

重铬酸钾体系存在酸碱平衡：

```
2CrO₄²⁻ (黄色) + 2H⁺ ⇌ Cr₂O₇²⁻ (橙色) + H₂O
```

溶液颜色随 pH 变化，通过机器学习建立颜色-浓度关系模型。

**English**

The potassium dichromate system has acid-base equilibrium:

```
2CrO₄²⁻ (yellow) + 2H⁺ ⇌ Cr₂O₇²⁻ (orange) + H₂O
```

Solution color changes with pH. Machine learning is used to establish a color-concentration relationship model.

---

## 🛠️ 技术栈 | Tech Stack

- **后端 | Backend**: FastAPI, OpenCV, scikit-learn, NumPy
- **前端 | Frontend**: Streamlit, Pillow, Requests
- **部署 | Deployment**: Vercel, Render, Docker

---

## 📄 许可证 | License

MIT License

---

## 🤝 贡献 | Contributing

**中文**: 欢迎提交 Issue 和 Pull Request！

**English**: Issues and Pull Requests are welcome!

---

## 🙏 致谢 | Acknowledgments

- 机器学习模型 | ML Model: [scikit-learn](https://scikit-learn.org)
- Web 框架 | Web Framework: [FastAPI](https://fastapi.tiangolo.com), [Streamlit](https://streamlit.io)
- 部署平台 | Deployment: [Vercel](https://vercel.com), [Render](https://render.com)

---

## 📧 联系方式 | Contact

如有问题或建议，请通过 GitHub Issues 联系我们。

For questions or suggestions, please contact us via GitHub Issues.
