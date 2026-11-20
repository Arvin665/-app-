<template>
  <view class="about-page app-page">
    <PageHeader title="关于" fallback="/pages/profile/index" />

    <scroll-view class="about-scroll" scroll-y>
      <view class="about-hero">
        <view class="brand-mark"><Boxes :size="30" :stroke-width="1.7" /></view>
        <text class="hero-kicker">SAYO SENSE</text>
        <view class="hero-wordmark"><text class="hero-brand-main">Sayo</text><text class="hero-brand-suffix">Sense</text></view>
        <text class="hero-subtitle">先完整收下，再慢慢整理成判断。</text>
        <view class="version-tag"><text>内部原型</text><text>1.1.0</text></view>
      </view>

      <view class="capability-section">
        <view class="capability-head">
          <view>
            <text class="section-kicker">LIVE CAPABILITIES</text>
            <text class="capability-heading">识别能力</text>
            <text class="capability-summary">{{ capabilitySummary }}</text>
          </view>
          <view class="capability-refresh pressable" @tap="loadCapabilities">
            <LoaderCircle v-if="capabilitiesLoading" :size="15" class="spin" />
            <RefreshCw v-else :size="15" />
          </view>
        </view>
        <StatePanel v-if="capabilitiesLoading" compact state="loading" title="正在读取识别能力" description="正在确认 OCR、语音转写和智能整理服务状态。" />
        <StatePanel v-else-if="capabilitiesError" compact state="error" title="能力状态暂时没有读取出来" :description="capabilitiesError" action-text="重新读取" @action="loadCapabilities" />
        <view v-else class="capability-grid">
          <view v-for="item in capabilityItems" :key="item.key" class="capability-card">
            <view class="capability-icon" :class="item.available ? 'active' : 'pending'"><component :is="item.icon" :size="18" /></view>
            <view class="capability-copy">
              <text class="capability-title">{{ item.title }}</text>
              <text class="capability-state" :class="{ 'pending-text': !item.available }">{{ item.state }}</text>
              <text class="capability-detail">{{ item.detail }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="about-section">
        <text class="section-kicker">HOW IT WORKS</text>
        <text class="section-title">它怎么处理你的信息</text>
        <view class="rule-list">
          <view class="rule-row">
            <view class="rule-symbol"><ShieldCheck :size="18" /></view>
            <view class="rule-copy">
              <text class="rule-title">先保存原件</text>
              <text class="rule-note">图片、PDF、表格、文档、音视频和其他格式都会按原文件存放，再尝试提取正文。</text>
            </view>
          </view>
          <view class="rule-row">
            <view class="rule-symbol"><ScanText :size="18" /></view>
            <view class="rule-copy">
              <text class="rule-title">能识别的先整理</text>
              <text class="rule-note">TXT、CSV、XLSX、DOCX、PPTX、PDF、图片，以及音频和视频音轨都可以提取可检索正文。</text>
            </view>
          </view>
          <view class="rule-row">
            <view class="rule-symbol"><CloudCheck :size="18" /></view>
            <view class="rule-copy">
              <text class="rule-title">离线先收，联网再同步</text>
              <text class="rule-note">网络中断时记录和待上传材料保存在本机，恢复网络后进入同步队列。</text>
            </view>
          </view>
        </view>
      </view>

      <view class="about-section">
        <text class="section-kicker">PRIVACY & RULES</text>
        <text class="section-title">数据与权限</text>
        <view class="info-table">
          <view class="info-row"><text class="info-label">业务范围</text><text class="info-value">上海商办买卖、企业租赁、工作记录与个人灵感</text></view>
          <view class="info-row"><text class="info-label">隐私规则</text><text class="info-value">工作记录默认仅本人可见，个人灵感只属于本人</text></view>
          <view class="info-row"><text class="info-label">删除规则</text><text class="info-value">软删除，进入回收站后保留 7 天</text></view>
          <view class="info-row"><text class="info-label">文件上限</text><text class="info-value">单份原件最多 50 MB</text></view>
          <view class="info-row"><text class="info-label">备份内容</text><text class="info-value">业务数据、资料元数据、原件与图片缩略图</text></view>
        </view>
      </view>

      <view class="about-section boundary-section">
        <text class="section-kicker">CURRENT LIMITS</text>
        <text class="section-title">当前边界</text>
        <view class="boundary-list">
          <view class="boundary-row"><view class="dot"></view><text>{{ nlpBoundaryText }}</text></view>
          <view class="boundary-row"><view class="dot"></view><text>{{ ocrBoundaryText }}</text></view>
          <view class="boundary-row"><view class="dot"></view><text>语音录音会优先交给后台离线识别；识别结果会进入核对流程，不会直接当作事实写入。</text></view>
          <view class="boundary-row"><view class="dot"></view><text>{{ mediaBoundaryText }}</text></view>
          <view class="boundary-row"><view class="dot"></view><text>{{ capabilityNotice }}</text></view>
        </view>
      </view>

      <view class="about-footer">
        <text>SAYO SENSE · JUST SAY IT</text>
        <text>把零散的信息，留给下一次判断。</text>
      </view>
      <view class="bottom-space"></view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import {
  Boxes,
  CloudCheck,
  FileText,
  LoaderCircle,
  Mic,
  RefreshCw,
  Sparkles,
  ScanText,
  ShieldCheck,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import StatePanel from "../../components/StatePanel.vue";
import { request } from "../../services/api";

const capabilities = ref(null);
const capabilitiesLoading = ref(false);
const capabilitiesError = ref("");
const ocrAvailable = computed(() => Boolean(capabilities.value?.ocr?.available));
const asrAvailable = computed(() => Boolean(capabilities.value?.asr?.available));
const mediaAvailable = computed(() => Boolean(capabilities.value?.media?.available));
const nlpAvailable = computed(() => capabilities.value?.nlp?.available !== false);
const deepseekConfigured = computed(() => Boolean(capabilities.value?.nlp?.deepseek_configured));
const nlpMode = computed(() => capabilities.value?.nlp?.mode || "local-rule");
const capabilitySummary = computed(() => {
  if (capabilitiesLoading.value) return "正在读取服务端真实状态";
  if (capabilitiesError.value) return "状态读取失败，原件仍会安全保存";
  if (deepseekConfigured.value) return "DeepSeek 已连接，识别结果进入人工核对";
  return "当前使用本地规则整理，配置 DeepSeek 后可增强语义识别";
});
const capabilityItems = computed(() => [
  {
    key: "documents",
    title: "文档与原件",
    state: "原件可存",
    detail: "文档提取后保留可检索正文",
    available: true,
    icon: FileText,
  },
  {
    key: "ocr",
    title: "图片与扫描件",
    state: ocrAvailable.value ? "本地 OCR" : "待配置",
    detail: ocrAvailable.value ? "图片、扫描 PDF 可提取正文" : "原件保存不受影响",
    available: ocrAvailable.value,
    icon: ScanText,
  },
  {
    key: "speech",
    title: "语音与音视频",
    state: asrAvailable.value ? "离线转写" : "待配置",
    detail: asrAvailable.value ? (mediaAvailable.value ? "录音与音轨可转写" : "录音可转写，音视频待配置") : "可先用文字记录",
    available: asrAvailable.value,
    icon: Mic,
  },
  {
    key: "nlp",
    title: "智能整理",
    state: nlpAvailable.value ? (nlpMode.value === "deepseek" ? "DeepSeek" : "本地规则") : "不可用",
    detail: nlpAvailable.value ? "分类、字段提取和计划拆分" : "等待后端能力恢复",
    available: nlpAvailable.value,
    icon: Sparkles,
  },
]);
const capabilityNotice = computed(
  () => capabilities.value?.notice || "正在读取后台识别能力；原件仍会安全保存。",
);
const nlpBoundaryText = computed(() =>
  deepseekConfigured.value
    ? "DeepSeek 已连接，用于文字纠错、字段提取和计划拆分；所有结果都要先核对再保存。"
    : "当前未连接 DeepSeek，智能整理会使用本地规则；配置 API Key 后自动切换。",
);
const ocrBoundaryText = computed(() =>
  ocrAvailable.value
    ? "图片和扫描 PDF 使用服务器本地 OCR，识别结果可搜索，也需要人工核对。"
    : "当前 OCR 尚未可用，图片和 PDF 原件仍会完整保存。",
);
const mediaBoundaryText = computed(() =>
  mediaAvailable.value
    ? "音频和视频会先提取音轨，再转写为可搜索文字。"
    : "当前音视频转码尚未可用，原件仍会先保存，可稍后重试转写。",
);

async function loadCapabilities() {
  if (capabilitiesLoading.value) return;
  capabilitiesLoading.value = true;
  capabilitiesError.value = "";
  try {
    capabilities.value = await request("/ai/capabilities");
  } catch (error) {
    capabilitiesError.value = error.message || "无法读取识别能力，请检查网络和资料库服务。";
  } finally {
    capabilitiesLoading.value = false;
  }
}

onLoad(loadCapabilities);
</script>

<style scoped>
.about-page {
  height: 100vh;
  overflow: hidden;
}
.about-scroll {
  height: calc(100vh - 62px - env(safe-area-inset-top));
}
.about-hero {
  position: relative;
  margin: 4px 16px 0;
  padding: 20px;
  overflow: hidden;
  border-radius: 13px;
  background: var(--ink);
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(22, 34, 31, 0.17);
}
.about-hero::after {
  content: "";
  position: absolute;
  right: -38px;
  bottom: -58px;
  width: 150px;
  height: 150px;
  border: 1px solid rgba(132, 221, 201, 0.18);
  border-radius: 50%;
}
.brand-mark {
  width: 54px;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(157, 236, 218, 0.31);
  border-radius: 14px;
  background: rgba(127, 223, 202, 0.1);
  color: #c6f8ec;
}
.hero-kicker {
  display: block;
  margin-top: 18px;
  color: #8ed8c8;
  font-size: 9px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.hero-title {
  display: block;
  margin-top: 7px;
  font-size: 25px;
  font-weight: 760;
  line-height: 32px;
}
.hero-subtitle {
  display: block;
  margin-top: 5px;
  color: #b6cbc4;
  font-size: 10px;
  line-height: 17px;
}
.version-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 4px 7px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  color: #c4d8d1;
  font-size: 8px;
}
.version-tag text + text {
  padding-left: 6px;
  border-left: 1px solid rgba(255, 255, 255, 0.14);
}
.capability-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 12px 16px 0;
  padding: 13px 0;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}
.capability-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-left: 1px solid var(--border);
}
.capability-item:first-child {
  border-left: 0;
}
.capability-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
}
.capability-icon.active {
  background: var(--accent-soft);
  color: var(--accent);
}
.capability-icon.pending {
  background: var(--warning-bg);
  color: var(--warning);
}
.capability-title {
  margin-top: 7px;
  color: var(--text-primary);
  font-size: 9px;
  font-weight: 650;
}
.capability-state {
  margin-top: 2px;
  color: var(--accent);
  font-size: 8px;
}
.pending-text {
  color: var(--warning);
}
.capability-section {
  margin: 18px 16px 0;
}
.capability-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.capability-heading {
  display: block;
  margin-top: 3px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.capability-summary {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 19px;
}
.capability-refresh {
  width: 36px;
  height: 36px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--accent);
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  margin-top: 11px;
}
.capability-card {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.capability-copy {
  min-width: 0;
  flex: 1;
}
.capability-card .capability-icon {
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 8px;
}
.capability-card .capability-title {
  display: block;
  margin-top: 0;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 18px;
}
.capability-card .capability-state {
  display: block;
  margin-top: 2px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 650;
}
.capability-detail {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 15px;
}
.about-section {
  margin: 24px 16px 0;
}
.section-kicker {
  display: block;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.11em;
}
.section-title {
  display: block;
  margin-top: 3px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 730;
  line-height: 24px;
}
.rule-list {
  margin-top: 9px;
  border-top: 1px solid var(--border);
}
.rule-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.rule-symbol {
  width: 35px;
  height: 35px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--surface);
  color: var(--accent);
}
.rule-copy {
  flex: 1;
  min-width: 0;
}
.rule-title {
  display: block;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}
