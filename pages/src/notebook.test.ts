import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeNotes, parseNotebook, serializeNotebook, type Note } from './notebook.ts';

const note: Note = { id: 'one', company: '虚构样例', thesis: '先查回款', invalidation: '连续恶化', reviewDate: '2026-12-01', createdAt: '2026-11-19T00:00:00Z' };
test('export/import round trip preserves Chinese and multiline text', () => {
  const notes = [{ ...note, thesis: '现金流\n与净利润一起看 <script>' }];
  assert.deepEqual(parseNotebook(serializeNotebook(notes)), notes);
});
test('malformed imports are rejected before any data is merged', () => {
  for (const data of [{ notes: [note] }, { version: 1, notes: [{ ...note, thesis: 2 }] }, { version: 1, notes: [note, note] }, { version: 1, notes: [{ ...note, createdAt: 'invalid' }] }]) {
    assert.throws(() => parseNotebook(JSON.stringify(data)));
  }
  assert.throws(() => parseNotebook('x'.repeat(2_000_001)));
});
test('import merges without overwriting an existing personal judgment', () => {
  assert.deepEqual(mergeNotes([note], [{ ...note, thesis: '覆盖' }, { ...note, id: 'two' }]), [{ ...note, id: 'two' }, note]);
  assert.throws(() => mergeNotes(Array.from({ length: 500 }, (_, i) => ({ ...note, id: `${i}` })), [note]));
});
