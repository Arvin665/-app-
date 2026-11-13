# 商办信息资产库

面向商办经纪团队的内部信息资产库 MVP，包含移动 H5、桌面 Web/Electron 管理端和 FastAPI 后端。

## 已交付内容

| 目录 | 内容 |
| --- | --- |
| `backend/` | FastAPI、SQLAlchemy、SQLite/MySQL、附件、Excel、备份恢复、设备与邀请码管理、本地 OCR/ASR |
| `mobile-app/` | uni-app Vue 3 移动端，语音优先录入，支持 H5 和 App 条件编译 |
| `desktop-app/` | Vue 3 + Element Plus 桌面 Web 与 Electron 客户端 |
| `docker/` | 移动 H5 的 Nginx 镜像、反向代理和 HTTPS 示例 |
| `docker-compose.yml` | MySQL 8、Redis 7、后端和 H5 Web 的生产编排 |
| `scripts/` | MySQL 与附件卷备份脚本、浏览器验收辅助脚本 |
| `backend/tests/` | 后端主流程和权限、隐私、备份范围测试 |

当前可直接使用的 Windows 产物：

- 安装包：`desktop-app/release/商办信息资产库-Setup-1.0.0.exe`
- 免安装目录：`desktop-app/release/win-unpacked/`
- 免安装程序：`desktop-app/release/win-unpacked/商办信息资产库.exe`
- 安装包 SHA-256：`83C6A739FDCB02B0A5E6C5BC1D2660B7185833EFF42F5AB3B2D88BE5D5338ABF`

安装包当前未配置代码签名，Windows SmartScreen 可能提示未知发布者。安装器也未配置自定义应用图标，使用 Electron 默认图标。正式分发前应补充品牌图标、签名证书和发布流程。

## 技术架构

- 后端：Python 3.12、FastAPI、SQLAlchemy 2、Fernet 敏感字段加密。
- 识别：RapidOCR + PyMuPDF 处理图片和扫描 PDF；Windows 使用 System.Speech，Linux/Docker 使用 Vosk 中文离线模型；ffmpeg 提取音视频音轨。
- 本地数据库：SQLite，零配置启动，适合单机开发和验收。
- 生产数据库：MySQL 8，数据卷持久化，由 `backend/app/database/init.sql` 初始化。
- 缓存：Redis 7 可选，只缓存设备鉴权和同步游标；Redis 故障时回退数据库查询，不承载业务主数据。
- 移动端：uni-app Vue 3，可编译 H5 和应用资源。
- 桌面端：Vue 3、Element Plus、Electron，支持托盘、开机自启、系统通知和离线缓存。
- 鉴权：邀请码绑定设备后，使用 `X-Device-ID` 访问接口，没有账号密码、MFA 或长期 Token。

## 本地启动

要求：Python 3.12、Node.js 20/22。以下命令均在项目根目录执行。

### 1. 后端与 SQLite

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r '.\backend\requirements.txt'
Set-Location .\backend
& '..\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

本地默认数据库为 `backend/asset_library.db`，首次启动自动建表。接口文档：

- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- Swagger：`http://127.0.0.1:8000/docs`

本地开发默认邀请码是 `246810`。首次绑定成功后该邀请码成为管理员邀请码；生产环境必须在第一次启动前修改 `BOOTSTRAP_INVITE_CODE`。

### 2. 移动 H5

```powershell
Set-Location .\mobile-app
npm ci
Copy-Item .env.example .env.local
npm run dev:h5
```

访问 `http://127.0.0.1:5173`。生产构建：

```powershell
npm run build:h5
```

构建输出在 `mobile-app/dist/build/h5`。

### 移动端语音与资料录入

- 四个模块共用语音优先录入页：可以整段口述，也可以对文本、日期、时间、金额、状态和开关字段逐项语音补充或修正。
- 再次点击麦克风会停止录音、上传后台识别，并在返回文字后自动整理字段。
- H5 使用 Edge/Chrome 录音权限，把麦克风音频转为 16 位单声道 WAV，再调用 `/api/v1/ai/transcribe`；不支持录音上传的浏览器才回退到浏览器语音识别。原生 App 使用 `plus.speech`。
- 录入页和资料库支持拍照、相册及 H5 系统文件导入。原件先落盘，再尝试识别，不因识别失败而丢失文件；单个文件上限为 50 MB。
- 当前可提取并可搜索正文的格式包括 TXT/Markdown、CSV、XLSX、DOCX、PPTX、文字 PDF、图片 OCR、扫描 PDF OCR，以及音频和视频中的语音。没有适配器的格式仍按原件保存，不伪造识别结果。
- Windows 本机默认使用系统中文离线识别；Linux/Docker 使用 Vosk。需要在本机准备 Vosk 备用引擎时运行：`& '.\.venv\Scripts\python.exe' 'backend\scripts\download_vosk_model.py'`。
- 项目买卖信息不设置业务必填项，可以只记下一条项目名称、传闻或零散线索，价格、买家、时间和交易条件均可之后补充。
- 四个模块均可在工作台查看最近记录，并通过模块历史、全部历史或资料库回看之前的记录和材料。

