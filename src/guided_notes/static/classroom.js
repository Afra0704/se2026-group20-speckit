const main = document.querySelector("main");
const role = main.dataset.role;
const byId = (id) => document.getElementById(id);
const roomKey = `classroom-004:${role}`;
const store = {
  get() {
    try { return localStorage.getItem(roomKey); } catch { return null; }
  },
  set(id) {
    try {
      if (id) localStorage.setItem(roomKey, id);
      else localStorage.removeItem(roomKey);
    } catch {
      // The active classroom can still be tracked in this tab.
    }
  },
};
let room = main.dataset.classroomId || store.get();
let version = -1;
let activeId = null;
let polling = false;
let selection = 0;
let courseSelection = 0;
let historyRequest = 0;
let historyNeedsRefresh = true;
let roomOpen = false;
let stateUnfinished = true;
let historyUnfinished = true;
let creatingActivity = false;
let verifiedGroup = null;
let activePhase = null;
let selectedResult = null;
let studentHistoryVersion = -1;
const submissionControls = new Set();

function updateCreateAvailability() {
  const button = byId("create-activity")?.querySelector("button");
  if (button) button.disabled = !room || !roomOpen || historyNeedsRefresh ||
    stateUnfinished || historyUnfinished || creatingActivity;
}

function url(id) {
  return encodeURIComponent(id);
}

async function api(path, body, key) {
  const headers = {"X-Activity-Role": role};
  const options = {headers, cache: "no-store"};
  if (body !== undefined) {
    Object.assign(headers, {"Content-Type": "application/json", "X-CSRF-Token": main.dataset.csrf});
    Object.assign(options, {method: "POST", body: JSON.stringify(body)});
    if (key) headers["Idempotency-Key"] = key;
  }
  const response = await fetch(path, options);
  const json = response.headers.get("Content-Type")?.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const error = new Error(json?.error || "REQUEST_FAILED");
    error.status = response.status;
    error.retryAfter = json?.retry_after ?? Number(response.headers.get("Retry-After"));
    throw error;
  }
  return json;
}

function note(text) {
  byId("message").textContent = text;
}

const errors = {
  AUTH_REQUIRED: "請重新登入或加入。關課後可在原瀏覽器恢復結果。",
  INVALID_LOGIN: "帳號或密碼不正確。",
  INVALID_CSRF: "頁面驗證已過期，請重新整理後再試。",
  CATALOG_UNAVAILABLE: "課程講義服務尚未接入。",
  DISPLAY_CONTENT_UNAVAILABLE: "題目全文服務暫時無法使用，請稍後重試。",
  DISPLAY_CONTENT_MISMATCH: "題目全文與講義版本不一致，請老師核對版本後重試。",
  QUESTION_TEXT_UNAVAILABLE: "這份講義版本缺少完整題目，請重新匯入並確認文字。",
  CLASSROOM_CODE_UNAVAILABLE: "暫時無法產生課堂碼，請再試一次。",
  CLASSROOM_CLOSED: "課堂已結束。",
  ACTIVITY_IN_PROGRESS: "請先結束目前活動，再建立下一活動。",
  INVALID_PHASE: "活動已切換或已結束，這筆操作未受理。",
  SUBMISSION_REPLAY_CONFLICT: "這次重試的內容與原送答不同，請核對後重新提交。",
  QUIZ_UNAVAILABLE: "正式搶答受理服務尚未接入。",
};

function report(error) {
  note(errorText(error));
}

function errorText(error) {
  if (error.message === "TOO_MANY_ATTEMPTS") {
    const seconds = Number(error.retryAfter);
    return `嘗試次數過多，請等待 ${seconds > 0 ? seconds : 60} 秒再試。`;
  }
  return errors[error.message] || error.message || "操作未完成";
}

function showFeedback(title, text) {
  note(text);
  const dialog = byId("feedback-dialog");
  if (typeof dialog?.showModal !== "function") return;
  byId("feedback-title").textContent = title;
  byId("feedback-message").textContent = text;
  if (!dialog.open) dialog.showModal();
}

function setLoginStatus(active) {
  const status = byId("login-status");
  if (!status) return;
  status.dataset.active = String(active);
  status.textContent = active ? "已登入" : "尚未登入";
}

function form(id, run, onError = report) {
  const target = byId(id);
  let submitting = false;
  target?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = target.querySelector("button");
    if (submitting || (id === "create-activity" && button?.disabled)) return;
    submitting = true;
    if (id === "create-activity") creatingActivity = true;
    if (button) button.disabled = true;
    try {
      await run(Object.fromEntries(new FormData(target)));
    } catch (error) {
      onError(error);
    } finally {
      submitting = false;
      if (id === "create-activity") {
        creatingActivity = false;
        updateCreateAvailability();
      } else if (button) button.disabled = false;
    }
  });
}

