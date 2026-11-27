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

  function attach(form, submit, question, context, send, accepted, report) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "重試此次送答";
    retry.hidden = true;
    form.append(retry);
    let busy = false;
    let sent = false;
    const scopeOf = (value) => JSON.stringify(value.operationScope
      ? [value.room, value.activity, value.group, question, value.operationScope]
      : [value.room, value.activity, value.group, question]);
    function update() {
      const value = context();
      const awaitingReply = value && read(scopeOf(value));
      retry.hidden = !awaitingReply;
      retry.disabled = busy || retry.hidden;
      submit.textContent = sent || awaitingReply ? "重新提交" : "提交";
      if (value) submit.disabled = busy || value.live === false || !!(value.operationScope && awaitingReply);
    }

    async function run(retrying) {
      const value = context();
      if (busy || !value || (!retrying && submit.disabled)) return;
      const scope = scopeOf(value);
      if (!retrying && value.operationScope && read(scope)) return;
      const operation = retrying ? read(scope) : {
        key: crypto.randomUUID(),
        body: {question_id: question, items: [...new FormData(form)].map(([item_id, answer_text]) =>
          ({item_id, answer_text}))},
      };
      if (!operation) return;
      save(scope, operation);
      sent = true;
      busy = true;
      update();
      const sameContext = () => {
        const current = context();
        return current && scopeOf(current) === scope;
      };
      const clearOwnOperation = () => {
        if (read(scope)?.key === operation.key) save(scope, null);
      };
      try {
        await send(value.activity, operation.body, operation.key);
        clearOwnOperation();
        if (sameContext()) accepted();
      } catch (error) {
        if (error.status >= 400 && error.status < 500 && ![401, 403, 429].includes(error.status)) {
          clearOwnOperation();
        }
        if (sameContext()) report(error);
      } finally {
        busy = false;
        update();
      }
    }
    form.onsubmit = (event) => {
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
