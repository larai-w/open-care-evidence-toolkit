import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../demo.html', import.meta.url), 'utf8');
const start = html.indexOf('    function parseCsv');
const end = html.indexOf('    function inspect', start);
assert.ok(start >= 0 && end > start, 'parseCsv function should be present');
const context = {};
vm.runInNewContext(`this.parseCsv = (${html.slice(start, end).replace(/^\s*function parseCsv/, 'function parseCsv')});`, context);

const rows = context.parseCsv('\uFEFFevent_id,observation,status\r\n"evt-1","水分, 食事",observed\r\n\r\n');
assert.equal(JSON.stringify(rows), JSON.stringify([{ event_id: 'evt-1', observation: '水分, 食事', status: 'observed', corrects: [] }]));
console.log('browser CSV parser: quoted comma, BOM, and blank line PASS');