### 3. 桌面 Web 与 Electron

```powershell
Set-Location .\desktop-app
npm ci
Copy-Item .env.example .env.local
npm run dev:web
```

桌面 Web 访问 `http://127.0.0.1:5174`。启动 Electron 开发客户端：

```powershell
npm run dev
```

生产构建和 Windows 安装包：

```powershell
npm run build
npm run dist:win
```

如果当前 Windows 环境因 `winCodeSign` 符号链接权限或 GitHub 下载失败，可使用已验证的兼容命令：

```powershell
$env:ELECTRON_BUILDER_BINARIES_MIRROR = 'https://npmmirror.com/mirrors/electron-builder-binaries/'
npm run build
npx electron-builder --win nsis --config.win.signAndEditExecutable=false
```

兼容命令跳过 EXE 元数据编辑，因此不会写入自定义版本信息或图标，也不会进行代码签名。`VITE_API_BASE_URL` 是构建时变量，正式打包前必须改成实际 HTTPS API 地址，然后重新构建。

## Docker 生产启动

Docker 拓扑为：`web -> backend -> mysql/redis`。后端不直接暴露端口，H5 和 API 都通过 Nginx 的 80 端口访问。

后端镜像会安装 ffmpeg、RapidOCR/PyMuPDF 运行库，并在构建时下载 Vosk 中文模型和 ONNX OCR 依赖。首次构建需要访问 PyPI、模型下载站和基础镜像仓库。

```powershell
Copy-Item .env.example .env
# 编辑 .env，至少替换数据库密码、SENSITIVE_FIELD_KEY 和邀请码
docker compose up -d --build
docker compose ps
```

默认访问 `http://localhost`。如设置 `WEB_PORT=8080`，则访问 `http://localhost:8080`。

关键配置：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 后端连接串；Docker 中使用 `mysql+pymysql://...@mysql:3306/...` |
| `REDIS_URL` | Redis 地址，可选能力，故障时自动退化 |
| `SENSITIVE_FIELD_KEY` | 佣金等敏感字段加密密钥，部署后必须保持稳定 |
| `PUBLIC_BASE_URL` | 对外站点根地址，例如 `https://asset.example.com`，用于附件 URL |
| `CORS_ORIGINS` | 允许的前端来源，多个地址用英文逗号分隔 |
| `BOOTSTRAP_INVITE_CODE` | 空库首次启动的管理员邀请码 |
| `AUTO_CREATE_TABLES` | Docker 中为 `false`，由 MySQL 初始化 SQL 建表 |
| `UPLOAD_DIR` | 附件目录，Docker 中为 `/app/uploads` |
| `OCR_ENABLED` | 是否启用图片/扫描 PDF OCR，默认 `true` |
| `ASR_ENGINE` | `auto`、`vosk` 或 `windows-speech`；Docker 中固定为 `vosk` |
| `ASR_TIMEOUT_SECONDS` | 单次录音或音视频转写超时，默认 180 秒 |

`backend/app/database/init.sql` 会先删除同名业务表再创建，只适合空数据卷首次初始化。不要把该脚本重复执行到已有生产库。修改 `SENSITIVE_FIELD_KEY` 会导致已有加密佣金无法解密。

## HTTPS 示例

`docker/nginx-https.example.conf` 提供 80 跳转 443、TLS 1.2/1.3、安全响应头和 API 反向代理示例。当前 `docker-compose.yml` 默认仍使用 HTTP 配置。启用 HTTPS 时需要：

1. 将域名和证书路径替换为真实值。
2. 用 HTTPS 配置覆盖容器内的 `/etc/nginx/conf.d/default.conf`。
3. 为 `web` 服务增加 `443:443` 端口和证书只读挂载，例如 `./certs:/etc/nginx/certs:ro`。
4. 设置 `PUBLIC_BASE_URL=https://asset.example.com`、`CORS_ORIGINS=https://asset.example.com`，然后重建 Web。

该 HTTPS 示例未在本机实际启用验证。

## 备份与恢复

### 管理员 ZIP 备份

桌面管理员后台可下载 ZIP，包含 `database.json`、管理员可见业务数据、设备/邀请码元数据、附件原件，以及资料库的 `sys_material` 元数据、原件和图片缩略图。成员私有工作记录、个人灵感及未共享的工作资料不会因管理员身份被越权纳入备份。

