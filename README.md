# Sayo Sense

面向上海商办经纪团队的信息资产库。移动端优先语音录入，支持把听到、看到、收到的业务信息和任意格式资料收进同一条业务记录；后端负责原件保存、OCR/ASR、字段整理和检索。

- GitHub：<https://github.com/Arvin665/-app->
- 本地管理员邀请码：`246810`（仅本地开发默认值，生产必须更换）
- 移动端登录页不再自动聚焦邀请码输入框，避免小屏键盘遮住底部按钮。

## 部署与发布教程

- [品牌与 App Store 文案](docs/品牌与商店文案.md)
- [完整部署与上架手册](docs/完整部署与上架手册.md)
- [云服务器与数据备份部署](docs/云端部署教程.md)
- [Android 内测与正式发布](docs/安卓发布教程.md)
- [iPhone 内测与 App Store 发布](docs/苹果发布教程.md)

当前本地代码如果有未提交改动，必须先上传到 GitHub，云服务器执行 `git clone/git pull` 才会拿到最新版本。不要只把代码留在 Windows 工作区。

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
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 默认 `deepseek-chat`；模型标识可能调整，以 DeepSeek 官方控制台当前列表为准 |

在项目根目录新建 `.env`（不是 `.env.local`），DeepSeek 部分按下面原样填写，只需把 Key 换成真实值：

```dotenv
AI_PROVIDER=auto
DEEPSEEK_API_KEY=sk-你的真实Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=90
```

配置文件里不要写反斜杠 `\`，不要写 Markdown。后端会自动请求 `https://api.deepseek.com/chat/completions`，该业务默认使用 JSON 输出；修改 `.env` 后必须重启后端。不要假定某个模型名永久是“最新版本”，请以 DeepSeek 官方控制台当前可用模型列表为准；模型名写错时会自动降级到本地规则。

录入页显示“DeepSeek 智能整理”表示本次调用成功；显示“本地智能整理”表示已自动降级，并在说明中给出网络、Key 或模型失败原因。

DeepSeek 接入属于外部网络调用。生产环境应确认团队对资料外发的授权、脱敏策略和供应商数据处理条款；不应把 API Key 写入前端或提交到 Git。

## 资料和字段规则

- 四个入口：项目买卖、企业租赁、工作记录、个人灵感角。
- 买卖信息不设置业务必填项，可以先只记一句“听到/看到/知道”的线索，价格、买家、时间等以后再补充。
- 所有模块都可以先存原话、再逐项补充；历史、草稿和资料库可回看之前内容。
- `+` 入口支持拍照、相册和系统文件选择，原件先落盘，再尝试正文提取。图片、扫描 PDF、文本 PDF、TXT/Markdown、CSV、XLSX、DOCX、PPTX、音频、视频都有提取适配器。
- 没有适配器的格式仍按原格式保存，不会因为识别失败而丢文件。
- 交易记录中的语音原话会进入备注，结构化字段只写入能从内容中确认的信息。所有自动整理结果都需要人工核对。

## 数据存放与跨模块联动

- 业务记录、设备身份、邀请码、操作日志和跨模块关联存放在 MySQL；生产使用持久化 Docker Volume，普通重启和 `docker compose down` 不会删除数据。
- 用户上传的任意格式原件、缩略图和音视频统一存放在 `uploads_data` Volume；数据库只保存元数据和内部地址，不把大文件塞进 MySQL。
- 四个业务模块沿用各自的结构化字段；原始文字、原话和文件识别正文作为可追溯材料保留。项目买卖允许空字段保存线索，不强制补全。
- `sys_record_link` 是用户确认后的显式关联表。系统可依据同类楼宇或项目名给出候选，但不会按名称自动合并，避免把同名项目错连。
- 详情上下文接口会同时返回当前记录、资料、早期附件、已确认关联和“可能相关”建议，移动端可从一条记录跳转到另一条。
- 后台文件不再公开挂在 `/uploads/`，统一通过带有效期的 `/api/v1/files/...` 签名地址读取；关联、搜索和候选建议均执行现有成员权限。
- 管理端导出备份包含 `sys_record_link`，但仍遵守工作记录和个人灵感的隔离规则。生产备份脚本位于 `scripts/backup.sh`（Linux）和 `scripts/backup.ps1`（Windows）。

