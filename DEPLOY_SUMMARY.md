# 云端部署完成总结

## 部署方案

**Vercel (前端) + Render (后端)** - 完全免费

## 已准备的文件

### 配置文件
- ✅ `vercel.json` - Vercel 部署配置
- ✅ `render.yaml` - Render 服务配置

### 部署脚本
- ✅ `deploy-cloud.bat` - Windows 一键准备脚本
- ✅ `deploy-cloud.sh` - Linux/Mac 一键部署脚本

### 文档
- ✅ `DEPLOY_CLOUD.md` - 详细部署指南
- ✅ `README_GITHUB.md` - GitHub 仓库 README

### 代码更新
- ✅ `frontend/app.py` - 支持环境变量配置 API 地址

## 部署步骤（3步完成）

### 第1步：创建 GitHub 仓库
1. 访问 https://github.com/new
2. 创建仓库 `k2cr2o7-predictor`
3. **不要**初始化 README

### 第2步：上传代码
**Windows 用户**：
```bash
双击运行 deploy-cloud.bat
按提示操作
```

**Linux/Mac 用户**：
```bash
bash deploy-cloud.sh
按提示操作
```

**手动方式**：
```bash
cd 网页部署

# 创建新仓库
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/k2cr2o7-predictor.git
git push -u origin main
```

### 第3步：部署服务

**部署后端（Render）**：
1. 访问 https://dashboard.render.com
2. 点击 "New +" → "Web Service"
3. 选择 GitHub 仓库 `k2cr2o7-predictor`
4. 配置：
   - Name: `k2cr2o7-api`
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
5. 点击创建，等待部署完成
6. 复制分配的 URL（如 `https://k2cr2o7-api.onrender.com`）

**部署前端（Vercel）**：
1. 访问 https://vercel.com/new
2. 导入 GitHub 仓库 `k2cr2o7-predictor`
3. 配置：
   - Framework: Other
   - 添加环境变量：`API_BASE_URL` = `https://k2cr2o7-api.onrender.com`
4. 点击 Deploy
5. 等待部署完成

## 最终访问地址

- **前端**: `https://k2cr2o7-predictor.vercel.app`（示例）
- **后端 API**: `https://k2cr2o7-api.onrender.com`（示例）
- **API 文档**: `https://k2cr2o7-api.onrender.com/docs`

用户只需访问前端网址即可使用！

## 免费额度说明

| 服务 | 免费额度 | 限制 |
|------|---------|------|
| Vercel | 每月 100GB 带宽 | 函数执行 10秒 |
| Render | 每月 750小时 | 15分钟休眠 |

**冷启动问题**：
- Render 免费版15分钟无请求会休眠
- 首次访问需要约 30 秒唤醒
- 可以使用 UptimeRobot 免费监控保持活跃

## 自定义域名（可选）

### Vercel 添加自定义域名
1. Vercel Dashboard → 项目 → Settings → Domains
2. 添加你的域名（如 `chem.yourdomain.com`）
3. 按提示配置 DNS

### Render 添加自定义域名
1. Render Dashboard → 服务 → Settings → Custom Domains
2. 添加你的域名
3. 按提示配置 DNS

## 更新部署

代码更新后自动重新部署：
1. 修改代码
2. `git add . && git commit -m "update"`
3. `git push`
4. Vercel 和 Render 会自动重新部署

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 后端无法启动 | 检查 render.yaml 配置，查看 Render Logs |
| 前端无法连接后端 | 检查 Vercel 环境变量 API_BASE_URL |
| 模型加载失败 | 确认 RF_model.joblib 在 GitHub 上 |
| 图片上传失败 | 检查图片大小（< 3MB）|

## 项目文件清单

```
网页部署/
├── backend/              # 后端代码
│   ├── main.py
│   ├── image_processor.py
│   ├── model.py
│   ├── requirements.txt
│   └── models/
│       └── RF_model.joblib
├── frontend/             # 前端代码
│   ├── app.py
│   └── requirements.txt
├── vercel.json           # Vercel 配置 ⭐
├── render.yaml           # Render 配置 ⭐
├── deploy-cloud.bat      # Windows 部署脚本 ⭐
├── deploy-cloud.sh       # Linux/Mac 部署脚本 ⭐
├── DEPLOY_CLOUD.md       # 部署指南 ⭐
├── README_GITHUB.md      # GitHub README ⭐
└── PROJECT_SUMMARY.md    # 项目总结
```

⭐ 标记的是为云端部署新增/修改的文件

## 完成状态

✅ **所有部署文件已准备就绪！**

只需按上述3步操作，即可让用户通过网址直接访问系统。
