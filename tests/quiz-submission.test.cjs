const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

test("same-tab reload restores an unresolved operation without auto-sending", async () => {
  const storage = new Map();
  const sent = [];
  let group = 1;
  let next = 0;
  function load() {
    const browser = {
      crypto: {randomUUID: () => String(++next)},
      sessionStorage: {getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v),
        removeItem: k => storage.delete(k)},
      document: {createElement: () => ({})},
      FormData: class { *[Symbol.iterator]() { yield ["i", " 原答案 "]; } },
    };
    vm.runInNewContext(fs.readFileSync("src/guided_notes/static/quiz-submission.js", "utf8"), browser);
    const form = {append(node) { this.retry = node; }};
    const button = {};
    const update = browser.QuizSubmission.attach(form, button, "q", () => ({activity: "a", group}),
      async (activity, body, key) => {
        sent.push({activity, body, key});
        if (sent.length === 1) throw new Error("offline");
      }, () => {}, () => {});
    update();
    return form;
  }
  const original = load();
  await original.onsubmit({preventDefault() {}});
  assert.equal(sent.length, 1);
  group = 2;
  assert.equal(load().retry.hidden, true);
  group = 1;
  const reloaded = load();
  assert.equal(reloaded.retry.hidden, false);
  assert.equal(sent.length, 1);
  await reloaded.retry.onclick();
  assert.deepEqual(JSON.stringify(sent[1]), JSON.stringify(sent[0]));
  assert.equal(storage.size, 0);
  await reloaded.onsubmit({preventDefault() {}});
  assert.notEqual(sent[2].key, sent[1].key);
});