function option(select, value, text) {
  select.append(new Option(text, value));
}

async function courses() {
  const select = byId("courses");
  const previous = select.value;
  const data = await api("/teacher/courses");
  select.replaceChildren();
  option(select, "", "請選擇課程");
  for (const item of data.courses) option(select, item.course_id, item.title);
  if (data.courses.some((item) => item.course_id === previous)) select.value = previous;
}

async function selectCourse() {
  const id = byId("courses").value;
  const chosen = ++courseSelection;
  setRoom(null);
  for (const field of ["classrooms", "catalogs"]) byId(field).replaceChildren();
  byId("code").textContent = "";
  byId("notes").hidden = !id;
  if (!id) return;
  byId("notes").href = `/teacher/notes/courses/${url(id)}`;
  const data = await api(`/teacher/courses/${url(id)}/classrooms`);
  if (chosen !== courseSelection) return;
  option(byId("classrooms"), "", "請選擇課堂");
  for (const item of data.classrooms) {
    option(byId("classrooms"), item.classroom_id, `${item.title}（${item.state === "OPEN" ? "進行中" : "已結束"}）`);
    byId("classrooms").lastElementChild.dataset.code = item.code;
  }
  let catalog;
  try {
    catalog = await api(`/teacher/courses/${url(id)}/catalogs`);
  } catch (error) {
    if (chosen === courseSelection) report(error);
    return;
  }
  if (chosen !== courseSelection) return;
  for (const lecture of catalog.lectures) {
    for (const item of lecture.versions) {
      option(byId("catalogs"), JSON.stringify([lecture.import_id, item.import_version]),
        `${item.title} · 版本 ${item.import_version}`);
    }
  }
}

function setRoom(id) {
  room = id;
  selection++;
  if (!main.dataset.classroomId) store.set(id);
  version = -1;
  activeId = null;
  selectedResult = null;
  studentHistoryVersion = -1;
  verifiedGroup = null;
  submissionControls.clear();
  historyRequest++;
  historyNeedsRefresh = true;
  roomOpen = false;
  stateUnfinished = true;
  historyUnfinished = true;
  updateCreateAvailability();
  for (const field of ["questions", "activities", "results", "state"]) byId(field)?.replaceChildren();
  if (byId("close-room")) byId("close-room").disabled = true;
}

async function activityList(id) {
  const request = ++historyRequest;
  const context = selection;
  const stateVersion = version;
  historyNeedsRefresh = true;
  updateCreateAvailability();
  const data = await api(`/teacher/classrooms/${url(id)}/activities`);
  if (room !== id || context !== selection || request !== historyRequest || stateVersion !== version) return;
  historyUnfinished = data.activities.some((activity) => activity.phase !== "CLOSED");
  const list = byId("activities");
  list.replaceChildren();
  for (const activity of data.activities) {
    const line = document.createElement("li");
    const phase = {PREPARING: "準備中", LIVE: "搶答中", CLOSED: "已結束"};
    line.textContent = `${activity.title} · ${phase[activity.phase]} · ${activity.created_at}`;
    if (activity.phase !== "CLOSED" && !byId("close-room").disabled) {
      for (const action of activity.phase === "PREPARING" ? ["start", "finish"] : ["finish"]) {
        const button = document.createElement("button");
        button.textContent = action === "start" ? "開啟搶答" : "結束活動";
        button.onclick = async () => {
          if (context !== selection || room !== id || button.disabled) return;
          button.disabled = true;
          try {
            await api(`/teacher/classrooms/${url(id)}/activities/${url(activity.activity_id)}/${action}`, {});
            historyNeedsRefresh = true;
            await refresh();
          } catch (error) {
            if (context !== selection) return;
            historyNeedsRefresh = true;
            report(error);
          }
        };
        line.append(button);
      }
    }
    if (activity.phase === "CLOSED" || activity.phase === "LIVE") addResultButton(line, activity);
    if (main.dataset.classroomId) {
      const historyLink = document.createElement("a");
      historyLink.href = `/teacher/workspace/activities/${url(activity.activity_id)}/lecture`;
      historyLink.textContent = "查看活動講義歷史";
      line.append(historyLink);
    }
    list.append(line);
  }
  historyNeedsRefresh = false;
  updateCreateAvailability();
}

function addResultButton(list, activity) {
  const button = document.createElement("button");
  button.textContent = activity.phase === "LIVE" ? "查看作答狀況" : `查看 ${activity.title} 結果`;
  const context = selection;
  const currentActivity = activeId;
  button.onclick = async () => {
    if (context !== selection || currentActivity !== activeId) return;
    selectedResult = {id: activity.activity_id, context, currentActivity, loading: false};
    await refreshResult();
  };
  list.append(button);
}

