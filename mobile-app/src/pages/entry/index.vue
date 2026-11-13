<template>
  <view class="entry-page">
    <PageHeader :title="config.name" :fallback="'/pages/home/index'">
      <template #actions>
        <view class="header-actions">
          <text class="header-action" @tap="openDrafts">草稿</text>
          <text class="header-action" @tap="openSecondary">{{ moduleKey === "work" ? "待办" : "历史" }}</text>
        </view>
      </template>
    </PageHeader>

    <view class="entry-body">
      <view class="confirm-pane">
        <view class="confirm-card">
          <view class="card-header">
            <view>
              <text class="card-title">识别结果 · 请核对</text>
              <text v-if="editingId" class="edit-tag">正在编辑已有记录</text>
            </view>
            <text class="confidence-summary">{{ lowConfidenceCount ? `${lowConfidenceCount} 项待确认` : "字段已核对" }}</text>
          </view>

          <scroll-view class="field-scroll" scroll-y>
            <view v-for="field in visibleFields" :key="field.key" class="field-row" :class="{ warning: isLowConfidence(field) }">
              <text class="field-label">{{ field.label }}</text>
              <view class="field-value" @tap="startEdit(field)">
                <template v-if="editingField === field.key">
                  <input
                    v-if="['text', 'number'].includes(field.type)"
                    v-model="form[field.key]"
                    class="inline-input"
                    :type="field.type === 'number' ? 'digit' : 'text'"
                    :focus="true"
                    :placeholder="placeholderFor(field)"
                    @blur="finishEdit"
                    @confirm="finishEdit"
                  />
                  <textarea
                    v-else-if="field.type === 'textarea'"
                    v-model="form[field.key]"
                    class="inline-textarea"
                    :focus="true"
                    :placeholder="placeholderFor(field)"
                    auto-height
                    @blur="finishEdit"
                  />
                  <picker
                    v-else-if="field.type === 'select'"
                    :range="field.options"
                    @change="selectOption(field, $event)"
                  >
                    <view class="picker-value">{{ form[field.key] || "请选择" }}</view>
                  </picker>
                  <picker
                    v-else-if="field.type === 'date'"
                    mode="date"
                    :value="form[field.key] || today"
                    @change="selectOption(field, $event)"
                  >
                    <view class="picker-value">{{ form[field.key] || "请选择日期" }}</view>
                  </picker>
                  <picker
                    v-else-if="field.type === 'time'"
                    mode="time"
                    :value="form[field.key] || '09:00'"
                    @change="selectOption(field, $event)"
                  >
                    <view class="picker-value">{{ form[field.key] || "全天" }}</view>
                  </picker>
                  <picker
                    v-else-if="field.type === 'datetime'"
                    mode="date"
                    :value="String(form[field.key] || today).slice(0, 10)"
                    @change="selectOption(field, $event)"
                  >
                    <view class="picker-value">{{ displayValue(field) }}</view>
                  </picker>
                  <switch
                    v-else-if="field.type === 'switch'"
                    :checked="Boolean(Number(form[field.key]))"
                    color="#165DFF"
                    @change="selectOption(field, $event)"
                  />
                  <text class="edit-hint">点其他位置完成</text>
                </template>

                <template v-else>
                  <text v-if="hasValue(form[field.key])" class="field-text">{{ displayValue(field) }}</text>
                  <text v-else class="missing-text">{{ field.required || field.core ? "待补充" : "未填写" }}</text>
                  <text v-if="field.unit && hasValue(form[field.key])" class="unit">{{ field.unit }}</text>
                  <text v-if="isLowConfidence(field)" class="low-tag">待核对</text>
                </template>
              </view>
            </view>

            <view class="extra-toggle" @tap="expanded = !expanded">
              <text>{{ expanded ? "收起扩展字段" : `展开全部字段（${extraFieldCount}）` }}</text>
            </view>

            <view v-if="pendingFiles.length" class="attachment-list">
              <view v-for="(file, index) in pendingFiles" :key="`${file.path}-${index}`" class="attachment-item">
                <text class="attachment-name">{{ file.name }}</text>
                <text class="attachment-remove" @tap.stop="removePendingFile(index)">移除</text>
              </view>
            </view>
          </scroll-view>

          <view class="card-actions">
            <button class="primary-button save-button" :disabled="saving" @tap="saveRecord">
              {{ saving ? "保存中..." : "确认保存" }}
            </button>
            <button class="secondary-button draft-button" @tap="saveCurrentDraft">存为草稿</button>
            <button class="text-button clear-button" @tap="clearForm">清空重录</button>
          </view>
        </view>
      </view>

      <view class="input-pane">
        <text class="input-hint">{{ voiceHint }}</text>
        <view class="input-row">
          <button
            class="voice-button"
            :class="{ recording: recording, cancelled: cancelRecording }"
            @touchstart.prevent="startVoice"
            @touchmove.prevent="moveVoice"
            @touchend.prevent="endVoice"
            @touchcancel.prevent="cancelVoice"
          >
            <view class="voice-dot"></view>
            <text class="voice-text">{{ recording ? (cancelRecording ? "松开取消" : "松开发送") : "按住说话" }}</text>
          </button>
          <input
            v-model="inputText"
            class="text-input"
            confirm-type="send"
            :disabled="analyzing"
            placeholder="输入文字，或修正字段"
            @confirm="sendText"
          />
          <button class="add-button" @tap="chooseMaterial">＋</button>
        </view>

        <view class="quick-row">
          <text v-for="example in examples" :key="example" class="quick-chip" @tap="sendExample(example)">
            {{ example }}
          </text>
        </view>
        <text class="status-line">{{ statusLine }}</text>
        <text v-if="analyzing" class="analyzing">正在识别并生成字段...</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad, onUnload } from "@dcloudio/uni-app";
