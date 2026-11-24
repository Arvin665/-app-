# 腾讯云 Android APP 备案操作

这篇只解决一件事：给腾讯云 APP 备案页面准备正确的安卓包名、公钥和签名 MD5。

当前项目已经确定：

```text
App 名称：Sayo Sense
包名：com.shcredible.sayo
生产后台：https://app.sh-credible.com/api/v1
健康检查：https://app.sh-credible.com/api/v1/health
```

不要手动修改包名。包名一旦用于商店和备案，后续应与正式 APK 完全一致。

## 一、备案页面三个字段是什么

腾讯云 APP 备案弹窗要求填写：

| 字段 | 本项目应该怎么取 |
| --- | --- |
| App 包名 | `com.shcredible.sayo` |
| 公钥 | 从最终正式签名的 APK 证书中提取 |
| 签名 MD5 值 | 从同一份最终正式签名 APK 的证书中提取，通常为 32 位十六进制 |

公钥和 MD5 必须来自**同一份最终 APK**，并且必须来自**正式 Release 签名证书**。

不要使用以下证书作为正式备案依据：

- Android Studio 自动生成的 `debug.keystore`
- CI 临时构建产生的 Debug 签名
- 不同电脑上重新生成的 Debug 签名
- 任意一次修改后又重新签名的 APK

原因很简单：正式应用上架和后续升级必须长期使用同一套签名。Debug 证书通常不是固定生产证书，拿它备案后再换正式证书，会造成签名不一致。

官方参考：