## 计划与提醒闭环

- 一段连续口述会先由 DeepSeek/本地规则拆成多条计划候选，不直接写入数据库。
- 核对页可逐条修改正文、日期、时间和关联项目，也可删除、补一条或取消勾选。
- 点击“确认创建并提醒”后，所有勾选计划通过一次事务批量保存；任一条校验失败会整批回滚。
- Android/iOS 原生端使用 Capacitor Local Notifications 调度后台提醒；H5 只能保证页面打开期间的前台提醒。
- 没有明确执行时刻的计划保留为“全天”，后台按当天 08:30 提醒，但不会把 08:30 写成计划执行时间。
- 已完成或搁置的计划会取消对应提醒；计划列表重新加载时会重新同步定时任务。

## 验收

已在当前 Windows 环境执行：

```powershell
Set-Location .\backend
& '..\.venv\Scripts\python.exe' -m pytest tests -q
Set-Location .\mobile-app
npm.cmd run build:h5
npm.cmd run native:sync:android:debug
```

当前结果：

- 后端测试：`20 passed`，覆盖批量计划原子保存、归档锁定、相对日期纠错、多任务拆分、跨模块关联与搜索、签名文件、备份版本和旧库初始邀请码停用。
- H5 构建通过；Capacitor Android 资源同步通过，已注册 `@capacitor/local-notifications`。
- 真实 DeepSeek 实测：用户示例拆为 4 条计划，日期均为 `2026-11-18`；仅首条带 `10:30`，其余保持未指定时刻。
- SenseVoiceSmall 真实中文样例：本机 `zh.wav` 成功转写为“开饭时间早上9点至下午5点。”，端点返回 `provider=sensevoice`。
- 麦克风权限、系统文件选择器和手机真机语音必须在有界面的设备上人工验收；无头环境不能代替真实录音验收。

当前机器与 CI 状态：

- 历史 GitHub Actions 曾通过 [Docker/MySQL/Redis 联调](https://github.com/Arvin665/-app-/actions/runs/44042488671)；本轮新增跨模块关联表、签名文件访问和 CORS 调整后，当前机器仍没有 Docker CLI，尚未重新做全栈容器联调，不能把旧结果当成本轮已验证。
- Android Debug APK：已在 [GitHub Actions Android 构建](https://github.com/Arvin665/-app-/actions/runs/44048218168) 通过；artifact `asset-library-android-debug` 内的 `app-debug.apk` 为 4,384,323 字节。这是调试包，不是正式签名发布包。
- iOS 模拟器包：已在 [GitHub Actions iOS 构建](https://github.com/Arvin665/-app-/actions/runs/44047326183) 通过；产物是未签名模拟器构建，不是 IPA，也没有上架。
- 当前机器没有 Docker CLI、Java、Android SDK 或 Xcode；本机无法重复 Android/iOS 原生构建。
- 尚未完成真机麦克风、系统文件选择器、Android/iOS 安装和后台提醒验收。
- 真实 DeepSeek Key 当前已配置，并已完成一次真实接口实测；额度、网络异常和长期稳定性仍需持续观察。
- `uni build -p app` 旧导出链路仍会遇到 IIFE 与代码分块不兼容；当前 Capacitor 原生包以 H5 构建同步为准，不把该命令视为已通过。
- 尚未生成正式签名的 APK/IPA，也未完成应用商店发布。

## 生产上线前

1. 更换管理员邀请码、数据库密码和 `SENSITIVE_FIELD_KEY`，不要沿用示例值。
2. 配置 HTTPS、真实域名和 CORS 白名单；移动浏览器录音必须使用 HTTPS。
   Android 原生容器需要 `https://localhost`，iOS 原生容器需要 `capacitor://localhost`；两者都要和正式域名一起写入 `CORS_ORIGINS`。
3. 按团队数据处理要求决定是否启用 DeepSeek，并对客户姓名、电话、交易文件做必要脱敏。
4. 执行一次 MySQL/附件备份恢复演练，确认原件和正文都能恢复。
5. 用真实 Android/iOS 设备验收麦克风权限、停止录音、任意文件导入、离线同步和后台提醒。
6. 配置正式 Android 签名密钥和 Apple 证书后再生成商店包。