import PageHeader from "../../components/PageHeader.vue";
import { upload, request, isNetworkError } from "../../services/api";
import { postForm } from "../../services/api";
import { ensureBound, getSession } from "../../services/session";
import {
  initialFields,
  localDate,
  modules,
  normalizeRecordPayload,
} from "../../data/modules";
import {
  enqueueOffline,
  getCachedRecords,
  listDrafts,
  persistPendingAttachments,
  removeDraft,
  saveDraft,
} from "../../services/localDb";
import { schedulePlanReminder } from "../../services/reminders";

const moduleKey = ref("sale");
const config = computed(() => modules[moduleKey.value]);
const form = ref({});
const confidence = ref({});
const missingFields = ref([]);
const editingField = ref("");
const expanded = ref(false);
const saving = ref(false);
const analyzing = ref(false);
const recording = ref(false);
const cancelRecording = ref(false);
const inputText = ref("");
const statusLine = ref("可直接说话，也可输入“字段名 + 新值”修正");
const pendingFiles = ref([]);
const editingId = ref("");
const today = localDate();
const startY = ref(0);
const nativeSpeechActive = ref(false);
let webRecognition = null;
let recorder = null;
// #ifdef APP-PLUS
recorder = uni.getRecorderManager();
// #endif

const fields = computed(() => config.value.fields);
const visibleFields = computed(() =>
  fields.value.filter((field) => {
    if (field.adminOnly && getSession()?.role_level !== 1) return false;
    return expanded.value || field.core;
  }),
);
const extraFieldCount = computed(() =>
  fields.value.filter((field) => !field.core && !(field.adminOnly && getSession()?.role_level !== 1)).length,
);
const lowConfidenceCount = computed(() =>
  fields.value.filter((field) => isLowConfidence(field)).length,
);
const examples = computed(() => {
  if (moduleKey.value === "sale") return ["总价改成3.2亿", "买家是陆家嘴集团"];
  if (moduleKey.value === "lease") return ["租金改成8.5", "新项目是前滩中心"];
  if (moduleKey.value === "work") return ["明天10点整理客户清单", "记录改成客户跟进"];
  return ["灵感类型改成行业观察", "标记为客户线索"];
});
const voiceHint = computed(() => {
  if (recording.value) return cancelRecording.value ? "松开手指取消本次录音" : "上滑取消，松开发送";
  return "长按说话，松手自动识别；上滑取消";
});

function resetState() {
  form.value = initialFields(moduleKey.value);
  confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
  missingFields.value = [];
  editingField.value = "";
  expanded.value = false;
  editingId.value = "";
  inputText.value = "";
  pendingFiles.value = [];
  statusLine.value = "可直接说话，也可输入“字段名 + 新值”修正";
}

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function placeholderFor(field) {
  return field.placeholder || `请输入${field.label}`;
}

function isLowConfidence(field) {
  const score = confidence.value[field.key];
  return score !== undefined && score < 0.8;
}

