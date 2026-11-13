const { contextBridge, ipcRenderer } = require("electron");

// 渲染层只拿到白名单系统能力，不暴露 Node 文件系统与进程 API。
contextBridge.exposeInMainWorld("desktop", {
  getSystemInfo: () => ipcRenderer.invoke("desktop:get-info"),
  setAutoLaunch: (enabled) => ipcRenderer.invoke("desktop:set-auto-launch", enabled),
  getAutoLaunch: () => ipcRenderer.invoke("desktop:get-auto-launch"),
  notify: (payload) => ipcRenderer.invoke("desktop:notify", payload),
  showWindow: () => ipcRenderer.invoke("desktop:show-window"),
  onSyncNow: (callback) => {
    const handler = () => callback();
    ipcRenderer.on("desktop:sync-now", handler);
    return () => ipcRenderer.removeListener("desktop:sync-now", handler);
  },
});
