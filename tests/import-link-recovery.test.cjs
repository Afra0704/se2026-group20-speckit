const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function screen(resume = false) {
  const element = () => ({hidden: true, disabled: false, textContent: '', attributes: {}, events: {},
    addEventListener(name, handler) { this.events[name] = handler; },
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; }, focus() {},
  });
  const input = Object.assign(element(), {value: 'https://docs.google.com/spreadsheets/d/test/edit'});
  const button = element(), field = element(), operation = element();
  const form = Object.assign(element(), {dataset: resume ? {flowUrl: '/flow/1'} : {},
    querySelector: name => name === 'input' ? input : button});
  const returnTo = {value: ''};
  const reconnect = Object.assign(element(), {querySelector: () => returnTo});
  const nodes = {'link-import': form, 'spreadsheet-url-error': field, 'link-import-error': operation,
    'link-import-reconnect': reconnect};
  const calls = [], destinations = [];
  let status = resume ? 'failed' : 'source_pending', failure = null, created = 0, loseResponse = false, authorization = false;
  const context = {
    document: {querySelector: name => name === 'main' ? {dataset: {courseId: 'course'}} : null,
      getElementById: id => nodes[id], querySelectorAll: () => [], addEventListener() {}},
    location: {assign: url => destinations.push(url)},
    report: error => { throw error; },
    async api(path, body) {
      calls.push(path);
      if (path.endsWith('/imports')) {
        created++;
        status = 'source_pending';
        return {flow_url: '/flow/' + created, status};
      }
      if (body === undefined) return {status};
      if (authorization) return {status: 'awaiting_sheets_auth', needs_authorization: 'sheets'};
      if (failure) {
        status = 'failed';
        throw Object.assign(new Error(failure === 'SOURCE_READ_FORBIDDEN' ? '請確認分享權限。' : '暫時無法讀取，請稍後重試。'), {code: failure});
      }
      status = 'worksheets_ready';
      if (loseResponse) { loseResponse = false; throw new Error('Connection lost'); }
      return {status};
    },
  };
  vm.runInNewContext(fs.readFileSync('src/guided_notes/static/import-flow.js', 'utf8')
    .replace(/^import [^\r\n]*[\r\n]+/, ''), context);
  return {input, button, field, operation, reconnect, returnTo, calls, destinations,
    fail(code) { failure = code; }, recover() { failure = null; },
    loseResponse() { loseResponse = true; },
    requireAuthorization() { authorization = true; },
    submit: () => form.events.submit({preventDefault() {}})};
}

test('revoked Sheets access exposes explicit reconnect for the same flow without automatic OAuth', async () => {
  const page = screen();
  page.fail('GOOGLE_REAUTH_REQUIRED');
  await page.submit();
  assert.equal(page.reconnect.hidden, false);
  assert.equal(page.returnTo.value, '/flow/1');
  assert.equal(page.destinations.length, 0);
  page.input.events.input();
  assert.equal(page.reconnect.hidden, true, 'editing the URL must hide the previous flow reconnect action');
});

test('an obsolete read error cannot offer reconnect for the previous link', async () => {
  const page = screen();
  page.fail('GOOGLE_REAUTH_REQUIRED');
  const pending = page.submit();
  page.input.value = 'https://docs.google.com/spreadsheets/d/other/edit';
  page.input.events.input();
  await pending;
  assert.equal(page.reconnect.hidden, true);
  assert.equal(page.operation.hidden, true);
  assert.equal(page.button.disabled, false);
});

for (const code of ['SOURCE_READ_FORBIDDEN', 'SOURCE_READ_UNAVAILABLE']) {
  test(`${code} stays beside the link; the same Read button retries after recovery`, async () => {
    const page = screen();
    page.fail(code);
    await page.submit();
    assert.equal(page.destinations.length, 0);
    assert.equal(page.operation.hidden, false);
    assert.equal(page.field.hidden, true, 'source errors must not mark the URL invalid');
    assert.equal(page.input.value, 'https://docs.google.com/spreadsheets/d/test/edit');
    assert.equal(page.button.disabled, false);
    page.recover();
    await page.submit();
    assert.deepEqual(page.calls, ['/teacher/workspace/courses/course/imports', '/flow/1/read', '/flow/1', '/flow/1/retry']);
    assert.deepEqual(page.destinations, ['/flow/1']);
    assert.equal(page.operation.hidden, true);
  });
}

test('editing a failed link creates a new flow without reusing the old source', async () => {
  const page = screen();
  page.fail('SOURCE_READ_FORBIDDEN');
  await page.submit();
  page.input.value = 'https://docs.google.com/spreadsheets/d/other/edit';
  page.recover();
  await page.submit();
  assert.deepEqual(page.destinations, ['/flow/2']);
  assert.equal(page.calls.includes('/flow/1/retry'), false);
});

test('a read whose success response was lost resumes its ready flow without reading twice', async () => {
  const page = screen();
  page.loseResponse();
  await page.submit();
  assert.equal(page.operation.hidden, false);
  await page.submit();
  assert.deepEqual(page.calls, ['/teacher/workspace/courses/course/imports', '/flow/1/read', '/flow/1']);
  assert.deepEqual(page.destinations, ['/flow/1']);
});

test('the failed page returned after authorization reuses its original flow', async () => {
  const page = screen(true);
  await page.submit();
  assert.deepEqual(page.calls, ['/flow/1', '/flow/1/retry']);
  assert.deepEqual(page.destinations, ['/flow/1']);
});

test('missing Sheets authorization continues to the existing authorization page', async () => {
  const page = screen();
  page.requireAuthorization();
  await page.submit();
  assert.deepEqual(page.destinations, ['/flow/1']);
  assert.equal(page.operation.hidden, true);
});