function displayValue(field) {
  const value = form.value[field.key];
  if (field.type === "switch") return Number(value) ? "是" : "否";
  if (field.key === "ext_field_5") {
    return { 0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置" }[Number(value)] || "未做";
  }
  return value || "";
}

function startEdit(field) {
  editingField.value = field.key;
  if (field.type === "select" && !hasValue(form.value[field.key])) {
    form.value[field.key] = field.options[0];
  }
}

function finishEdit() {
  editingField.value = "";
}

function selectOption(field, event) {
  if (field.type === "switch") form.value[field.key] = event.detail.value ? 1 : 0;
  else if (field.type === "datetime") form.value[field.key] = `${event.detail.value}T${String(form.value[field.key] || "09:00:00").split("T")[1] || "09:00:00"}`;
  else form.value[field.key] = event.detail.value;
  confidence.value[field.key] = 1;
  editingField.value = "";
}

function applyExtraction(result) {
  Object.entries(result.fields || {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") form.value[key] = value;
  });
  Object.entries(result.confidence || {}).forEach(([key, value]) => {
    confidence.value[key] = Number(value);
  });
  missingFields.value = result.missing_fields || [];
  statusLine.value = result.note || "识别完成，请核对黄色字段后保存";
  if (!Object.keys(result.fields || {}).length) {
    uni.showToast({ title: "未识别到可用字段，请补充文字", icon: "none", duration: 2600 });
  }
}

function isCorrectionCommand(text) {
  return Object.keys(form.value).length > 0 && /改成|改为|调整为|更新为|改成是|买家是|卖家是|企业是|项目是/.test(text);
}

async function analyzeText(text) {
  const trimmed = text.trim();
  if (!trimmed || analyzing.value) return;
  analyzing.value = true;
  try {
    const payload = normalizeRecordPayload(moduleKey.value, form.value);
    let result;
    if (isCorrectionCommand(trimmed)) {
      result = await request("/ai/apply-command", {
        method: "POST",
        data: { module: moduleKey.value, current_fields: payload, command: trimmed },
      });
      if (!result.changed_fields?.length) {
        result = await callExtract(trimmed);
      }
    } else {
      result = await callExtract(trimmed);
    }
    applyExtraction(result);
    inputText.value = "";
  } catch (error) {
    statusLine.value = error.message || "识别失败，请检查网络后重试";
    uni.showToast({ title: statusLine.value, icon: "none" });
  } finally {
    analyzing.value = false;
  }
}

function callExtract(text) {
  return postForm("/ai/extract", { module: moduleKey.value, text });
}

function sendText() {
  analyzeText(inputText.value);
}

function sendExample(example) {
  inputText.value = example;
  analyzeText(example);
}

async function analyzeFile(path, name) {
  analyzing.value = true;
  statusLine.value = `正在读取 ${name}`;
  try {
    const result = await upload("/ai/extract", path, { module: moduleKey.value });
    applyExtraction(result);
  } catch (error) {
    statusLine.value = error.message || "文件识别失败";
    uni.showToast({ title: statusLine.value, icon: "none" });
  } finally {
    analyzing.value = false;
  }
}

function chooseMaterial() {
  uni.showActionSheet({
    itemList: ["拍照", "从相册选择", "导入系统文件"],
    success: async (result) => {
      if (result.tapIndex < 2) {
        uni.chooseImage({
          count: 3,
          sourceType: [result.tapIndex === 0 ? "camera" : "album"],
          success: async (choice) => {
            for (let index = 0; index < choice.tempFilePaths.length; index += 1) {
              const path = choice.tempFilePaths[index];
              const name = choice.tempFiles?.[index]?.name || `图片${index + 1}.jpg`;
              pendingFiles.value.push({ path, name, file: choice.tempFiles?.[index] });
              await analyzeFile(path, name);
            }
          },
        });
        return;
      }
      if (typeof uni.chooseFile === "function") {
        uni.chooseFile({
          count: 5,
          extension: ["jpg", "jpeg", "png", "pdf", "xlsx", "doc", "docx", "mp3", "wav", "m4a"],
          success: async (choice) => {
            const paths = choice.tempFilePaths || [];
            for (let index = 0; index < paths.length; index += 1) {
              const file = choice.tempFiles?.[index] || {};
              const name = file.name || paths[index].split("/").pop() || "业务文件";
              pendingFiles.value.push({ path: paths[index], name, raw: file });
              await analyzeFile(paths[index], name);
            }
          },
          fail: (error) => {
            if (!/cancel/i.test(error.errMsg || "")) uni.showToast({ title: "当前运行环境不支持系统文件选择", icon: "none" });
          },
        });
      } else {
        uni.showToast({ title: "请在 App 或微信环境中导入文件", icon: "none" });
      }
    },
  });
}

function removePendingFile(index) {
  pendingFiles.value.splice(index, 1);
}

function beginWebRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return false;
  webRecognition = new Recognition();
  webRecognition.lang = "zh-CN";
  webRecognition.continuous = true;
  webRecognition.interimResults = true;
  let transcript = "";
  webRecognition.onresult = (event) => {
    transcript = Array.from(event.results)
      .map((result) => result[0]?.transcript || "")
      .join("");
  };
  webRecognition.onend = () => {
    if (transcript.trim()) analyzeText(transcript);
    webRecognition = null;
  };
  webRecognition.start();
  return true;
}

