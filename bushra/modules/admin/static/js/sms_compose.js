(function () {
  const form = document.getElementById("smsComposeForm");
  if (!form) return;

  const config = window.SMS_COMPOSE || {};
  const bodyEl = document.getElementById("smsBody");
  const counterEl = document.getElementById("smsCounter");
  const labelEl = document.getElementById("smsAudienceLabel");
  const hintEl = document.getElementById("smsAudienceHint");
  const whoHint = document.getElementById("smsWhoHint");
  const readyCountEl = document.getElementById("smsReadyCount");
  const skippedCountEl = document.getElementById("smsSkippedCount");
  const costText = document.getElementById("smsCostText");
  const sendBtn = document.getElementById("smsSendBtn");
  const sendError = document.getElementById("smsSendError");
  const toPeopleBtn = document.getElementById("smsToPeople");
  const toWriteBtn = document.getElementById("smsToWrite");
  const classFields = document.getElementById("smsClassFields");
  const classSelect = document.getElementById("smsClassId");
  const streamSelect = document.getElementById("smsStream");
  const streamWrap = document.getElementById("smsStreamWrap");
  const assignmentSelect = document.getElementById("smsAssignmentSelect");
  const purposeEl = document.getElementById("smsPurpose");
  const templateEl = document.getElementById("smsTemplate");
  const whoSelect = document.getElementById("smsWho");
  const audienceTypeEl = document.getElementById("smsAudienceType");
  const whoTab = document.getElementById("sms-who-tab");
  const peopleTab = document.getElementById("sms-people-tab");
  const writeTab = document.getElementById("sms-write-tab");

  const GSM =
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
  const GSM_EXT = "^{}\\[~]|€";
  const MAX_PARTS = Number(config.maxParts || 3);

  let audience = { recipients: [], ready: 0, skipped: 0, label: "" };

  function audienceType() {
    return (audienceTypeEl?.value || whoSelect?.value || "").trim();
  }

  function setAudienceType(value) {
    if (audienceTypeEl) audienceTypeEl.value = value || "";
  }

  function selectionComplete() {
    const type = audienceType();
    if (type === "teachers" || type === "parents_school" || type === "parent_one") {
      return true;
    }
    if (type === "parents_class") {
      if (assignmentSelect) return Boolean(assignmentSelect.value);
      if (document.getElementById("smsAssignmentId")?.value && !classSelect) {
        return true;
      }
      return Boolean(classSelect?.value);
    }
    return false;
  }

  function setTabEnabled(tab, enabled) {
    if (!tab) return;
    tab.classList.toggle("disabled", !enabled);
    tab.setAttribute("aria-disabled", enabled ? "false" : "true");
    if (enabled) tab.removeAttribute("tabindex");
    else tab.setAttribute("tabindex", "-1");
  }

  function showTab(tabBtn) {
    if (!tabBtn || tabBtn.classList.contains("disabled") || !window.bootstrap) return;
    bootstrap.Tab.getOrCreateInstance(tabBtn).show();
  }

  function isGsm(text) {
    return Array.from(text || "").every(
      (ch) => GSM.includes(ch) || GSM_EXT.includes(ch),
    );
  }

  function countParts(text) {
    if (!text) return { parts: 0, gsm: true, length: 0 };
    const gsm = isGsm(text);
    let length = 0;
    if (gsm) {
      for (const ch of text) length += GSM_EXT.includes(ch) ? 2 : 1;
    } else {
      length = text.length;
    }
    const single = gsm ? 160 : 70;
    const concat = gsm ? 153 : 67;
    const limit = length <= single ? single : concat;
    const parts = Math.ceil(length / limit) || 0;
    return { parts, gsm, length };
  }

  function updateCounter() {
    const info = countParts(bodyEl.value);
    const encoding = info.gsm ? "English / Kiswahili" : "Unicode (uses more SMS)";
    counterEl.innerHTML = `<i class="bi bi-text-paragraph"></i> ${info.length} characters · ${info.parts || 0} SMS each · ${encoding}`;
    counterEl.classList.toggle("is-warn", !info.gsm);
    counterEl.classList.toggle("is-bad", info.parts > MAX_PARTS);
    updateCost();
  }

  function updateCost() {
    const info = countParts(bodyEl.value);
    const selected = Number(audience.ready || 0);
    const credits = selected * (info.parts || 0);
    const left = Number(config.credits || 0);
    costText.textContent =
      selected && info.parts
        ? `${selected} people × ${info.parts} SMS = ${credits} credit`
        : "Choose recipients and write a message";
    const tooLong = info.parts > MAX_PARTS;
    const blocked = !selected || !bodyEl.value.trim() || tooLong || credits > left;
    if (sendBtn) sendBtn.disabled = blocked;
  }

  function renderSummary() {
    const ready = Number(audience.ready || 0);
    const skipped = Number(audience.skipped || 0);
    labelEl.textContent = audience.label || "—";
    readyCountEl.textContent = String(ready);
    skippedCountEl.textContent = String(skipped);
    if (!selectionComplete()) {
      hintEl.textContent = "Select who this is for first.";
    } else if (ready === 0) {
      hintEl.textContent = skipped
        ? "Nobody has a valid Kenya mobile number yet."
        : "No recipients found for that choice.";
    } else if (skipped) {
      hintEl.textContent = `${skipped} skipped because the number is missing or not a Kenya mobile.`;
    } else {
      hintEl.textContent = "Everyone in this group can receive the SMS.";
    }
    if (toWriteBtn) toWriteBtn.disabled = ready === 0;
    if (toPeopleBtn) toPeopleBtn.disabled = !selectionComplete();
    setTabEnabled(writeTab, ready > 0);
    updateCost();
  }

  function fillStreams(preferred) {
    if (!classSelect || !streamSelect) return;
    const option = classSelect.selectedOptions[0];
    let streams = [];
    try {
      streams = JSON.parse(option?.dataset.streams || "[]");
    } catch (err) {
      streams = [];
    }
    streamSelect.innerHTML = '<option value="">All</option>';
    streams.forEach((name) => {
      const item = document.createElement("option");
      item.value = name;
      item.textContent = name;
      if (preferred && preferred === name) item.selected = true;
      streamSelect.appendChild(item);
    });
    if (streamWrap) streamWrap.classList.toggle("d-none", streams.length === 0);
  }

  function toggleClassFields() {
    if (!classFields) return;
    classFields.classList.toggle("d-none", audienceType() !== "parents_class");
  }

  function toggleAudienceTools() {
    const teacher = audienceType() === "teachers";
    document.querySelectorAll("#smsChips [data-insert]").forEach((chip) => {
      const kind = chip.getAttribute("data-insert");
      const show =
        kind === "shared" || (teacher ? kind === "teacher" : kind === "parent");
      chip.classList.toggle("d-none", !show);
    });
    if (!templateEl) return;
    Array.from(templateEl.options).forEach((option, index) => {
      if (!index) return;
      const forTeachers = option.dataset.teachers === "1";
      option.hidden = teacher ? !forTeachers : forTeachers;
    });
    if (templateEl.selectedOptions[0]?.hidden) templateEl.value = "";
  }

  async function loadAudience({ advance = false } = {}) {
    const complete = selectionComplete();
    setTabEnabled(peopleTab, complete);
    if (!complete) {
      setTabEnabled(writeTab, false);
      if (toPeopleBtn) toPeopleBtn.disabled = true;
      audience = { recipients: [], ready: 0, skipped: 0, label: "" };
      renderSummary();
      if (whoHint) whoHint.textContent = "Choose a group, then recipients open automatically.";
      return;
    }

    const params = new URLSearchParams();
    params.set("audience_type", audienceType());
    params.set("branch_id", document.getElementById("smsBranchId").value);
    const assignmentId = document.getElementById("smsAssignmentId")?.value;
    const studentId = document.getElementById("smsStudentId")?.value;
    if (assignmentId) params.set("assignment_id", assignmentId);
    if (studentId) params.set("student_id", studentId);
    if (classSelect?.value) params.set("class_id", classSelect.value);
    if (streamSelect?.value) params.set("stream", streamSelect.value);

    if (whoHint) whoHint.textContent = "Loading numbers…";
    hintEl.textContent = "Loading numbers…";
    try {
      const response = await fetch(`/admin/api/sms/audience?${params}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not load recipients");
      audience = data;
      renderSummary();
      if (whoHint) whoHint.textContent = "Recipients are ready. You can change this anytime.";
      if (advance) showTab(peopleTab);
    } catch (err) {
      audience = { recipients: [], ready: 0, skipped: 0, label: "" };
      renderSummary();
      hintEl.textContent = err.message;
      if (whoHint) whoHint.textContent = err.message;
      setTabEnabled(peopleTab, false);
      setTabEnabled(writeTab, false);
    }
  }

  function payload() {
    return {
      audience_type: audienceType(),
      branch_id: document.getElementById("smsBranchId").value,
      assignment_id: document.getElementById("smsAssignmentId")?.value || "",
      student_id: document.getElementById("smsStudentId")?.value || "",
      class_id: classSelect?.value || "",
      stream: streamSelect?.value || "",
      purpose: purposeEl?.value || "custom",
      body: bodyEl.value,
      exclude_keys: [],
    };
  }

  [peopleTab, writeTab].forEach((tab) => {
    tab?.addEventListener("click", (event) => {
      if (tab.classList.contains("disabled")) event.preventDefault();
    });
  });

  bodyEl.addEventListener("input", updateCounter);

  whoSelect?.addEventListener("change", () => {
    setAudienceType(whoSelect.value);
    toggleClassFields();
    toggleAudienceTools();
    if (audienceType() === "teachers" && purposeEl && purposeEl.value === "notice") {
      purposeEl.value = "staff";
    }
    if (audienceType() === "parents_class") {
      showTab(whoTab);
      const readyToAdvance = Boolean(classSelect?.value) && selectedStreams().length === 0;
      loadAudience({ advance: readyToAdvance });
      return;
    }
    loadAudience({
      advance: audienceType() === "parents_school" || audienceType() === "teachers",
    });
  });

  function selectedStreams() {
    if (!classSelect || !classSelect.value) return [];
    try {
      return JSON.parse(classSelect.selectedOptions[0]?.dataset.streams || "[]");
    } catch (err) {
      return [];
    }
  }

  classSelect?.addEventListener("change", () => {
    fillStreams("");
    const hasStreams = selectedStreams().length > 0;
    loadAudience({ advance: Boolean(classSelect.value) && !hasStreams });
  });
  streamSelect?.addEventListener("change", () => loadAudience({ advance: true }));

  assignmentSelect?.addEventListener("change", () => {
    const option = assignmentSelect.selectedOptions[0];
    document.getElementById("smsAssignmentId").value = assignmentSelect.value;
    if (option) {
      document.getElementById("smsBranchId").value = option.dataset.branchId || "";
    }
    loadAudience({ advance: true });
  });

  templateEl?.addEventListener("change", () => {
    const option = templateEl.selectedOptions[0];
    if (!option || !option.dataset.body) return;
    bodyEl.value = option.dataset.body;
    if (option.dataset.purpose && purposeEl) purposeEl.value = option.dataset.purpose;
    updateCounter();
  });

  document.getElementById("smsChips")?.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-token]");
    if (!chip) return;
    const token = chip.getAttribute("data-token");
    const start = bodyEl.selectionStart || bodyEl.value.length;
    bodyEl.value =
      bodyEl.value.slice(0, start) + token + bodyEl.value.slice(bodyEl.selectionEnd || start);
    bodyEl.focus();
    updateCounter();
  });

  toPeopleBtn?.addEventListener("click", () => showTab(peopleTab));
  toWriteBtn?.addEventListener("click", () => showTab(writeTab));

  form.addEventListener("submit", (event) => event.preventDefault());

  sendBtn?.addEventListener("click", async () => {
    sendError?.classList.add("d-none");
    sendBtn.disabled = true;
    try {
      const response = await fetch("/admin/api/sms/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload()),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not send");
      window.location.href = data.redirect;
    } catch (err) {
      if (sendError) {
        sendError.textContent = err.message;
        sendError.classList.remove("d-none");
      } else {
        alert(err.message);
      }
      sendBtn.disabled = false;
    }
  });

  if (whoSelect) setAudienceType(whoSelect.value);
  fillStreams(config.defaultStream || "");
  toggleClassFields();
  toggleAudienceTools();
  updateCounter();
  loadAudience({ advance: selectionComplete() });
})();
