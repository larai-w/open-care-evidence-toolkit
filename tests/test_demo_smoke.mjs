import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../demo.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script(?! type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)][0][1];
const ids = ['language', 'title', 'privacy-note', 'file-label', 'file', 'sample', 'results-heading', 'summary', 'output', 'rule-registry'];
const elements = new Map(ids.map(id => [id, { id, textContent: id === 'rule-registry' ? html.match(/<script type="application\/json" id="rule-registry">([\s\S]*?)<\/script>/)[1] : '', listeners: {}, attrs: {}, addEventListener(type, fn) { this.listeners[type] = fn; }, setAttribute(name, value) { this.attrs[name] = value; }}]));
elements.get('summary').textContent = 'ファイルを選択してください。';
const context = { document: { documentElement: { lang: 'ja' }, querySelector(selector) { return elements.get(selector.slice(1)); } }, console };
vm.runInNewContext(script, context);

assert.equal(elements.get('summary').textContent, 'ファイルを選択してください。');
elements.get('sample').listeners.click();
assert.match(elements.get('summary').textContent, /1イベント \/ 0件の問題/);
assert.match(elements.get('output').textContent, /6規則を通過/);
elements.get('language').listeners.click();
assert.equal(context.document.documentElement.lang, 'en');
assert.match(elements.get('summary').textContent, /1 event\(s\) \/ 0 issue\(s\)/);
assert.match(elements.get('output').textContent, /Passed all 6 rules/);
console.log('browser demo smoke: sample and language toggle PASS');
