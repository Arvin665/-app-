// 提醒采用“原生调度插件优先、前台定时器兜底”的适配层。
// 纯 JS 无法在被系统杀死后保证准点触发，生产必须在 HBuilderX 中接入原生通知插件。
const timers = new Map();
const plugin = () => {
  try {
    return uni.requireNativePlugin("AssetLibrary-Notification");
  } catch (error) {
    return null;
  }
};

function planTimestamp(plan) {
  if (!plan.record_date) return 0;
  const time = plan.ext_field_4 || "09:00";
  return new Date(`${plan.record_date}T${time}:00`).getTime();
}

export function notificationPermission() {
  if (typeof Notification !== "undefined") return Notification.permission;
  return plugin()?.getPermission?.() || "unknown";
}

export async function requestNotificationPermission() {
  if (typeof Notification !== "undefined" && Notification.permission === "default") {
    return Notification.requestPermission();
  }
  const native = plugin();
  if (native?.requestPermission) {
    return new Promise((resolve) => native.requestPermission((result) => resolve(result?.granted ? "granted" : "denied")));
  }
  return notificationPermission();
}

export function showNotification(title, content, payload = {}) {
  if (typeof Notification !== "undefined" && Notification.permission === "granted") {
    const message = new Notification(title, { body: content, data: payload });
    message.onclick = () => {
      if (payload.recordId) {
        uni.navigateTo({ url: `/pages/detail/index?module=${payload.module || "work"}&id=${payload.recordId}` });
      } else {
        uni.navigateTo({ url: "/pages/plans/index" });
      }
    };
    return true;
  }
  // #ifdef APP-PLUS
  try {
    plus.push.createMessage(content, JSON.stringify(payload), { title });
    return true;
  } catch (error) {
    console.warn("本地通知不可用", error);
  }
  // #endif
  return false;
}

export function cancelPlanReminder(recordId) {
  const timer = timers.get(recordId);
  if (timer) clearTimeout(timer);
  timers.delete(recordId);
  plugin()?.cancelPlanReminder?.({ recordId });
}

export async function schedulePlanReminder(plan) {
  if (!plan?.record_id || [2, 3].includes(Number(plan.ext_field_5))) {
    cancelPlanReminder(plan?.record_id);
    return false;
  }
  const triggerAt = planTimestamp(plan);
  if (!triggerAt || triggerAt <= Date.now()) return false;

  const native = plugin();
  if (native?.schedulePlanReminder) {
    await new Promise((resolve) => {
      native.schedulePlanReminder(
        {
          id: plan.record_id,
          title: "商办信息资产库 · 计划提醒",
          content: plan.content || "你有一条待办计划",
          triggerAt,
          payload: { module: "work", recordId: plan.record_id },
        },
        resolve,
      );
    });
    return true;
  }

  // 前台保底：允许触发时应用仍在运行。后台/杀进程场景由原生插件负责。
  cancelPlanReminder(plan.record_id);
  const delay = Math.min(triggerAt - Date.now(), 2 ** 31 - 1);
  const timer = setTimeout(() => {
    showNotification("计划提醒", plan.content || "待办计划到时间了", {
      module: "work",
      recordId: plan.record_id,
    });
    timers.delete(plan.record_id);
  }, delay);
  timers.set(plan.record_id, timer);
  return false;
}

export function scheduleDailyReminders() {
  const native = plugin();
  if (native?.scheduleDailySummaries) {
    native.scheduleDailySummaries({
      morning: "08:30",
      evening: "17:30",
      morningTitle: "今日待办清单",
      eveningTitle: "每日计划确认",
    });
    return true;
  }
  // 无原生插件时只在 App 前台运行期间触发；文档会明确该限制。
  const nextRun = (hour, minute) => {
    const now = new Date();
    const target = new Date(now);
    target.setHours(hour, minute, 0, 0);
    if (target <= now) target.setDate(target.getDate() + 1);
    const delay = Math.min(target.getTime() - now.getTime(), 2 ** 31 - 1);
    setTimeout(() => {
      showNotification(
        hour === 8 ? "今日待办清单" : "每日计划确认",
        hour === 8 ? "查看今天的待办计划" : "17:30，确认并归档今日计划",
        { module: "work" },
      );
      nextRun(hour, minute);
    }, delay);
  };
  nextRun(8, 30);
  nextRun(17, 30);
  return false;
}

export function clearForegroundTimers() {
  timers.forEach((timer) => clearTimeout(timer));
  timers.clear();
}