async function refreshResult() {
  const target = selectedResult;
  if (!target || target.loading) return;
  const isCurrent = () => target === selectedResult && target.context === selection &&
    target.currentActivity === activeId;
  target.loading = true;
  try {
    const data = await api(`/activities/${url(target.id)}/results`);
    if (isCurrent()) note(data.status === "pending" ? "結算中" :
      data.status === "unavailable" ? "這場活動沒有正式結算資料。" : describeResults(data.results));
  } catch (error) {
    if (isCurrent()) report(error);
  } finally {
    target.loading = false;
  }
}

function describeResults(results = []) {
  const answer = (value, items) => items
    ? items.map(item => [item.subitem_label, item.answer_text].filter(v => v != null).join(" ")).join("、")
    : typeof value === "string" ? value : Object.values(value || {}).join("、");
  if (!results.length) return "沒有已公布的結果。";
  return results.map((row) => {
    if ("submitted" in row) return `${row.question_id} · ${row.group_name} · ${row.submitted ? "已作答" : "未作答"}`;
    const groups = row.groups || (row.own ? [{...row.own, group_name: "本組"}] : []);
    const details = groups.map((group) => `${group.group_name}：${answer(group.answer, group.items)}（順位 ${group.rank}）`);
    return [row.display_number ?? row.question_id, row.winner_name ? `勝組 ${row.winner_name}：${answer(row.winner_answer, row.winner_items)}` : "無勝組",
      ...details].join(" · ");
  }).join(" ｜ ");
}

function showQuestions(activity, classroomOpen) {
  const list = byId("questions");
  const id = activity?.activity_id ?? null;
  activePhase = classroomOpen ? activity?.phase : null;
  if (activeId !== id && selectedResult) {
    selectedResult = null;
    note("");
  }
  if (!list) {
    activeId = id;
    return;
  }
  if (activeId !== id) {
    list.replaceChildren();
    activeId = id;
    submissionControls.clear();
    for (const question of activity?.questions || []) {
      const li = document.createElement("li");
      li.append(`題目 ${question.display_number}`);
      const inputForm = document.createElement("form");
      for (const item of question.items) {
        const label = document.createElement("label");
        if (item.subitem_label) label.append(item.subitem_label);
        const prompt = document.createElement("p");
        prompt.className = "question-prompt";
        prompt.textContent = item.prompt_text ?? "此活動版本未包含完整題目，請老師選擇完整版本並建立新活動；文字仍缺漏時請重新匯入。";
        label.append(prompt);
        const input = document.createElement("input");
        input.required = true;
        input.name = item.item_id;
        label.append(input);
        inputForm.append(label);
      }
      const button = document.createElement("button");
      button.textContent = "提交";
      inputForm.append(button);
      const context = selection;
      const update = globalThis.QuizSubmission?.attach(inputForm, button, question.question_id,
        () => context === selection && activeId === id && verifiedGroup !== null
          ? {room, activity: id, group: verifiedGroup, live: activePhase === "LIVE"} : null,
        (activity, body, key) => api(`/activities/${url(activity)}/submissions`, body, key),
        () => note("答案已受理"), report);
      if (update) submissionControls.add(update);
      li.append(inputForm);
      list.append(li);
    }
  }
  for (const button of list.querySelectorAll("input, button")) {
    button.disabled = !classroomOpen || activity?.phase !== "LIVE";
  }
  for (const update of submissionControls) update();
}