.rule-note {
  display: block;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 16px;
}
.info-table {
  margin-top: 9px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 11px 12px;
  border-bottom: 1px solid var(--border);
}
.info-row:last-child {
  border-bottom: 0;
}
.info-label {
  width: 64px;
  flex: none;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 16px;
}
.info-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 9px;
  line-height: 16px;
}
.boundary-section {
  margin-bottom: 0;
}
.boundary-list {
  margin-top: 9px;
  padding: 12px;
  border: 1px solid #ead7c5;
  border-radius: 9px;
  background: #fffaf4;
}
.boundary-row {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 5px 0;
  color: var(--text-secondary);
  font-size: 9px;
  line-height: 16px;
}
.dot {
  width: 5px;
  height: 5px;
  flex: none;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--warning);
}
.about-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 26px 16px 10px;
  color: var(--text-muted);
  font-size: 8px;
  letter-spacing: 0.04em;
  text-align: center;
}
.bottom-space {
  height: calc(18px + env(safe-area-inset-bottom));
}
.hero-wordmark {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-top: 7px;
}
.hero-brand-main {
  font-size: 28px;
  font-weight: 760;
  line-height: 34px;
  letter-spacing: 0;
}
.hero-brand-suffix {
  color: #b9d2ca;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: 0;
}
</style>
