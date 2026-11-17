# 商办信息资产库

面向上海商办经纪团队的信息资产库。移动端优先语音录入，支持把听到、看到、收到的业务信息和任意格式资料收进同一条业务记录；后端负责原件保存、OCR/ASR、字段整理和检索。

- GitHub：<https://github.com/Arvin665/-app->
- 本地管理员邀请码：`246810`（仅本地开发默认值，生产必须更换）
- 移动端登录页不再自动聚焦邀请码输入框，避免小屏键盘遮住底部按钮。

## 已接入的语音链路

```text
uni-app / H5 录音
        ↓
POST /api/v1/ai/transcribe
        ↓
本地 SenseVoiceSmall（Sherpa-ONNX，CPU）
        ↓
识别文字
        ↓
POST /api/v1/ai/extract
        ↓
DeepSeek（可选）纠错和字段分类
        ↓
人工核对后保存业务记录
```

- `SenseVoiceSmall` 模型是本地离线运行，不把音频发到第三方。
- H5 录音会先把 WAV 发给后台 SenseVoiceSmall；浏览器实时识别只用于预览，在后台识别不可用时才作为兜底，不再因为浏览器先报错而误提示“没有听到”。
- 有声音但没有识别出文字时，提示会区分“录音静音”和“没有识别到文字”，不再统一显示为“没有听到”。
- 无法使用 SenseVoiceSmall 时，按配置降级到 Windows Speech 或 Vosk。
- DeepSeek 只有配置 `DEEPSEEK_API_KEY` 才会调用；没有 Key 时自动保留本地规则结果，不会伪造外部模型结果。
- DeepSeek 输出经过字段白名单校验，未知字段不会写入业务记录；`corrected_text` 会优先写入记录，识别结果仍可人工核对和修改。

## 目录

| 目录 | 内容 |
| --- | --- |
| `backend/` | FastAPI、SQLAlchemy、SQLite/MySQL、原件存储、OCR、ASR、DeepSeek 接入 |
| `mobile-app/` | uni-app Vue 3 移动端，适配 H5 和 Capacitor Android/iOS |
| `desktop-app/` | Vue 3 + Element Plus + Electron 管理端 |
| `docker/` | Nginx、H5 镜像和 HTTPS 示例 |
| `.github/workflows/` | Docker/MySQL/Redis 集成、Android Debug APK、iOS 模拟器构建工作流 |
| `backend/scripts/` | 模型下载、识别和部署验收脚本 |

## 本地启动

要求：Python 3.10+、Node.js 20/22。以下命令在项目根目录执行。

### 1. 后端和本地 SQLite

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r '.\backend\requirements.txt'
Set-Location .\backend
& '..\.venv\Scripts\python.exe' 'scripts\download_sense_voice_model.py'
& '..\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

首次下载 SenseVoiceSmall 约 163 MB 压缩包，解压后的模型约 240 MB。模型目录在 `backend/models/`，已在 `.gitignore` 中，不会提交到 Git。

本地没有 SenseVoiceSmall 时，可先下载 Vosk 备用模型：

```powershell
& '..\.venv\Scripts\python.exe' 'scripts\download_vosk_model.py'
```

健康检查：`http://127.0.0.1:8000/api/v1/health`；Swagger：`http://127.0.0.1:8000/docs`。

### 2. 移动 H5

```powershell
Set-Location .\mobile-app
npm ci
Copy-Item .env.example .env.local
npm run dev:h5
```

访问 `http://127.0.0.1:5173`。开发服务器会把 `/api` 和 `/uploads` 代理到 `127.0.0.1:8000`。生产构建：

```powershell
npm run build:h5
```

### 3. Android/iOS 原生工程

移动端前端仍使用 uni-app 的 H5 资源，外层由 Capacitor 打包。首次同步：

```powershell
Set-Location .\mobile-app
npm run native:sync:android:debug
```

Android 原生构建需要 Android SDK、Java 21 和签名配置：

```powershell
npm run native:build:android:debug
```

iOS 需要 macOS、Xcode、Apple Team 和描述文件：

```powershell
npx cap sync ios
npx cap open ios
```

仓库中的 GitHub Actions 会尝试生成 Android Debug APK 和未签名 iOS 模拟器包；这不是可直接上架商店的正式签名包。

### 4. Docker、MySQL、Redis

要求安装 Docker Desktop 或 Docker Engine：

```powershell
Copy-Item .env.example .env
# 编辑 .env，至少替换数据库密码、SENSITIVE_FIELD_KEY 和邀请码
docker compose up -d --build
docker compose ps
```

