const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

test("a copied operation scope cannot retry or clear the original document's pending answer", async () => {
  const storage = new Map();
  const sent = [];
  const browser = {
    crypto: {randomUUID: () => "original-key"},
    sessionStorage: {getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v),
      removeItem: k => storage.delete(k), get length() { return storage.size; },
      key: i => [...storage.keys()][i]},
    document: {createElement: () => ({})},
    FormData: class { *[Symbol.iterator]() { yield ["i", "original answer"]; } },
  };
  vm.runInNewContext(fs.readFileSync("src/guided_notes/static/quiz-submission.js", "utf8"), browser);
  const quiz = browser.QuizSubmission;
  function attach(operationScope) {
    const form = {append(node) { this.retry = node; }};
    const button = {};
    const update = quiz.attach(form, button, "q", () => ({room: "r", activity: "a", group: 1, operationScope}),
      async (activity, body, key) => {
        sent.push({activity, body, key});
        if (sent.length === 1) throw new Error("unknown outcome");
      }, () => {}, () => {});
    update();
    return {form, button};
  }
  const original = attach("original");
  await original.form.onsubmit({preventDefault() {}});
  assert.equal(original.button.disabled, true);
  assert.equal(quiz.hasPending("r", "original"), true);
  const copy = attach("copy");
  assert.equal(copy.form.retry.hidden, true);
  quiz.clearScope("r", "copy");
  assert.equal(sent.length, 1);
  await attach("original").form.retry.onclick();
  assert.deepEqual(sent[1], sent[0]);
  assert.equal(storage.size, 0);
});

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

for (const oldStatus of [201, 409]) {
  test(`late ${oldStatus} from a replaced form preserves the newer operation for retry`, async () => {
    const storage = new Map();
    const sent = [];
    let next = 0;
    const browser = {
      crypto: {randomUUID: () => String(++next)},
      sessionStorage: {getItem: k => storage.get(k), setItem: (k, v) => storage.set(k, v),
        removeItem: k => storage.delete(k)},
      document: {createElement: () => ({})},
      FormData: class {
        constructor(form) { this.answer = form.answer; }
        *[Symbol.iterator]() { yield ["i", this.answer]; }
      },
    };
    vm.runInNewContext(fs.readFileSync("src/guided_notes/static/quiz-submission.js", "utf8"), browser);

    function attach(answer) {
      const form = {answer, append(node) { this.retry = node; }};
      browser.QuizSubmission.attach(form, {}, "q", () => ({room: "r", activity: "a", group: 1}),
        (activity, body, key) => new Promise((resolve, reject) => sent.push({activity, body, key, resolve, reject})),
        () => {}, () => {});
      return form;
    }

    const event = {preventDefault() {}};
    const first = attach("舊答案").onsubmit(event);
    const replacement = attach(" 新答案\n");
    const second = replacement.onsubmit(event);
    assert.notEqual(sent[0].key, sent[1].key);
    if (oldStatus === 201) sent[0].resolve();
    else sent[0].reject(Object.assign(new Error("rejected"), {status: oldStatus}));
    await first;
    sent[1].reject(new Error("response lost"));
    await second;

    assert.equal(storage.size, 1);
    assert.equal(replacement.retry.hidden, false);
    const retry = replacement.retry.onclick();
    assert.equal(sent[2].key, sent[1].key);
    assert.deepEqual(sent[2].body, sent[1].body);
    assert.equal(next, 2);
    sent[2].resolve();
    await retry;
    assert.equal(storage.size, 0);
  });
}
