# 免费云端部署指南

使用 Vercel (前端) + Render (后端) 实现完全免费的在线部署。

## 部署架构

```
用户浏览器
    ↓ HTTPS
Vercel (前端) - Streamlit 界面
    ↓ HTTPS
Render (后端) - FastAPI 服务
    ↓
  模型预测
```

## 部署步骤

### 第一步：准备 GitHub 仓库

1. 创建新的 GitHub 仓库（如 `k2cr2o7-predictor`）
2. 上传项目文件（保留 `网页部署/` 目录下的内容）

推荐的仓库结构：
```
k2cr2o7-predictor/
├── backend/
│   ├── main.py
│   ├── image_processor.py
│   ├── model.py
│   ├── requirements.txt
│   └── models/
│       └── RF_model.joblib
├── frontend/
│   ├── app.py
│   └── requirements.txt
├── vercel.json
├── render.yaml
└── README.md
```

### 第二步：部署后端到 Render

1. 访问 https://render.com
2. 使用 GitHub 账号登录
3. 点击 "New +" → "Web Service"
4. 选择你的 GitHub 仓库
5. 配置如下：
   - **Name**: `k2cr2o7-api`（或自定义）
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
6. 点击 "Create Web Service"
7. 等待部署完成（约 2-3 分钟）
8. 记下分配的 URL（如 `https://k2cr2o7-api.onrender.com`）

### 第三步：部署前端到 Vercel

1. 访问 https://vercel.com
2. 使用 GitHub 账号登录
3. 点击 "Add New..." → "Project"
4. 选择你的 GitHub 仓库
5. 配置如下：
   - **Framework Preset**: Other
   - **Root Directory**: `./`（或 `frontend` 如果单独部署）
   - **Build Command**: 留空
   - **Output Directory**: 留空
6. 点击 "Environment Variables" 添加：
   - `API_BASE_URL` = `https://k2cr2o7-api.onrender.com`（你的 Render URL）
7. 点击 "Deploy"
8. 等待部署完成（约 1-2 分钟）

### 第四步：验证部署

1. 访问 Vercel 分配的域名（如 `https://k2cr2o7-predictor.vercel.app`）
2. 测试上传图片和预测功能
3. 检查浏览器开发者工具的网络请求是否正常

## 配置文件说明

### vercel.json
配置 Vercel 部署参数，指定 Python 运行时和路由。

### render.yaml
配置 Render 服务，包括构建命令、启动命令和环境变量。

### 环境变量

**前端 (Vercel)**:
- `API_BASE_URL`: 后端 API 地址

**后端 (Render)**:
- `PYTHON_VERSION`: 3.11.0
- `PORT`: 由 Render 自动分配

## 注意事项

### 免费版限制

**Render Free**:
- 15分钟无请求后进入休眠
- 首次访问有冷启动延迟（约 30 秒）
- 每月 750 小时运行时间
- 512 MB RAM

**Vercel Free**:
- 函数执行时间限制 10 秒
- 每天 100 GB 带宽
- 无冷启动问题

### 优化建议

1. **减少冷启动影响**:
   - 使用 UptimeRobot 等免费服务定期 ping 后端
   - 设置每 10 分钟访问一次 `/health`

2. **模型文件大小**:
   - 当前模型约 471 KB，在限制内
   - 如果模型变大，考虑使用 Git LFS

3. **图片大小限制**:
   - Vercel 免费版请求体限制 4.5 MB
   - 建议上传图片不超过 3 MB

## 故障排查

### 后端无法启动
```
检查 render.yaml 配置
检查 backend/requirements.txt 是否完整
查看 Render Dashboard 的 Logs
```

### 前端无法连接后端
```
检查 Vercel 环境变量 API_BASE_URL 是否正确
检查后端 CORS 配置是否允许前端域名
查看浏览器控制台的网络错误
```

### 模型加载失败
```
确认 RF_model.joblib 已上传到 GitHub
检查模型文件路径是否正确
查看 Render Logs 中的文件路径错误
```

## 更新部署

### 更新代码后
1. 推送代码到 GitHub
2. Render 和 Vercel 会自动重新部署
3. 等待 1-2 分钟后刷新页面

### 更新模型
1. 替换 `backend/models/RF_model.joblib`
2. 提交并推送
3. Render 会自动重新部署

## 自定义域名（可选）

### Vercel 自定义域名
1. 在 Vercel Dashboard 选择项目
2. Settings → Domains
3. 添加你的域名
4. 按提示配置 DNS

### Render 自定义域名
1. 在 Render Dashboard 选择服务
2. Settings → Custom Domains
3. 添加你的域名
4. 按提示配置 DNS

## 监控与日志

### Render 日志
- Dashboard → 选择服务 → Logs
- 实时查看应用日志

### Vercel 日志
- Dashboard → 选择项目 → Functions
- 查看函数执行日志

## 备份与恢复

### 备份
- 代码：GitHub 自动备份
- 模型：保留本地副本

### 恢复
- 重新部署即可恢复
- 模型文件从 GitHub 拉取

## 联系与支持

- Render 文档: https://render.com/docs
- Vercel 文档: https://vercel.com/docs
- 项目 Issues: GitHub Issues

---

**部署完成后，用户只需访问 Vercel 分配的网址即可使用系统，无需任何安装！**
