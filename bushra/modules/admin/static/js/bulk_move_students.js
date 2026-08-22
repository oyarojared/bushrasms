(function () {
  const resultsCard = document.getElementById("stu-results-card");
  const selectAll = document.getElementById("bulk-move-select-all");
  const openBtn = document.getElementById("bulk-move-open");
  const clearBtn = document.getElementById("bulk-move-clear");
  const selectBar = document.getElementById("stu-select-bar");
  const selectCountEl = document.getElementById("stu-select-bar-count");
  const selectNounEl = document.getElementById("stu-select-bar-noun");
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
  const subtitleEl = document.getElementById("bulk-move-subtitle");
  const selectSubtitle = "Choose the class these students should join.";
  const confirmSubtitle = "Confirm this class change.";

  if (!resultsCard || !openBtn || !modalEl || !form) return;

  const gradesUrlBase =
    resultsCard.dataset.gradesUrl || "/admin/api/grades/";

  function selectedChecks() {
    return Array.from(document.querySelectorAll(".bulk-move-check:checked"));
  }

  function allChecks() {
    return Array.from(document.querySelectorAll(".bulk-move-check"));
  }

  function visibleChecks() {
    return allChecks().filter((input) => {
      const row = input.closest("tr");
      return row && !row.classList.contains("stu-row-hidden");
    });
  }

  function refreshSelection() {
    const selected = selectedChecks();
    const total = visibleChecks().length;
    if (selectAll) {
      selectAll.checked = total > 0 && selected.length === total;
      selectAll.indeterminate = selected.length > 0 && selected.length < total;
    }
    if (countEl) countEl.textContent = String(selected.length);
    if (selectCountEl) {
      selectCountEl.textContent = String(selected.length);
    }
    if (selectNounEl) {
      selectNounEl.textContent =
        selected.length === 1 ? "student selected" : "students selected";
    }
    if (selectBar) {
      selectBar.classList.toggle("is-open", selected.length > 0);
    }
    document.dispatchEvent(new Event("stu-selection-changed"));
  }

  function openMoveModal() {
    if (selectedChecks().length === 0) return;
    refreshSelection();
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
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

    const streamField = buildUploadSelect(
      "bulk-move-stream",
      "stream",
      "Stream",
      true,
      { iconClass: "bi bi-layers", addStyle: true },
    );
    fillStreamSelect(streamField.select, streams);
    streamContainer.appendChild(streamField.fragment);
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
    if (subtitleEl) subtitleEl.textContent = selectSubtitle;
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
    if (subtitleEl) subtitleEl.textContent = confirmSubtitle;
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

      const gradeField = buildUploadSelect(
        "bulk-move-grade",
        "grade_form",
        "Grade / Form",
        true,
        { iconClass: "bi bi-journal-text", addStyle: true },
      );
      const select = gradeField.select;
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

      gradeContainer.appendChild(gradeField.fragment);
    } catch (error) {
      console.error("Error loading destination classes:", error);
    }
  }

  allChecks().forEach((input) => {
    input.addEventListener("change", refreshSelection);
  });

  if (selectAll) {
    selectAll.addEventListener("change", () => {
      visibleChecks().forEach((input) => {
        input.checked = selectAll.checked;
      });
      refreshSelection();
    });
  }

  openBtn.addEventListener("click", openMoveModal);

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      allChecks().forEach((input) => {
        input.checked = false;
      });
      refreshSelection();
    });
  }

  document.querySelectorAll(".js-move-student").forEach((btn) => {
    btn.addEventListener("click", () => {
      const studentId = btn.dataset.studentId;
      allChecks().forEach((input) => {
        input.checked = input.value === studentId;
      });
      refreshSelection();
      openMoveModal();
    });
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
  document.addEventListener("stu-class-list-filtered", refreshSelection);
})();
