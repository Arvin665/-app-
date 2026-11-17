<template>
  <view class="entry-page app-page">
    <PageHeader :title="`${config.visual.short}记录`" :fallback="`/pages/module/index?module=${moduleKey}`">
      <template #actions>
        <view class="header-actions">
          <view class="header-action pressable" @tap="openDrafts"><text>草稿</text></view>
          <view class="header-action pressable" @tap="openHistory"><text>历史</text></view>
        </view>
      </template>
    </PageHeader>

    <scroll-view class="entry-scroll" scroll-y>
      <view class="module-hero" :class="`tone-${moduleKey}`">
        <view class="hero-head">
          <ModuleMark :module-key="moduleKey" size="lg" />
          <view class="hero-copy">
            <text class="hero-kicker">{{ config.visual.kicker }}</text>
            <text class="hero-title">{{ editingId ? "补充这条记录" : heroTitle }}</text>
            <text class="hero-desc">{{ config.visual.description }}</text>
          </view>
        </view>

        <view class="voice-capture pressable" :class="{ recording: voice.active && voice.kind === 'main', stopping: voice.active && voice.kind === 'main' && voice.phase === 'stopping' }" @tap="toggleMainVoice">
          <view class="voice-mark">
            <Square v-if="voice.active && voice.kind === 'main'" :size="21" fill="currentColor" />
            <Mic v-else :size="25" />
          </view>
          <view class="voice-copy">
            <text class="voice-title">{{ mainVoiceTitle }}</text>
            <text class="voice-note">{{ mainVoiceNote }}</text>
          </view>
          <view v-if="voice.active && voice.kind === 'main'" class="voice-wave">
            <view v-for="index in 4" :key="index" class="wave-bar" :style="{ animationDelay: `${index * 90}ms` }"></view>
          </view>
          <ChevronRight v-else :size="18" class="voice-arrow" />
        </view>

        <view class="text-capture">
          <textarea
            v-model="inputText"
            class="raw-input"
            auto-height
            maxlength="3000"
            :disabled="analyzing"
            placeholder="也可以补一句文字，或直接修正字段"
          />
          <view class="raw-actions">
            <view class="parse-hint">
              <TextQuote :size="14" />
              <text>{{ analyzing ? "正在整理信息..." : "说错可以直接说：总价改成 3.2 亿" }}</text>
            </view>
            <button class="send-button pressable" :disabled="!inputText.trim() || analyzing" @tap="sendText">
              <ArrowUp :size="17" />
            </button>
          </view>
        </view>
      </view>

      <view class="record-summary" :class="{ incomplete: missingFields.length }">
        <view class="summary-icon"><Check v-if="!missingFields.length" :size="17" /><CircleHelp v-else :size="17" /></view>
        <view class="summary-copy">
          <text class="summary-title">{{ summaryTitle }}</text>
          <text class="summary-note">{{ summaryNote }}</text>
          <text v-if="providerLabel" class="summary-provider">{{ providerLabel }}</text>
        </view>
        <text v-if="moduleKey === 'sale'" class="summary-tag">自由记录</text>
      </view>

      <view v-if="recognizedItems.length" class="summary-detail">
        <view class="summary-detail-head">
          <text class="summary-detail-title">已整理关键信息</text>
          <text class="summary-detail-count">{{ recognizedItems.length }} 项</text>
        </view>
        <view class="summary-grid">
          <view v-for="item in recognizedItems" :key="item.key" class="summary-item">
            <text class="summary-item-label">{{ item.label }}</text>
            <text class="summary-item-value">{{ item.value }}</text>
          </view>
        </view>
      </view>

      <view class="section-block">
        <view class="section-head">
          <view>
            <text class="section-kicker">KEY INFORMATION</text>
            <text class="section-title">关键信息</text>
          </view>
          <text class="section-count">{{ filledCoreCount }}/{{ coreFields.length }}</text>
        </view>

        <view class="field-list">
          <view v-for="field in coreFields" :key="field.key" class="field-row">
            <view class="field-main pressable" @tap="openEditor(field)">
              <view class="field-label-line">
                <text class="field-label">{{ field.label }}</text>
                <text v-if="field.required" class="required-dot"></text>
                <text v-if="confidence[field.key] !== undefined && confidence[field.key] < 0.8" class="check-tag">待核对</text>
              </view>
              <text class="field-value" :class="{ empty: !hasValue(form[field.key]) }">{{ fieldValue(field) || placeholderFor(field) }}</text>
            </view>
            <button class="field-mic pressable" :class="{ active: voice.active && voice.kind === 'field' && voice.field === field.key }" @tap.stop="speakField(field)">
              <Mic :size="16" />
            </button>
          </view>
        </view>
      </view>

      <view v-if="extraFields.length" class="section-block extra-section">
        <view class="section-head pressable" @tap="expanded = !expanded">
          <view>
            <text class="section-kicker">MORE DETAILS</text>
            <text class="section-title">补充信息</text>
          </view>
          <view class="expand-action">
            <text>{{ expanded ? "收起" : `${extraFields.length} 项` }}</text>
            <ChevronUp v-if="expanded" :size="16" />
            <ChevronDown v-else :size="16" />
          </view>
        </view>

        <view v-if="expanded" class="field-list">
          <view v-for="field in extraFields" :key="field.key" class="field-row">
            <view class="field-main pressable" @tap="openEditor(field)">
              <view class="field-label-line">
                <text class="field-label">{{ field.label }}</text>
                <text v-if="confidence[field.key] !== undefined && confidence[field.key] < 0.8" class="check-tag">待核对</text>
              </view>
              <text class="field-value" :class="{ empty: !hasValue(form[field.key]) }">{{ fieldValue(field) || placeholderFor(field) }}</text>
            </view>
            <button class="field-mic pressable" :class="{ active: voice.active && voice.kind === 'field' && voice.field === field.key }" @tap.stop="speakField(field)">
              <Mic :size="16" />
            </button>
          </view>
        </view>
      </view>

      <view class="section-block material-section">
        <view class="section-head">
          <view>
            <text class="section-kicker">ANY FORMAT</text>
            <text class="section-title">资料与原件</text>
          </view>
          <view class="add-material pressable" @tap="chooseMaterial">
            <Plus :size="17" />
            <text>添加</text>
          </view>
        </view>

        <view v-if="materials.length || pendingFiles.length || uploadingCount" class="material-list">
          <view v-for="item in materials" :key="item.material_id || item.localId" class="material-line">
            <view class="material-symbol"><FileText :size="18" /></view>
            <view class="material-copy">
              <text class="material-name">{{ item.title || item.file_name }}</text>
              <text class="material-meta">{{ materialMeta(item) }}</text>
            </view>
            <view class="material-remove pressable" @tap.stop="removeMaterial(item)"><X :size="15" /></view>
          </view>
          <view v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="material-line pending">
            <view class="material-symbol"><CloudOff :size="18" /></view>
            <view class="material-copy">
              <text class="material-name">{{ file.name }}</text>
              <text class="material-meta">等待联网后归入资料库</text>
            </view>
            <view class="material-remove pressable" @tap.stop="pendingFiles.splice(index, 1)"><X :size="15" /></view>
          </view>
          <view v-if="uploadingCount" class="material-line pending">
            <view class="material-symbol"><LoaderCircle :size="18" class="spin" /></view>
            <view class="material-copy">
              <text class="material-name">正在保存 {{ uploadingCount }} 份资料</text>
              <text class="material-meta">图片、文件、表格和音视频都按原格式存放</text>
            </view>
          </view>
        </view>
        <view v-else class="material-empty pressable" @tap="chooseMaterial">
          <view class="empty-icon"><Upload :size="22" /></view>
          <view class="empty-copy">
            <text class="empty-title">把看到、听到的材料放进来</text>
            <text class="empty-note">拍照、相册或系统文件，不限制格式</text>
          </view>
          <ChevronRight :size="17" />
        </view>
      </view>

      <view class="entry-bottom-space"></view>
    </scroll-view>

    <view class="bottom-bar safe-bottom">
      <button class="draft-action pressable" @tap="saveCurrentDraft">
        <Bookmark :size="18" />
        <text>存草稿</text>
      </button>
      <button class="save-action pressable" :disabled="saving" @tap="saveRecord">
        <LoaderCircle v-if="saving" :size="18" class="spin" />
        <Save v-else :size="18" />
        <text>{{ saving ? "正在保存" : editingId ? "保存修改" : "收好这条记录" }}</text>
      </button>
    </view>

    <view v-if="editor.visible" class="editor-mask" @tap="closeEditor">
      <view class="editor-sheet safe-bottom" @tap.stop>
        <view class="editor-head">
          <view>
            <text class="editor-kicker">VOICE OR TYPE</text>
            <text class="editor-title">{{ editor.field?.label }}</text>
          </view>
          <view class="editor-close pressable" @tap="closeEditor"><X :size="19" /></view>
        </view>

        <view v-if="editor.field?.type === 'select' || editor.field?.type === 'switch'" class="option-grid">
          <view
            v-for="option in editorOptions"
            :key="String(option.value)"
            class="option-chip pressable"
            :class="{ selected: String(editor.value) === String(option.value) }"
            @tap="editor.value = option.value"
          >
            <Check v-if="String(editor.value) === String(option.value)" :size="15" />
            <text>{{ option.label }}</text>
          </view>
        </view>

        <view v-else class="editor-input-zone">
          <picker
            v-if="['date', 'datetime'].includes(editor.field?.type)"
            mode="date"
            :value="editor.date"
            @change="pickDate"
          >
            <view class="picker-line">
              <CalendarDays :size="17" />
              <text>{{ editor.date || "选择日期" }}</text>
            </view>
          </picker>
          <picker
            v-if="['time', 'datetime'].includes(editor.field?.type)"
            mode="time"
            :value="editor.time || '09:00'"
            @change="pickTime"
          >
            <view class="picker-line">
              <Clock3 :size="17" />
              <text>{{ editor.time || "选择时间" }}</text>
            </view>
          </picker>
          <textarea
            v-if="editor.field?.type === 'textarea'"
            v-model="editor.value"
            class="editor-textarea"
            :focus="true"
            :placeholder="placeholderFor(editor.field)"
            maxlength="5000"
          />
          <input
            v-else-if="['text', 'number'].includes(editor.field?.type)"
            v-model="editor.value"
            class="editor-input"
            :type="editor.field?.type === 'number' ? 'digit' : 'text'"
            :focus="true"
            :placeholder="placeholderFor(editor.field)"
          />
        </view>

        <view class="editor-voice-hint">
          <Mic :size="15" />
          <text>不想打字，点麦克风直接说这一项</text>
        </view>

        <view class="editor-actions">
          <button class="editor-voice pressable" :class="{ recording: editor.voiceActive }" @tap="voiceCurrentEditor">
            <Square v-if="editor.voiceActive" :size="17" fill="currentColor" />
            <Mic v-else :size="18" />
            <text>{{ editor.voiceActive ? (voice.phase === "stopping" ? "收尾中" : "停止") : "语音填写" }}</text>
          </button>
          <button class="editor-save pressable" @tap="applyEditor">
            <Check :size="18" />
            <text>确认填入</text>
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onUnload } from "@dcloudio/uni-app";
import {
  ArrowUp,
  Bookmark,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  CircleHelp,
  Clock3,
  CloudOff,
  FileText,
  LoaderCircle,
  Mic,
  Plus,
  Save,
  Square,
  TextQuote,
  Upload,
  X,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import ModuleMark from "../../components/ModuleMark.vue";
import {
  initialFields,
  localDate,
  modules,
  normalizeRecordPayload,
} from "../../data/modules";
import { isNetworkError, postForm, request } from "../../services/api";
import { dictationAvailable, startDictation } from "../../services/voice";
import {
  chooseFiles,
  chooseImages,
  deleteMaterial,
  linkMaterial,
  listMaterials,
  uploadMaterial,
} from "../../services/material";
import {
  enqueueOffline,
  getCachedRecords,
  listDrafts,
  persistPendingAttachments,
  removeDraft,
  saveDraft,
} from "../../services/localDb";
import { schedulePlanReminder } from "../../services/reminders";
import { ensureBound, getSession } from "../../services/session";

const moduleKey = ref("sale");
const config = computed(() => modules[moduleKey.value]);
const form = ref({});
const confidence = ref({});
const missingFields = ref([]);
const recognizedKeys = ref([]);
const provider = ref("");
const expanded = ref(false);
const editingId = ref("");
const today = localDate();
const inputText = ref("");
const voiceStatus = ref("点一下麦克风，把事情完整说给我听");
const analyzing = ref(false);
const saving = ref(false);
const uploadingCount = ref(0);
const pendingFiles = ref([]);
const materials = ref([]);
const voice = reactive({ active: false, phase: "idle", kind: "", field: "", interim: "" });
const editor = reactive({
  visible: false,
  field: null,
  value: "",
  date: today,
  time: "09:00",
  voiceActive: false,
});
let voiceSession = null;

const heroTitle = computed(() => {
  if (moduleKey.value === "sale") return "听到什么，就记什么";
  if (moduleKey.value === "lease") return "企业的新动向，说给我听";
  if (moduleKey.value === "work") return "把今天的工作留在今天";
  return "一个念头，也值得被收好";
});
const allFields = computed(() => {
  const roleLevel = getSession()?.role_level;
  return config.value.fields.filter((field) => !field.adminOnly || roleLevel === 1);
});
const coreFields = computed(() => allFields.value.filter((field) => field.core));
const extraFields = computed(() => allFields.value.filter((field) => !field.core));
const filledCoreCount = computed(() => coreFields.value.filter((field) => hasValue(form.value[field.key])).length);
const recognizedItems = computed(() => {
  const fieldsByKey = Object.fromEntries(allFields.value.map((field) => [field.key, field]));
  return recognizedKeys.value
    .map((key) => fieldsByKey[key])
    .filter((field) => field && hasValue(form.value[field.key]))
    .map((field) => ({ key: field.key, label: field.label, value: fieldValue(field) }));
});
const providerLabel = computed(() => {
  if (provider.value === "deepseek") return "DeepSeek 智能整理";
  if (provider.value === "local-rule") return "本地智能整理";
  return "";
});
const mainVoiceTitle = computed(() => {
  if (voice.active && voice.kind === "main" && voice.phase === "stopping") return "正在收尾，请稍等";
  if (voice.active && voice.kind === "main") return "正在听你说";
  return "点一下，说完整情况";
});
const mainVoiceNote = computed(() => {
  if (voice.active && voice.kind === "main") {
    if (voice.phase === "stopping") return voice.interim || "正在整理刚才的内容，请稍等";
    return voice.interim || "正在听，再按一下结束并整理";
  }
  return voiceStatus.value;
});
const summaryTitle = computed(() => {
  if (editingId.value) return `正在补充已有${config.value.visual.short}记录`;
  if (filledCoreCount.value === 0) return moduleKey.value === "sale" ? "可以先记一句零散资讯" : "还没有填写关键信息";
  return `已整理 ${filledCoreCount.value} 项关键信息`;
});
const summaryNote = computed(() => {
  if (analyzing.value) return "正在把语音整理进对应字段，请稍候";
  if (missingFields.value.length) return `还有 ${missingFields.value.length} 项建议补充，也可以先保存`;
  if (moduleKey.value === "sale") return "没有必填项，价格、买家和时间都可以之后再补";
  return "可以直接保存，也可以继续逐项补充或补充资料";
});
const editorOptions = computed(() => {
  if (editor.field?.type === "switch") {
    return [
      { value: 0, label: "仅本人可见" },
      { value: 1, label: "团队共享" },
    ];
  }
  return (editor.field?.options || []).map((option) => ({ value: option, label: option }));
});

function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function placeholderFor(field) {
  return field?.placeholder || "未填写，点这里补充";
}

function fieldValue(field) {
  if (!field) return "";
  const value = form.value[field.key];
  if (!hasValue(value)) return "";
  if (field.type === "switch") return Number(value) ? "团队共享" : "仅本人可见";
  if (field.type === "datetime") return String(value).replace("T", " ").slice(0, 16);
  return `${value}${field.unit ? ` ${field.unit}` : ""}`;
}

function resetState() {
  form.value = initialFields(moduleKey.value);
  confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
  missingFields.value = [];
  expanded.value = false;
  recognizedKeys.value = [];
  provider.value = "";
  editingId.value = "";
  inputText.value = "";
  pendingFiles.value = [];
  materials.value = [];
  voiceStatus.value = "点一下麦克风，把事情完整说给我听";
  closeEditor();
}

function applyExtraction(result, rawText = "") {
  const incoming = Object.entries(result.fields || {}).filter(([, value]) => value !== null && value !== undefined && value !== "");
  incoming.forEach(([key, value]) => {
    if (Object.prototype.hasOwnProperty.call(form.value, key)) form.value[key] = value;
  });
  Object.entries(result.confidence || {}).forEach(([key, value]) => {
    confidence.value[key] = Number(value);
  });
  recognizedKeys.value = incoming.map(([key]) => key).filter((key) => Object.prototype.hasOwnProperty.call(form.value, key));
  provider.value = String(result.provider || "");
  missingFields.value = result.missing_fields || [];
  const storedText = String(result.corrected_text || rawText || "").trim();
  if (storedText) inputText.value = storedText;
  const transcriptLabel = result.corrected_text ? "语音整理" : "语音原文";
  if (!incoming.length && rawText) {
    preserveTranscript(storedText, transcriptLabel);
    voiceStatus.value = "已经先把原话存进备注，之后可以继续补充字段";
  } else {
    voiceStatus.value = result.note || `整理出 ${incoming.length} 项信息，请看一眼再保存`;
    if (storedText) preserveTranscript(storedText, transcriptLabel);
  }
}

function preserveTranscript(text, label = "语音原文") {
  const clean = String(text || "").trim();
  if (!clean) return;
  if (["sale", "lease"].includes(moduleKey.value)) {
    if (!String(form.value.remark || "").includes(clean)) {
      form.value.remark = [form.value.remark, `${label}：${clean}`].filter(Boolean).join("\n\n");
    }
    return;
  }
  if (!hasValue(form.value.content)) form.value.content = clean;
}

function isCorrectionCommand(text) {
  return /改成|改为|调整为|更新为|不是|应该是/.test(text);
}

function extractionIntent() {
  return moduleKey.value === "work" && form.value.record_type === "待办计划" ? "plans" : "record";
}

async function analyzeText(text) {
  const trimmed = String(text || "").trim();
  if (!trimmed || analyzing.value) return;
  analyzing.value = true;
  voiceStatus.value = "正在理解这段话，并整理到字段...";
  try {
    let result;
    if (isCorrectionCommand(trimmed)) {
      result = await request("/ai/apply-command", {
        method: "POST",
        data: {
          module: moduleKey.value,
          current_fields: normalizeRecordPayload(moduleKey.value, form.value),
          command: trimmed,
        },
      });
      if (!result.changed_fields?.length) {
        result = await postForm("/ai/extract", {
          module: moduleKey.value,
          text: trimmed,
          intent: extractionIntent(),
        });
      }
      applyExtraction({ ...result, missing_fields: result.missing_fields || [] }, trimmed);
    } else {
      result = await postForm("/ai/extract", {
        module: moduleKey.value,
        text: trimmed,
        intent: extractionIntent(),
      });
      applyExtraction(result, trimmed);
    }
    uni.vibrateShort?.({ type: "light" });
  } catch (error) {
    voiceStatus.value = error.message || "暂时没整理成功，原话还留在输入框";
    if (!inputText.value) inputText.value = trimmed;
    uni.showToast({ title: voiceStatus.value, icon: "none", duration: 2600 });
  } finally {
    analyzing.value = false;
  }
}

function sendText() {
  analyzeText(inputText.value);
}

function toggleMainVoice() {
  if (voice.active) {
    stopVoice();
    return;
  }
  startVoice("main");
}

function startVoice(kind, field = null) {
  if (analyzing.value || voice.active) return;
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "请检查麦克风权限和资料库服务连接。你仍然可以先用文字输入。",
      showCancel: false,
    });
    return;
  }
  voice.active = true;
  voice.phase = "listening";
  voice.kind = kind;
  voice.field = field?.key || "";
  voice.interim = "";
  if (kind === "main") voiceStatus.value = "正在听，再按一下结束并整理";
  else voiceStatus.value = `正在听：${field.label}，再按一下结束`;
  voiceSession = startDictation({
    continuous: true,
    onStateChange: (state) => {
      if (voice.kind !== kind) return;
      voice.phase = state;
      if (state === "stopping") {
        voiceStatus.value = kind === "main" ? "正在收尾，请稍等" : `正在收尾并整理「${field.label}」`;
      }
    },
    onInterim: (text) => {
      voice.interim = text;
      if (kind === "field" && editor.visible) editor.value = text;
    },
    onFinal: (text) => {
      voice.interim = text;
      if (kind === "main") analyzeText(text);
      else parseFieldVoice(field, text);
    },
    onError: (error) => {
      voiceStatus.value = error.message || "语音识别暂时不可用";
      uni.showToast({ title: voiceStatus.value, icon: "none", duration: 2600 });
    },
    onEnd: () => {
      if (voice.kind === kind) {
        voice.active = false;
        voice.phase = "idle";
        voice.kind = "";
        voice.field = "";
        voice.interim = "";
      }
      if (kind === "field") editor.voiceActive = false;
      voiceSession = null;
    },
  });
  if (!voiceSession) {
    voice.active = false;
    voice.phase = "idle";
    voice.kind = "";
    voice.field = "";
    voiceStatus.value = "麦克风没有启动，可以稍后重试或使用文字输入";
  }
}

