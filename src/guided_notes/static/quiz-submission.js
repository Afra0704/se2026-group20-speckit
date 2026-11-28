globalThis.QuizSubmission = (() => {
  const pending = new Map();
  const prefix = "quiz-submission:";

  function read(scope) {
    if (pending.has(scope)) return pending.get(scope);
    try { return JSON.parse(sessionStorage.getItem(prefix + scope)); }
    catch { return null; }
  }

  function save(scope, operation) {
    if (operation) pending.set(scope, operation);
    else pending.delete(scope);
    try {
      if (operation) sessionStorage.setItem(prefix + scope, JSON.stringify(operation));
      else sessionStorage.removeItem(prefix + scope);
    } catch {
      // The pending operation remains recoverable on the current page.
    }
  }

  function scopesFor(room, documentScope) {
    if (!documentScope) return [];
    const scopes = new Set(pending.keys());
    try {
      for (let index = 0; index < sessionStorage.length; index++) {
        const key = sessionStorage.key(index);
        if (key?.startsWith(prefix)) scopes.add(key.slice(prefix.length));
      }
    } catch {}
    return [...scopes].filter(scope => {
      try {
        const parts = JSON.parse(scope);
        return parts[0] === room && parts[4] === documentScope;
      } catch { return false; }
    });
  }

  const attempts = new Map();
  // Match Python str.strip() for validation without changing the submitted text.
  const blank = /^[\u0009-\u000d\u001c-\u001f\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u;
  const unknown = "送答結果未確認，伺服器可能已受理。";
  const conflict = "無法核對原送答，請向老師確認，或使用「重新加入課堂」。";

  function rejection(error) {
    if (error.status === 429) {
      const seconds = Number(error.retryAfter);
      return Number.isInteger(seconds) && seconds > 0
        ? `送答過於頻繁，請在 ${seconds} 秒後再試。`
        : "送答過於頻繁，請稍後再試。";
    }
    switch (error.message) {
      case "INVALID_ITEMS": return "請檢查本題的作答欄位。";
      case "INVALID_REQUEST":
      case "INVALID_QUESTION": return "本次送答未受理，請確認題目及答案。";
      case "INVALID_PHASE": return "活動目前無法送答。";
      case "INVALID_CSRF": return "頁面驗證已失效，請重新整理。";
      default: return "";
    }
  }

  function attach(form, submit, question, context, send, accepted, report, fields = new Map()) {
    const feedback = document.createElement("p");
    feedback.className = "submission-feedback";
    feedback.setAttribute?.("role", "status");
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "重試此次送答";
    form.append(feedback);
    form.append(retry);
    let busy = false;
    let hasAccepted = false;
    let message = "";
    const scopeOf = value => JSON.stringify(value.operationScope
      ? [value.room, value.activity, value.group, question, value.operationScope]
      : [value.room, value.activity, value.group, question]);

    function markField(field, invalid) {
      if (invalid) field.input.setAttribute("aria-invalid", "true");
      else field.input.removeAttribute("aria-invalid");
      field.notice.hidden = !invalid;
    }

    for (const field of fields.values()) {
      field.input.addEventListener("input", () => {
        if (!blank.test(field.input.value)) markField(field, false);
      });
    }

    function showFields(ids, focus = false) {
      let first;
      for (const [id, field] of fields) {
        const invalid = ids.includes(id);
        markField(field, invalid);
        if (invalid && !first) first = field.input;
      }
      if (focus) first?.focus();
    }

    function update() {
      const value = context();
      const awaiting = value && read(scopeOf(value));
      const blocked = awaiting?.conflict;
      const inactive = !value || value.live === false;
      retry.hidden = !awaiting;
      retry.disabled = inactive || busy || !awaiting || !!blocked;
      submit.disabled = inactive || busy || !!(value?.operationScope && awaiting);
      submit.textContent = busy ? "送出中…" : hasAccepted ? "重新提交" : "提交";
      const text = busy ? "送出中" : blocked ? conflict : message || (awaiting ? unknown : "");
      if (feedback.textContent !== text) feedback.textContent = text;
    }

    async function run(retrying) {
      const value = context();
      if (!value || busy || value.live === false) return;
      const scope = scopeOf(value);
      const awaiting = read(scope);
      if (retrying ? (!awaiting || awaiting.conflict) : (value.operationScope && awaiting)) return;

      let operation = awaiting;
      if (!retrying) {
        const items = [...new FormData(form)].map(([item_id, answer_text]) => ({item_id, answer_text}));
        const invalidIds = items.filter(item => blank.test(item.answer_text)).map(item => item.item_id);
        showFields(invalidIds, true);
        if (invalidIds.length) {
          message = "請填寫標示的答案欄位。";
          update();
          return;
        }
        operation = {key: crypto.randomUUID(), body: {question_id: question, items}};
        save(scope, operation);
      }

      const attempt = {};
      attempts.set(scope, attempt);
      const isLatest = () => attempts.get(scope) === attempt && read(scope)?.key === operation.key;
      const isVisible = () => {
        const current = context();
        return current && scopeOf(current) === scope;
      };
      busy = true;
      update();
      try {
        await send(value.activity, operation.body, operation.key);
        if (!isLatest()) return;
        save(scope, null);
        if (isVisible()) {
          hasAccepted = true;
          message = "答案已受理";
          accepted?.();
        }
      } catch (error) {
        if (!isLatest()) return;
        const detail = rejection(error);
        if (error.status === 409 && error.message === "SUBMISSION_REPLAY_CONFLICT") {
          save(scope, {...operation, conflict: true});
        } else if (detail && (!retrying || error.message === "INVALID_PHASE")) {
          save(scope, null);
          if (isVisible()) {
            message = detail;
            if (!retrying && Array.isArray(error.invalidItemIds)) showFields(error.invalidItemIds, true);
          }
        } else if (isVisible()) {
          message = detail ? `${unknown} ${detail}` : unknown;
        }
        if (isVisible()) report?.(error);
      } finally {
        if (attempts.get(scope) === attempt) attempts.delete(scope);
        busy = false;
        update();
      }
    }

    form.onsubmit = event => {
      event.preventDefault();
      return run(false);
    };
    retry.onclick = () => run(true);
    return update;
  }
  return {
    attach,
    hasPending: (room, scope) => scopesFor(room, scope).some(read),
    clearScope: (room, scope) => scopesFor(room, scope).forEach(key => save(key, null)),
  };
})();
