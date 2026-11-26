const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const nodes = {
  "activity-state": {},
  questions: {replaceChildren() {}, querySelectorAll: () => [submit]},
  results: {replaceChildren() {}},
  close: {addEventListener() {}, disabled: true},
};
const submit = {disabled: true};
const browser = {
  localStorage: {getItem: () => null, setItem() {}},
  document: {
    querySelector: () => ({dataset: {role: "student"}}),
    getElementById: (id) => nodes[id],
    addEventListener() {},
  },
  window: {addEventListener() {}},
  setInterval() {},
};
vm.runInNewContext(
  fs.readFileSync("src/guided_notes/static/activity-sync.js", "utf8") + `
    setActivity({activity_id: "activity"});
    render({activity_id: "activity", phase: "PREPARING", phase_version: 0});
    if (byId("close").disabled) throw new Error("PREPARING should allow the teacher to close");
    render({activity_id: "activity", phase: "LIVE", phase_version: 1});
    if (byId("close").disabled) throw new Error("LIVE should allow the teacher to close");
    if (byId("questions").querySelectorAll("button")[0].disabled) throw new Error("LIVE should accept input");
    render({activity_id: "activity", phase: "CLOSED", phase_version: 2});
    render({activity_id: "activity", phase: "LIVE", phase_version: 1});
  `,
  browser,
);
assert.equal(nodes["activity-state"].textContent, "已結束");
assert.equal(submit.disabled, true);
assert.equal(nodes.close.disabled, true);
console.log("Stale phase response: passed");