默认访问 `http://localhost`（或 `http://localhost:8080`，取决于 `WEB_PORT`）。后端镜像会安装 `ffmpeg`，并下载 SenseVoiceSmall 和 Vosk 备用模型。首次构建访问 Docker Hub、PyPI 和模型发布页，耗时和磁盘占用都较高。

关键识别配置：

| 变量 | 说明 |
| --- | --- |
| `ASR_ENGINE` | `auto`、`sensevoice`、`windows-speech` 或 `vosk` |
| `SENSE_VOICE_MODEL_PATH` | SenseVoiceSmall 模型目录 |
| `VOSK_MODEL_PATH` | Vosk 备用模型目录 |
| `AI_PROVIDER` | `auto`、`local` 或 `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，留空则只用本地规则 |
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 默认 `deepseek-chat` |

DeepSeek 接入属于外部网络调用。生产环境应确认团队对资料外发的授权、脱敏策略和供应商数据处理条款；不应把 API Key 写入前端或提交到 Git。

## 资料和字段规则

- 四个入口：项目买卖、企业租赁、工作记录、个人灵感角。
- 买卖信息不设置业务必填项，可以先只记一句“听到/看到/知道”的线索，价格、买家、时间等以后再补充。
- 所有模块都可以先存原话、再逐项补充；历史、草稿和资料库可回看之前内容。
- `+` 入口支持拍照、相册和系统文件选择，原件先落盘，再尝试正文提取。图片、扫描 PDF、文本 PDF、TXT/Markdown、CSV、XLSX、DOCX、PPTX、音频、视频都有提取适配器。
- 没有适配器的格式仍按原格式保存，不会因为识别失败而丢文件。
- 交易记录中的语音原话会进入备注，结构化字段只写入能从内容中确认的信息。所有自动整理结果都需要人工核对。

## 验收

已在当前 Windows 环境执行：

```powershell
Set-Location .\backend
& '..\.venv\Scripts\python.exe' -m pytest tests -q
Set-Location .\mobile-app
npm.cmd run build:h5
npm.cmd run build:app
```

当前结果：

- 后端测试：`11 passed`，覆盖 API、权限、资料保存、媒体转录、SenseVoice/Vosk 降级、DeepSeek 成功落地和故障回退。
- H5 构建和 App 资源构建：通过。
- SenseVoiceSmall 真实中文样例：本机 `zh.wav` 成功转写为“开饭时间早上9点至下午5点。”，端点返回 `provider=sensevoice`。
- 麦克风权限、系统文件选择器和手机真机语音必须在有界面的设备上人工验收；无头环境不能代替真实录音验收。

当前机器与 CI 状态：

- Docker Compose、MySQL 8、Redis 7、Nginx、OCR/ASR、附件写入和重启后数据保留：已在 [GitHub Actions 联调任务](https://github.com/Arvin665/-app-/actions/runs/44042488671) 全部通过。当前本机没有 Docker CLI，无法在本地重复这项验证。
- Android Debug APK：已在 [GitHub Actions Android 构建](https://github.com/Arvin665/-app-/actions/runs/44048218168) 通过；artifact `asset-library-android-debug` 内的 `app-debug.apk` 为 4,384,323 字节。这是调试包，不是正式签名发布包。
- iOS 模拟器包：已在 [GitHub Actions iOS 构建](https://github.com/Arvin665/-app-/actions/runs/44047326183) 通过；产物是未签名模拟器构建，不是 IPA，也没有上架。
- 当前机器没有 Docker CLI、Java、Android SDK 或 Xcode；本机无法重复 Android/iOS 原生构建。
- 尚未完成真机麦克风、系统文件选择器、Android/iOS 安装和后台提醒验收。
- 尚未配置真实 DeepSeek Key，因此真实线上纠错准确率、限额和异常网络重试仍需验收。
- 尚未生成正式签名的 APK/IPA，也未完成应用商店发布。

## 生产上线前

1. 更换管理员邀请码、数据库密码和 `SENSITIVE_FIELD_KEY`，不要沿用示例值。
2. 配置 HTTPS、真实域名和 CORS 白名单；移动浏览器录音必须使用 HTTPS。
3. 按团队数据处理要求决定是否启用 DeepSeek，并对客户姓名、电话、交易文件做必要脱敏。
4. 执行一次 MySQL/附件备份恢复演练，确认原件和正文都能恢复。
5. 用真实 Android/iOS 设备验收麦克风权限、停止录音、任意文件导入、离线同步和后台提醒。
6. 配置正式 Android 签名密钥和 Apple 证书后再生成商店包。
