<template>
  <view class="about-page">
    <PageHeader title="关于" fallback="/pages/profile/index" />

    <view class="about-content">
      <text class="product-name">商办信息资产库</text>
      <text class="version">团队内部 MVP 1.0.0</text>

      <view class="info-card">
        <view class="info-row">
          <text class="info-label">数据范围</text>
          <text class="info-value">上海商办租赁与买卖业务</text>
        </view>
        <view class="info-row">
          <text class="info-label">隐私规则</text>
          <text class="info-value">工作记录默认私有，个人灵感仅本人可见</text>
        </view>
        <view class="info-row">
          <text class="info-label">删除规则</text>
          <text class="info-value">软删除，回收站保留 7 天</text>
        </view>
        <view class="info-row">
          <text class="info-label">同步规则</text>
          <text class="info-value">离线写入本地，联网后自动增量同步</text>
        </view>
      </view>

      <view class="notice-card">
        <text class="notice-title">原生能力说明</text>
        <text class="notice-text">系统通知和语音转写依赖安装包中的原生插件。未接入真实 OCR/ASR 服务时，图片和音频不会伪造识别文字。</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import PageHeader from "../../components/PageHeader.vue";
</script>

<style scoped>
.about-page {
  width: 100vw;
  min-height: 100vh;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--page-bg);
}
.about-content {
  padding: 8px 16px 24px;
}
.product-name {
  display: block;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 600;
}
.version {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}
.info-card,
.notice-card {
  margin-top: 24px;
  padding: 16px;
  border-radius: 8px;
  background: var(--surface);
}
.info-row {
  display: flex;
  align-items: flex-start;
  padding: 11px 0;
  border-bottom: 1px solid var(--border);
}
.info-row:first-child {
  padding-top: 0;
}
.info-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}
.info-label {
  width: 76px;
  flex: none;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 19px;
}
.info-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 19px;
}
.notice-card {
  background: var(--warning-bg);
}
.notice-title {
  display: block;
  color: var(--warning);
  font-size: 13px;
  font-weight: 600;
}
.notice-text {
  display: block;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 20px;
}
</style>