async function refresh() {
  if (!room || polling) return;
  const id = room;
  const context = selection;
  polling = true;
  try {
    const data = await api(`/classrooms/${url(id)}/state`);
    if (context !== selection || data.classroom_id !== id || data.state_version < version) return;
    const changed = data.state_version !== version;
    version = data.state_version;
    const open = data.classroom_state === "OPEN";
    const phase = data.activity?.phase;
    verifiedGroup = data.activity?.group_id ?? null;
    const text = !open ? "課堂已結束" :
      phase === "LIVE" ? "搶答中" : phase === "CLOSED" ? "活動已結束，等候下一活動" :
      phase === "PREPARING" ? "尚未開放搶答" : "等候老師建立活動";
    byId("state").textContent = [data.activity?.title, text, data.group_name].filter(Boolean).join(" · ");
    showQuestions(data.activity, open);
    if (role === "teacher") {
      roomOpen = open;
      stateUnfinished = phase === "PREPARING" || phase === "LIVE";
      byId("close-room").disabled = !open;
      if (changed) historyNeedsRefresh = true;
      updateCreateAvailability();
      if (historyNeedsRefresh) await activityList(id);
      if (main.dataset.classroomId && byId("classroom-groups")) {
        const groups = await api(`/teacher/workspace/courses/${url(main.dataset.courseId)}/classrooms/${url(id)}/groups`);
        if (context !== selection || room !== id) return;
        const list = byId("classroom-groups"); list.replaceChildren();
        for (const group of groups.groups) { const item = document.createElement("li"); item.textContent = group.name; list.append(item); }
        if (!groups.groups.length) { const item = document.createElement("li"); item.textContent = "尚無學生組別"; list.append(item); }
      }
    } else {
      byId("recover").hidden = true;
      if (byId("results") && studentHistoryVersion !== version) {
        const list = await api(`/classrooms/${url(id)}/results`);
        if (context !== selection) return;
        const results = byId("results");
        results.replaceChildren();
        for (const item of list.activities) addResultButton(results, item);
        studentHistoryVersion = version;
      }
    }
    await refreshResult();
  } catch (error) {
    if (context !== selection) return;
    verifiedGroup = null;
    if (role === "teacher") {
      historyNeedsRefresh = true;
      roomOpen = false;
      updateCreateAvailability();
    }
    for (const button of main.querySelectorAll("#questions input, #questions button, #activities button")) button.disabled = true;
    for (const update of submissionControls) update();
    if (byId("close-room")) byId("close-room").disabled = true;
    if (byId("recover")) byId("recover").hidden = error.message !== "AUTH_REQUIRED";
    report(error);
  } finally {
    polling = false;
  }
}

form("login", async (body) => {
  await api("/teacher/session", body);
  byId("login").reset();
  setLoginStatus(true);
  showFeedback("登入成功", "你已登入，可以建立或選擇課程。");
  await courses().catch(report);
}, (error) => showFeedback("登入未完成", errorText(error)));
form("create-course", async (body) => {
  const created = await api("/teacher/courses", body);
  await courses();
  byId("courses").value = created.course_id;
  note("課程已建立。");
  await selectCourse();
});
form("create-classroom", async (body) => {
  const id = byId("courses").value;
  if (!id) return note("請先選課程。");
  const created = await api(`/teacher/courses/${url(id)}/classrooms`, body);
  await selectCourse();
  byId("classrooms").value = created.classroom_id;
  byId("classrooms").dispatchEvent(new Event("change"));
});
form("create-activity", async ({title}) => {
  if (!room || !byId("catalogs").value) return note("請先選課堂和講義版本。");
  const id = room;
  const context = selection;
  const [import_id, import_version] = JSON.parse(byId("catalogs").value);
  try {
    await api(`/teacher/classrooms/${url(id)}/activities`, {title, import_id, import_version});
  } finally {
    if (context === selection) {
      historyNeedsRefresh = true;
      roomOpen = false;
      updateCreateAvailability();
    }
  }
  if (context === selection) await refresh();
});
form("join", async (body) => {
  const data = await api("/classroom-memberships", body);
  setRoom(data.classroom_id);
  await refresh();
});
byId("courses")?.addEventListener("change", () => selectCourse().catch(report));
byId("classrooms")?.addEventListener("change", (event) => {
  setRoom(event.target.value || null);
  const code = event.target.selectedOptions[0]?.dataset.code;
  byId("code").textContent = code ? `課堂碼：${code}` : "";
  refresh();
});
byId("close-room")?.addEventListener("click", async () => {
  if (!room || !window.confirm("確定結束課堂？準備中或搶答中的活動也會結束。")) return;
  try {
    await api(`/teacher/classrooms/${url(room)}/close`, {confirm: true});
    await refresh();
  } catch (error) {
    report(error);
  }
});
byId("recover")?.addEventListener("click", async () => {
  try {
    await api(`/classrooms/${url(room)}/result-access`, {});
    await refresh();
  } catch (error) {
    report(error);
  }
});
if (role === "teacher") {
  (main.dataset.classroomId ? fixedClassroom() : courses()).catch((error) => {
    if (error.message === "AUTH_REQUIRED") setLoginStatus(false);
  });
  const feedback = document.querySelector("[data-feedback]");
  if (feedback) showFeedback(feedback.dataset.feedback === "error" ? "操作未完成" : "操作成功",
    feedback.textContent.trim());
}
window.addEventListener("online", refresh);
window.addEventListener("pageshow", refresh);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refresh();
});
setInterval(refresh, 1000);
refresh();

async function fixedClassroom() {
  setRoom(main.dataset.classroomId);
  const data = await api(`/teacher/courses/${url(main.dataset.courseId)}/catalogs`);
  const select = byId('catalogs');select.replaceChildren();
  for(const lecture of data.lectures) for(const v of lecture.versions) option(select,JSON.stringify([lecture.import_id,v.import_version]),`${v.title} · 版本 ${v.import_version}`);
  await refresh();
}
