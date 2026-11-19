export interface Note {
  id: string;
  company: string;
  thesis: string;
  invalidation: string;
  reviewDate: string;
  createdAt: string;
}
export const STORAGE_KEY = "xiamimate-stock-lab:pages:notebook:v1";
export const MAX_NOTES = 500;

/** Imports are user files, never HTML. Reject the whole file before modifying local notes. */
export function parseNotebook(raw: string): Note[] {
  if (raw.length > 2_000_000) throw new Error("文件过大，请使用本站导出的笔记文件（不超过 2 MB）。");
  const data: unknown = JSON.parse(raw);
  if (!data || typeof data !== "object" || !("version" in data) || data.version !== 1 || !("notes" in data) || !Array.isArray(data.notes)) {
    throw new Error("文件格式不对，请选择本站导出的笔记 JSON。");
  }
  if (data.notes.length > MAX_NOTES) throw new Error(`最多保存 ${MAX_NOTES} 条笔记。`);
  const ids = new Set<string>();
  return data.notes.map((n: unknown) => {
    if (!n || typeof n !== "object") throw new Error("笔记格式不完整。");
    const row = n as Record<string, unknown>;
    const fields = ["id", "company", "thesis", "invalidation", "reviewDate", "createdAt"] as const;
    if (fields.some(k => typeof row[k] !== "string" || (row[k] as string).length > 6000)) throw new Error("笔记字段缺失或过长。");
    if (!(row.id as string).trim() || !(row.company as string).trim() || !(row.thesis as string).trim()) throw new Error("公司和判断不能为空。");
    if (!Number.isFinite(Date.parse(row.createdAt as string))) throw new Error("记录时间格式不对。");
    if (row.reviewDate && !/^\d{4}-\d{2}-\d{2}$/.test(row.reviewDate as string)) throw new Error("复核日期格式不对。");
    if (ids.has(row.id as string)) throw new Error("文件中有重复记录编号。");
    ids.add(row.id as string);
    return Object.fromEntries(fields.map(k => [k, row[k]])) as unknown as Note;
  });
}

export function serializeNotebook(notes: Note[]): string {
  return JSON.stringify({ app: "xiamimate-stock-lab-pages", version: 1, notes }, null, 2);
}

export function mergeNotes(current: Note[], incoming: Note[]): Note[] {
  const ids = new Set(current.map(n => n.id));
  const result = [...incoming.filter(n => !ids.has(n.id)), ...current];
  if (result.length > MAX_NOTES) throw new Error(`合并后超过 ${MAX_NOTES} 条，请先导出整理。`);
  return result;
}
