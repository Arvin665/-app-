// Capture browser console and runtime errors for a local UI smoke check.
// Usage: node scripts/cdp-listen.mjs <url-fragment> [reload|none] [milliseconds]
import { setTimeout as delay } from "node:timers/promises";

const [, , targetFragment, action = "none", waitMs = "2500"] = process.argv;
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
const messages = [];
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
    return;
  }

  if (message.method === "Runtime.exceptionThrown") {
    const details = message.params.exceptionDetails;
    messages.push({
      type: "exception",
      text: details.exception?.description || details.text,
      url: details.url,
      line: details.lineNumber,
      column: details.columnNumber,
    });
  }
  if (message.method === "Runtime.consoleAPICalled") {
    messages.push({
      type: `console.${message.params.type}`,
      text: message.params.args.map((arg) => arg.value ?? arg.description ?? "").join(" "),
    });
  }
  if (message.method === "Log.entryAdded") {
    messages.push({
      type: `log.${message.params.entry.level}`,
      text: message.params.entry.text,
      url: message.params.entry.url,
    });
  }
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
await send("Log.enable");
if (action === "reload") {
  await send("Page.enable");
  await send("Page.reload", { ignoreCache: true });
}
await delay(Number(waitMs));
console.log(JSON.stringify({ target: target.url, messages }, null, 2));
socket.close();
