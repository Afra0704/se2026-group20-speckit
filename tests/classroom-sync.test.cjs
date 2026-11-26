const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const nodes = Object.fromEntries(["state", "message", "questions", "recover", "results"].map((id) => [
  id, {textContent: "", replaceChildren() {}, addEventListener() {}, querySelectorAll: () => []},
]));
const responses = [];
nodes["feedback-dialog"] = {open: false, showModal() { this.open = true; }};
nodes["feedback-title"] = {};
nodes["feedback-message"] = {};
nodes["login-status"] = {dataset: {}};
const context = vm.createContext({
  document: {
    querySelector: () => ({dataset: {role: "student"}, querySelectorAll: () => []}),
    getElementById: (id) => nodes[id],
    addEventListener() {},
  },
  window: {addEventListener() {}},
  localStorage: {
    getItem() { throw new Error("Storage blocked"); },
    setItem() { throw new Error("Storage blocked"); },
  },
  setInterval() {},
  fetch: async (path) => ({ok: true, status: 200, headers: {get: () => "application/json"},
    json: async () => path.endsWith("/results") ? {activities: []} : responses.shift()}),
});

vm.runInContext(fs.readFileSync("src/guided_notes/static/classroom.js", "utf8"), context);
const state = (version, id, phase) => ({
  classroom_id: "room", classroom_state: "OPEN", state_version: version,
  activity: {activity_id: id, phase, questions: []},
});

(async () => {
  vm.runInContext('setRoom("room")', context);
  responses.push(state(1, "first", "LIVE"), state(3, "second", "LIVE"), state(2, "first", "CLOSED"));
  await vm.runInContext("refresh()", context);
  assert.equal(vm.runInContext("activeId", context), "first");
  await vm.runInContext("refresh()", context);
  await vm.runInContext("refresh()", context);
  assert.equal(vm.runInContext("activeId", context), "second");
  assert.equal(nodes.state.textContent, "搶答中");
  vm.runInContext(`setLoginStatus(true); showFeedback("登入未完成",
    errorText(Object.assign(new Error("TOO_MANY_ATTEMPTS"), {retryAfter: 32})))`, context);
  assert.equal(nodes["login-status"].textContent, "已登入");
  assert.equal(nodes["feedback-dialog"].open, true);
  assert.match(nodes["feedback-message"].textContent, /32 秒/);
  console.log("Classroom switch and stale response: passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
