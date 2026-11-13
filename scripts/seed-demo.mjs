// Optional demo-data seed for local acceptance. Set DEVICE_ID to a bound admin device.
const baseUrl = (process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
const deviceId = process.env.DEVICE_ID;
if (!deviceId) throw new Error("DEVICE_ID is required");

const headers = { "Content-Type": "application/json", "X-Device-ID": deviceId };
const suffix = String(Date.now()).slice(-6);

async function post(path, body) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${path}: ${response.status} ${JSON.stringify(data)}`);
  return data;
}

const sale = await post("/sales", {
  project_name: `陆家嘴演示项目-${suffix}`,
  district: "浦东-陆家嘴",
  address: "世纪大道演示地址",
  total_area: "32000",
  deal_total_price: "86000",
  deal_unit_price: "26875",
  deal_date: "2026-11-12",
  deal_type: "资产转让",
  deal_status: "已签约",
  seller: "演示业主",
  buyer: "演示买方",
  main_intermediary: "演示居间方",
  commission_remark: "管理员可见演示佣金",
  remark: "本地验收样例",
});

const lease = await post("/leases", {
  company_name: `演示企业-${suffix}`,
  industry: "专业服务",
  company_scale: "100-300人",
  old_project: "原办公项目",
  new_project: "前滩演示中心",
  new_area: "3200",
  lease_type: "搬迁",
  rent_price: "6.80",
  property_fee: "32",
  start_date: "2026-11-10",
  lease_term: 3,
  main_intermediary: "演示居间方",
  move_reason: "扩租并升级办公形象",
  remark: "本地验收样例",
});

const work = await post("/work-logs", {
  record_type: "客户跟进",
  record_date: "2026-11-13",
  content: `演示客户已完成现场带看-${suffix}`,
  related_project: "前滩演示中心",
  follow_status: "待反馈",
  is_shared: 1,
});

const plan = await post("/work-logs", {
  record_type: "待办计划",
  record_date: "2026-11-13",
  ext_field_4: "17:30",
  ext_field_5: 0,
  content: `整理演示客户清单-${suffix}`,
  is_shared: 0,
});

const inspiration = await post("/inspirations", {
  record_time: "2026-11-13T15:30:00",
  inspiration_type: "行业观察",
  content: `演示灵感：关注企业总部搬迁需求-${suffix}`,
  tags: "演示,行业",
});

console.log(JSON.stringify({
  sale_id: sale.record_id,
  lease_id: lease.record_id,
  work_id: work.record_id,
  plan_id: plan.record_id,
  inspiration_id: inspiration.record_id,
}, null, 2));
