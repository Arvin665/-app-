/** @type {import("@capacitor/cli").CapacitorConfig} */
const config = {
  appId: "com.shangban.assetlibrary",
  appName: "商办信息资产库",
  webDir: "dist/build/h5",
  backgroundColor: "#F2F5F3",
  server: {
    androidScheme: "https",
  },
  android: {
    // 仅调试构建通过环境变量放行局域网 HTTP 后台；正式构建保持 false。
    allowMixedContent: process.env.CAPACITOR_ALLOW_HTTP === "true",
  },
  ios: {
    contentInset: "automatic",
  },
};

module.exports = config;