async function stopVoice() {
  const session = voiceSession;
  if (!session) {
    voice.active = false;
    voice.phase = "idle";
    voice.kind = "";
    voice.field = "";
    return null;
  }
  voice.phase = "stopping";
  voiceStatus.value = voice.kind === "main" ? "正在收尾，请稍等" : "正在收尾并整理这一项";
  const result = await session.stop();
  if (voiceSession === session) voiceSession = null;
  return result;
}

async function speakField(field) {
  if (voice.active) {
    if (voice.kind === "field" && voice.field === field.key) {
      await stopVoice();
      return;
    }
    await stopVoice();
  }
  openEditor(field);
  startVoice("field", field);
}

async function parseFieldVoice(field, text) {
  if (!field || !String(text || "").trim()) return;
  voiceStatus.value = `正在理解「${field.label}」...`;
  try {
    const result = await request("/ai/parse-field", {
      method: "POST",
      data: { module: moduleKey.value, field: field.key, text: String(text).trim() },
    });
    if (result.value === null || result.value === undefined || result.value === "") {
      voiceStatus.value = result.note || "没有识别到这一项的值，请换一种说法";
      uni.showToast({ title: voiceStatus.value, icon: "none", duration: 2400 });
      return;
    }
    form.value[field.key] = result.value;
    confidence.value[field.key] = Number(result.confidence || 0.85);
    if (editor.visible && editor.field?.key === field.key) {
      editor.value = result.value;
      if (["date", "datetime"].includes(field.type)) editor.date = String(result.value).slice(0, 10);
      if (["time", "datetime"].includes(field.type)) {
        editor.time = field.type === "time" ? String(result.value) : String(result.value).split("T")[1]?.slice(0, 5) || "09:00";
      }
    }
    voiceStatus.value = `已填入「${field.label}」：${fieldValue(field)}`;
    uni.showToast({ title: "已智能填入，请核对", icon: "success" });
  } catch (error) {
    voiceStatus.value = error.message || "这一项没有识别成功";
    uni.showToast({ title: voiceStatus.value, icon: "none" });
  }
}

