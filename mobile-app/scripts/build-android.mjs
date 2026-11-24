import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const mobileDir = path.resolve(scriptDir, "..");
const androidDir = path.join(mobileDir, "android");
const mode = process.argv.includes("--release") ? "release" : "debug";
const apiBaseUrl = (
  process.env.VITE_API_BASE_URL || "https://app.sh-credible.com/api/v1"
).replace(/\/$/, "");

if (mode === "release" && !apiBaseUrl.startsWith("https://")) {
  throw new Error("Release APK must use an HTTPS API address.");
}

if (mode === "release" && /localhost|127\.0\.0\.1|10\.0\.2\.2/i.test(apiBaseUrl)) {
  throw new Error("Release APK cannot use a local API address.");
}

if (mode === "release") {
  const signingProperties = path.join(androidDir, "keystore.properties");
  if (!fs.existsSync(signingProperties)) {
    throw new Error(
      "Missing mobile-app/android/keystore.properties. Configure the permanent release keystore before building a filing or store APK.",
    );
  }
}

const env = {
  ...process.env,
  VITE_API_BASE_URL: apiBaseUrl,
  CAPACITOR_ALLOW_HTTP: mode === "debug" && process.env.CAPACITOR_ALLOW_HTTP === "true" ? "true" : "false",
};

if (mode === "release") {
  delete env.VITE_BOOTSTRAP_INVITE_HINT;
}

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const npx = process.platform === "win32" ? "npx.cmd" : "npx";
const gradle = process.platform === "win32" ? "gradlew.bat" : "./gradlew";

function run(command, args, cwd, extraEnv = env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      env: extraEnv,
      stdio: "inherit",
      shell: process.platform === "win32" && /\.(cmd|bat)$/i.test(command),
    });

    child.on("error", reject);
    child.on("exit", (code, signal) => {
      if (signal) {
        reject(new Error(`${command} terminated by ${signal}`));
        return;
      }
      if (code !== 0) {
        reject(new Error(`${command} exited with code ${code}`));
        return;
      }
      resolve();
    });
  });
}

console.log(`Building Android ${mode} APK`);
console.log(`API base: ${apiBaseUrl}`);

await run(npm, ["run", "build:h5"], mobileDir);
await run(npx, ["cap", "sync", "android"], mobileDir);

if (process.platform !== "win32") {
  fs.chmodSync(path.join(androidDir, "gradlew"), 0o755);
}

const task = mode === "release" ? "assembleRelease" : "assembleDebug";
await run(gradle, ["--no-daemon", task], androidDir);

const apk = path.join(
  androidDir,
  "app",
  "build",
  "outputs",
  "apk",
  mode,
  mode === "release" ? "app-release.apk" : "app-debug.apk",
);

if (!fs.existsSync(apk)) {
  throw new Error(`APK was not generated at ${apk}`);
}

console.log(`APK ready: ${apk}`);