恢复接口和后台界面采用“按主键合并”，不会清空现有库，也不会覆盖设备身份和邀请码。恢复属于数据写入操作，执行前应确认包来源并先保留当前备份。

### MySQL 与附件卷脚本备份

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup.ps1
```

Linux：

```sh
sh scripts/backup.sh
```

默认备份到 `backups/`，保留 30 天。脚本输出 MySQL SQL 和附件 `tar.gz`。恢复时建议先停止后端，再按备份时的数据库和附件版本成对恢复：

```sh
docker compose stop backend
docker compose exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < backups/database_YYYYMMDD_HHMMSS.sql
docker compose run --rm --no-deps -T backend tar -xzf - -C /app < backups/uploads_YYYYMMDD_HHMMSS.tar.gz
docker compose start backend
```

## 当前能力边界

- AI 文本结构化仍使用本地规则，不调用第三方大模型，结果必须人工核对。
- 本机已用真实中文图片、图片型 PDF、WAV 和 MP4 验证 OCR、扫描 PDF OCR、音频 ASR、视频 ASR。Windows 识别文本可能有同音字和标点误差。
- H5 语音已用浏览器假麦克风完成“开始录音 -> 再次点击停止 -> 上传 -> 识别 -> 字段整理”闭环；真实物理麦克风仍需人工听测。生产 H5 必须使用 HTTPS，否则移动浏览器会拒绝麦克风。
- `uni.chooseFile` 只提供 H5 通用文件选择。原生 App 当前已验证拍照/相册导入，但“系统文件”中的任意格式需要额外接入 Android/iOS 原生文件选择插件，尚未完成真机验收。
- 移动端只在 H5 上完成核心流程验收，App 仅生成资源构建，未完成真实 Android/iOS 原生运行验收。
- 原生通知插件 `AssetLibrary-Notification` 未随项目提供。前台运行时可使用浏览器/系统通知兜底；App 被系统杀死后，准点提醒无法保证，正式上线需在 HBuilderX 中接入原生调度插件。
- 仓库没有 APK、IPA。`npm run build:app` 只生成应用资源，APK 还需要 Android SDK、原生打包和签名；iOS 需要 macOS、证书和描述文件。
- Excel 导入导出、邀请码、设备禁用、操作日志、回收站、日常计划确认和管理员备份恢复已在桌面 Web 中做过页面验收。
- Pixso 预览材料位于 `backend/.design-preview/`。设计稿是同一 Pixso 文件的不同页面，不是两个独立设计文件：[Pixso 文件](https://pixso.cn/app/design/QV529sAa8-WKpie6S-y_wQ)。

## 验收与检查

已执行并通过：

```powershell
Set-Location .\backend
& '..\.venv\Scripts\python.exe' -m pytest tests -q
& '..\.venv\Scripts\python.exe' 'scripts\smoke_extraction.py' --speech-wav '<中文语音WAV路径>'

Set-Location .\desktop-app
npm run build

Set-Location .\mobile-app
npm run build:h5
npm run build:app
```

后端测试结果为 `4 passed`。桌面 1440x900 和移动 390x844 已完成核心页面与业务流程验收，包括邀请码、语音优先录入、AI 规则提取、计划与每日复盘、资料原格式入库/正文提取、资料详情、历史、回收站、管理员统计、设备、日志、备份下载与合并恢复。真实提取烟测依次通过图片 OCR、扫描 PDF OCR、音频 ASR、视频 ASR。

未在当前环境验证：

- Docker Compose、MySQL 8 和 Redis 的真实联调，因为本机没有可用 Docker。
- APK、IPA、iOS 签名和 Android 原生运行。
- 推送、代码签名、自动更新和商店发布仍未接入；Docker 中的 Vosk/OCR 运行尚未实际启动验证。
- 当前电脑没有 Docker CLI、WSL Linux 发行版、MySQL、Redis、Java、Android SDK 或 HBuilderX，因此不能把 Compose 启动、MySQL 持久化、Redis 实读写、APK 和真机结果标记为已验证。
- 生产 HTTPS 证书链和外部域名访问。

## 上线前最小检查

1. 换掉所有示例密码和 `SENSITIVE_FIELD_KEY`，并安全保存密钥。
2. 修改默认邀请码，绑定首个管理员后停用不需要的管理员邀请码。
3. 使用真实 HTTPS 域名，限制来源，不要把设备 ID 鉴权直接裸露在公网。
4. 执行一次数据库和附件恢复演练，确认备份可用。
5. 补原生通知插件、代码签名和正式应用图标，再分发安装包或移动安装包。
6. 在 Android/iOS 原生工程中补系统文件选择插件，并用真机验证麦克风、拍照、相册、系统文件上传和后台识别。
