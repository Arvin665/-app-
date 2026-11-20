import { Capacitor } from "@capacitor/core";
import { LocalNotifications } from "@capacitor/local-notifications";

const timers = new Map();
const dailyTimers = [];
const PLAN_CHANNEL_ID = "plan-reminders";
export const ALL_DAY_REMINDER_TIME = "08:30";
const DAILY_IDS = {
  morning: 18083001,
  evening: 17300001,
};
let channelPromise = null;

function isNative() {
  return Capacitor.isNativePlatform();
}

function planTimestamp(plan) {
  if (!plan?.record_date) return 0;
  const time = plan.ext_field_4 || ALL_DAY_REMINDER_TIME;
  return new Date(`${plan.record_date}T${time}:00`).getTime();
}

function notificationId(recordId) {
  const text = String(recordId || "plan");
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return ((hash >>> 0) % 2147483647) || 1;
}

function openNotification(payload = {}) {
  if (payload.recordId) {
    uni.reLaunch({ url: `/pages/detail/index?module=${payload.module || "work"}&id=${payload.recordId}` });
  } else {
    uni.reLaunch({ url: "/pages/plans/index" });
  }
}

function parsePayload(value) {
  if (!value) return {};
  if (typeof value === "object") return value;
  try {
    return JSON.parse(String(value));
  } catch (error) {
    return {};
  }
}

async function ensurePlanChannel() {
  if (!isNative() || Capacitor.getPlatform() !== "android") return;
  if (!channelPromise) {
    channelPromise = LocalNotifications.createChannel({
      id: PLAN_CHANNEL_ID,
      name: "计划提醒",
      description: "工作计划与待办提醒",
      importance: 4,
      visibility: 1,
      vibration: true,
    }).catch((error) => {
      channelPromise = null;
      console.warn("提醒通道创建失败", error);
    });
  }
  await channelPromise;
}

async function nativePermission(request = false) {
  if (!isNative()) return "unsupported";
  let status = await LocalNotifications.checkPermissions();
  if (status.display !== "granted" && request) {
    status = await LocalNotifications.requestPermissions();
  }
  return status.display;
}

export async function notificationPermission() {
  if (isNative()) return nativePermission(false);
  if (typeof Notification === "undefined") return "unsupported";
  return Notification.permission;
}

export async function requestNotificationPermission() {
  if (isNative()) {
    const permission = await nativePermission(true);
    if (permission === "granted") {
      await ensurePlanChannel();
      await scheduleDailyReminders();
    }
    return permission;
  }
  if (typeof Notification === "undefined") return "unsupported";
  if (Notification.permission === "default") {
    try {
      const permission = await Notification.requestPermission();
      if (permission === "granted") await scheduleDailyReminders();
      return permission;
    } catch (error) {
      return Notification.permission;
    }
  }
  return Notification.permission;
}

export function setupNotificationActions() {
  if (!isNative()) return null;
  LocalNotifications.addListener("localNotificationActionPerformed", (action) => {
    openNotification(parsePayload(action?.notification?.extra));
  });
  return true;
}

export async function showNotification(title, content, payload = {}) {
  if (isNative()) {
    const permission = await nativePermission(false);
    if (permission !== "granted") return false;
    await ensurePlanChannel();
    await LocalNotifications.schedule({
      notifications: [
        {
          id: notificationId(payload.recordId || `${Date.now()}`),
          title,
          body: content,
          channelId: PLAN_CHANNEL_ID,
          extra: payload,
          schedule: { at: new Date(Date.now() + 1000), allowWhileIdle: true },
        },
      ],
    });
    return true;
  }
  if (typeof Notification !== "undefined" && Notification.permission === "granted") {
    const message = new Notification(title, { body: content, data: payload });
    message.onclick = () => openNotification(payload);
    return true;
  }
  return false;
}

