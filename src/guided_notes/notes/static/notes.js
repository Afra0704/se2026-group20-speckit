"use strict";
for (const group of document.querySelectorAll("[data-name-options]")) {
  const input = group.querySelector("input[name='custom_title']");
  const wrapper = group.querySelector("[data-custom-name]");
  const update = () => {
    const custom = group.querySelector("input[name='name_mode']:checked").value === "custom";
    input.disabled = !custom;
    input.required = custom;
    wrapper.hidden = !custom;
  };
  group.addEventListener("change", update);
  update();
}
for (const form of document.querySelectorAll("form[data-activity-form]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    const feedback = form.querySelector("[data-feedback]");
    button.disabled = true;
    feedback.textContent = "正在建立活動…";
    const data = new FormData(form);
    try {
      const response = await fetch("/activities", {
        method: "POST", headers: {"Content-Type": "application/json", "X-Activity-Role": "teacher", "X-CSRFToken": data.get("csrf_token")},
        body: JSON.stringify({import_id: data.get("import_id"), import_version: Number(data.get("import_version"))})
      });
      const result = await response.json();
      if (!response.ok) throw new Error("建立活動未完成，請確認教師登入狀態後重試。");
      localStorage.setItem("guided-notes:teacher", JSON.stringify({id: result.activity_id, code: result.code}));
      window.location.assign("/teacher");
    } catch (error) {
      feedback.textContent = "建立活動未完成，請確認登入與連線狀態後重試。";
      button.disabled = false;
    }
  });
}