function openEditor(field) {
  if (!field) return;
  editor.visible = true;
  editor.field = field;
  const raw = form.value[field.key];
  editor.value = field.type === "switch" ? Number(raw || 0) : raw ?? "";
  const text = String(raw || "");
  editor.date = text.slice(0, 10) || today;
  editor.time = field.type === "time" ? text || "09:00" : text.split("T")[1]?.slice(0, 5) || "09:00";
  editor.voiceActive = voice.active && voice.kind === "field" && voice.field === field.key;
}

function closeEditor() {
  if (editor.voiceActive) stopVoice();
  editor.visible = false;
  editor.field = null;
  editor.voiceActive = false;
  editor.value = "";
}

function pickDate(event) {
  editor.date = event.detail.value;
  if (editor.field?.type === "date") editor.value = editor.date;
}

function pickTime(event) {
  editor.time = event.detail.value;
  if (editor.field?.type === "time") editor.value = editor.time;
}

function voiceCurrentEditor() {
  if (!editor.field) return;
  if (editor.voiceActive) {
    stopVoice();
    return;
  }
  editor.voiceActive = true;
  startVoice("field", editor.field);
}

function applyEditor() {
  const field = editor.field;
  if (!field) return;
  let value = editor.value;
  if (field.type === "date") value = editor.date;
  if (field.type === "time") value = editor.time;
  if (field.type === "datetime") value = `${editor.date}T${editor.time || "09:00"}:00`;
  if (field.type === "switch") value = Number(value) ? 1 : 0;
  if (field.type === "number" && hasValue(value)) value = String(value).replace(/[^\d.-]/g, "");
  form.value[field.key] = hasValue(value) ? value : null;
  confidence.value[field.key] = 1;
  voiceStatus.value = hasValue(value) ? `已更新「${field.label}」` : `已清空「${field.label}」`;
  closeEditor();
}

