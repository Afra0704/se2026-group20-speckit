const main = document.querySelector("main");
const byId = (id) => document.getElementById(id);
const storageKey = `guided-notes:${main.dataset.role}`;
let current = JSON.parse(localStorage.getItem(storageKey) || "null");
let latestVersion = -1;
let phase = null;
let polling = false;
let verifiedGroup = null;
const submissionControls = new Set();

const messages = {
  AUTH_REQUIRED: "授權已失效，請重新登入、加入或恢復結果存取。",
  INVALID_LOGIN: "帳號或密碼不正確。",
  FORBIDDEN: "此操作需要該活動的授權。請確認已登入正確的教師帳號。",
  INVALID_PHASE: "目前階段不允許此操作。",
  SUBMISSION_REPLAY_CONFLICT: "這次重試的內容與原送答不同，請核對後重新提交。",
  CATALOG_UNAVAILABLE: "尚未連接講義匯入服務。",
  DISPLAY_CONTENT_UNAVAILABLE: "題目全文服務暫時無法使用，請稍後重試。",
  DISPLAY_CONTENT_MISMATCH: "題目全文與講義版本不一致，請老師核對版本後重試。",
  QUESTION_TEXT_UNAVAILABLE: "這份講義版本缺少完整題目，請重新匯入並確認文字。",
  QUIZ_UNAVAILABLE: "尚未連接搶答受理服務。",
  INVALID_CATALOG: "找不到可使用的清單版本。",
  JOIN_DENIED: "無法加入活動，請核對活動碼。",
  RECOVERY_DENIED: "此瀏覽器無法恢復這場活動的結果。",
};

async function request(path, body, key) {
  const options = {cache: "no-store", headers: {"X-Activity-Role": main.dataset.role}};
  if (body !== undefined) {
    options.method = "POST";
    Object.assign(options.headers, {"Content-Type": "application/json", "X-CSRF-Token": main.dataset.csrf});
    options.body = JSON.stringify(body);
    if (key) options.headers["Idempotency-Key"] = key;
  }
  const response = await fetch(path, options);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = new Error(data?.error || "REQUEST_FAILED");
    error.status = response.status;
    throw error;
  }
  return data;
}

function report(error) {
  byId("activity-state").textContent = messages[error.message] || "操作未完成，請重新整理或稍後重試。";
}

function setActivity(data) {
  current = {id: data.activity_id, code: data.code};
  localStorage.setItem(storageKey, JSON.stringify(current));
  latestVersion = -1;
  phase = null;
  verifiedGroup = null;
  submissionControls.clear();
  byId("questions").replaceChildren();
  byId("results").replaceChildren();
  if (data.code) byId("activity-code").textContent = `活動碼：${data.code}`;
}

function renderResults(data) {
  const container = byId("results");
  container.replaceChildren();
  if (data.status === "pending" || data.status === "unavailable") {
    container.textContent = data.status === "pending" ? "結算中" : "這場活動沒有正式結算資料。";
    return;
  }
  const answers = (entry, items) => items
    ? items.map(item => [item.subitem_label, item.answer_text].filter(v => v != null).join(" ")).join("、")
    : typeof entry === "string" ? entry : Object.values(entry || {}).join("、");
  for (const row of data.results) {
    const question = document.createElement("p");
    const label = row.winner_name ? `勝組：${row.winner_name} · ${answers(row.winner_answer, row.winner_items)}` :
      row.group_name ? `${row.group_name} · ${row.submitted ? "已作答" : "未作答"}` : "尚無勝組";
    question.textContent = `${row.display_number ?? row.question_id} · ${label}`;
    container.append(question);
    for (const group of row.groups || (row.own ? [{...row.own, group_name: "本組"}] : [])) {
      const result = document.createElement("p");
      result.textContent = `${group.group_name} · ${answers(group.answer, group.items)} · 順位 ${group.rank}`;
      container.append(result);
    }
  }
}

