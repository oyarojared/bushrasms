(function () {
  const resultsCard = document.getElementById("stu-results-card");
  const selectAll = document.getElementById("bulk-move-select-all");
  const openBtn = document.getElementById("bulk-move-open");
  const modalEl = document.getElementById("bulkMoveModal");
  const form = document.getElementById("bulk-move-form");
  const idsBox = document.getElementById("bulk-move-ids");
  const countEl = document.getElementById("bulk-move-count");
  const fromLabel = document.getElementById("bulk-move-from-label");
  const gradeContainer = document.getElementById("bulk-move-grade-container");
  const streamContainer = document.getElementById("bulk-move-stream-container");
  const stepSelect = document.getElementById("bulk-move-step-select");
  const stepConfirm = document.getElementById("bulk-move-step-confirm");
  const continueBtn = document.getElementById("bulk-move-continue");
  const backBtn = document.getElementById("bulk-move-back");
  const submitBtn = document.getElementById("bulk-move-submit");
  const warnCount = document.getElementById("bulk-move-warn-count");
  const warnFrom = document.getElementById("bulk-move-warn-from");
  const warnTo = document.getElementById("bulk-move-warn-to");
  const gradesUrlBase =
    resultsCard.dataset.gradesUrl || "/admin/api/grades/";

  if (!resultsCard || !openBtn || !modalEl || !form) return;

  function selectedChecks() {
    return Array.from(document.querySelectorAll(".bulk-move-check:checked"));
  }

  function allChecks() {
    return Array.from(document.querySelectorAll(".bulk-move-check"));
  }

  function refreshSelection() {
    const selected = selectedChecks();
    const total = allChecks().length;
    openBtn.disabled = selected.length === 0;
    if (selectAll) {
      selectAll.checked = total > 0 && selected.length === total;
      selectAll.indeterminate = selected.length > 0 && selected.length < total;
    }
    if (countEl) countEl.textContent = String(selected.length);
  }

  function syncHiddenIds() {
    if (!idsBox) return;
    idsBox.innerHTML = "";
    selectedChecks().forEach((input) => {
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "student_ids";
      hidden.value = input.value;
      idsBox.appendChild(hidden);
    });
  }

  function fillStreamSelect(select, streams) {
    select.innerHTML = '<option value="">Select stream</option>';
    streams.forEach((stream) => {
      const option = document.createElement("option");
      option.value = stream;
      option.textContent = stream;
      select.appendChild(option);
    });
  }

  function renderStreamField(streams) {
    streamContainer.innerHTML = "";
    if (!streams.length) return;

    const label = document.createElement("label");
    label.className = "stu-label stu-label-required";
    label.setAttribute("for", "bulk-move-stream");
    label.textContent = "Stream";

    const select = document.createElement("select");
    select.id = "bulk-move-stream";
    select.name = "stream";
    select.className = "form-select form-select-sm stu-control";
    select.required = true;
    fillStreamSelect(select, streams);

    streamContainer.appendChild(label);
    streamContainer.appendChild(select);
  }

  function destinationLabel() {
    const gradeSelect = document.getElementById("bulk-move-grade");
    const streamSelect = document.getElementById("bulk-move-stream");
    const gradeName = gradeSelect?.selectedOptions[0]?.textContent || "";
    const streamName = streamSelect?.value || "";
    if (streamName) return `${gradeName} · ${streamName}`;
    return gradeName;
  }

  function showSelectStep() {
    stepSelect.classList.remove("d-none");
    stepConfirm.classList.add("d-none");
    continueBtn.classList.remove("d-none");
    backBtn.classList.add("d-none");
    submitBtn.classList.add("d-none");
  }

  function showConfirmStep() {
    const selectedCount = selectedChecks().length;
    const fromText = fromLabel ? fromLabel.textContent.trim() : "the current class";
    const toText = destinationLabel();
    if (warnCount) warnCount.textContent = String(selectedCount);
    if (warnFrom) warnFrom.textContent = fromText;
    if (warnTo) warnTo.textContent = toText;
    stepSelect.classList.add("d-none");
    stepConfirm.classList.remove("d-none");
    continueBtn.classList.add("d-none");
    backBtn.classList.remove("d-none");
    submitBtn.classList.remove("d-none");
  }

  function destinationIsValid() {
    const gradeSelect = document.getElementById("bulk-move-grade");
    if (!gradeSelect || !gradeSelect.value) {
      if (gradeSelect) gradeSelect.reportValidity();
      return false;
    }
    const streamSelect = document.getElementById("bulk-move-stream");
    if (streamSelect && !streamSelect.value) {
      streamSelect.reportValidity();
      return false;
    }
    return true;
  }

  async function loadDestinationClasses() {
    const branchId = resultsCard.dataset.branchId;
    gradeContainer.innerHTML = "";
    streamContainer.innerHTML = "";
    if (!branchId) return;

    try {
      const response = await fetch(`${gradesUrlBase}${branchId}`);
      const classes = await response.json();
      if (!Array.isArray(classes) || !classes.length) return;

      const label = document.createElement("label");
      label.className = "stu-label stu-label-required";
      label.setAttribute("for", "bulk-move-grade");
      label.textContent = "Grade / Form";

      const select = document.createElement("select");
      select.id = "bulk-move-grade";
      select.name = "grade_form";
      select.className = "form-select form-select-sm stu-control";
      select.required = true;
      select.innerHTML = '<option value="">Select grade / form</option>';

      classes.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.grade_form;
        option.dataset.streams = JSON.stringify(item.streams || []);
        select.appendChild(option);
      });

      select.addEventListener("change", () => {
        const selected = select.selectedOptions[0];
        const streams = JSON.parse(selected?.dataset.streams || "[]");
        renderStreamField(streams);
      });

      gradeContainer.appendChild(label);
      gradeContainer.appendChild(select);
    } catch (error) {
      console.error("Error loading destination classes:", error);
    }
  }

  allChecks().forEach((input) => {
    input.addEventListener("change", refreshSelection);
  });

  if (selectAll) {
    selectAll.addEventListener("change", () => {
      allChecks().forEach((input) => {
        input.checked = selectAll.checked;
      });
      refreshSelection();
    });
  }

  openBtn.addEventListener("click", () => {
    if (selectedChecks().length === 0) return;
    refreshSelection();
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  });

  modalEl.addEventListener("show.bs.modal", () => {
    refreshSelection();
    showSelectStep();
    loadDestinationClasses();
  });

  if (continueBtn) {
    continueBtn.addEventListener("click", () => {
      if (!destinationIsValid()) return;
      showConfirmStep();
    });
  }

  if (backBtn) {
    backBtn.addEventListener("click", showSelectStep);
  }

  form.addEventListener("submit", (event) => {
    if (stepConfirm.classList.contains("d-none")) {
      event.preventDefault();
      return;
    }
    syncHiddenIds();
    if (selectedChecks().length === 0) {
      event.preventDefault();
    }
  });

  refreshSelection();
})();
