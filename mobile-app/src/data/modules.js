// 四大模块的字段定义严格对应数据库列，不在前端增加新的业务字段。
export const modules = {
  sale: {
    key: "sale",
    name: "项目买卖信息",
    endpoint: "sales",
    visual: {
      short: "买卖",
      icon: "Building2",
      kicker: "PROJECT DEALS",
      description: "项目动向、交易价格与市场传闻",
    },
    dateField: "deal_date",
    optional: true,
    titleField: "project_name",
    subtitleFields: ["district", "deal_status"],
    fields: [
      { key: "project_name", label: "项目名称", type: "text", core: true },
      { key: "district", label: "所在区域", type: "text", core: true, placeholder: "如浦东-陆家嘴" },
      { key: "deal_date", label: "交易时间", type: "date", core: true },
      { key: "deal_total_price", label: "交易总价", type: "number", core: true, unit: "万元" },
      { key: "buyer", label: "受让方", type: "text", core: true },
      { key: "address", label: "详细地址", type: "text" },
      { key: "total_area", label: "总建筑面积", type: "number", unit: "㎡" },
      { key: "standard_floor_area", label: "标准层面积", type: "number", unit: "㎡" },
      { key: "total_floors", label: "总楼层", type: "text" },
      { key: "property_grade", label: "物业等级", type: "text" },
      { key: "project_feature", label: "项目核心特点", type: "textarea" },
      { key: "deal_unit_price", label: "成交单价", type: "number", unit: "元/㎡" },
      { key: "deal_type", label: "交易方式", type: "select", options: ["买卖", "股权交易", "资产转让", "司法拍卖", "其他"] },
      { key: "deal_target", label: "交易标的", type: "text" },
      { key: "deal_status", label: "交易状态", type: "select", options: ["信息待补充", "洽谈中", "意向中", "已签约", "已成交", "已终止"] },
      { key: "seller", label: "原业主方", type: "text" },
      { key: "buyer_purpose", label: "买家购置用途", type: "text" },
      { key: "has_intermediary", label: "是否有居间", type: "select", options: ["是", "否"] },
      { key: "main_intermediary", label: "主居间方", type: "text" },
      { key: "joint_intermediary", label: "联合居间方", type: "text" },
      { key: "commission_remark", label: "佣金备注", type: "textarea", adminOnly: true },
      { key: "deal_background", label: "交易背景", type: "textarea" },
      { key: "inside_story", label: "内部趣事/传闻", type: "textarea" },
      { key: "tags", label: "标签", type: "text", placeholder: "逗号分隔" },
      { key: "remark", label: "通用备注", type: "textarea" },
    ],
  },
  lease: {
    key: "lease",
    name: "企业租赁信息",
    endpoint: "leases",
    visual: {
      short: "租赁",
      icon: "BriefcaseBusiness",
      kicker: "TENANT MOVES",
      description: "企业搬迁、扩租与成交条件",
    },
    dateField: "start_date",
    titleField: "company_name",
    subtitleFields: ["new_project", "lease_type"],
    fields: [
      { key: "company_name", label: "企业名称", type: "text", required: true, core: true },
      { key: "new_project", label: "新办公项目", type: "text", required: true, core: true },
      { key: "lease_type", label: "租赁类型", type: "select", required: true, core: true, options: ["新租", "续租", "扩租", "搬迁"] },
      { key: "start_date", label: "起租日期", type: "date", core: true },
      { key: "new_area", label: "新租赁面积", type: "number", core: true, unit: "㎡" },
      { key: "industry", label: "所属行业", type: "text" },
      { key: "company_scale", label: "企业规模", type: "text" },
      { key: "old_project", label: "原办公项目", type: "text" },
      { key: "old_area", label: "原租赁面积", type: "number", unit: "㎡" },
      { key: "old_expire_date", label: "原租约到期时间", type: "date" },
      { key: "floor", label: "所在楼层", type: "text" },
      { key: "rent_price", label: "租金单价", type: "number", unit: "元/㎡/天" },
      { key: "ext_field_3", label: "净租金单价", type: "number", unit: "元/㎡/天" },
      { key: "property_fee", label: "物业费标准", type: "number", unit: "元/㎡/月" },
      { key: "rent_free_period", label: "免租期", type: "number", unit: "月" },
      { key: "lease_term", label: "签约年限", type: "number", unit: "年" },
      { key: "end_date", label: "到期日期", type: "date" },
      { key: "rent_increase", label: "租金递增", type: "text" },
      { key: "main_intermediary", label: "主居间方", type: "text" },
      { key: "joint_intermediary", label: "联合居间方", type: "text" },
      { key: "broker_name", label: "经办经纪人", type: "text" },
      { key: "move_reason", label: "搬迁原因", type: "textarea" },
      { key: "company_background", label: "企业动态背景", type: "textarea" },
      { key: "tags", label: "标签", type: "text", placeholder: "逗号分隔" },
      { key: "remark", label: "通用备注", type: "textarea" },
    ],
  },
  work: {
    key: "work",
    name: "工作记录",
    endpoint: "work-logs",
    visual: {
      short: "工作",
      icon: "ClipboardCheck",
      kicker: "WORK RHYTHM",
      description: "跟进、复盘与每天的待办节奏",
    },
    dateField: "record_date",
    titleField: "record_type",
    subtitleFields: ["related_project", "follow_status"],
    fields: [
      { key: "record_type", label: "记录类型", type: "select", required: true, core: true, options: ["每日心得", "客户跟进", "踩盘记录", "周计划", "周总结", "月计划", "月总结", "业务规划", "待办计划", "每日复盘"] },
      { key: "record_date", label: "记录日期", type: "date", required: true, core: true },
      { key: "ext_field_4", label: "计划执行时分", type: "time", core: true, placeholder: "全天计划可留空" },
      { key: "content", label: "记录正文", type: "textarea", required: true, core: true },
      { key: "related_project", label: "关联项目/企业", type: "text" },
      { key: "follow_status", label: "跟进状态", type: "text" },
      { key: "is_shared", label: "团队共享", type: "switch", default: 0 },
      { key: "ext_field_1", label: "执行情况/完成说明", type: "textarea" },
      { key: "todo_items", label: "待办事项", type: "textarea" },
      { key: "tags", label: "标签", type: "text", placeholder: "逗号分隔" },
    ],
  },
  inspiration: {
    key: "inspiration",
    name: "个人灵感角",
    endpoint: "inspirations",
    visual: {
      short: "灵感",
      icon: "Sparkles",
      kicker: "PRIVATE NOTES",
      description: "只属于你的观察、线索与念头",
    },
    dateField: "record_time",
    titleField: "inspiration_type",
    subtitleFields: ["tags"],
    private: true,
    fields: [
      { key: "inspiration_type", label: "灵感类型", type: "select", core: true, options: ["想法", "灵感", "行业观察", "人脉", "业务线索"] },
      { key: "record_time", label: "记录时间", type: "datetime", required: true, core: true },
      { key: "content", label: "灵感正文", type: "textarea", required: true, core: true },
      { key: "tags", label: "自定义标签", type: "text", placeholder: "逗号分隔" },
      { key: "ext_field_1", label: "扩展备注", type: "textarea" },
    ],
  },
};