function chooseMaterial() {
  uni.showActionSheet({
    itemList: ["拍照", "从相册选择", "导入任意文件"],
    success: async (result) => {
      try {
        let files = [];
        if (result.tapIndex === 0) files = await chooseImages({ sourceType: ["camera"], count: 3 });
        else if (result.tapIndex === 1) files = await chooseImages({ sourceType: ["album"], count: 9 });
        else files = await chooseFiles({ count: 9 });
        if (files.length) await uploadFiles(files);
      } catch (error) {
        uni.showToast({ title: error.message || error.errMsg || "没有读取到文件", icon: "none" });
      }
    },
  });
}

async function uploadFiles(files) {
  uploadingCount.value += files.length;
  for (const file of files) {
    try {
      const uploaded = await uploadMaterial(file, {
        module: moduleKey.value,
        recordId: editingId.value || undefined,
        title: file.name.replace(/\.[^.]+$/, ""),
      });
      uploaded._needsLink = !uploaded.record_id;
      materials.value.unshift(uploaded);
    } catch (error) {
      pendingFiles.value.push(file);
      const title = isNetworkError(error) ? "已留在这里，等联网后上传" : error.message || "文件暂时没有上传成功";
      uni.showToast({ title, icon: "none", duration: 2600 });
    } finally {
      uploadingCount.value = Math.max(0, uploadingCount.value - 1);
    }
  }
}

