const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function screen(status, respond) {
  const buttons = [{disabled: false}];
  const flow = {dataset: {flowId: 'flow', status}, querySelectorAll: () => buttons};
  const nodes = {'import-flow': flow};
  for (const id of ['read-source', 'retry-import']) {
    nodes[id] = {addEventListener(event, handler) { this[event] = handler; }};
  }
  const calls = [], errors = [];
  let reloads = 0;
  const context = vm.createContext({
    document: {
      querySelector: selector => selector === 'main' ? {dataset: {courseId: 'course'}} : null,
      getElementById: id => nodes[id], addEventListener() {}, querySelectorAll: () => [],
    },
    location: {reload() { reloads++; }},
    api: async (path, body) => { calls.push({path, body}); return respond(path, body); },
    report: error => errors.push(error),
  });
  vm.runInContext(fs.readFileSync('src/guided_notes/static/import-flow.js', 'utf8')
    .replace(/^import [^\r\n]*[\r\n]+/, ''), context);
  return {nodes, buttons, calls, errors, get reloads() { return reloads; },
    flush: () => new Promise(setImmediate)};
}

for (const code of ['SOURCE_READ_FORBIDDEN', 'SOURCE_READ_UNAVAILABLE']) {
  test(`${code} opens the failed flow and retries through the retry endpoint`, async () => {
    const first = screen('awaiting_sheets_auth', async (path, body) => {
      if (body !== undefined) throw Object.assign(new Error(code), {code});
      return {status: 'failed', error_code: code};
    });
    first.nodes['read-source'].click();
    await first.flush();
    assert.equal(first.reloads, 1, 'render the failed page without a manual refresh');
    assert.equal(first.buttons[0].disabled, false);
    assert.deepEqual(first.calls.map(call => call.path), [
      '/teacher/workspace/imports/flow/read', '/teacher/workspace/imports/flow',
    ]);

    // The failed page exposes retry-import instead of the stale read-source action.
    const retry = screen('failed', async () => ({status: 'worksheets_ready'}));
    await retry.nodes['retry-import'].click();
    assert.deepEqual(retry.calls.map(call => call.path), ['/teacher/workspace/imports/flow/retry']);
    assert.equal(retry.reloads, 1);
    assert.equal(retry.errors.length, 0);
  });
}

test('failed state lookup preserves the original read error and restores the button', async () => {
  const original = Object.assign(new Error('Read unavailable'), {code: 'SOURCE_READ_UNAVAILABLE'});
  const page = screen('awaiting_sheets_auth', async (path, body) => {
    if (body !== undefined) throw original;
    throw new Error('Offline');
  });
  page.nodes['read-source'].click();
  await page.flush();
  assert.equal(page.reloads, 0);
  assert.equal(page.errors[0], original);
  assert.equal(page.buttons[0].disabled, false);
});
