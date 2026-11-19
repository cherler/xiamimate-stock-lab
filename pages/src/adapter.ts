import fixtures from "./fixtures.json" with { type: "json" };

const responses = fixtures.responses as Record<string, unknown>;
const UNAVAILABLE = "此功能需要后台服务。Pages 使用虚构样例供浏览，不会同步行情、调用 AI、保存到服务器或发送提醒。请打开完整在线服务或在本机部署；个人想法可用顶部的「我的笔记」保存。";

function keyFor(path: string) {
  const url = new URL(path, 'https://preview.invalid');
  const kept = new URLSearchParams();
  const keys = url.pathname === '/api/v1/heatmap' ? ['metric','scope'] : url.pathname === '/api/v1/screen/run' ? ['strategy'] : url.pathname === '/api/v1/industries/comparison' ? ['industry'] : [];
  for (const key of keys) if (url.searchParams.has(key)) kept.set(key, url.searchParams.get(key)!);
  kept.sort();
  return url.pathname + (kept.size ? `?${kept}` : '');
}

/** Same UI, a different read transport. No network fallback and no fake write success. */
export async function previewRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const method = (options?.method ?? 'GET').toUpperCase();
  const url = new URL(path, 'https://preview.invalid');
  if (options?.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  if (method !== 'GET' && !(method === 'POST' && url.pathname === '/api/v1/screen/run' && !options?.body)) throw new Error(UNAVAILABLE);
  let value: unknown;
  const key = keyFor(path);
  if (url.pathname.startsWith('/api/v1/jobs/')) value = null;
  else if (url.pathname === '/api/v1/universe/lookup') {
    const q = (url.searchParams.get('q') ?? '').toLowerCase();
    const companies = responses['/api/v1/companies'] as { id:number; symbol:string; name:string; industry:string; latest_price:number }[];
    value = companies.filter(c => `${c.name} ${c.symbol}`.toLowerCase().includes(q)).map(c => ({ ...c, company_id:c.id, price:c.latest_price }));
  } else if (url.pathname === '/api/v1/response-reports') {
    const ids = (url.searchParams.get('company_ids') ?? '').split(',').map(Number);
    value = (responses['/api/v1/response-reports'] as { company_id: number }[] ?? []).filter(c => ids.includes(c.company_id));
  } else if (url.pathname.startsWith('/api/v1/methods/')) {
    const library = responses['/api/v1/methods'] as { categories: { methods: { key:string }[] }[] };
    value = library.categories.flatMap(c => c.methods).find(m => m.key === decodeURIComponent(url.pathname.split('/').pop()!));
  } else if (Object.hasOwn(responses, key)) value = responses[key];
  else if (key === url.pathname && Object.hasOwn(responses, url.pathname)) value = responses[url.pathname];
  else throw new Error(UNAVAILABLE);
  if (value === undefined) throw new Error(UNAVAILABLE);
  if (value && typeof value === 'object' && 'preview_error' in value) throw new Error(`演示样本不足：${String(value.preview_error)}`);
  const result = structuredClone(value);
  if (url.pathname === '/api/v1/companies' && Array.isArray(result)) {
    const q = (url.searchParams.get('q') ?? '').trim().toLowerCase();
    return result.filter((c: { name:string; symbol:string }) => `${c.name} ${c.symbol}`.toLowerCase().includes(q)) as T;
  }
  return result as T;
}