function materialMeta(item) {
  const status = item.extraction_status === "extracted" ? "正文可检索" : item.extraction_status === "unavailable" ? "原件已保存" : "已收好";
  return `${status}${item._needsLink ? " · 待关联" : ""}`;
}

function removeMaterial(item) {
  if (!item.material_id) {
    materials.value = materials.value.filter((entry) => entry !== item);
    return;
  }
  uni.showModal({
    title: "移除这份资料",
    content: "资料会从本次录入和资料库中移除。",
    confirmColor: "#b64c46",
    success: async (result) => {
      if (!result.confirm) return;
      try {
        await deleteMaterial(item.material_id);
        materials.value = materials.value.filter((entry) => entry.material_id !== item.material_id);
      } catch (error) {
        uni.showToast({ title: error.message || "移除失败", icon: "none" });
      }
    },
  });
}

function requiredMissing() {
  return allFields.value.filter((field) => field.required && !hasValue(form.value[field.key]));
}

function openDuplicateConfirm(error) {
  const duplicates = error.data?.detail?.duplicates || [];
  const names = duplicates.map((item) => item.summary).filter(Boolean).join("、");
  return new Promise((resolve) => {
    uni.showModal({
      title: "发现相近记录",
      content: `${names || "已有相近数据"}。是否仍保存为新记录？`,
      confirmText: "仍然保存",
      cancelText: "返回核对",
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    });
  });
}

