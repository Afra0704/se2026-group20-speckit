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
    document: {querySelectorAll: () => [form]},
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

(async () => {
  await scenario(false);
  await scenario(true);
  console.log("Notes activity handoff and failure recovery: passed");
})().catch(error => {console.error(error); process.exitCode = 1;});
