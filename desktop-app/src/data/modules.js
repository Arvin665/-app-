import { localDateString } from "../utils/date";

// 字段与后端固定表结构一一对应；桌面端不额外发明业务字段。
const saleFields = [
  { key: "deal_date", label: "交易时间", type: "date", required: true },
  { key: "project_name", label: "项目名称", type: "text", required: true },
  { key: "district", label: "所在区域", type: "text", required: true },
  { key: "address", label: "详细地址", type: "text" },
  { key: "total_area", label: "总建筑面积", type: "number", unit: "㎡" },
  { key: "standard_floor_area", label: "标准层面积", type: "number", unit: "㎡" },
  { key: "total_floors", label: "总楼层", type: "text" },
  { key: "property_grade", label: "物业等级", type: "text" },
  { key: "project_feature", label: "项目核心特点", type: "textarea" },
  { key: "deal_total_price", label: "交易总价", type: "number", unit: "万元" },
  { key: "deal_unit_price", label: "成交单价", type: "number", unit: "元/㎡" },
  { key: "deal_type", label: "交易方式", type: "select", options: ["买卖", "股权交易", "资产转让", "司法拍卖", "其他"] },
  { key: "deal_target", label: "交易标的", type: "text" },
  { key: "deal_status", label: "交易状态", type: "select", options: ["已签约", "已成交", "洽谈中", "意向中", "已终止"], required: true },
  { key: "seller", label: "原业主方", type: "text" },
  { key: "buyer", label: "受让方（买家）", type: "text" },
  { key: "buyer_purpose", label: "买家购置用途", type: "text" },
  { key: "has_intermediary", label: "是否有居间", type: "select", options: ["是", "否"] },
  { key: "main_intermediary", label: "主居间方", type: "text" },
  { key: "joint_intermediary", label: "联合居间方", type: "text" },
  { key: "commission_remark", label: "佣金备注", type: "textarea", adminOnly: true },
  { key: "deal_background", label: "交易背景", type: "textarea" },
  { key: "inside_story", label: "内部趣事/传闻", type: "textarea" },
  { key: "tags", label: "标签", type: "text" },
  { key: "remark", label: "通用备注", type: "textarea" },
];

const leaseFields = [
  { key: "start_date", label: "起租日期", type: "date" },
  { key: "company_name", label: "企业名称", type: "text", required: true },
  { key: "industry", label: "所属行业", type: "text" },
  { key: "company_scale", label: "企业规模", type: "text" },
  { key: "old_project", label: "原办公项目", type: "text" },
  { key: "old_area", label: "原租赁面积", type: "number", unit: "㎡" },
  { key: "old_expire_date", label: "原租约到期时间", type: "date" },
  { key: "new_project", label: "新办公项目", type: "text", required: true },
  { key: "new_area", label: "新租赁面积", type: "number", unit: "㎡" },
  { key: "floor", label: "所在楼层", type: "text" },
  { key: "lease_type", label: "租赁类型", type: "select", options: ["新租", "续租", "扩租", "搬迁"], required: true },
  { key: "rent_price", label: "租金单价", type: "number", unit: "元/㎡/天" },
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
  { key: "tags", label: "标签", type: "text" },
  { key: "remark", label: "通用备注", type: "textarea" },
];

const workFields = [
  { key: "record_date", label: "记录日期", type: "date", required: true },
  { key: "record_type", label: "记录类型", type: "select", options: ["每日心得", "客户跟进", "踩盘记录", "周计划", "周总结", "月计划", "月总结", "业务规划", "待办计划", "每日复盘"], required: true },
  { key: "ext_field_4", label: "计划执行时分", type: "time" },
  { key: "content", label: "记录正文", type: "textarea", required: true },
  { key: "todo_items", label: "待办事项", type: "textarea" },
  { key: "related_project", label: "关联项目/企业", type: "text" },
  { key: "follow_status", label: "跟进状态", type: "text" },
  { key: "is_shared", label: "是否共享", type: "switch" },
  { key: "ext_field_1", label: "执行情况/完成说明", type: "textarea" },
  { key: "ext_field_2", label: "推迟记录", type: "textarea", readonly: true },
  { key: "ext_field_5", label: "计划状态", type: "select", options: ["未做", "正在做", "已做好", "计划搁置"], optionValues: [0, 1, 2, 3] },
  { key: "tags", label: "标签", type: "text" },
];