function startVoice(event) {
  if (analyzing.value) return;
  startY.value = event.touches?.[0]?.clientY || 0;
  cancelRecording.value = false;
  recording.value = true;

  // #ifdef H5
  if (beginWebRecognition()) return;
  // #endif

  // #ifdef APP-PLUS
  if (plus.speech?.startRecognize) {
    nativeSpeechActive.value = true;
    plus.speech.startRecognize(
      { engine: "iFly", punctuation: true, timeout: 60000 },
      (text) => {
        nativeSpeechActive.value = false;
        recording.value = false;
        if (!cancelRecording.value && text) analyzeText(text);
      },
      (error) => {
        nativeSpeechActive.value = false;
        recording.value = false;
        statusLine.value = error.message || "语音识别不可用，可改用文字输入";
      },
    );
    return;
  }
  // #endif

  if (!recorder) {
    recording.value = false;
    statusLine.value = "当前环境不支持语音录音，可改用文字输入";
    return;
  }
  recorder.start({ duration: 60000, format: "mp3", sampleRate: 16000, numberOfChannels: 1, encodeBitRate: 48000 });
}

function moveVoice(event) {
  if (!recording.value) return;
  const currentY = event.touches?.[0]?.clientY || startY.value;
  cancelRecording.value = startY.value - currentY > 80;
}

function cancelVoice() {
  cancelRecording.value = true;
  recording.value = false;
  if (webRecognition) {
    webRecognition.onend = null;
    webRecognition.stop();
    webRecognition = null;
  }
  // #ifdef APP-PLUS
  if (nativeSpeechActive.value && plus.speech?.stopRecognize) plus.speech.stopRecognize();
  // #endif
  recorder?.stop();
}

async function endVoice() {
  if (!recording.value) return;
  recording.value = false;
  if (webRecognition) {
    webRecognition.stop();
    return;
  }
  // #ifdef APP-PLUS
  if (nativeSpeechActive.value) {
    if (plus.speech?.stopRecognize) plus.speech.stopRecognize();
    nativeSpeechActive.value = false;
    return;
  }
  // #endif
  recorder?.stop();
}

recorder?.onStop((result) => {
  if (cancelRecording.value || !result.tempFilePath) return;
  analyzing.value = true;
  statusLine.value = "录音已提交，正在等待语音转写";
  upload("/ai/extract", result.tempFilePath, { module: moduleKey.value })
    .then((response) => {
      applyExtraction(response);
      if (!Object.keys(response.fields || {}).length) {
        statusLine.value = "语音已接收；当前后端为 ASR 模拟模式，请在配置中接入真实转写服务";
      }
    })
    .catch((error) => {
      statusLine.value = error.message || "语音处理失败";
    })
    .finally(() => {
      analyzing.value = false;
    });
});

recorder?.onError((error) => {
  recording.value = false;
  statusLine.value = error.errMsg || "录音失败，请检查麦克风权限";
  uni.showToast({ title: statusLine.value, icon: "none" });
});

function requiredMissing() {
  return fields.value.filter((field) => field.required && !hasValue(form.value[field.key]));
}

async function openDuplicateConfirm(error) {
  const duplicates = error.data?.detail?.duplicates || [];
  const names = duplicates.map((item) => item.summary).filter(Boolean).join("、");
  return new Promise((resolve) => {
    uni.showModal({
      title: "发现相近记录",
      content: `${names || "已有相近数据"}。是否仍要保存为新记录？`,
      confirmText: "仍然保存",
      cancelText: "返回核对",
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    });
  });
}