async function persistOnline(force = false) {
  const payload = normalizeRecordPayload(moduleKey.value, form.value);
  const endpoint = `/${config.value.endpoint}${editingId.value ? `/${editingId.value}` : ""}${force ? "?force=true" : ""}`;
  return request(endpoint, { method: editingId.value ? "PATCH" : "POST", data: payload });
}

function clientRecordId() {
  if (editingId.value) return editingId.value;
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}

async function linkUploadedMaterials(recordId) {
  const toLink = materials.value.filter((item) => item.material_id && item._needsLink);
  for (const item of toLink) {
    try {
      const linked = await linkMaterial(item.material_id, recordId);
      Object.assign(item, linked, { _needsLink: false });
    } catch (error) {
      console.warn("资料关联失败", error);
    }
  }
}

async function uploadOutstandingFiles(recordId) {
  if (!pendingFiles.value.length) return true;
  const outstanding = [...pendingFiles.value];
  let allUploaded = true;
  for (const file of outstanding) {
    try {
      const uploaded = await uploadMaterial(file, { module: moduleKey.value, recordId });
      materials.value.unshift(uploaded);
      pendingFiles.value = pendingFiles.value.filter((item) => item !== file);
    } catch (error) {
      allUploaded = false;
    }
  }
  return allUploaded;
}

async function saveRecord() {
  if (saving.value) return;
  const missing = requiredMissing();
  if (missing.length) {
    uni.showToast({ title: `请先补充：${missing.map((item) => item.label).join("、")}`, icon: "none", duration: 2600 });
    return;
  }
  saving.value = true;
  let savedResult = null;
  try {
    let saved;
    let offline = false;
    try {
      saved = await persistOnline(false);
    } catch (error) {
      if (error.status === 409 && (await openDuplicateConfirm(error))) {
        saved = await persistOnline(true);
      } else if (isNetworkError(error)) {
        offline = true;
        const recordId = clientRecordId();
        const localAttachments = await persistPendingAttachments(pendingFiles.value);
        await enqueueOffline({
          module: moduleKey.value,
          action: editingId.value ? "update" : "create",
          recordId,
          payload: normalizeRecordPayload(moduleKey.value, form.value),
          localAttachments,
          clientUpdatedAt: new Date().toISOString(),
        });
        pendingFiles.value = [];
        saved = { record_id: recordId, offline: true };
      } else {
        throw error;
      }
    }

    savedResult = saved;
    if (!offline) {
      await linkUploadedMaterials(saved.record_id);
      const attachmentsReady = await uploadOutstandingFiles(saved.record_id);
      if (!attachmentsReady) {
        const localAttachments = await persistPendingAttachments(pendingFiles.value);
        await enqueueOffline({
          module: moduleKey.value,
          action: "update",
          recordId: saved.record_id,
          payload: normalizeRecordPayload(moduleKey.value, form.value),
          localAttachments,
          clientUpdatedAt: new Date().toISOString(),
        });
        pendingFiles.value = [];
      }
    }

    if (moduleKey.value === "work" && form.value.record_type === "待办计划") {
      schedulePlanReminder({ ...form.value, record_id: saved.record_id });
    }
    uni.vibrateShort({ type: "light" });
    uni.showToast({
      title: offline ? "已离线收好，联网后自动同步" : "记录和资料已经收好",
      icon: "success",
      duration: 1800,
    });
    if (editingId.value) {
      setTimeout(() => uni.navigateBack(), 450);
      return;
    }
    resetState();
  } catch (error) {
    uni.showToast({ title: error.message || "保存失败，请稍后重试", icon: "none", duration: 2600 });
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
    itemList: drafts.map((item) => {
      const payload = item.payload || {};
      const title = payload.content || payload.project_name || payload.company_name || "未命名草稿";
      return `${new Date(item.updated_at).toLocaleString()} · ${String(title).slice(0, 22)}`;
    }),
    success: async (result) => {
      const draft = drafts[result.tapIndex];
      form.value = { ...initialFields(moduleKey.value), ...draft.payload };
      confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
      await removeDraft(draft.draft_id);
      voiceStatus.value = "草稿已载入，请核对后保存";
    },
  });
}