function render(data) {
  if (current?.id !== data.activity_id || data.phase_version < latestVersion) return;
  latestVersion = data.phase_version;
  phase = data.phase;
  verifiedGroup = data.group_id ?? null;
  const phases = {PREPARING: "準備中", LIVE: "搶答中", CLOSED: "已結束"};
  byId("activity-state").textContent = phases[phase] + (data.group_name ? ` · ${data.group_name}` : "");
  if (byId("start")) byId("start").disabled = phase !== "PREPARING";
  if (byId("close")) byId("close").disabled = phase !== "PREPARING" && phase !== "LIVE";
  if (byId("recover")) byId("recover").hidden = true;
  if (data.questions && !byId("questions").hasChildNodes()) {
    for (const question of data.questions) {
      const row = document.createElement("li");
      row.append(`題目 ${question.display_number}`);
      if (main.dataset.role === "student") {
        const form = document.createElement("form");
        for (const item of question.items) {
          const label = document.createElement("label");
          if (item.subitem_label) label.append(item.subitem_label);
          const prompt = document.createElement("p");
          prompt.className = "question-prompt";
          prompt.textContent = item.prompt_text ?? "此活動版本未包含完整題目，請老師選擇完整版本並建立新活動；文字仍缺漏時請重新匯入。";
          label.append(prompt);
          const input = document.createElement("input");
          input.name = item.item_id;
          input.required = true;
          label.append(input);
          form.append(label);
        }
        const button = document.createElement("button");
        button.textContent = "提交";
        form.append(button);
        const id = data.activity_id;
        const update = globalThis.QuizSubmission?.attach(form, button, question.question_id,
          () => current?.id === id && verifiedGroup !== null
            ? {activity: id, group: verifiedGroup, live: phase === "LIVE"} : null,
          (activity, body, key) => request(`/activities/${encodeURIComponent(activity)}/submissions`, body, key),
          () => { byId("results").textContent = "答案已受理"; }, report);
        if (update) submissionControls.add(update);
        row.append(form);
      }
      byId("questions").append(row);
    }
  }
  for (const button of byId("questions").querySelectorAll("input, button")) button.disabled = phase !== "LIVE";
  for (const update of submissionControls) update();
}

async function refresh() {
  if (polling || !current) return;
  const id = current.id;
  polling = true;
  try {
    render(await request(`/activities/${id}/state`));
    if (current?.id === id && (phase === "CLOSED" || (phase === "LIVE" && main.dataset.role === "teacher"))) {
      const data = await request(`/activities/${id}/results`);
      if (current?.id === id) renderResults(data);
    }
  } catch (error) {
    if (current?.id !== id) return;
    verifiedGroup = null;
    if (error.message === "AUTH_REQUIRED" && byId("recover")) byId("recover").hidden = false;
    for (const field of byId("questions").querySelectorAll("input, button")) field.disabled = true;
    for (const update of submissionControls) update();
    report(error);
  } finally {
    polling = false;
  }
}

function bind(id, handler, event = "submit") {
  byId(id)?.addEventListener(event, async (action) => {
    action.preventDefault();
    try {
      await handler(action.currentTarget);
    } catch (error) {
      report(error);
    }
  });
}

const values = (form) => Object.fromEntries(new FormData(form));
bind("login", async (form) => {
  await request("/teacher/session", values(form));
  form.reset();
  byId("activity-state").textContent = "已登入";
  await refresh();
});
bind("create", async (form) => {
  const data = values(form);
  data.import_version = Number(data.import_version);
  setActivity(await request("/activities", data));
  await refresh();
});
bind("join", async (form) => {
  const data = await request("/activity-memberships", values(form));
  setActivity(data);
  render(data);
});
for (const action of ["start", "close", "recover"]) {
  bind(action, async () => {
    const endpoint = action === "recover" ? "result-access" : action;
    const data = await request(`/activities/${current.id}/${endpoint}`, {});
    if (data) render(data);
    await refresh();
  }, "click");
}
if (current?.code && byId("activity-code")) byId("activity-code").textContent = `活動碼：${current.code}`;
window.addEventListener("online", refresh);
window.addEventListener("pageshow", refresh);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refresh();
});
setInterval(refresh, 1000);
refresh();
