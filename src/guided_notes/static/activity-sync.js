const main = document.querySelector("main");
const byId = (id) => document.getElementById(id);
const storageKey = `guided-notes:${main.dataset.role}`;
let current = JSON.parse(localStorage.getItem(storageKey) || "null");
let latestVersion = -1;
let phase = null;
let polling = false;

const messages = {
  AUTH_REQUIRED: "授權已失效，請重新登入、加入或恢復結果存取。",
  INVALID_LOGIN: "帳號或密碼不正確。",
  FORBIDDEN: "此操作需要該活動的授權。請確認已登入正確的教師帳號。",
  INVALID_PHASE: "目前階段不允許此操作。",
  CATALOG_UNAVAILABLE: "尚未連接講義匯入服務。",
  QUIZ_UNAVAILABLE: "尚未連接搶答受理服務。",
  INVALID_CATALOG: "找不到可使用的清單版本。",
  JOIN_DENIED: "無法加入活動，請核對活動碼。",
  RECOVERY_DENIED: "此瀏覽器無法恢復這場活動的結果。",
};

async function request(path, body) {
  const options = {cache: "no-store", headers: {"X-Activity-Role": main.dataset.role}};
  if (body !== undefined) {
    options.method = "POST";
    Object.assign(options.headers, {"Content-Type": "application/json", "X-CSRF-Token": main.dataset.csrf});
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    throw new Error(data?.error || "REQUEST_FAILED");
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
  byId("questions").replaceChildren();
  byId("results").replaceChildren();
  if (data.code) byId("activity-code").textContent = `活動碼：${data.code}`;
}

function renderResults(data) {
  const container = byId("results");
  container.replaceChildren();
  if (data.status === "pending") {
    container.textContent = "結算中";
    return;
  }
  const answers = (entry) => typeof entry === "string" ? entry : Object.values(entry || {}).join("、");
  for (const row of data.results) {
    const question = document.createElement("p");
    const label = row.winner_name ? `勝組：${row.winner_name} · ${answers(row.winner_answer)}` :
      row.group_name ? `${row.group_name} · ${row.submitted ? "已作答" : "未作答"}` : "尚無勝組";
    question.textContent = `${row.question_id} · ${label}`;
    container.append(question);
    for (const group of row.groups || (row.own ? [{...row.own, group_name: "本組"}] : [])) {
      const result = document.createElement("p");
      result.textContent = `${group.group_name} · ${answers(group.answer)} · 順位 ${group.rank}`;
      container.append(result);
    }
  }
}

function render(data) {
  if (current?.id !== data.activity_id || data.phase_version < latestVersion) return;
  latestVersion = data.phase_version;
  phase = data.phase;
  const phases = {PREPARING: "準備中", LIVE: "搶答中", CLOSED: "已結束"};
  byId("activity-state").textContent = phases[phase] + (data.group_name ? ` · ${data.group_name}` : "");
  if (byId("start")) byId("start").disabled = phase !== "PREPARING";
  if (byId("close")) byId("close").disabled = phase !== "LIVE";
  if (byId("recover")) byId("recover").hidden = true;
  if (data.questions && !byId("questions").hasChildNodes()) {
    for (const question of data.questions) {
      const row = document.createElement("li");
      row.append(`題目 ${question.display_number}`);
      if (main.dataset.role === "student") {
        const form = document.createElement("form");
        for (const item of question.items) {
          const label = document.createElement("label");
          label.append(item.subitem_label || "答案");
          const input = document.createElement("input");
          input.name = item.item_id;
          input.required = true;
          label.append(input);
          form.append(label);
        }
        const button = document.createElement("button");
        button.textContent = "提交";
        form.append(button);
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          try {
            const items = [...new FormData(form)].map(([item_id, answer_text]) => ({item_id, answer_text}));
            await request(`/activities/${current.id}/submissions`, {question_id: question.question_id, items});
            byId("results").textContent = "答案已受理";
          } catch (error) {
            report(error);
          }
        });
        row.append(form);
      }
      byId("questions").append(row);
    }
  }
  for (const button of byId("questions").querySelectorAll("button")) button.disabled = phase !== "LIVE";
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
    if (error.message === "AUTH_REQUIRED" && byId("recover")) byId("recover").hidden = false;
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