function openHistory() {
  uni.navigateTo({ url: `/pages/history/index?module=${moduleKey.value}` });
}

async function loadRecord(recordId) {
  try {
    const record = await request(`/${config.value.endpoint}/${recordId}`);
    form.value = { ...initialFields(moduleKey.value), ...record };
    confidence.value = Object.fromEntries(Object.keys(form.value).map((key) => [key, 1]));
    editingId.value = recordId;
    voiceStatus.value = "已载入现有记录，修改后保存会更新原记录";
  } catch (error) {
    const cached = (await getCachedRecords(moduleKey.value)).find((item) => item.record_id === recordId);
    if (cached) {
      form.value = { ...initialFields(moduleKey.value), ...cached };
      editingId.value = recordId;
      voiceStatus.value = "网络不可用，已载入本地缓存";
    } else {
      uni.showToast({ title: error.message || "记录加载失败", icon: "none" });
    }
  }
  try {
    const response = await listMaterials({ module: moduleKey.value, recordId, pageSize: 100 });
    materials.value = (response.items || []).map((item) => ({ ...item, _needsLink: false }));
  } catch (error) {
    materials.value = [];
  }
}

onLoad((options) => {
  if (!ensureBound()) return;
  if (modules[options?.module]) moduleKey.value = options.module;
  resetState();
  if (moduleKey.value === "work" && options?.type === "待办计划") {
    form.value.record_type = "待办计划";
    voiceStatus.value = "直接说事项和时间，例如：明天下午三点联系张总确认看房";
  }
  if (options?.id) loadRecord(options.id);
  if (options?.voice === "1") {
    voiceStatus.value = "点一下上方麦克风，直接说完整情况";
    setTimeout(() => uni.showToast({ title: "点一下麦克风开始说", icon: "none" }), 300);
  }
  if (options?.fromShare) voiceStatus.value = "已从分享入口带入，可以继续补充听到或看到的材料";
});

onUnload(() => {
  voiceSession?.abort?.();
});
</script>

