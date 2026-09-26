import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../demo.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script(?! type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)][0][1];
const ids = ['language', 'title', 'privacy-note', 'file-label', 'file', 'sample', 'results-heading', 'summary', 'output', 'rule-registry'];
const initialAttrs = {
  output: { role: 'status', 'aria-live': 'polite', tabindex: '0', 'aria-atomic': 'true', 'aria-label': '検査結果' },
  summary: { role: 'status' }
};
const elements = new Map(ids.map(id => {
  const textContent = id === 'rule-registry' ? html.match(/<script type="application\/json" id="rule-registry">([\s\S]*?)<\/script>/)[1] : '';
  const attrs = { ...(initialAttrs[id] || {}) };
  return [id, { id, textContent, listeners: {}, attrs, addEventListener(type, fn) { this.listeners[type] = fn; }, setAttribute(name, value) { this.attrs[name] = value; } }];
}));
elements.get('summary').textContent = 'ファイルを選択してください。';
const context = { document: { documentElement: { lang: 'ja' }, querySelector(selector) { return elements.get(selector.slice(1)); } }, console };
vm.runInNewContext(script, context);

assert.equal(elements.get('summary').textContent, 'ファイルを選択してください。');
elements.get('sample').listeners.click();
assert.match(elements.get('summary').textContent, /1イベント \/ 0件の問題/);
assert.match(elements.get('output').textContent, /6規則を通過/);
assert.equal(elements.get('output').attrs.role, 'status');
assert.equal(elements.get('output').attrs['aria-live'], 'polite');
elements.get('language').listeners.click();
assert.equal(context.document.documentElement.lang, 'en');
assert.match(elements.get('summary').textContent, /1 event\(s\) \/ 0 issue\(s\)/);
assert.match(elements.get('output').textContent, /Passed all 6 rules/);
console.log('browser demo smoke: sample and language toggle PASS');

// The same synthetic corpus is evaluated by the actual CLI and browser entry point.
const { spawnSync } = await import('node:child_process');
const { tmpdir } = await import('node:os');
const { join } = await import('node:path');
const corpus = JSON.parse(fs.readFileSync(new URL('../fixtures/input-contract.json', import.meta.url)));
const directory = fs.mkdtempSync(join(tmpdir(), 'care-input-contract-'));
const failures = [];
try {
  for (const item of corpus) {
    const path = join(directory, `synthetic.${item.extension}`);
    fs.writeFileSync(path, item.text);
    const cli = spawnSync(process.env.PYTHON || 'python3', [
      new URL('../care_evidence.py', import.meta.url).pathname, path, '--format', 'json'
    ], { encoding: 'utf8' });
    assert.ifError(cli.error);
    assert.equal(cli.status, item.accepted ? 0 : 2, `CLI: ${item.name}: ${cli.stderr}`);
    context.setLanguage('en');
    elements.get('sample').listeners.click(); // Make stale results observable.
    try {
      context.inspect(item.text, path);
      const accepted = /event\(s\)/.test(elements.get('summary').textContent);
      assert.equal(accepted, item.accepted, item.name);
      if (item.accepted) {
        assert.equal(vm.runInNewContext('lastResults.length', context), JSON.parse(cli.stdout).events);
      } else {
        assert.equal(elements.get('output').textContent, '');
        elements.get('language').listeners.click();
        assert.match(elements.get('summary').textContent, /読み込みエラー/);
        assert.equal(elements.get('output').textContent, '');
        elements.get('language').listeners.click();
        assert.match(elements.get('summary').textContent, /Input error:/);
      }
    } catch (error) { failures.push(`${item.name}: ${error.message}`); }
  }
} finally { fs.rmSync(directory, { recursive: true }); }
assert.deepEqual(failures, [], failures.join('\n'));
console.log(`CLI/browser input contract: ${corpus.length} synthetic cases PASS`);
