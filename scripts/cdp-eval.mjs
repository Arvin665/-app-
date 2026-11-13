// Minimal Chrome DevTools Protocol helper for local UI smoke checks.
// Usage: node scripts/cdp-eval.mjs <url-fragment> "<javascript expression>"
import fs from "node:fs";
import path from "node:path";

const [, , targetFragment, expression = "document.body.innerText"] = process.argv;
const targets = await fetch("http://127.0.0.1:9222/json/list").then((response) => response.json());
const target = targets.find((item) => item.type === "page" && item.url.includes(targetFragment));
if (!target) throw new Error(`No page target found for ${targetFragment}`);

const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let nextId = 1;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function send(method, params = {}) {
  const id = nextId++;
  const response = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  socket.send(JSON.stringify({ id, method, params }));
  return response;
}

await send("Runtime.enable");
await send("Page.enable");
await send("Page.bringToFront");
if (process.env.CDP_WIDTH && process.env.CDP_HEIGHT) {
  await send("Emulation.setDeviceMetricsOverride", {
    width: Number(process.env.CDP_WIDTH),
    height: Number(process.env.CDP_HEIGHT),
    deviceScaleFactor: 1,
    mobile: process.env.CDP_MOBILE === "1",
  });
}

// Browser file inputs cannot be assigned directly. Inject a File through
// DataTransfer before running the requested expression when requested.
if (process.env.CDP_FILE_INPUT && process.env.CDP_FILE_PATH) {
  const file = fs.readFileSync(process.env.CDP_FILE_PATH);
  const fileName = path.basename(process.env.CDP_FILE_PATH);
  const fileExpression = `(() => {
    const input = document.querySelector(${JSON.stringify(process.env.CDP_FILE_INPUT)});
    if (!input) throw new Error("file input not found");
    const bytes = Uint8Array.from(atob(${JSON.stringify(file.toString("base64"))}), c => c.charCodeAt(0));
    const file = new File([bytes], ${JSON.stringify(fileName)}, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return file.name;
  })()`;
  const injected = await send("Runtime.evaluate", {
    expression: fileExpression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (injected.exceptionDetails) throw new Error(injected.exceptionDetails.text);
}

const evaluation = await send("Runtime.evaluate", {
  expression,
  awaitPromise: true,
  returnByValue: true,
  userGesture: true,
});
if (evaluation.exceptionDetails) {
  console.error(JSON.stringify(evaluation.exceptionDetails, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify(evaluation.result.value, null, 2));
}

if (process.env.CDP_SCREENSHOT) {
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  fs.writeFileSync(process.env.CDP_SCREENSHOT, Buffer.from(shot.data, "base64"));
}

socket.close();