export async function cancelPlanReminder(recordId) {
  if (!recordId) return;
  const timer = timers.get(recordId);
  if (timer) clearTimeout(timer);
  timers.delete(recordId);
  if (!isNative()) return;
  try {
    await LocalNotifications.cancel({
      notifications: [{ id: notificationId(recordId) }],
    });
  } catch (error) {
    console.warn("取消提醒失败", error);
  }
}

export async function schedulePlanReminder(plan, { requestPermission = false } = {}) {
  if (!plan?.record_id || [2, 3].includes(Number(plan.ext_field_5))) {
    await cancelPlanReminder(plan?.record_id);
    return false;
  }
  const triggerAt = planTimestamp(plan);
  if (!triggerAt || triggerAt <= Date.now()) return false;

  if (isNative()) {
    const permission = await nativePermission(requestPermission);
    if (permission !== "granted") return false;
    await ensurePlanChannel();
    const id = notificationId(plan.record_id);
    await cancelPlanReminder(plan.record_id);
    await LocalNotifications.schedule({
      notifications: [
        {
          id,
          title: "Sayo Sense · 计划提醒",
          body: String(plan.content || "你有一条待办计划"),
          largeBody: String(plan.content || "你有一条待办计划"),
          summaryText: `${plan.record_date || ""} ${plan.ext_field_4 || `全天 · ${ALL_DAY_REMINDER_TIME} 提醒`}`.trim(),
          channelId: PLAN_CHANNEL_ID,
          extra: { module: "work", recordId: plan.record_id },
          schedule: {
            at: new Date(triggerAt),
            allowWhileIdle: true,
            isExactNotification: true,
          },
        },
      ],
    });
    return true;
  }

  await cancelPlanReminder(plan.record_id);
  const delay = Math.min(triggerAt - Date.now(), 2 ** 31 - 1);
  const timer = setTimeout(() => {
    showNotification("计划提醒", String(plan.content || "待办计划到时间了"), {
      module: "work",
      recordId: plan.record_id,
    });
    timers.delete(plan.record_id);
  }, delay);
  timers.set(plan.record_id, timer);
  return true;
}

export async function scheduleDailyReminders() {
  if (isNative()) {
    const permission = await nativePermission(false);
    if (permission !== "granted") return false;
    await ensurePlanChannel();
    await LocalNotifications.schedule({
      notifications: [
        {
          id: DAILY_IDS.morning,
          title: "今日待办清单",
          body: "查看今天的工作计划，先确认最重要的三件事。",
          channelId: PLAN_CHANNEL_ID,
          schedule: { on: { hour: 8, minute: 30 }, repeats: true, allowWhileIdle: true },
        },
        {
          id: DAILY_IDS.evening,
          title: "每日计划确认",
          body: "确认今天完成情况，并为明天留下清晰的安排。",
          channelId: PLAN_CHANNEL_ID,
          schedule: { on: { hour: 17, minute: 30 }, repeats: true, allowWhileIdle: true },
        },
      ],
    });
    return true;
  }

  const nextRun = (key, hour, minute) => {
    const now = new Date();
    const target = new Date(now);
    target.setHours(hour, minute, 0, 0);
    if (target <= now) target.setDate(target.getDate() + 1);
    const delay = Math.min(target.getTime() - now.getTime(), 2 ** 31 - 1);
    const timer = setTimeout(() => {
      showNotification(
        key === "morning" ? "今日待办清单" : "每日计划确认",
        key === "morning" ? "查看今天的待办计划" : "确认并归档今日计划",
        { module: "work" },
      );
      nextRun(key, hour, minute);
    }, delay);
    dailyTimers.push(timer);
  };
  nextRun("morning", 8, 30);
  nextRun("evening", 17, 30);
  return true;
}

export function clearForegroundTimers() {
  timers.forEach((timer) => clearTimeout(timer));
  timers.clear();
  dailyTimers.splice(0).forEach((timer) => clearTimeout(timer));
}

export function hasBackgroundReminderSupport() {
  return isNative();
}

export { notificationId };
