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
    if (module && ["sale", "lease", "work", "inspiration"].includes(module)) {
      // 微信/系统分享落入应用时，保留当前模块并直达二级录入页。
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
</style>
