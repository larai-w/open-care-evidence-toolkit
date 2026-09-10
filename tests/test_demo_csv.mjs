import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../demo.html', import.meta.url), 'utf8');
const start = html.indexOf('    function parseCsv');
const end = html.indexOf('    function inspect', start);
assert.ok(start >= 0 && end > start, 'parseCsv function should be present');
const context = {};
vm.runInNewContext(`this.parseCsv = (${html.slice(start, end).replace(/^\s*function parseCsv/, 'function parseCsv')});`, context);

const normalizeRows = (rows) => rows.map((row) => ({
  event_id: row.event_id,
  observation: row.observation,
  status: row.status,
  corrects: row.corrects,
  schema_version: row.schema_version,
}));

const canonicalRows = (rows) => rows.map((row) => JSON.stringify(row, [
  'event_id',
  'observation',
  'status',
  'corrects',
  'schema_version',
]));

const rows = normalizeRows(context.parseCsv('\uFEFFevent_id,observation,status\r\n"evt-1","水分, 食事",observed\r\n\r\n'));
const rowRows = canonicalRows(rows);
assert.strictEqual(rowRows.length, 1);
assert.strictEqual(rowRows[0], JSON.stringify({ event_id: 'evt-1', observation: '水分, 食事', status: 'observed', corrects: [], schema_version: undefined }));

const edgeRows = normalizeRows(context.parseCsv(
  'event_id,observation,status\r\n' +
  '"evt-2","line1\r\nline2","observed"\r\n' +
  '"evt-3","He said ""Hello"" today","observed"\r\n' +
  'evt-4,,observed'
));
const edgeCanonicalRows = canonicalRows(edgeRows);
assert.strictEqual(edgeCanonicalRows.length, 3);
assert.strictEqual(edgeCanonicalRows[0], JSON.stringify({ event_id: 'evt-2', observation: 'line1\r\nline2', status: 'observed', corrects: [], schema_version: undefined }));
assert.strictEqual(edgeCanonicalRows[1], JSON.stringify({ event_id: 'evt-3', observation: 'He said "Hello" today', status: 'observed', corrects: [], schema_version: undefined }));
assert.strictEqual(edgeCanonicalRows[2], JSON.stringify({ event_id: 'evt-4', observation: '', status: 'observed', corrects: [], schema_version: undefined }));
console.log('browser CSV parser: quoted comma, BOM, and blank line PASS');
