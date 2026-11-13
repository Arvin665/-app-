<script>
import { scheduleDailyReminders } from "./services/reminders";
import { checkBinding } from "./services/session";
import { flushOfflineQueue } from "./services/localDb";

export default {
  onLaunch() {
    // 点击本地通知时按消息载荷直达计划详情或计划列表。
    // #ifdef APP-PLUS
    plus.push.addEventListener("click", (message) => {
      try {
        const payload = typeof message.payload === "string" ? JSON.parse(message.payload) : message.payload || {};
        if (payload.recordId) {
          uni.reLaunch({ url: `/pages/detail/index?module=${payload.module || "work"}&id=${payload.recordId}` });
        } else {
          uni.reLaunch({ url: "/pages/plans/index" });
        }
      } catch (error) {
        uni.reLaunch({ url: "/pages/plans/index" });
      }
    });
    // #endif
    // 已绑定设备直接进首页；首次启动或无本地身份时立即进入邀请码页。
    checkBinding()
      .then((session) => {
        if (!session?.device_id) uni.reLaunch({ url: "/pages/bind/index" });
      })
      .catch(() => uni.reLaunch({ url: "/pages/bind/index" }));
    flushOfflineQueue().catch(() => {});
    scheduleDailyReminders();
  },
  onShow(options) {
    const module = options?.query?.module;
    const sharePath = options?.query?.path;
    const isShareEntry = options?.query?.fromShare === "1" || options?.query?.share === "1";
    if (isShareEntry && module && ["sale", "lease", "work", "inspiration"].includes(module)) {
      // 只有显式分享链接才直达录入页，普通模块路由必须保留原页面。
      setTimeout(() => uni.reLaunch({ url: `/pages/entry/index?module=${module}&fromShare=1` }), 80);
    } else if (sharePath === "history") {
      setTimeout(() => uni.reLaunch({ url: "/pages/history/index" }), 80);
    }
  },
};
</script>

<style>
/* 全局只保留一套基础变量，所有页面共享同一色值和间距体系。 */
page {
  --text-primary: #333333;
  --text-secondary: #666666;
  --text-muted: #999999;
  --page-bg: #f5f7fa;
  --surface: #ffffff;
  --accent: #165dff;
  --warning-bg: #fff7e6;
  --warning: #ff7d00;
  --border: #e5e6eb;
  --soft: #f2f3f5;
  background: var(--page-bg);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 14px;
}

view,
text,
input,
textarea,
button {
  box-sizing: border-box;
}

button::after {
  border: 0;
}

button {
  margin: 0;
}

.safe-top {
  padding-top: env(safe-area-inset-top);
}

.safe-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

.primary-button {
  height: 44px;
  border-radius: 8px;
  background: var(--accent);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  line-height: 44px;
}

.secondary-button {
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 42px;
}

.text-button {
  background: transparent;
  color: var(--text-muted);
  font-size: 14px;
}

.card {
  background: var(--surface);
  border-radius: 8px;
}

.empty-state {
  padding: 48px 24px;
  color: var(--text-muted);
  text-align: center;
}
/* Mobile visual system: restrained, warm and material-led. */
page {
  --ink: #16221f;
  --text-primary: #1c2825;
  --text-secondary: #5f6b66;
  --text-muted: #8a9691;
  --page-bg: #f2f5f3;
  --surface: #ffffff;
  --surface-soft: #e9efec;
  --accent: #0b7565;
  --accent-deep: #075a4e;
  --accent-soft: #dff2ed;
  --warning: #c86428;
  --warning-bg: #fbeee3;
  --danger: #b64c46;
  --border: #dce5e1;
  --soft: #eef2f0;
  --sale: #b85639;
  --sale-soft: #f7e7e0;
  --lease: #0c7a68;
  --lease-soft: #def2ed;
  --work: #3d68b3;
  --work-soft: #e5ecf8;
  --inspiration: #a34f68;
  --inspiration-soft: #f6e5eb;
  --radius: 8px;
  --shadow-soft: 0 8px 28px rgba(20, 45, 38, 0.07);
  background: var(--page-bg);
  color: var(--text-primary);
}

view,
text,
input,
textarea,
button,
scroll-view,
picker {
  box-sizing: border-box;
}

.app-page {
  width: 100vw;
  min-height: 100vh;
  background: var(--page-bg);
}

.primary-button {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--radius);
  background: var(--accent);
  color: #ffffff;
  font-size: 15px;
  font-weight: 650;
  line-height: 48px;
}

.secondary-button {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 550;
  line-height: 42px;
}

.icon-button {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text-primary);
}

.card {
  border: 1px solid rgba(220, 229, 225, 0.72);
  border-radius: var(--radius);
  background: var(--surface);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 38px;
}

.section-title {
  color: var(--text-primary);
  font-size: 19px;
  font-weight: 700;
  line-height: 26px;
}

.section-link {
  min-height: 32px;
  display: flex;
  align-items: center;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
}

.eyebrow {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 650;
  text-transform: uppercase;
}

.pressable {
  transition: transform 120ms ease, opacity 120ms ease;
}

.pressable:active {
  transform: scale(0.985);
  opacity: 0.88;
}

.tabbar-space {
  padding-bottom: calc(78px + env(safe-area-inset-bottom));
}

.line-clamp-2 {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@keyframes voice-wave {
  0%, 100% { transform: scaleY(0.45); }
  50% { transform: scaleY(1); }
}

@keyframes soft-pulse {
  0% { box-shadow: 0 0 0 0 rgba(108, 231, 206, 0.32); }
  70% { box-shadow: 0 0 0 14px rgba(108, 231, 206, 0); }
  100% { box-shadow: 0 0 0 0 rgba(108, 231, 206, 0); }
}
</style>