<style scoped>
.entry-page {
  height: 100vh;
  overflow: hidden;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.header-action {
  min-width: 34px;
  min-height: 32px;
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.entry-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.module-hero {
  margin: 4px 16px 0;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.module-hero.tone-sale {
  border-color: #ecd2c9;
  background: linear-gradient(145deg, #fffaf8 0%, #ffffff 68%);
}
.module-hero.tone-lease {
  border-color: #cbe2dc;
  background: linear-gradient(145deg, #f5fffb 0%, #ffffff 68%);
}
.module-hero.tone-work {
  border-color: #d1dceb;
  background: linear-gradient(145deg, #f6f9ff 0%, #ffffff 68%);
}
.module-hero.tone-inspiration {
  border-color: #e9d4db;
  background: linear-gradient(145deg, #fff8fa 0%, #ffffff 68%);
}
.hero-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
}
.hero-copy {
  flex: 1;
  min-width: 0;
}
.hero-kicker,
.section-kicker,
.editor-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.hero-title {
  display: block;
  margin-top: 5px;
  color: var(--ink);
  font-size: 21px;
  font-weight: 750;
  line-height: 28px;
}
.hero-desc {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 17px;
}
.voice-capture {
  min-height: 88px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 17px;
  padding: 13px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(22, 34, 31, 0.15);
}
.voice-capture.recording {
  background: #123e35;
  box-shadow: 0 0 0 4px rgba(11, 117, 101, 0.12), 0 12px 28px rgba(22, 34, 31, 0.2);
}
.voice-capture.stopping .voice-wave,
.voice-capture.stopping .voice-mark {
  animation: none;
  opacity: 0.72;
}
.voice-mark {
  width: 48px;
  height: 48px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(138, 240, 216, 0.32);
  border-radius: 50%;
  background: rgba(119, 218, 196, 0.12);
  color: #bdf4e8;
}
.recording .voice-mark {
  background: #18a085;
  color: #ffffff;
  animation: soft-pulse 1.8s infinite;
}
.voice-copy {
  flex: 1;
  min-width: 0;
}
.voice-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
  line-height: 21px;
}
.voice-note {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  color: #b9ccc6;
  font-size: 10px;
  line-height: 16px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.voice-arrow {
  flex: none;
  color: #a8cbc2;
}
.voice-wave {
  width: 28px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}
.wave-bar {
  width: 3px;
  height: 24px;
  border-radius: 2px;
  background: #a6f0df;
  animation: voice-wave 780ms ease-in-out infinite;
}
.text-capture {
  margin-top: 14px;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.76);
}
.raw-input {
  width: 100%;
  min-height: 44px;
  max-height: 108px;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 20px;
}
.raw-actions {
  min-height: 34px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  margin-top: 5px;
}
.parse-hint {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 15px;
}
.send-button {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent);
  color: #ffffff;
}
.send-button[disabled] {
  background: var(--soft);
  color: var(--text-muted);
}
.record-summary {
  min-height: 62px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 16px 0;
  padding: 10px 12px;
  border: 1px solid #cfe6df;
  border-radius: 8px;
  background: #f1faf7;
}
.record-summary.incomplete {
  border-color: #ead9c7;
  background: #fffaf4;
}
.summary-icon {
  width: 32px;
  height: 32px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(11, 117, 101, 0.1);
  color: var(--accent);
}
.incomplete .summary-icon {
  background: rgba(200, 100, 40, 0.09);
  color: var(--warning);
}
.summary-copy {
  flex: 1;
  min-width: 0;
}
.summary-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
}
.summary-note {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.summary-tag {
  flex: none;
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(184, 86, 57, 0.08);
  color: var(--sale);
  font-size: 9px;
  font-weight: 700;
}
.summary-provider {
  display: block;
  margin-top: 5px;
  color: var(--accent);
  font-size: 9px;
  font-weight: 650;
}
.summary-detail {
  margin: 8px 16px 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}
.summary-detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.summary-detail-title {
  color: var(--ink);
  font-size: 12px;
  font-weight: 700;
}
.summary-detail-count {
  color: var(--text-muted);
  font-size: 9px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.summary-item {
  min-width: 0;
  padding: 8px 9px;
  border-radius: 7px;
  background: #f6f9f7;
}
.summary-item-label {
  display: block;
  color: var(--text-muted);
  font-size: 9px;
}
.summary-item-value {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 650;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.section-block {
  margin: 22px 16px 0;
}
.section-head {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-kicker {
  margin-bottom: 3px;
}
.section-title {
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.section-count {
  color: var(--text-muted);
  font-size: 11px;
}
.field-list {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.field-row {
  min-height: 64px;
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid var(--border);
}
.field-row:last-child {
  border-bottom: 0;
}
.field-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 10px 4px 10px 13px;
}
.field-label-line {
  display: flex;
  align-items: center;
  gap: 5px;
}
.field-label {
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
}
.required-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--warning);
}
.check-tag {
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 8px;
}
.field-value {
  display: block;
  margin-top: 5px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 570;
  line-height: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.field-value.empty {
  color: var(--text-muted);
  font-weight: 450;
}
.field-mic {
  width: 50px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}
.field-mic.active {
  background: var(--accent-soft);
}
.expand-action {
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--text-secondary);
  font-size: 11px;
}
.material-section {
  margin-bottom: 8px;
}
.add-material {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--surface);
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.material-empty {
  min-height: 78px;
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 9px;
  padding: 13px;
  border: 1px dashed #cfdcd7;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.55);
}
.empty-icon {
  width: 42px;
  height: 42px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: var(--surface-soft);
  color: var(--accent);
}
.empty-copy {
  flex: 1;
  min-width: 0;
}
.empty-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.empty-note {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 9px;
}
.material-list {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.material-line {
  min-height: 62px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border-bottom: 1px solid var(--border);
}
.material-line:last-child {
  border-bottom: 0;
}
.material-symbol {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--accent);
}
.material-line.pending .material-symbol {
  background: var(--warning-bg);
  color: var(--warning);
}
.material-copy {
  flex: 1;
  min-width: 0;
}
.material-name {
  display: block;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.material-meta {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 9px;
}
.material-remove {
  width: 30px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
.entry-bottom-space {
  height: 110px;
}
.bottom-bar {
  position: fixed;
  z-index: 60;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  gap: 9px;
  padding: 10px 16px;
  border-top: 1px solid rgba(220, 229, 225, 0.9);
  background: rgba(247, 250, 248, 0.96);
  backdrop-filter: blur(16px);
}
.draft-action,
.save-action {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 650;
}
.draft-action {
  width: 96px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-primary);
}
.save-action {
  flex: 1;
  background: var(--accent);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(11, 117, 101, 0.2);
}
.save-action[disabled] {
  opacity: 0.64;
}
.editor-mask {
  position: fixed;
  z-index: 200;
  inset: 0;
  display: flex;
  align-items: flex-end;
  background: rgba(14, 25, 21, 0.38);
}
.editor-sheet {
  width: 100%;
  max-height: 78vh;
  overflow-y: auto;
  padding: 18px 16px;
  border-radius: 14px 14px 0 0;
  background: var(--surface);
}
.editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.editor-title {
  display: block;
  margin-top: 5px;
  color: var(--ink);
  font-size: 21px;
  font-weight: 730;
}
.editor-close {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--soft);
  color: var(--text-secondary);
}
.editor-input-zone {
  margin-top: 18px;
}
.editor-input,
.editor-textarea,
.picker-line {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8faf9;
  color: var(--text-primary);
  font-size: 16px;
}
.editor-input {
  height: 50px;
  padding: 0 13px;
}
.editor-textarea {
  min-height: 118px;
  padding: 12px 13px;
  font-size: 14px;
  line-height: 22px;
}
.picker-line {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding: 0 13px;
  color: var(--text-primary);
  font-size: 14px;
}
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}
.option-chip {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 12px;
}
.option-chip.selected {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-weight: 650;
}
.editor-voice-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  color: var(--text-muted);
  font-size: 10px;
}
.editor-actions {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.editor-voice,
.editor-save {
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 650;
}
.editor-voice {
  width: 116px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--accent);
}
.editor-voice.recording {
  border-color: var(--warning);
  background: var(--warning-bg);
  color: var(--warning);
}
.editor-save {
  flex: 1;
  background: var(--accent);
  color: #ffffff;
}
.spin {
  animation: spin 900ms linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes voice-wave {
  0%, 100% { transform: scaleY(0.42); }
  50% { transform: scaleY(1); }
}
</style>
