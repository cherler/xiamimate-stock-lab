import test from 'node:test';
import assert from 'node:assert/strict';
import { previewRequest } from './adapter.ts';

test('real frontend contracts are backed by fictional companies, finance, valuation and chains', async () => {
  const rows=await previewRequest<{id:number;name:string;symbol:string}[]>('/api/v1/companies');
  assert.equal(rows.length,6);
  assert.ok(rows.every(c=>c.name.includes('示例') && c.symbol.startsWith('99000')));
  for(const c of rows) {
    const valuation=await previewRequest<{ready:boolean;scenarios:unknown[]}>(`/api/v1/companies/${c.id}/valuation`);
    assert.equal(valuation.ready,true); assert.equal(valuation.scenarios.length,3);
  }
  const themes=await previewRequest<unknown[]>('/api/v1/industry-chains');assert.equal(themes.length,14);
});
test('query-dependent screens do not silently reuse a different metric or company', async () => {
  const rows=await previewRequest<{name:string}[]>('/api/v1/companies?q=青岚');assert.equal(rows.length,1);
  const heatmap=await previewRequest<{metric:string}>('/api/v1/heatmap?scope=all&metric=change_percent&limit=60');assert.equal(heatmap.metric,'change_percent');
  const summaries=await previewRequest<{company_id:number}[]>('/api/v1/response-reports?company_ids=1,2');assert.deepEqual(summaries.map(s=>s.company_id),[1,2]);
});
test('writes, uploads and unknown requests never fabricate success or use live services', async () => {
  await assert.rejects(previewRequest('/api/v1/companies/1/theses',{method:'POST',body:'{}'}),/需要后台服务/);
  await assert.rejects(previewRequest('/api/v1/assistant/web/messages',{method:'POST',body:'{}'}),/需要后台服务/);
  await assert.rejects(previewRequest('/api/v1/does-not-exist'),/需要后台服务/);
  await assert.rejects(previewRequest('/api/v1/screen/run',{method:'POST',body:'{}'}),/需要后台服务/);
});
