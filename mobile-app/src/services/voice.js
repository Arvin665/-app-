function browserRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

const EMPTY_RESULT_MESSAGE = "没有听到内容，请再说一次";
const BROWSER_STOP_FALLBACK_MS = 1600;
const NATIVE_STOP_FALLBACK_MS = 4000;
let currentSession = null;

function notify(callback, ...args) {
  try {
    callback?.(...args);
  } catch (error) {
    console.error("Voice callback failed", error);
  }
}

function speechError(value) {
  if (value instanceof Error) return value;
  const message = String(value?.message || value?.errMsg || value || "").trim();
  const normalized = message.toLowerCase();
  if (normalized.includes("no-speech") || normalized.includes("没有听到")) {
    return new Error(EMPTY_RESULT_MESSAGE);
  }
  if (normalized.includes("not-allowed") || normalized.includes("permission") || normalized.includes("权限")) {
    return new Error("请允许麦克风权限后重试");
  }
  if (normalized.includes("audio-capture") || normalized.includes("microphone")) {
    return new Error("没有找到可用麦克风，请检查设备设置");
  }
  if (normalized.includes("network") || normalized.includes("网络")) {
    return new Error("网络不稳定，语音识别未完成，请重试");
  }
  if (normalized.includes("aborted") || normalized.includes("取消")) {
    return new Error("语音识别已取消");
  }
  return new Error(message || "语音识别暂时不可用，请重试");
}

export function dictationAvailable() {
  return Boolean(browserRecognition() || (typeof plus !== "undefined" && plus.speech?.startRecognize));
}

export function startDictation({
  onInterim = () => {},
  onFinal = () => {},
  onError = () => {},
  onEnd = () => {},
  onStateChange = () => {},
  continuous = true,
} = {}) {
  const Recognition = browserRecognition();
  const nativeSpeech = typeof plus !== "undefined" && plus.speech?.startRecognize ? plus.speech : null;
  if (!Recognition && !nativeSpeech) return null;

  if (currentSession && currentSession.state !== "finished") currentSession.abort("replaced");

  let state = "starting";
  let transcript = "";
  let engineError = null;
  let endNotified = false;
  let abortRequested = false;
  let stopRequested = false;
  let stopTimer = null;
  let lastResult = null;
  let stopEngine = null;
  let abortEngine = null;
  let resolveStop;
  const stopPromise = new Promise((resolve) => {
    resolveStop = resolve;
  });

  const setState = (nextState) => {
    if (state === nextState) return;
    state = nextState;
    notify(onStateChange, state);
  };

  const complete = (reason = "ended", explicitError = null) => {
    if (endNotified) return lastResult;
    endNotified = true;
    clearTimeout(stopTimer);
    state = "finished";

    const text = String(transcript || "").trim();
    let finalError = explicitError || engineError || null;
    if (!abortRequested) {
      if (text) {
        notify(onFinal, text);
      } else if (!finalError) {
        finalError = new Error(EMPTY_RESULT_MESSAGE);
      }
      if (finalError) notify(onError, finalError);
    }

    lastResult = { text, reason, error: finalError || null, aborted: abortRequested };
    notify(onStateChange, "finished");
    if (currentSession === session) currentSession = null;
    resolveStop(lastResult);
    notify(onEnd, lastResult);
    return lastResult;
  };

  const session = {
    get state() {
      return state;
    },
    get isActive() {
      return !endNotified;
    },
    stop() {
      if (endNotified) return Promise.resolve(lastResult);
      if (state === "stopping") return stopPromise;
      stopRequested = true;
      setState("stopping");
      clearTimeout(stopTimer);
      stopTimer = setTimeout(
        () => complete("stopped-timeout", engineError),
        nativeSpeech && !Recognition ? NATIVE_STOP_FALLBACK_MS : BROWSER_STOP_FALLBACK_MS,
      );
      try {
        stopEngine?.();
      } catch (error) {
        engineError = speechError(error);
      }
      return stopPromise;
    },
    abort(reason = "aborted") {
      if (endNotified) return Promise.resolve(lastResult);
      abortRequested = true;
      setState("stopping");
      clearTimeout(stopTimer);
      try {
        abortEngine?.();
      } catch (error) {
        engineError = speechError(error);
      }
      complete(reason);
      return Promise.resolve(lastResult);
    },
  };

  currentSession = session;

  if (Recognition) {
    let recognition;
    try {
      recognition = new Recognition();
    } catch (error) {
      engineError = speechError(error);
      complete("error", engineError);
      return null;
    }

    recognition.lang = "zh-CN";
    recognition.continuous = continuous;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      if (abortRequested) return;
      transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join("")
        .trim();
      if (transcript) notify(onInterim, transcript);
    };
    recognition.onerror = (event) => {
      if (abortRequested) return;
      const code = String(event?.error || "");
      if (code === "aborted") {
        complete(stopRequested ? "stopped" : "aborted");
        return;
      }
      engineError = speechError(code);
      complete("error", engineError);
    };
    recognition.onend = () => complete(stopRequested ? "stopped" : "ended");
    stopEngine = () => recognition.stop();
    abortEngine = () => recognition.abort();

    try {
      recognition.start();
      setState("listening");
    } catch (error) {
      engineError = speechError(error);
      complete("error", engineError);
      return null;
    }
    return session;
  }

  try {
    stopEngine = nativeSpeech.stopRecognize ? () => nativeSpeech.stopRecognize() : null;
    abortEngine = stopEngine;
    nativeSpeech.startRecognize(
      { engine: "iFly", punctuation: true, timeout: 60000, userInterface: false },
      (text) => {
        transcript = String(text || "").trim();
        complete(stopRequested ? "stopped" : "ended");
      },
      (error) => {
        engineError = speechError(error);
        complete("error", engineError);
      },
    );
    setState("listening");
  } catch (error) {
    engineError = speechError(error);
    complete("error", engineError);
    return null;
  }
  return session;
}
