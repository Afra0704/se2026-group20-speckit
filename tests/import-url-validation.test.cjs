const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup() {
  function node() {
    return {
      events: {}, attributes: {}, hidden: true, disabled: false, textContent: '',
      addEventListener(event, handler) { this.events[event] = handler; },
      setAttribute(key, value) { this.attributes[key] = value; },
      removeAttribute(key) { delete this.attributes[key]; },
      focus() { this.focused = true; }
    };
  }
  const input = Object.assign(node(), {value: '', validity: {valueMissing: false}});
  const button = node();
  const fieldError = node();
  const operationError = node();
  const form = Object.assign(node(), {
    querySelector(selector) { return selector === 'input' ? input : button; }
  });
  const nodes = {'link-import': form, 'spreadsheet-url-error': fieldError, 'link-import-error': operationError};
  const calls = [];
  const destinations = [];
  let code;
  const context = {
    document: {
      querySelector(selector) { return selector === 'main' ? {dataset: {courseId: 'course'}} : null; },
      getElementById(id) { return nodes[id] ?? null; },
      addEventListener() {},
      querySelectorAll() { return []; }
    },
    location: {assign(url) { destinations.push(url); }},
    async api(path, body) {
      calls.push(body);
      if (code) throw Object.assign(new Error(code), {code});
      return {flow_url: '/imported'};
    },
    report(error) { throw error; }
  };
  const source = fs.readFileSync('src/guided_notes/static/import-flow.js', 'utf8').replace(/^import [^\r\n]*[\r\n]+/, '');
  vm.runInNewContext(source, context);
  return {form, input, button, fieldError, operationError, calls, destinations, setCode(value) { code = value; }};
}

test('native URL validation shows an inline error without starting an import', () => {
  const screen = setup();
  screen.input.validity.valueMissing = true;
  screen.input.events.invalid({preventDefault() {}});
  assert.match(screen.fieldError.textContent, /請輸入/);
  assert.equal(screen.input.attributes['aria-invalid'], 'true');
  assert.equal(screen.calls.length, 0);
});

test('server URL validation preserves the input and clears the error on retry', async () => {
  const screen = setup();
  screen.input.value = 'https://example.org/notes';
  screen.setCode('INVALID_SHEETS_URL');
  const submit = () => screen.form.events.submit({preventDefault() {}, target: screen.form});
  await submit();
  assert.equal(screen.input.value, 'https://example.org/notes');
  assert.equal(screen.fieldError.hidden, false);
  assert.equal(screen.button.disabled, false);
  screen.input.value = 'https://docs.google.com/spreadsheets/d/test/edit';
  screen.input.events.input();
  screen.setCode(null);
  await submit();
  assert.equal(screen.fieldError.hidden, true);
  assert.equal(screen.input.attributes['aria-invalid'], undefined);
  assert.deepEqual(screen.destinations, ['/imported']);
});

test('read failure uses an operation alert and leaves the URL unchanged', async () => {
  const screen = setup();
  screen.input.value = 'https://docs.google.com/spreadsheets/d/test/edit';
  screen.setCode('SOURCE_READ_UNAVAILABLE');
  await screen.form.events.submit({preventDefault() {}, target: screen.form});
  assert.equal(screen.operationError.hidden, false);
  assert.equal(screen.fieldError.hidden, true);
  assert.equal(screen.input.value, 'https://docs.google.com/spreadsheets/d/test/edit');
});