// 首页顺序与 Pixso 设计稿保持一致，四项入口固定不变。
export const homeModules = [modules.inspiration, modules.work, modules.lease, modules.sale];
export const moduleList = [modules.sale, modules.lease, modules.work, modules.inspiration];

function pad(value) {
  return String(value).padStart(2, "0");
}

export function localDate(now = new Date()) {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function localDateTime(now = new Date()) {
  return `${localDate(now)}T${pad(now.getHours())}:${pad(now.getMinutes())}:00`;
}

export function initialFields(moduleKey) {
  const fields = {};
  modules[moduleKey].fields.forEach((field) => {
    fields[field.key] = Object.prototype.hasOwnProperty.call(field, "default") ? field.default : null;
  });
  if (moduleKey === "sale") Object.assign(fields, { deal_date: localDate(), deal_status: "信息待补充" });
  if (moduleKey === "lease") Object.assign(fields, { start_date: localDate(), lease_type: "新租" });
  if (moduleKey === "work") Object.assign(fields, { record_date: localDate(), record_type: "每日心得", is_shared: 0 });
  if (moduleKey === "inspiration") Object.assign(fields, { record_time: localDateTime(), inspiration_type: "灵感" });
  return fields;
}

export function fieldMap(moduleKey) {
  return Object.fromEntries(modules[moduleKey].fields.map((field) => [field.key, field]));
}

export function normalizeRecordPayload(moduleKey, input) {
  const config = modules[moduleKey];
  const payload = {};
  config.fields.forEach((field) => {
    if (field.adminOnly) return;
    const value = input[field.key];
    if (value === "" || value === undefined) {
      payload[field.key] = null;
      return;
    }
    if (field.type === "datetime" && value && !String(value).includes("T")) {
      payload[field.key] = `${value}T00:00:00`;
    } else if (field.type === "switch") {
      payload[field.key] = Number(value) ? 1 : 0;
    } else {
      payload[field.key] = value;
    }
  });
  // 管理员的佣金字段需要单独提交；普通成员由后端自动隐藏。
  if (moduleKey === "sale" && Object.prototype.hasOwnProperty.call(input, "commission_remark")) {
    payload.commission_remark = input.commission_remark || null;
  }
  return payload;
}

export function recordTitle(moduleKey, record) {
  if (moduleKey === "sale") return record.project_name || "未命名项目";
  if (moduleKey === "lease") return record.company_name || "未命名企业";
  if (moduleKey === "work") return record.content || record.record_type || "工作记录";
  return record.content || "未命名灵感";
}

export function recordDate(moduleKey, record) {
  const value = record[modules[moduleKey].dateField];
  return value ? String(value).slice(0, 10) : "";
}
