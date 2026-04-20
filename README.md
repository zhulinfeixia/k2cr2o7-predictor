# 🧪 重铬酸钾浓度预测系统

基于图像颜色分析与机器学习的溶液浓度智能检测工具。

## 🌐 在线演示

- **前端界面**: https://k2cr2o7-predictor.vercel.app
- **API 文档**: https://k2cr2o7-api.onrender.com/docs

## ✨ 功能特点

- 📷 上传比色皿照片即可预测浓度
- 🎨 自动提取 RGB/HSV/Lab 颜色特征
- 📊 实时显示预测结果与置信度
- 🔍 ROI 区域自动识别
- 📱 响应式网页设计
- 💯 完全免费部署

## 🚀 快速开始

### 使用在线版本

直接访问 https://k2cr2o7-predictor.vercel.app 即可使用，无需安装任何软件。

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/yourusername/k2cr2o7-predictor.git
cd k2cr2o7-predictor

# 安装依赖并启动后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 安装依赖并启动前端（新终端）
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

访问 http://localhost:8501

## 📖 使用说明

1. 打开网页，上传比色皿照片
2. 输入溶液的 pH 值（0-14）
3. 点击"开始预测"
4. 查看浓度结果、置信度和可靠性评估

### 拍摄建议

- 使用均匀的自然光或白光
- 白色背景（如白纸）
- 确保比色皿清晰可见
- 避免阴影和反光

## 🏗️ 技术架构

```
前端 (Streamlit) ←→ 后端 (FastAPI) ←→ 机器学习模型 (Random Forest)
     Vercel              Render              Joblib
```

### 模型信息

- **类型**: Random Forest Regressor
- **特征**: 16维 (pH + RGB + HSV + Lab + 比值)
- **训练数据**: 重铬酸钾溶液标准曲线

## 🆓 免费部署

本项目可以完全免费部署：

- **前端**: [Vercel](https://vercel.com) (免费版)
- **后端**: [Render](https://render.com) (免费版)
- **存储**: [GitHub](https://github.com) (免费版)

详细部署步骤请参考 [DEPLOY_CLOUD.md](./DEPLOY_CLOUD.md)

## 📁 项目结构

```
.
├── backend/              # FastAPI 后端
│   ├── main.py           # API 主入口
│   ├── image_processor.py # 图像预处理
│   ├── model.py          # 模型封装
│   ├── requirements.txt  # Python 依赖
│   └── models/
│       └── RF_model.joblib  # 训练好的模型
├── frontend/             # Streamlit 前端
│   ├── app.py            # Web 界面
│   └── requirements.txt  # Python 依赖
├── docker/               # Docker 配置
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── vercel.json           # Vercel 部署配置
├── render.yaml           # Render 部署配置
└── README.md             # 项目说明
```

## 🔬 化学原理

重铬酸钾体系存在酸碱平衡：

```
2CrO₄²⁻ (黄色) + 2H⁺ ⇌ Cr₂O₇²⁻ (橙色) + H₂O
```

溶液颜色随 pH 变化，通过机器学习建立颜色-浓度关系模型。

## 🛠️ 技术栈

- **后端**: FastAPI, OpenCV, scikit-learn, NumPy
- **前端**: Streamlit, Pillow, Requests
- **部署**: Vercel, Render, Docker

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🙏 致谢

- 随机森林模型: [scikit-learn](https://scikit-learn.org)
- Web 框架: [FastAPI](https://fastapi.tiangolo.com), [Streamlit](https://streamlit.io)
- 部署平台: [Vercel](https://vercel.com), [Render](https://render.com)