async function uploadPendingFiles(recordId) {
  for (const file of pendingFiles.value) {
    if (file.local?.storage === "native" || file.local?.storage === "h5") {
      // 离线附件已经持久化，交给统一队列补传。
      continue;
    }
    await upload("/attachments", file.path, { biz_type: moduleKey.value, biz_id: recordId });
  }
  pendingFiles.value = [];
}

async function persistOnline(force = false) {
  const payload = normalizeRecordPayload(moduleKey.value, form.value);
  const endpoint = `/${config.value.endpoint}${editingId.value ? `/${editingId.value}` : ""}${force ? "?force=true" : ""}`;
  const response = await request(endpoint, {
    method: editingId.value ? "PATCH" : "POST",
    data: payload,
  });
  if (pendingFiles.value.length) await uploadPendingFiles(response.record_id);
  return response;
}

function clientRecordId() {
  if (editingId.value) return editingId.value;
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

async function saveRecord() {
  if (saving.value) return;
  const missing = requiredMissing();
  if (missing.length) {
    uni.showToast({ title: `请补充：${missing.map((item) => item.label).join("、")}`, icon: "none", duration: 2600 });
    return;
  }
  saving.value = true;
  try {
    let saved;
    try {
      saved = await persistOnline(false);
    } catch (error) {
      if (error.status === 409 && (await openDuplicateConfirm(error))) {
        saved = await persistOnline(true);
      } else if (isNetworkError(error)) {
        const recordId = clientRecordId();
        const payload = normalizeRecordPayload(moduleKey.value, form.value);
        const localAttachments = await persistPendingAttachments(pendingFiles.value);
        await enqueueOffline({
          module: moduleKey.value,
          action: editingId.value ? "update" : "create",
          recordId,
          payload,
          localAttachments,
          clientUpdatedAt: new Date().toISOString(),
        });
        pendingFiles.value = [];
        saved = { record_id: recordId, offline: true };
      } else {
        throw error;
      }
    }

    if (moduleKey.value === "work" && form.value.record_type === "待办计划") {
      schedulePlanReminder({ ...form.value, record_id: saved.record_id });
    }
    uni.vibrateShort({ type: "light" });
    const message = saved.offline
      ? "已离线保存，联网后自动同步"
      : pendingFiles.value.length
        ? "保存成功，附件待上传"
        : "保存成功，可继续录入下一条";
    uni.showToast({ title: message, icon: "success", duration: 1800 });
    if (editingId.value) {
      setTimeout(() => uni.navigateBack(), 500);
      return;
    }
    resetState();
  } catch (error) {
    uni.showToast({ title: error.message || "保存失败", icon: "none", duration: 2600 });
  } finally {
    saving.value = false;
  }
}

async function saveCurrentDraft() {
  const payload = normalizeRecordPayload(moduleKey.value, form.value);
  await saveDraft(moduleKey.value, payload);
  uni.showToast({ title: "已存为本地草稿", icon: "success" });
}

async function openDrafts() {
  const drafts = (await listDrafts()).filter((item) => item.module === moduleKey.value);
  if (!drafts.length) {
    uni.showToast({ title: "当前模块没有草稿", icon: "none" });
    return;
  }
  uni.showActionSheet({
    itemList: drafts.map((item) => `${new Date(item.updated_at).toLocaleString()} · ${item.payload.content || item.payload.project_name || item.payload.company_name || "草稿"}`),
    success: async (result) => {
      const draft = drafts[result.tapIndex];
      form.value = { ...initialFields(moduleKey.value), ...draft.payload };
      confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
      await removeDraft(draft.draft_id);
      statusLine.value = "草稿已载入，请核对后保存";
    },
  });
}

function clearForm() {
  uni.showModal({
    title: "清空重录",
    content: "当前未保存内容将被清空。",
    success: (result) => {
      if (result.confirm) resetState();
    },
  });
}

function openSecondary() {
  uni.navigateTo({ url: moduleKey.value === "work" ? "/pages/plans/index" : "/pages/history/index" });
}

async function loadRecord(recordId) {
  try {
    const record = await request(`/${config.value.endpoint}/${recordId}`);
    form.value = { ...initialFields(moduleKey.value), ...record };
    confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
    editingId.value = recordId;
    statusLine.value = "已载入现有记录，保存后将覆盖更新";
  } catch (error) {
    const cached = (await getCachedRecords(moduleKey.value)).find((item) => item.record_id === recordId);
    if (cached) {
      form.value = { ...initialFields(moduleKey.value), ...cached };
      editingId.value = recordId;
      statusLine.value = "网络不可用，已载入本地缓存";
    } else {
      uni.showToast({ title: error.message || "记录加载失败", icon: "none" });
    }
  }
}

onLoad((options) => {
  if (!ensureBound()) return;
  if (modules[options?.module]) moduleKey.value = options.module;
  resetState();
  if (options?.id) loadRecord(options.id);
  if (options?.fromShare) statusLine.value = "已从分享入口带入当前模块，可继续补充文字";
});

onUnload(() => {
  if (webRecognition) webRecognition.stop();
});
</script>

<style scoped>
.entry-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--page-bg);
}
.header-actions {
  display: flex;
  gap: 8px;
}
.header-action {
  color: var(--accent);
  font-size: 13px;
}
.entry-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.confirm-pane {
  flex: 55 1 0;
  min-height: 0;
  padding: 0 16px 8px;
}
.confirm-card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 8px;
  background: var(--surface);
}
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
}
.card-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
}
.edit-tag {
  display: block;
  margin-top: 3px;
  color: var(--warning);
  font-size: 11px;
}
.confidence-summary {
  color: var(--text-muted);
  font-size: 11px;
}
.field-scroll {
  flex: 1;
  min-height: 0;
}
.field-row {
  min-height: 42px;
  display: flex;
  align-items: center;
  margin: 0 16px;
  border-bottom: 1px solid var(--border);
}
.field-row.warning {
  margin: 0;
  padding: 0 16px;
  border-bottom-color: #ffe2b8;
  background: var(--warning-bg);
}
.field-label {
  width: 108px;
  flex: none;
  color: var(--text-secondary);
  font-size: 13px;
}
.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 0;
}
.field-text {
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.missing-text {
  color: var(--text-muted);
  font-size: 13px;
}
.unit,
.low-tag {
  flex: none;
  font-size: 10px;
}
.unit {
  color: var(--text-muted);
}
.low-tag {
  margin-left: auto;
  color: var(--warning);
}
.inline-input,
.inline-textarea,
.picker-value {
  width: 100%;
  color: var(--text-primary);
  font-size: 13px;
}
.inline-textarea {
  min-height: 44px;
  line-height: 20px;
}
.edit-hint {
  flex: none;
  color: var(--text-muted);
  font-size: 10px;
}
.extra-toggle {
  padding: 10px 16px;
  color: var(--accent);
  font-size: 12px;
}
.attachment-list {
  padding: 0 16px 10px;
}
.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  margin-bottom: 4px;
  background: var(--page-bg);
}
.attachment-name {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-remove {
  flex: none;
  margin-left: 8px;
  color: var(--warning);
  font-size: 11px;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
}
.save-button {
  flex: 1.2;
  height: 36px;
  line-height: 36px;
}
.draft-button {
  flex: 1;
  height: 36px;
  line-height: 34px;
}
.clear-button {
  width: 66px;
  height: 36px;
  line-height: 36px;
  font-size: 12px;
}
.save-button[disabled] {
  opacity: 0.6;
}
.input-pane {
  flex: 45 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  background: #f7f8fa;
}
.input-hint {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 18px;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.voice-button {
  width: 74px;
  height: 74px;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
}
.voice-button.recording {
  background: #0e4ed8;
}
.voice-button.cancelled {
  background: var(--warning);
}
.voice-dot {
  width: 12px;
  height: 16px;
  border: 2px solid #ffffff;
  border-radius: 8px;
}
.voice-text {
  margin-top: 4px;
  color: #ffffff;
  font-size: 10px;
  line-height: 13px;
}
.text-input {
  flex: 1;
  min-width: 0;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-size: 13px;
}
.add-button {
  width: 40px;
  height: 40px;
  flex: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 24px;
  line-height: 36px;
  text-align: center;
}
.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.quick-chip {
  padding: 6px 8px;
  border-radius: 4px;
  background: #eef0f3;
  color: var(--text-secondary);
  font-size: 11px;
}
.status-line {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 17px;
}
.analyzing {
  display: block;
  margin-top: 4px;
  color: var(--accent);
  font-size: 11px;
}
</style>
