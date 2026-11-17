import { spawn } from "node:child_process";

const executable = process.platform === "win32" ? "npx.cmd" : "npx";
const child = spawn(executable, ["cap", "sync", "android"], {
  stdio: "inherit",
  shell: process.platform === "win32",
  env: {
    ...process.env,
    CAPACITOR_ALLOW_HTTP: "true",
  },
});

child.on("error", (error) => {
  console.error(error);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`Capacitor sync terminated by ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 1);
});
