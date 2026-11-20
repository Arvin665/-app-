<template>
  <view class="review-page app-page">
    <PageHeader title="核对计划" fallback="/pages/plans/index">
      <template #actions>
        <view class="header-action pressable" @tap="addBlank">
          <Plus :size="15" />
          <text>补一条</text>
        </view>
      </template>
    </PageHeader>

    <scroll-view class="review-scroll" scroll-y>
      <view class="process-strip">
        <view
          v-for="(step, index) in processSteps"
          :key="step.key"
          class="process-step"
          :class="{ active: currentStep === index, done: currentStep > index }"
        >
          <view class="process-dot">
            <Check v-if="currentStep > index" :size="12" />
            <text v-else>{{ index + 1 }}</text>
          </view>
          <text class="process-label">{{ step.label }}</text>
        </view>
      </view>

      <view class="voice-hero" :class="{ recording: voice.active }">
        <view class="hero-head">
          <view class="hero-mark">
            <Square v-if="voice.active" :size="19" fill="currentColor" />
            <Mic v-else :size="22" />
          </view>
          <view class="hero-copy">
            <text class="hero-kicker">VOICE TO PLAN</text>
            <text class="hero-title">{{ voiceTitle }}</text>
            <text class="hero-note">{{ voiceNote }}</text>
          </view>
          <view v-if="voice.active" class="voice-wave">
            <view v-for="index in 4" :key="index" class="wave-bar" :style="{ animationDelay: `${index * 90}ms` }"></view>
          </view>
        </view>

        <view class="voice-button pressable" :class="{ stopping: voice.phase === 'stopping' }" @tap="toggleVoice">
          <Square v-if="voice.active" :size="16" fill="currentColor" />
          <Mic v-else :size="17" />
          <text>{{ voice.active ? (voice.phase === "stopping" ? "正在收尾" : "说完，点这里结束") : "开始连续说计划" }}</text>
        </view>
      </view>

      <view class="capture-panel">
        <view class="capture-head">
          <view>
            <text class="section-kicker">WHAT I HEARD</text>
            <text class="capture-title">听到的原话</text>
          </view>
          <text class="capture-count">{{ inputText.length }}/3000</text>
        </view>
        <textarea
          v-model="inputText"
          class="raw-textarea"
          auto-height
          maxlength="3000"
          :disabled="analyzing || creating"
          placeholder="点上方麦克风连续说，或者把计划直接打在这里。例如：明天上午十点整理客户清单，下午三点联系张总确认看房。"
        />
        <view class="capture-actions">
          <text class="capture-tip">{{ providerLabel || "日期、时间、任务会拆开核对" }}</text>
          <button class="parse-button pressable" :disabled="!inputText.trim() || analyzing || creating" @tap="analyzeText()">
            <LoaderCircle v-if="analyzing" :size="16" class="spin" />
            <Plus v-else :size="16" />
            <text>{{ analyzing ? "正在拆分" : "整理成计划" }}</text>
          </button>
        </view>
      </view>

      <StatusNotice
        v-if="analysisError"
        tone="error"
        title="这次没有拆分成功"
        :message="analysisError"
        action-text="重新整理"
        closeable
        @action="analyzeText(inputText)"
        @close="analysisError = ''"
      />

      <StatusNotice
        v-if="candidates.length && providerLabel"
        tone="success"
        :title="providerLabel"
        message="请核对公司、事项、日期和提醒时间；低置信度项目已经单独标出。"
        compact
      />

      <StatusNotice
        v-if="candidates.length && reminderPermission !== 'granted'"
        :tone="reminderPermission === 'unsupported' ? 'info' : 'warning'"
        title="创建前再确认提醒权限"
        :message="reminderPermissionMessage"
        :action-text="reminderPermission === 'unsupported' ? '' : '开启提醒'"
        @action="enableNotificationPermission"
      />

      <view v-if="analyzing" class="loading-panel">
        <view class="loading-orbit"><LoaderCircle :size="21" class="spin" /></view>
        <view>
          <text class="loading-title">正在理解整段安排</text>
          <text class="loading-note">会按日期、时间和任务拆分，不会自动写入提醒。</text>
        </view>
      </view>

      <view v-else-if="candidates.length" class="candidate-section">
        <view class="section-head">
          <view>
            <text class="section-kicker">REVIEW FIRST</text>
            <text class="section-title">请逐条核对</text>
          </view>
          <view class="select-all pressable" @tap="toggleSelectAll">
            <Check v-if="allSelected" :size="14" />
            <view v-else class="empty-check"></view>
            <text>{{ allSelected ? "取消全选" : "全选" }}</text>
          </view>
        </view>

        <view class="review-note">
          <text>确认日期、时间和内容后再创建。未勾选的计划不会写入，也不会设置提醒。</text>
          <text>未指定时刻的计划按当天 08:30 提醒，不会改写为具体执行时间。</text>
        </view>

        <view class="candidate-overview">
          <view class="overview-item">
            <text class="overview-value">{{ candidates.length }}</text>
            <text class="overview-label">条候选计划</text>
          </view>
          <view class="overview-item">
            <text class="overview-value">{{ selectedCount }}</text>
            <text class="overview-label">条待确认</text>
          </view>
          <view class="overview-item">
            <text class="overview-value" :class="{ warning: lowConfidenceCount }">{{ lowConfidenceCount }}</text>
            <text class="overview-label">条需核对</text>
          </view>
        </view>

        <view class="candidate-list">
          <view
            v-for="(item, index) in candidates"
            :key="item.id"
            class="candidate-card"
            :class="{ excluded: !item.selected }"
          >
            <view class="candidate-head">
              <view class="candidate-select pressable" @tap="item.selected = !item.selected">
                <view class="check-box" :class="{ checked: item.selected }">
                  <Check v-if="item.selected" :size="13" />
                </view>
                <text class="candidate-number">计划 {{ index + 1 }}</text>
              </view>
              <view class="candidate-head-right">
                <text v-if="item.confidence < 0.8" class="confidence warning">待核对 {{ confidenceText(item.confidence) }}</text>
                <text v-else class="confidence">{{ confidenceText(item.confidence) }}</text>
                <view class="remove-action pressable" @tap="removeCandidate(item.id)">
                  <X :size="15" />
                </view>
              </view>
            </view>

            <textarea
              v-model="item.content"
              class="candidate-textarea"
              auto-height
              maxlength="500"
              :disabled="creating"
              placeholder="这条计划要做什么"
            />

            <view class="meta-grid">
              <picker mode="date" :value="item.record_date" :disabled="creating" @change="pickDate(item, $event)">
                <view class="meta-cell">
                  <view class="meta-label"><CalendarDays :size="14" /><text>日期</text></view>
                  <text class="meta-value">{{ displayDate(item.record_date) }}</text>
                </view>
              </picker>

              <view class="meta-cell time-cell">
                <picker mode="time" :value="item.ext_field_4 || '09:00'" :disabled="creating" @change="pickTime(item, $event)">
                  <view>
                    <view class="meta-label"><Clock3 :size="14" /><text>时间</text></view>
                  <text class="meta-value">{{ item.ext_field_4 || `全天 · ${ALL_DAY_REMINDER_TIME} 提醒` }}</text>
                  </view>
                </picker>
                <text class="all-day pressable" @tap="toggleAllDay(item)">{{ item.ext_field_4 ? "设为全天" : "指定时间" }}</text>
              </view>
            </view>

            <view class="related-row">
              <text class="related-label">关联项目/企业</text>
              <input
                v-model="item.related_project"
                class="related-input"
                maxlength="255"
                :disabled="creating"
                placeholder="可不填"
              />
            </view>

            <view class="candidate-reminder" :class="{ muted: reminderPermission !== 'granted' }">
              <BellRing v-if="reminderPermission === 'granted'" :size="14" />
              <BellOff v-else :size="14" />
              <text>{{ reminderPreview(item) }}</text>
            </view>

            <view v-if="item.source_text" class="source-line">
              <text class="source-label">原话</text>
              <text class="source-text">{{ item.source_text }}</text>
            </view>
          </view>
        </view>
      </view>

      <view v-else class="empty-review">
        <view class="empty-mark"><CalendarDays :size="25" /></view>
        <text class="empty-title">还没有拆出计划</text>
        <text class="empty-note">试着一次说完整天安排，App 会先列出来给你核对。</text>
        <button class="empty-button pressable" @tap="toggleVoice">
          <Mic :size="16" />
          <text>现在说计划</text>
        </button>
      </view>

      <StatusNotice
        v-if="saveError"
        tone="error"
        title="计划还没有保存成功"
        :message="saveError"
        action-text="重新提交"
        closeable
        @action="createSelected"
        @close="saveError = ''"
      />

      <view class="scroll-space"></view>
    </scroll-view>

    <view class="review-bottom safe-bottom">
      <view class="bottom-summary">
        <text class="bottom-count">{{ selectedCount }} 条计划</text>
        <text class="bottom-note">{{ selectedCount ? "核对无误后创建并设置提醒" : "请先勾选要保存的计划" }}</text>
      </view>
      <button class="create-button pressable" :disabled="!selectedCount || creating" @tap="createSelected">
        <LoaderCircle v-if="creating" :size="18" class="spin" />
        <Check v-else :size="18" />
        <text>{{ createButtonText }}</text>
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { onLoad, onUnload } from "@dcloudio/uni-app";
import {
  BellOff,
  BellRing,
  CalendarDays,
  Check,
  Clock3,
  LoaderCircle,
  Mic,
  Plus,
  Square,
  X,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import StatusNotice from "../../components/StatusNotice.vue";
import { localDate, normalizeRecordPayload } from "../../data/modules";
import { postForm, request } from "../../services/api";
import { consumePlanReview } from "../../services/planReview";
import {
  ALL_DAY_REMINDER_TIME,
  hasBackgroundReminderSupport,
  notificationPermission,
  requestNotificationPermission,
  schedulePlanReminder,
} from "../../services/reminders";
import { ensureBound } from "../../services/session";
import { dictationAvailable, startDictation } from "../../services/voice";

const today = localDate();
const inputText = ref("");
const candidates = ref([]);
const analyzing = ref(false);
const creating = ref(false);
const analysisError = ref("");
const saveError = ref("");
const reminderPermission = ref("checking");
const provider = ref("");
const reviewSource = ref("plans");
const voiceStatus = ref("点一下麦克风，把一整天的安排连续说完");
const voice = reactive({ active: false, phase: "idle", interim: "" });
let voiceSession = null;

const selectedCount = computed(() => candidates.value.filter((item) => item.selected && item.content.trim()).length);
const allSelected = computed(() => candidates.value.length > 0 && candidates.value.every((item) => item.selected));
const lowConfidenceCount = computed(() => candidates.value.filter((item) => Number(item.confidence) < 0.8).length);
const processSteps = [
  { key: "say", label: "说出安排" },
  { key: "split", label: "智能拆分" },
  { key: "review", label: "逐条核对" },
  { key: "confirm", label: "确认提醒" },
];
const currentStep = computed(() => {
  if (creating.value) return 3;
  if (candidates.value.length) return 2;
  if (analyzing.value || inputText.value.trim()) return 1;
  return 0;
});
const reminderPermissionMessage = computed(() => {
  if (reminderPermission.value === "unsupported") {
    return "当前网页环境不能弹系统通知。计划会正常保存，安装 App 后可获得后台提醒。";
  }
  if (reminderPermission.value === "denied") {
    return "系统通知已被关闭。计划仍会保存，但到点不会主动提醒；需要在系统设置中重新开启。";
  }
  return hasBackgroundReminderSupport()
    ? "开启后，确认创建时会同时安排后台提醒。"
    : "网页打开时可提醒；安装 App 后可获得后台通知。";
});
const createButtonText = computed(() => {
  if (creating.value) return "正在创建";
  if (!selectedCount.value) return "确认创建并提醒";
  return `确认 ${selectedCount.value} 条并提醒`;
});
const providerLabel = computed(() => {
  if (provider.value === "deepseek") return "DeepSeek 已拆分，请逐条核对";
  if (provider.value === "local-rule") return "本地智能规则已拆分，请逐条核对";
  return "";
});
const voiceTitle = computed(() => {
  if (voice.active && voice.phase === "stopping") return "正在收尾并整理";
  if (voice.active) return "正在听，你把计划说完";
  return "一次说清，先核对再提醒";
});
const voiceNote = computed(() => {
  if (voice.active) {
    if (voice.phase === "stopping") return voice.interim || "正在识别最后一段，请稍等";
    return voice.interim || "说完后点下方结束，内容会先显示出来";
  }
  return voiceStatus.value;
});

function appendText(current, text) {
  const value = String(current || "").trim();
  const next = String(text || "").trim();
  if (!value) return next;
  return `${value}${/[。！？!?]$/.test(value) ? "" : "。"}${next}`;
}

function confidenceText(value) {
  return `${Math.round(Number(value || 0.8) * 100)}%`;
}

function candidateId() {
  return `plan-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeCandidate(item, index = 0) {
  return {
    id: item.id || candidateId(),
    selected: item.selected !== false,
    content: String(item.content || "").trim(),
    record_date: String(item.record_date || today).slice(0, 10),
    ext_field_4: item.ext_field_4 || "",
    related_project: item.related_project || "",
    source_text: String(item.source_text || "").trim(),
    confidence: Number.isFinite(Number(item.confidence)) ? Number(item.confidence) : 0.8,
    order: index,
  };
}

function displayDate(value) {
  const raw = String(value || today);
  const [year, month, day] = raw.split("-").map(Number);
  if (!year || !month || !day) return raw;
  const current = new Date(year, month - 1, day);
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return `${month}月${day}日 ${weekdays[current.getDay()]}`;
}

async function refreshReminderPermission() {
  reminderPermission.value = await notificationPermission().catch(() => "unknown");
}

async function enableNotificationPermission() {
  const result = await requestNotificationPermission().catch(() => "unknown");
  reminderPermission.value = result;
  if (result === "granted") {
    uni.showToast({ title: "提醒权限已开启", icon: "success" });
    return;
  }
  uni.showModal({
    title: "需要开启系统通知",
    content: "请在系统设置中找到当前浏览器或 Sayo Sense，开启通知权限后再回来核对。",
    showCancel: false,
  });
}

function reminderPreview(item) {
  const dateLabel = displayDate(item.record_date);
  if (reminderPermission.value !== "granted") return `${dateLabel} · 提醒权限未开启`;
  if (item.ext_field_4) {
    return hasBackgroundReminderSupport()
      ? `${dateLabel} ${item.ext_field_4} 后台提醒`
      : `${dateLabel} ${item.ext_field_4} 网页提醒`;
  }
  return `${dateLabel} ${ALL_DAY_REMINDER_TIME} 提醒 · 全天计划`;
}

function setCandidates(items) {
  candidates.value = (items || [])
    .map((item, index) => normalizeCandidate(item, index))
    .filter((item) => item.content);
}

async function analyzeText(text = inputText.value) {
  const trimmed = String(text || "").trim();
  if (!trimmed || analyzing.value) return;
  inputText.value = trimmed;
  analyzing.value = true;
  analysisError.value = "";
  saveError.value = "";
  voiceStatus.value = "正在理解整段安排，请稍等";
  try {
    const result = await postForm("/ai/extract", {
      module: "work",
      text: trimmed,
      intent: "plans",
    });
    provider.value = String(result.provider || "");
    const items = Array.isArray(result.plan_candidates) && result.plan_candidates.length
      ? result.plan_candidates
      : result.fields?.content
        ? [{
            content: result.fields.content,
            record_date: result.fields.record_date || today,
            ext_field_4: result.fields.ext_field_4 || "",
            related_project: result.fields.related_project || "",
            confidence: result.confidence?.content || 0.7,
            source_text: trimmed,
          }]
        : [];
    setCandidates(items);
    voiceStatus.value = items.length
      ? `已拆出 ${items.length} 条计划，请逐条核对`
      : "没有拆出可用计划，请换一种说法";
    if (items.length) uni.vibrateShort?.({ type: "light" });
    else analysisError.value = "没有拆出可用计划。原话仍然保留，可以换一种说法后重新整理。";
  } catch (error) {
    voiceStatus.value = error.message || "计划整理失败，原话仍保留在输入框";
    analysisError.value = error.message || "计划整理失败，原话仍保留在输入框。";
  } finally {
    analyzing.value = false;
  }
}

function toggleVoice() {
  if (voice.active) {
    stopVoice();
    return;
  }
  startVoice();
}

function startVoice() {
  if (analyzing.value || creating.value || voice.active) return;
  if (!dictationAvailable()) {
    uni.showModal({
      title: "当前环境没有语音识别",
      content: "请检查麦克风权限和资料库服务连接。你仍然可以先输入文字。",
      showCancel: false,
    });
    return;
  }
  voice.active = true;
  voice.phase = "listening";
  voice.interim = "";
  voiceStatus.value = "正在听，再按一下结束并整理";
  voiceSession = startDictation({
    continuous: true,
    onStateChange: (state) => {
      if (voice.active) voice.phase = state;
    },
    onInterim: (text) => {
      voice.interim = text;
      inputText.value = text;
    },
    onFinal: (text) => {
      const clean = String(text || "").trim();
      voice.interim = clean;
      if (clean) {
        inputText.value = clean;
        analyzeText(clean);
      }
    },
    onError: (error) => {
      voiceStatus.value = error.message || "语音识别暂时不可用";
      uni.showToast({ title: voiceStatus.value, icon: "none", duration: 2600 });
    },
    onEnd: () => {
      voice.active = false;
      voice.phase = "idle";
      voice.interim = "";
      voiceSession = null;
    },
  });
  if (!voiceSession) {
    voice.active = false;
    voice.phase = "idle";
    voiceStatus.value = "麦克风没有启动，可以稍后重试或先输入文字";
  }
}

async function stopVoice() {
  const session = voiceSession;
  if (!session) {
    voice.active = false;
    voice.phase = "idle";
    return null;
  }
  voice.phase = "stopping";
  voiceStatus.value = "正在收尾，请稍等";
  const result = await session.stop?.();
  if (voiceSession === session) voiceSession = null;
  return result;
}

function pickDate(item, event) {
  item.record_date = event.detail.value;
}

function pickTime(item, event) {
  item.ext_field_4 = event.detail.value;
}

function toggleAllDay(item) {
  item.ext_field_4 = item.ext_field_4 ? "" : "09:00";
}

function removeCandidate(id) {
  candidates.value = candidates.value.filter((item) => item.id !== id);
}

function toggleSelectAll() {
  const next = !allSelected.value;
  candidates.value.forEach((item) => {
    item.selected = next;
  });
}

function addBlank() {
  if (candidates.value.length >= 20) {
    uni.showToast({ title: "一次最多核对 20 条计划", icon: "none" });
    return;
  }
  candidates.value.push(normalizeCandidate({
    content: "",
    record_date: today,
    ext_field_4: "",
    confidence: 0.8,
    selected: true,
  }, candidates.value.length));
  setTimeout(() => {
    uni.pageScrollTo({ scrollTop: 99999, duration: 260 });
  }, 80);
}

async function createSelected() {
  if (creating.value) return;
  saveError.value = "";
  const chosen = candidates.value.filter((item) => item.selected);
  if (!chosen.length) {
    uni.showToast({ title: "请先勾选要创建的计划", icon: "none" });
    return;
  }
  if (chosen.some((item) => !item.content.trim())) {
    uni.showToast({ title: "有计划的正文为空，请补充或取消勾选", icon: "none" });
    return;
  }

  creating.value = true;
  const payloads = chosen.map((item) => normalizeRecordPayload("work", {
    record_type: "待办计划",
    record_date: item.record_date || today,
    ext_field_4: item.ext_field_4 || null,
    content: item.content.trim(),
    related_project: item.related_project?.trim() || null,
    is_shared: 0,
  }));

  try {
    const permission = await requestNotificationPermission().catch(() => "unknown");
    reminderPermission.value = permission;
    const result = await request("/work-logs/batch", { method: "POST", data: { items: payloads } });
    let scheduled = 0;
    for (const plan of result.items || []) {
      try {
        if (await schedulePlanReminder(plan, { requestPermission: false })) scheduled += 1;
      } catch (error) {
        console.warn("计划已保存，但提醒调度失败", error);
      }
    }
    const count = Number(result.count || result.items?.length || chosen.length);
    const reminderReady = permission === "granted" || scheduled > 0;
    let message = `已创建 ${count} 条，提醒权限未开启`;
    if (reminderReady && scheduled === count) message = `已创建 ${count} 条并安排提醒`;
    else if (reminderReady) message = `已创建 ${count} 条，已安排 ${scheduled} 条提醒`;
    uni.showToast({
      title: message,
      icon: reminderReady ? "success" : "none",
      duration: 1800,
    });
    setTimeout(() => uni.reLaunch({ url: "/pages/plans/index?tab=plans" }), 650);
  } catch (error) {
    saveError.value = error.message || "计划创建失败，请检查网络后重试。已核对的内容仍保留在当前页面。";
  } finally {
    creating.value = false;
  }
}

onLoad((options) => {
  if (!ensureBound()) return;
  refreshReminderPermission();
  const pending = consumePlanReview();
  if (pending) {
    reviewSource.value = pending.source || "entry";
    provider.value = pending.provider || "";
    inputText.value = pending.rawText || "";
    setCandidates(pending.candidates);
    voiceStatus.value = `已整理 ${candidates.value.length} 条计划，请逐条核对`;
  } else if (!candidates.value.length) {
    voiceStatus.value = "点一下麦克风，把一整天的安排连续说完";
  }
  if (options?.voice === "1" && !candidates.value.length) {
    setTimeout(() => {
      if (!voice.active && !analyzing.value && !creating.value) startVoice();
    }, 420);
  }
});

onUnload(() => {
  voiceSession?.abort?.();
});
</script>

<style scoped>
.review-page {
  height: 100vh;
  overflow: hidden;
}
.header-action {
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}
.review-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.voice-hero {
  margin: 4px 16px 0;
  padding: 18px;
  border: 1px solid #cfe0dc;
  border-radius: 12px;
  background: linear-gradient(145deg, #f3fbf8 0%, #ffffff 72%);
}
.voice-hero.recording {
  border-color: #8bc8b9;
  box-shadow: 0 8px 24px rgba(11, 117, 101, 0.1);
}
.hero-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.hero-mark {
  width: 46px;
  height: 46px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.recording .hero-mark {
  background: var(--accent);
  color: #ffffff;
  animation: soft-pulse 1.8s infinite;
}
.hero-copy {
  flex: 1;
  min-width: 0;
}
.hero-kicker,
.section-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.hero-title {
  display: block;
  margin-top: 5px;
  color: var(--ink);
  font-size: 21px;
  font-weight: 740;
  line-height: 28px;
}
.hero-note {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.voice-wave {
  width: 25px;
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}
.wave-bar {
  width: 3px;
  height: 22px;
  border-radius: 2px;
  background: var(--accent);
  animation: voice-wave 780ms ease-in-out infinite;
}
.voice-button {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 15px;
  border-radius: 8px;
  background: var(--ink);
  color: #ffffff;
  font-size: 12px;
  font-weight: 650;
}
.voice-button.stopping {
  opacity: 0.72;
}
.capture-panel {
  margin: 13px 16px 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
}
.capture-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.capture-title {
  display: block;
  margin-top: 3px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 710;
}
.capture-count {
  color: var(--text-muted);
  font-size: 9px;
}
.raw-textarea {
  width: 100%;
  min-height: 96px;
  margin-top: 11px;
  padding: 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8faf9;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 21px;
}
.capture-actions {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 9px;
}
.capture-tip {
  min-width: 0;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 15px;
}
.parse-button {
  min-width: 102px;
  height: 38px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: 7px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 650;
}
.parse-button[disabled],
.create-button[disabled] {
  opacity: 0.5;
}
.loading-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 16px 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}
.loading-orbit {
  width: 38px;
  height: 38px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.loading-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.loading-note {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 15px;
}
.candidate-section {
  margin: 20px 16px 0;
}
.section-head {
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.section-title {
  display: block;
  margin-top: 3px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
}
.select-all {
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
  font-size: 10px;
}
.empty-check {
  width: 15px;
  height: 15px;
  border: 1px solid #b8c6c1;
  border-radius: 4px;
}
.review-note {
  margin-top: 6px;
  padding: 9px 10px;
  border-radius: 7px;
  background: var(--warning-bg);
  color: #8b5128;
  font-size: 9px;
  line-height: 15px;
}
.review-note text {
  display: block;
}
.review-note text + text {
  margin-top: 4px;
}
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 11px;
}
.candidate-card {
  padding: 13px;
  border: 1px solid #d5e4df;
  border-radius: 10px;
  background: var(--surface);
}
.candidate-card.excluded {
  opacity: 0.56;
  border-color: var(--border);
}
.candidate-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.candidate-select {
  min-height: 28px;
  display: flex;
  align-items: center;
  gap: 7px;
}
.check-box {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #b8c6c1;
  border-radius: 5px;
  color: #ffffff;
}
.check-box.checked {
  border-color: var(--accent);
  background: var(--accent);
}
.candidate-number {
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 700;
}
.candidate-head-right {
  display: flex;
  align-items: center;
  gap: 5px;
}
.confidence {
  padding: 3px 6px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 8px;
  font-weight: 650;
}
.confidence.warning {
  background: var(--warning-bg);
  color: var(--warning);
}
.remove-action {
  width: 29px;
  height: 29px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
.candidate-textarea {
  width: 100%;
  min-height: 54px;
  margin-top: 9px;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #f8faf9;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 580;
  line-height: 20px;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 9px;
}
.meta-cell {
  min-height: 62px;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--surface);
}
.meta-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  font-size: 9px;
}
.meta-value {
  display: block;
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 650;
}
.time-cell {
  position: relative;
}
.all-day {
  position: absolute;
  right: 8px;
  bottom: 8px;
  color: var(--accent);
  font-size: 8px;
}
.related-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 9px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
}
.related-label {
  flex: none;
  color: var(--text-muted);
  font-size: 9px;
}
.related-input {
  min-width: 0;
  flex: 1;
  color: var(--text-primary);
  font-size: 11px;
  text-align: right;
}
.source-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.source-label {
  flex: none;
  color: var(--text-muted);
  font-size: 8px;
}
.source-text {
  min-width: 0;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 15px;
}
.empty-review {
  margin: 24px 16px 0;
  padding: 30px 20px;
  border: 1px dashed #cbd9d4;
  border-radius: 10px;
  text-align: center;
}
.empty-mark {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
}
.empty-title {
  display: block;
  margin-top: 12px;
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
}
.empty-note {
  display: block;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 16px;
}
.empty-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 14px;
  padding: 0 16px;
  border-radius: 7px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 650;
}
.scroll-space {
  height: 104px;
}
.review-bottom {
  position: fixed;
  z-index: 60;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-top: 1px solid rgba(220, 229, 225, 0.92);
  background: rgba(247, 250, 248, 0.97);
  backdrop-filter: blur(16px);
}
.bottom-summary {
  min-width: 0;
  flex: 1;
}
.bottom-count {
  display: block;
  color: var(--ink);
  font-size: 13px;
  font-weight: 720;
}
.bottom-note {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
}
.create-button {
  min-width: 148px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 680;
  box-shadow: 0 8px 18px rgba(11, 117, 101, 0.18);
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

.process-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  margin: 4px 16px 0;
  padding: 10px 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.process-step {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
}
.process-dot {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface-soft);
  font-size: 11px;
  font-weight: 700;
}
.process-step.active {
  color: var(--accent-deep);
}
.process-step.active .process-dot {
  border-color: var(--accent);
  background: var(--accent);
  color: #ffffff;
}
.process-step.done {
  color: var(--accent);
}
.process-step.done .process-dot {
  border-color: #cfe5df;
  background: var(--accent-soft);
  color: var(--accent);
}
.process-label {
  max-width: 100%;
  overflow: hidden;
  font-size: 10px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidate-overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-top: 9px;
  padding: 11px 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.overview-item {
  min-width: 0;
  padding: 0 10px;
  border-left: 1px solid var(--border);
}
.overview-item:first-child {
  border-left: 0;
}
.overview-value {
  display: block;
  color: var(--ink);
  font-size: 19px;
  font-weight: 740;
}
.overview-value.warning {
  color: var(--warning);
}
.overview-label {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}
.candidate-reminder {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 9px;
  padding: 7px 9px;
  border-radius: 6px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 12px;
  font-weight: 600;
  line-height: 18px;
}
.candidate-reminder.muted {
  background: var(--warning-bg);
  color: #8b5128;
}
.voice-hero,
.capture-panel,
.loading-panel,
.candidate-card,
.empty-review {
  border-radius: 8px;
}
.hero-kicker,
.section-kicker {
  font-size: 10px;
  letter-spacing: 0;
}
.hero-note,
.capture-tip,
.capture-count,
.review-note,
.select-all,
.loading-note,
.empty-note {
  font-size: 12px;
  line-height: 19px;
}
.hero-note {
  white-space: normal;
}
.candidate-number,
.meta-value,
.related-input {
  font-size: 13px;
}
.confidence {
  font-size: 10px;
}
.meta-label,
.related-label,
.all-day {
  font-size: 11px;
}
.all-day {
  right: 9px;
  bottom: 7px;
}
.source-label,
.source-text {
  font-size: 11px;
  line-height: 18px;
}
.bottom-note {
  font-size: 10px;
  line-height: 15px;
}
.create-button {
  font-size: 13px;
}
@media (max-width: 360px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
  .review-bottom {
    gap: 7px;
    padding-left: 12px;
    padding-right: 12px;
  }
  .create-button {
    min-width: 132px;
    padding: 0 9px;
  }
}
</style>
