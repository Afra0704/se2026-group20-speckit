const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

test("both result clients preserve item labels and literal answers", () => {
  const results = [{question_id: "opaque", display_number: "2", winner_name: "A",
    winner_items: [{item_id: "i", subitem_label: "(1)", answer_text: "<b>answer</b>"}],
    own: {rank: 2, items: [{item_id: "i", subitem_label: "(1)", answer_text: " B "}]}}];
  for (const file of ["classroom.js", "activity-sync.js"]) {
    const output = [];
    const nodes = {results: {replaceChildren() {}, append: (item) => output.push(item.textContent)}};
    const context = {results, window: {addEventListener() {}}, setInterval() {},
      localStorage: {getItem: () => null},
      document: {querySelector: () => ({dataset: {role: "student"}}),
        getElementById: id => nodes[id], addEventListener() {}, createElement: () => ({})}};
    const call = file === "classroom.js" ? "describeResults(results)" :
      "renderResults({status:'settled',results});";
    const value = vm.runInNewContext(fs.readFileSync("src/guided_notes/static/" + file, "utf8") + "\n" + call, context);
    const rendered = value || output.join(" ");
    assert.match(rendered, /2.*\(1\).*<b>answer<\/b>/);
    assert.match(rendered, /\(1\).* B /);
  }
});

test("a delayed classroom result cannot replace feedback after the activity changes", async () => {
  const nodes = {message: {textContent: ""}};
  let resolveResult;
  const browser = vm.createContext({
    document: {querySelector: () => ({dataset: {role: "student"}}),
      getElementById: id => nodes[id], addEventListener() {}},
    localStorage: {getItem: () => null, setItem() {}},
    window: {addEventListener() {}}, setInterval() {},
    fetch: async () => new Promise(resolve => { resolveResult = resolve; }),
  });
  vm.runInContext(fs.readFileSync("src/guided_notes/static/classroom.js", "utf8"), browser);
  const result = vm.runInContext(`
    setRoom("r");
    showQuestions({activity_id:"first",phase:"CLOSED"},true);
    selectedResult={id:"first",context:selection,currentActivity:activeId};
    refreshResult();
  `, browser);
  vm.runInContext('showQuestions({activity_id:"second",phase:"LIVE"},true); note("second");', browser);
  resolveResult({ok: true, headers: {get: () => "application/json"},
    json: async () => ({status: "settled", results: [{question_id: "old", winner_name: "A"}]})});
  await result;
  assert.equal(nodes.message.textContent, "second");
});
