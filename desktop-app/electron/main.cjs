const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain, Notification, shell } = require("electron");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");

let mainWindow = null;
let tray = null;
let quitting = false;

// 使用本机稳定信息派生设备标识，不上传主机名或用户名原文。
const rawIdentity = `${os.hostname()}|${os.userInfo().username}|${os.platform()}|asset-library-desktop`;
const deviceId = crypto.createHash("sha256").update(rawIdentity).digest("hex").slice(0, 32);
const deviceName = `${os.hostname()} · Windows`;

const appIconPath = path.join(__dirname, "assets/app-icon.png");
const trayIconPath = path.join(__dirname, "assets/tray-icon.png");

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 980,
    minWidth: 1180,
    minHeight: 720,
    title: "Sayo Sense",
    icon: appIconPath,
    backgroundColor: "#F5F7FA",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL || "http://127.0.0.1:5174";
  if (!app.isPackaged) mainWindow.loadURL(devUrl);
  else mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));

  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
}

function showWindow() {
  if (!mainWindow) createWindow();
  mainWindow.show();
  mainWindow.focus();
}

function createTray() {
  const icon = nativeImage.createFromPath(trayIconPath).resize({ width: 16, height: 16 });
  tray = new Tray(icon);
  tray.setToolTip("Sayo Sense");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "打开主界面", click: showWindow },
      { label: "立即同步", click: () => { showWindow(); mainWindow?.webContents.send("desktop:sync-now"); } },
      { type: "separator" },
      { label: "退出", click: () => { quitting = true; app.quit(); } },
    ]),
  );
  tray.on("double-click", showWindow);
}

app.whenReady().then(() => {
  app.setAppUserModelId("com.assetlibrary.desktop");
  if (app.isPackaged) app.setLoginItemSettings({ openAtLogin: true, openAsHidden: true });
  createWindow();
  createTray();
});

app.on("activate", showWindow);
app.on("before-quit", () => { quitting = true; });
app.on("window-all-closed", () => {
  // Windows 托盘常驻，关闭窗口时不退出进程。
});

ipcMain.handle("desktop:get-info", () => ({
  deviceId,
  deviceName,
  platform: os.platform(),
  release: os.release(),
  version: app.getVersion(),
  isPackaged: app.isPackaged,
}));

ipcMain.handle("desktop:set-auto-launch", (_event, enabled) => {
  if (!app.isPackaged) return { enabled: false, development: true };
  app.setLoginItemSettings({ openAtLogin: Boolean(enabled), openAsHidden: true });
  return app.getLoginItemSettings();
});

ipcMain.handle("desktop:get-auto-launch", () => app.getLoginItemSettings());

ipcMain.handle("desktop:notify", (_event, payload = {}) => {
  if (!Notification.isSupported()) return false;
  const notification = new Notification({ title: payload.title || "Sayo Sense", body: payload.body || "" });
  notification.on("click", showWindow);
  notification.show();
  return true;
});

ipcMain.handle("desktop:show-window", showWindow);
