<template>
  <view class="about-page app-page">
    <PageHeader title="关于" fallback="/pages/profile/index" />

    <scroll-view class="about-scroll" scroll-y>
      <view class="about-hero">
        <view class="brand-mark"><Boxes :size="30" :stroke-width="1.7" /></view>
        <text class="hero-kicker">COMMERCIAL ASSET LIBRARY</text>
        <text class="hero-title">商办信息资产库</text>
        <text class="hero-subtitle">先完整收下，再慢慢整理成判断。</text>
        <view class="version-tag"><text>内部原型</text><text>1.1.0</text></view>
      </view>

      <view class="capability-strip">
        <view class="capability-item">
          <view class="capability-icon active"><FileText :size="18" /></view>
          <text class="capability-title">文档提取</text>
          <text class="capability-state">可用</text>
        </view>
        <view class="capability-item">
          <view class="capability-icon active"><Mic :size="18" /></view>
          <text class="capability-title">语音 / 音视频</text>
          <text class="capability-state" :class="{ 'pending-text': !asrAvailable }">{{ asrAvailable ? "离线识别" : "待配置" }}</text>
        </view>
        <view class="capability-item">
          <view class="capability-icon" :class="ocrAvailable ? 'active' : 'pending'"><ScanText :size="18" /></view>
          <text class="capability-title">图片 OCR</text>
          <text class="capability-state" :class="{ 'pending-text': !ocrAvailable }">{{ ocrAvailable ? "本地可用" : "待配置" }}</text>
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
          <view class="boundary-row"><view class="dot"></view><text>后端文字理解使用本地规则，不调用第三方大模型，结果需要人工核对。</text></view>
          <view class="boundary-row"><view class="dot"></view><text>图片和扫描 PDF 使用服务器本地 OCR，识别结果可搜索，也需要人工核对。</text></view>
          <view class="boundary-row"><view class="dot"></view><text>H5 与 App 都会先把录音上传到后台离线识别，避免原生语音模块返回空内容。</text></view>
          <view class="boundary-row"><view class="dot"></view><text>音频和视频先在本机提取音轨，再转写为可搜索文字。</text></view>
          <view class="boundary-row"><view class="dot"></view><text>{{ capabilityNotice }}</text></view>
        </view>
      </view>

      <view class="about-footer">
        <text>ASSET LIBRARY · INTERNAL USE</text>
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
  Mic,
  ScanText,
  ShieldCheck,
} from "@lucide/vue";
import PageHeader from "../../components/PageHeader.vue";
import { request } from "../../services/api";

const capabilities = ref(null);
const ocrAvailable = computed(() => Boolean(capabilities.value?.ocr?.available));
const asrAvailable = computed(() => Boolean(capabilities.value?.asr?.available));
const capabilityNotice = computed(
  () => capabilities.value?.notice || "正在读取后台识别能力；原件仍会安全保存。",
);

onLoad(async () => {
  try {
    capabilities.value = await request("/ai/capabilities");
  } catch (error) {
    capabilities.value = null;
  }
});
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
</style>
