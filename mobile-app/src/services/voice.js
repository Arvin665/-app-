function browserRecognition() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function dictationAvailable() {
  return Boolean(browserRecognition() || (typeof plus !== "undefined" && plus.speech?.startRecognize));
}

export function startDictation({
  onInterim = () => {},
  onFinal = () => {},
  onError = () => {},
  onEnd = () => {},
  continuous = true,
} = {}) {
  let stopped = false;
  let finished = false;
  const Recognition = browserRecognition();

  if (Recognition) {
    const recognition = new Recognition();
    recognition.lang = "zh-CN";
    recognition.continuous = continuous;
    recognition.interimResults = true;
    let transcript = "";
    recognition.onresult = (event) => {
      transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join("")
        .trim();
      onInterim(transcript);
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted" && !stopped) {
        onError(new Error(event.error === "not-allowed" ? "请允许麦克风权限后重试" : "语音识别暂时不可用"));
      }
    };
    recognition.onend = () => {
      if (finished) return;
      finished = true;
      if (transcript) onFinal(transcript);
      onEnd(transcript);
    };
    try {
      recognition.start();
    } catch (error) {
      onError(error instanceof Error ? error : new Error("麦克风启动失败"));
      onEnd("");
      return null;
    }
    return {
      stop() {
        stopped = true;
        recognition.stop();
      },
      abort() {
        stopped = true;
        recognition.onend = null;
        recognition.abort();
        onEnd("");
      },
    };
  }

  if (typeof plus !== "undefined" && plus.speech?.startRecognize) {
    let nativeActive = true;
    const finish = (text, error) => {
      if (finished) return;
      finished = true;
      nativeActive = false;
      if (error && !stopped) onError(error);
      if (text && !stopped) onFinal(text);
      onEnd(text || "");
    };
    try {
      plus.speech.startRecognize(
        { engine: "iFly", punctuation: true, timeout: 60000, userInterface: false },
        (text) => finish(text, null),
        (error) => finish("", error instanceof Error ? error : new Error(error?.message || "语音识别失败")),
      );
    } catch (error) {
      onError(error instanceof Error ? error : new Error("麦克风启动失败"));
      onEnd("");
      return null;
    }
    return {
      stop() {
        stopped = true;
        if (nativeActive && plus.speech?.stopRecognize) plus.speech.stopRecognize();
      },
      abort() {
        stopped = true;
        if (nativeActive && plus.speech?.stopRecognize) plus.speech.stopRecognize();
        if (!finished) onEnd("");
      },
    };
  }

  return null;
}
