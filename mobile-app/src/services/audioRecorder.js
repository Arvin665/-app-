function audioContextConstructor() {
  if (typeof window === "undefined") return null;
  return window.AudioContext || window.webkitAudioContext || null;
}

export function canRecordWav() {
  return Boolean(
    typeof navigator !== "undefined"
    && navigator.mediaDevices?.getUserMedia
    && audioContextConstructor(),
  );
}

function writeAscii(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function encodeWav(chunks, sampleRate) {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, sampleCount * 2, true);

  let offset = 44;
  chunks.forEach((chunk) => {
    for (let index = 0; index < chunk.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, chunk[index]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  });
  return new Blob([buffer], { type: "audio/wav" });
}

export async function startWavRecorder() {
  if (!canRecordWav()) {
    throw new Error("当前浏览器不支持录音上传");
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
  const Context = audioContextConstructor();
  const context = new Context({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const silentOutput = context.createGain();
  const chunks = [];
  let closed = false;
  let sampleCount = 0;
  let sumSquares = 0;
  let peak = 0;

  silentOutput.gain.value = 0;
  processor.onaudioprocess = (event) => {
    if (closed) return;
    const chunk = new Float32Array(event.inputBuffer.getChannelData(0));
    chunks.push(chunk);
    for (let index = 0; index < chunk.length; index += 1) {
      const sample = chunk[index];
      sumSquares += sample * sample;
      peak = Math.max(peak, Math.abs(sample));
    }
    sampleCount += chunk.length;
  };
  source.connect(processor);
  processor.connect(silentOutput);
  silentOutput.connect(context.destination);
  await context.resume();

  function close() {
    if (closed) return;
    closed = true;
    processor.onaudioprocess = null;
    source.disconnect();
    processor.disconnect();
    silentOutput.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    context.close().catch(() => {});
  }

  return {
    stop() {
      const stats = {
        durationMs: Math.round((sampleCount / context.sampleRate) * 1000),
        peak,
        rms: sampleCount ? Math.sqrt(sumSquares / sampleCount) : 0,
        sampleRate: context.sampleRate,
      };
      close();
      return {
        blob: encodeWav(chunks, stats.sampleRate),
        ...stats,
      };
    },
    abort() {
      close();
      chunks.length = 0;
    },
  };
}