- [腾讯云 APP 备案特征信息说明](https://cloud.tencent.com/document/product/243/97789)
- [腾讯云 APP 备案安卓公钥和 MD5 填写说明](https://cloud.tencent.com/document/product/243/19148)

## 二、备案前的服务器确认

先用手机浏览器打开：

```text
https://app.sh-credible.com/api/v1/health
```

必须能访问，并看到类似：

```json
{"status":"ok"}
```

服务器 `.env` 中应包含：

```dotenv
PUBLIC_BASE_URL=https://app.sh-credible.com
CORS_ORIGINS=https://app.sh-credible.com,https://localhost,capacitor://localhost
```

如果手机浏览器打不开，先修域名、HTTPS 或服务器，不要先改 App 包名和签名。

## 三、安装 Android 开发环境

在 Windows 上安装：

1. Android Studio
2. Android SDK Platform-Tools
3. Android SDK Platform 36
4. Android SDK Build-Tools 36.0.0
5. Android Studio 自带的 JDK 21

Android Studio 第一次打开后：

1. 进入 `More Actions -> SDK Manager`。
2. 打开 `SDK Platforms`，勾选 `Android 16.0 (API 36)`。
3. 打开 `SDK Tools`，勾选 `Android SDK Build-Tools 36.0.0` 和 `Android SDK Platform-Tools`。
4. 点击 `Apply`，等待安装完成。

在 Android Studio 中打开：

```text
D:\product\made from codex\写字楼业务信息管理App开发计划\mobile-app\android
```

如果提示 Gradle JDK，选择 Android Studio 自带的 JDK 21。等待 Gradle Sync 完成。

在 Android Studio 的 Terminal 中检查：

```powershell
java -version
```

## 四、创建一次正式签名密钥

只需要创建一次。以后所有版本都使用它。丢失后通常无法更新同一个应用。

### 1. 用 Android Studio 图形界面创建

在 Android Studio 菜单中：

```text
Build -> Generate Signed App Bundle / APK -> APK -> Next -> Create new
```

填写：

```text
Key store path：mobile-app\android\sayo-sense-release.jks
Password：自己设置并保存
Key alias：sayo-sense-release
Key password：自己设置并保存
Validity：至少 25 年
First and Last Name：Sayo Sense
Organizational Unit：Mobile
Organization：Sayo Sense
City：Shanghai
State：Shanghai
Country Code：CN
```

完成后，把 `.jks` 文件和两个密码保存到可信密码管理器和离线备份。

### 2. 在项目 Android 目录创建 `keystore.properties`

路径：

```text
mobile-app\android\keystore.properties
```

内容示例：

```properties
storeFile=sayo-sense-release.jks
storePassword=你的keystore密码
keyAlias=sayo-sense-release
keyPassword=你的key密码
```

注意：

- `keystore.properties` 已在 `.gitignore` 中。
- `.jks` 已在 `.gitignore` 中。
- 不要把密码写进 GitHub、聊天记录、截图或普通云盘。
- 至少做两份离线备份。
- 以后升级必须继续使用这个 `.jks`。

## 五、生成正式 Release APK

在项目 `mobile-app` 目录打开 PowerShell：

```powershell
Set-Location 'D:\product\made from codex\写字楼业务信息管理App开发计划\mobile-app'
$env:VITE_API_BASE_URL = 'https://app.sh-credible.com/api/v1'
npm.cmd ci
npm.cmd run native:build:android:release
```

构建脚本会拒绝本地地址，并会检查 `keystore.properties` 是否存在。

产物路径：

```text
mobile-app\android\app\build\outputs\apk\release\app-release.apk
```

如果构建提示没有签名，检查：

```powershell
Get-ChildItem '.\android\sayo-sense-release.jks'
Get-Content '.\android\keystore.properties'
```

不要把 `keystore.properties` 的内容发给别人。

## 六、从最终 APK 提取备案公钥和 MD5

腾讯云推荐用 jadx-gui 打开 APK 的签名信息。操作如下：

1. 从 jadx 官方发布页下载 jadx-gui：
   [https://github.com/skylot/jadx/releases](https://github.com/skylot/jadx/releases)
2. 启动 `jadx-gui`。
3. 打开：

   ```text
   mobile-app\android\app\build\outputs\apk\release\app-release.apk
   ```

4. 在左下方找到 `APK signature`。
5. 记录其中的：
   - `Public key`
   - `MD5`
6. 这两项必须来自这份 `app-release.apk`。

也可以用 Android SDK 的 `keytool` 查看证书指纹：

```powershell
keytool -printcert -jarfile '.\android\app\build\outputs\apk\release\app-release.apk'
```

输出中会包含 `MD5`、`SHA1` 和 `SHA256`。正式备案填写 `MD5`。

如果 `keytool` 只显示了指纹、没有可直接复制的公钥，仍用 jadx-gui 读取 `Public key`，不要把 SHA1 或 SHA256 当成公钥。

检查 APK 是否被正确签名：

```powershell
& "$env:ANDROID_HOME\build-tools\36.0.0\apksigner.bat" verify --print-certs '.\android\app\build\outputs\apk\release\app-release.apk'
```

看到证书信息和验证成功，才继续备案。

## 七、填写腾讯云弹窗

按以下方式填写：

```text
App 包名：com.shcredible.sayo
公钥：从 app-release.apk 的 APK signature 中复制
签名 MD5 值：从同一份 app-release.apk 的 APK signature 中复制
```

签名 MD5 通常是 32 位十六进制字符串。不要手动添加空格、冒号或其他内容。

点击腾讯云页面的“验证”后，如果提示不通过，优先核对：

1. APK 是否真的是 Release 签名版本。
2. 公钥和 MD5 是否来自同一份 APK。
3. 包名是否仍为 `com.shcredible.sayo`。
4. 是否误用了 `app-debug.apk` 或 Android Studio Debug 证书。

## 八、安装到手机验收

手机开启“开发者选项”和“USB 调试”，连接电脑后执行：

```powershell
adb devices
adb install -r '.\android\app\build\outputs\apk\release\app-release.apk'
```

至少检查：

- 能通过邀请码登录。
- 顶部能显示生产服务连接正常。
- 语音录音可以开始、停止、识别。
- 任一文件能上传并在历史中回看。
- 提醒弹窗能出现并能关闭。
- 卸载前先确认已备份正式签名密钥。

## 九、目录和备份

本机需要保留：

```text
mobile-app\android\sayo-sense-release.jks
mobile-app\android\keystore.properties
```

还需要把以下内容抄写或存入密码管理器：

```text
keystore 密码
key 密码
key alias
证书指纹
首次创建日期
```

不要把 `.jks`、`keystore.properties` 或密码提交到 GitHub。

## 十、本次正式 APK 备案取值（2026-11-24）

当前源码已经具备：

- 包名 `com.shcredible.sayo`
- 生产 API 注入入口
- Release 签名配置读取
- Android 36 编译配置
- 生产地址构建脚本

本次已经生成并通过 `apksigner` 验签的正式 APK，腾讯云页面填写：

```text
App 包名：
com.shcredible.sayo

签名 MD5 值：
b1b7a97200ccb9f188b0673013c7c6a3
```

公钥（SPKI DER 十六进制，完整复制这一整行）：

```text
30820122300d06092a864886f70d01010105000382010f003082010a0282010100eec2b3b97d1c8c4b45858a64d25cdd6ff6fb267a184ed712e60cd006ab8badc8c4f8c4d42f0f8a123ebfe2672de0a25bd64411f04f6b4a8167c86b435fd4a41d12fd333c66de52fcccd2c3a00daf435e434209ca80975edec8e0b9ca8a207fbdcc7c860d50cb65f0c20623a0ac9955f69c02dd1323d3513deba1e32c11e5c53b544e02945a20a711279442598e73198b1f3766aa623385a4b52d90e93ba11c3bebace082d3fa670379b40823f0c776ed6a8f6a11cbd6147343011f3f131f509c1210ba2d8a95fd23bff5b90937fa4ddbbb3c55d6e1310c19be9b0c96ff0040c86fc2e28c01b1f83c2c469d2ea1854b06532112ea720e8fb2c0fb1b25d305d0650203010001
```

APK 文件：

```text
release\Sayo-Sense-Android\Sayo-Sense-v1.0-release.apk
```

该结果已同时写入 `release\Sayo-Sense-Android\腾讯云APP备案信息.txt`。公钥、MD5 和 APK 必须作为同一套正式签名材料保存。
