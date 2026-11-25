const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

async function scenario(fail) {
  let handler;
  const button = {disabled: false};
  const feedback = {textContent: ""};
  const form = {
    addEventListener(event, callback) {handler = callback;},
    querySelector(selector) {return selector === "button" ? button : feedback;}
  };
  const saved = [];
  const locations = [];
  const fields = {csrf_token: "fixture-csrf", import_id: "fixture-catalog", import_version: "2"};
  const browser = {
    document: {querySelectorAll: selector => selector === "form[data-activity-form]" ? [form] : []},
    FormData: class {get(key) {return fields[key];}},
    fetch: async (path, options) => {
      assert.equal(path, "/activities");
      assert.equal(options.headers["X-CSRFToken"], "fixture-csrf");
      assert.deepEqual(JSON.parse(options.body), {import_id: "fixture-catalog", import_version: 2});
      if (fail) throw new Error("network failure");
      return {ok: true, json: async () => ({activity_id: "activity", code: "code"})};
    },
    localStorage: {setItem: (...args) => saved.push(args)},
    window: {location: {assign: (url) => locations.push(url)}}
  };
  vm.runInNewContext(fs.readFileSync("src/guided_notes/notes/static/notes.js", "utf8"), browser);
  await handler({preventDefault() {}});
  if (fail) {
    assert.equal(button.disabled, false);
    assert.match(feedback.textContent, /未完成/);
    assert.equal(saved.length, 0);
  } else {
    assert.equal(button.disabled, true);
    assert.equal(saved[0][0], "guided-notes:teacher");
    assert.deepEqual(JSON.parse(saved[0][1]), {id: "activity", code: "code"});
    assert.deepEqual(locations, ["/teacher"]);
  }
}

function namingScenario() {
  let mode = "source";
  let change;
  const input = {disabled:false,required:false};
  const wrapper = {hidden:false};
  const group = {
    addEventListener(event, callback) {change = callback;},
    querySelector(selector) {
      if (selector === "input[name='custom_title']") return input;
      if (selector === "[data-custom-name]") return wrapper;
      return {value:mode};
    }
  };
  const browser = {document:{querySelectorAll:selector => selector === "[data-name-options]" ? [group] : []}};
  vm.runInNewContext(fs.readFileSync("src/guided_notes/notes/static/notes.js", "utf8"),browser);
  assert.equal(input.disabled,true);
  assert.equal(wrapper.hidden,true);
  mode = "custom";
  change();
  assert.equal(input.disabled,false);
  assert.equal(input.required,true);
  assert.equal(wrapper.hidden,false);
  mode = "source";
  change();
  assert.equal(input.disabled,true);
  assert.equal(input.required,false);
}

function previewActivityScenario(stored, initial, expected) {
  const input = {value: initial};
  const browser = {
    document: {querySelectorAll: selector => selector === "[data-current-activity]" ? [input] : []},
    localStorage: {getItem: () => stored},
  };
  vm.runInNewContext(fs.readFileSync("src/guided_notes/notes/static/notes.js", "utf8"), browser);
  assert.equal(input.value, expected);
}

function writebackConfirmationScenario() {
  const button = {disabled:false};
  let submit;
  const form = {querySelector:() => button, addEventListener:(event, handler) => {submit=handler;}};
  const browser = {document:{querySelectorAll:selector => selector === "form[data-writeback-confirm]" ? [form] : []}};
  vm.runInNewContext(fs.readFileSync("src/guided_notes/notes/static/notes.js", "utf8"), browser);
  submit();
  assert.equal(button.disabled,true);
  assert.match(button.textContent,/回讀/);
}

(async () => {
  namingScenario();
  writebackConfirmationScenario();
  previewActivityScenario('{"id":"last-activity"}', "", "last-activity");
  previewActivityScenario('{"id":"last-activity"}', "typed-activity", "typed-activity");
  previewActivityScenario("broken-json", "", "");
  previewActivityScenario('{"id":123}', "", "");
  await scenario(false);
  await scenario(true);
  console.log("Notes naming, preview activity selection, activity handoff and failure recovery: passed");
})().catch(error => {console.error(error); process.exitCode = 1;});