const inspirationFields = [
  { key: "record_time", label: "记录时间", type: "datetime", required: true },
  { key: "inspiration_type", label: "灵感类型", type: "select", options: ["想法", "灵感", "行业观察", "人脉", "业务线索"] },
  { key: "content", label: "灵感正文", type: "textarea", required: true },
  { key: "tags", label: "标签", type: "text" },
  { key: "ext_field_1", label: "扩展备注", type: "textarea" },
];

export const modules = {
  sale: {
    key: "sale", name: "项目买卖信息", endpoint: "sales", dateField: "deal_date", nameField: "project_name", fields: saleFields,
    defaultColumns: ["deal_date", "project_name", "district", "total_area", "deal_total_price", "deal_unit_price", "seller", "buyer", "deal_type", "main_intermediary", "deal_status", "remark"],
    advancedFilters: ["project_name", "district", "deal_status"],
  },
  lease: {
    key: "lease", name: "企业租赁信息", endpoint: "leases", dateField: "start_date", nameField: "company_name", fields: leaseFields,
    defaultColumns: ["start_date", "company_name", "industry", "new_project", "new_area", "rent_price", "lease_type", "lease_term", "main_intermediary", "move_reason", "remark"],
    advancedFilters: ["company_name", "industry", "new_project"],
  },
  work: {
    key: "work", name: "工作记录", endpoint: "work-logs", dateField: "record_date", nameField: "content", fields: workFields,
    defaultColumns: ["record_date", "record_type", "content", "follow_status", "is_shared", "related_project"],
    advancedFilters: ["record_type", "follow_status", "is_shared"],
  },
  inspiration: {
    key: "inspiration", name: "个人灵感角", endpoint: "inspirations", dateField: "record_time", nameField: "content", fields: inspirationFields,
    defaultColumns: ["record_time", "inspiration_type", "content", "tags"],
    advancedFilters: ["inspiration_type"],
  },
};

export const moduleList = Object.values(modules);
export const moduleNames = Object.fromEntries(moduleList.map((item) => [item.key, item.name]));

export function fieldConfig(moduleKey, fieldKey) {
  return modules[moduleKey].fields.find((field) => field.key === fieldKey);
}

export function formatCell(moduleKey, fieldKey, value) {
  if (value === null || value === undefined || value === "") return "";
  if (fieldKey === "is_shared") return Number(value) ? "团队共享" : "仅本人可见";
  if (fieldKey === "ext_field_5") return ["未做", "正在做", "已做好", "计划搁置"][Number(value)] || "未做";
  const field = fieldConfig(moduleKey, fieldKey);
  if (field?.type === "switch") return Number(value) ? "是" : "否";
  return value;
}

export function displayTitle(moduleKey, record) {
  if (moduleKey === "sale") return record.project_name || "未命名项目";
  if (moduleKey === "lease") return record.company_name || "未命名企业";
  return record.content || record.record_type || "未命名记录";
}

export function defaultForm(moduleKey) {
  const today = localDateString();
  const result = {};
  modules[moduleKey].fields.forEach((field) => { result[field.key] = field.type === "switch" ? 0 : ""; });
  if (moduleKey === "sale") Object.assign(result, { deal_date: today, deal_status: "已签约" });
  if (moduleKey === "lease") Object.assign(result, { start_date: today, lease_type: "新租" });
  if (moduleKey === "work") Object.assign(result, { record_date: today, record_type: "每日心得", is_shared: 0, ext_field_5: 0 });
  if (moduleKey === "inspiration") Object.assign(result, { record_time: `${today}T09:00:00`, inspiration_type: "灵感" });
  return result;
}
