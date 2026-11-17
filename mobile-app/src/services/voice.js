import { transcribeAudio, transcribeFile } from "./api";
import { canRecordWav, startWavRecorder } from "./audioRecorder";

function nativeRecorderAvailable() {
  return Boolean(
    typeof plus !== "undefined"
    && plus.audio?.getRecorder
    && (plus.os?.name === "Android" || plus.os?.name === "iOS"),
  );
}

function browserRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

const EMPTY_RESULT_MESSAGE = "录音文件没有生成成功，请检查麦克风权限后重试";
const NO_TEXT_MESSAGE = "录音已结束，但没有识别到文字。请靠近麦克风，说完后稍等半秒再点结束。";
const SILENT_RECORDING_MESSAGE = "录音里没有检测到声音，请确认麦克风输入设备没有被静音。";
const BROWSER_STOP_FALLBACK_MS = 1600;
const NATIVE_STOP_FALLBACK_MS = 4000;
const MIN_AUDIO_PEAK = 0.0015;
const SERVER_ASR_STOP_WAIT_MS = 125000;
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
  if (
    normalized.includes("no-speech")
    || normalized.includes("no speech")
    || normalized.includes("没有听到")
    || normalized.includes("未识别到")
  ) {
    return new Error(NO_TEXT_MESSAGE);
  }
  if (normalized.includes("not-allowed") || normalized.includes("permission") || normalized.includes("权限")) {
    return new Error("请允许麦克风权限后重试");
  }
  if (normalized.includes("audio-capture") || normalized.includes("microphone")) {
    return new Error("没有找到可用麦克风，请检查设备设置");
  }
  if (normalized.includes("notfound") || normalized.includes("devicesnotfound")) {
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
  return Boolean(
    browserRecognition()
    || nativeRecorderAvailable()
    || canRecordWav()
    || (typeof plus !== "undefined" && plus.speech?.startRecognize),
  );
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
  const serverRecorderKind = nativeRecorderAvailable() ? "native" : canRecordWav() ? "browser" : "";
  const preferServerRecognition = Boolean(serverRecorderKind);
  if (!Recognition && !nativeSpeech && !preferServerRecognition) return null;

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
        finalError = null;
        notify(onFinal, text);
      } else {
        if (!finalError) finalError = new Error(NO_TEXT_MESSAGE);
        notify(onError, finalError);
      }
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
        () => complete(
          "stopped-timeout",
          engineError || (preferServerRecognition ? new Error("语音识别超时，请重试") : null),
        ),
        preferServerRecognition
          ? SERVER_ASR_STOP_WAIT_MS
          : nativeSpeech && !Recognition
            ? NATIVE_STOP_FALLBACK_MS
            : BROWSER_STOP_FALLBACK_MS,
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

  if (serverRecorderKind === "native") {
    let nativeRecorder = null;
    let finalizing = false;

    const finishNativeRecording = async (recorded) => {
      if (finalizing || abortRequested) return;
      finalizing = true;
      const filePath = typeof recorded === "string"
        ? recorded
        : recorded?.path || recorded?.filePath || "";
      if (!filePath) {
        complete("error", new Error(EMPTY_RESULT_MESSAGE));
        return;
      }
      try {
        const result = await transcribeFile(filePath);
        transcript = String(result?.text || "").trim();
        complete(stopRequested ? "stopped" : "ended");
      } catch (error) {
        engineError = speechError(error);
        complete("error", engineError);
      }
    };

    try {
      nativeRecorder = plus.audio.getRecorder();
      stopEngine = () => {
        if (nativeRecorder) nativeRecorder.stop();
      };
      abortEngine = () => {
        if (nativeRecorder) nativeRecorder.stop();
        nativeRecorder = null;
      };
      const filename = `_doc/asset-library-dictation-${Date.now()}.wav`;
      nativeRecorder.record(
        { filename, format: "wav" },
        (recorded) => {
          nativeRecorder = null;
          finishNativeRecording(recorded || filename);
        },
        (error) => {
          nativeRecorder = null;
          if (abortRequested) return;
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

  if (serverRecorderKind === "browser") {
    let recorder = null;
    let recognition = null;
    let finalizePromise = null;
    let recognitionRestarts = 0;
    let recognitionDone = !Recognition;
    let serverDone = false;
    let browserTranscript = "";
    let browserError = null;
    let serverError = null;
    let recorderStats = null;

    const settle = (reason = "ended") => {
      if (abortRequested || endNotified || !stopRequested) return;
      const serverText = String(transcript || "").trim();
      if (serverDone && serverText) {
        transcript = serverText;
        complete(reason);
        return;
      }
      if (!serverDone || !recognitionDone) return;
      // 浏览器识别只作为实时预览和 SenseVoice 故障时的兜底。
      const browserText = String(browserTranscript || "").trim();
      if (browserText) {
        transcript = browserText;
        complete(reason);
        return;
      }
      const finalError = serverError || browserError || engineError || new Error(NO_TEXT_MESSAGE);
      engineError = finalError;
      complete("error", finalError);
    };

    const beginBrowserRecognition = () => {
      if (!Recognition || abortRequested) return;
      try {
        recognition = new Recognition();
      } catch (error) {
        browserError = speechError(error);
        recognitionDone = true;
        settle("stopped");
        return;
      }
      recognitionDone = false;
      recognition.lang = "zh-CN";
      recognition.continuous = continuous;
      recognition.interimResults = true;
      recognition.onresult = (event) => {
        if (abortRequested || endNotified) return;
        browserTranscript = Array.from(event.results)
          .map((result) => result[0]?.transcript || "")
          .join("")
          .trim();
        if (browserTranscript) notify(onInterim, browserTranscript);
      };
      recognition.onerror = (event) => {
        if (abortRequested || endNotified) return;
        const code = String(event?.error || "");
        if (code !== "aborted") browserError = speechError(code);
        recognitionDone = true;
        settle("stopped");
      };
      recognition.onend = () => {
        if (abortRequested || endNotified) {
          recognitionDone = true;
          return;
        }
        if (stopRequested || browserError) {
          recognitionDone = true;
          settle("stopped");
          return;
        }
        if (continuous && recognitionRestarts < 2) {
          recognitionRestarts += 1;
          setTimeout(beginBrowserRecognition, 80);
          return;
        }
        recognitionDone = true;
        if (!continuous && browserTranscript) session.stop();
      };
      try {
        recognition.start();
        if (!stopRequested) setState("listening");
      } catch (error) {
        browserError = speechError(error);
        recognitionDone = true;
        settle("stopped");
      }
    };

    const stopBrowserRecognition = () => {
      if (!recognition) {
        recognitionDone = true;
        return;
      }
      try {
        recognition.stop();
      } catch (error) {
        browserError = speechError(error);
        recognitionDone = true;
      }
      setTimeout(() => {
        if (!recognitionDone) {
          recognitionDone = true;
          settle("stopped");
        }
      }, BROWSER_STOP_FALLBACK_MS);
    };

    const finalizeRecording = async () => {
      if (finalizePromise || abortRequested) return finalizePromise;
      finalizePromise = (async () => {
        if (!recorder) {
          serverError = new Error(NO_TEXT_MESSAGE);
          serverDone = true;
          settle("stopped");
          return;
        }
        const activeRecorder = recorder;
        recorder = null;
        let stopped;
        try {
          stopped = activeRecorder.stop();
        } catch (error) {
          serverError = speechError(error);
          serverDone = true;
          settle("stopped");
          return;
        }
        const audioBlob = stopped?.blob || stopped;
        recorderStats = stopped?.blob ? stopped : null;
        if (!audioBlob || audioBlob.size <= 44) {
          serverError = new Error(NO_TEXT_MESSAGE);
          serverDone = true;
          settle("stopped");
          return;
        }
        if (recorderStats && recorderStats.durationMs < 250) {
          serverError = new Error(NO_TEXT_MESSAGE);
          serverDone = true;
          settle("stopped");
          return;
        }
        if (recorderStats && recorderStats.peak < MIN_AUDIO_PEAK) {
          serverError = new Error(SILENT_RECORDING_MESSAGE);
          serverDone = true;
          settle("stopped");
          return;
        }
        try {
          const result = await transcribeAudio(audioBlob);
          transcript = String(result?.text || "").trim();
          if (!transcript) serverError = new Error(NO_TEXT_MESSAGE);
        } catch (error) {
          serverError = speechError(error);
        } finally {
          serverDone = true;
          settle("stopped");
        }
      })();
      return finalizePromise;
    };

    stopEngine = () => {
      stopBrowserRecognition();
      if (recorder) finalizeRecording();
    };
    abortEngine = () => {
      try {
        recognition?.abort?.();
      } catch (error) {
        // 结束流程以用户取消为准，不再提示识别错误。
      }
      recorder?.abort();
      recorder = null;
    };

    beginBrowserRecognition();
    startWavRecorder()
      .then((instance) => {
        recorder = instance;
        if (abortRequested) {
          recorder.abort();
          recorder = null;
          return;
        }
        if (!stopRequested) setState("listening");
        if (stopRequested) finalizeRecording();
      })
      .catch((error) => {
        if (abortRequested) return;
        serverError = speechError(error);
        serverDone = true;
        if (!Recognition) complete("error", serverError);
        else settle("stopped");
      });
    return session;
  }

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
