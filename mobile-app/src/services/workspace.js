import { request } from "./api";

export function getRecordContext(module, recordId) {
  return request(`/workspace/records/${module}/${recordId}/context`);
}

export function createRecordLink({
  sourceModule,
  sourceRecordId,
  targetModule,
  targetRecordId,
  relationType = "related",
  note,
}) {
  return request("/workspace/links", {
    method: "POST",
    data: {
      source_module: sourceModule,
      source_record_id: sourceRecordId,
      target_module: targetModule,
      target_record_id: targetRecordId,
      relation_type: relationType,
      note,
    },
  });
}

export function deleteRecordLink(linkId) {
  return request(`/workspace/links/${linkId}`, { method: "DELETE" });
}

export function searchWorkspace({ keyword, modules, kinds, page = 1, pageSize = 30 } = {}) {
  const params = new URLSearchParams();
  params.set("keyword", keyword);
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (modules?.length) params.set("modules", modules.join(","));
  if (kinds?.length) params.set("kinds", kinds.join(","));
  return request(`/workspace/search?${params.toString()}`);
}
