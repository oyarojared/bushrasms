const gradingSystemSelect = document.getElementById("grading-system");
const gradingFields = document.getElementById("grading-fields");
const gradingPlaceholder = document.getElementById("grading-placeholder");
const boundaryContainer = document.getElementById("boundary-container");
const addBoundaryBtn = document.getElementById("add-boundary-btn");
const classesSection = document.getElementById("classes-section");
const gradingSuccessAlert = document.getElementById("gradingSuccessAlert");
const gradingSuccessCloseBtn = document.getElementById("gradingSuccessCloseBtn");
const saveGradingBtn = document.getElementById("save-grading");

let isSavingGrading = false;

function showSection(element) {
  element.classList.remove("d-none");
}

function hideSection(element) {
  element.classList.add("d-none");
}

function hideGradingSuccessAlert() {
  if (gradingSuccessAlert) {
    gradingSuccessAlert.classList.add("d-none");
  }
}

function showGradingSuccessAlert() {
  if (!gradingSuccessAlert) return;

  gradingSuccessAlert.classList.remove("d-none");
  gradingSuccessAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function forceHideLoadingOverlay() {
  const blocker = document.getElementById("uiBlocker");
  if (blocker) {
    blocker.classList.add("d-none");
    blocker.setAttribute("aria-busy", "false");
  }
  document.body.classList.remove("ui-blocker-active");
}

if (gradingSuccessCloseBtn) {
  gradingSuccessCloseBtn.addEventListener("click", hideGradingSuccessAlert);
}

function addBoundaryRow(values = {}) {
  const row = document.createElement("div");
  row.className = "grading-boundary-card boundary-row";

  row.innerHTML = `
    <div class="grading-boundary-card-head">
      <span class="grading-boundary-card-title">
        <i class="bi bi-layers me-1"></i> Score Band
      </span>
      <button type="button" class="btn grading-remove-boundary remove-row" title="Remove boundary">
        <i class="bi bi-trash"></i>
      </button>
    </div>

    <div class="row g-2 g-md-3">
      <div class="col-6 col-md-4 col-lg-2">
        <label class="grading-field-label">Min Score</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text"><i class="bi bi-arrow-down-right-circle"></i></span>
          <input type="number" class="form-control" placeholder="0" min="0" max="100" value="${values.min_score ?? ""}">
        </div>
      </div>

      <div class="col-6 col-md-4 col-lg-2">
        <label class="grading-field-label">Max Score</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text"><i class="bi bi-arrow-up-right-circle"></i></span>
          <input type="number" class="form-control" placeholder="100" min="0" max="100" value="${values.max_score ?? ""}">
        </div>
      </div>

      <div class="col-6 col-md-4 col-lg-2">
        <label class="grading-field-label">Level</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text"><i class="bi bi-award"></i></span>
          <input type="text" class="form-control" placeholder="EE1" value="${values.performance_level ?? ""}">
        </div>
      </div>

      <div class="col-6 col-md-4 col-lg-2">
        <label class="grading-field-label">Points</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text"><i class="bi bi-star"></i></span>
          <input type="number" class="form-control" placeholder="8" min="0" value="${values.points ?? ""}">
        </div>
      </div>

      <div class="col-12 col-lg-4">
        <label class="grading-field-label">Descriptor</label>
        <div class="input-group input-group-sm">
          <span class="input-group-text"><i class="bi bi-journal-text"></i></span>
          <input type="text" class="form-control" placeholder="Exceeding Expectation 1" value="${values.descriptor ?? ""}">
        </div>
      </div>
    </div>
  `;

  boundaryContainer.appendChild(row);

  row.querySelector(".remove-row").addEventListener("click", () => {
    row.remove();
  });
}

function parseBoundaryRow(row) {
  const inputs = row.querySelectorAll("input");
  const minRaw = inputs[0].value.trim();
  const maxRaw = inputs[1].value.trim();
  const level = inputs[2].value.trim();
  const pointsRaw = inputs[3].value.trim();
  const descriptor = inputs[4].value.trim();

  const isEmpty = !minRaw && !maxRaw && !level && !pointsRaw && !descriptor;
  if (isEmpty) return null;

  if (!minRaw || !maxRaw || !level) {
    return {
      invalid: true,
      message:
        "Each boundary must include min score, max score, and performance level.",
    };
  }

  const min_score = Number(minRaw);
  const max_score = Number(maxRaw);

  if (Number.isNaN(min_score) || Number.isNaN(max_score)) {
    return {
      invalid: true,
      message: "Min and max scores must be valid numbers.",
    };
  }

  if (pointsRaw !== "" && Number.isNaN(Number(pointsRaw))) {
    return {
      invalid: true,
      message: "Points must be a valid number when provided.",
    };
  }

  return {
    min_score,
    max_score,
    performance_level: level,
    points: pointsRaw !== "" ? Number(pointsRaw) : null,
    descriptor: descriptor || null,
  };
}

function collectBoundaries() {
  const boundaries = [];
  let invalidMessage = null;

  boundaryContainer.querySelectorAll(".boundary-row").forEach((row) => {
    const parsed = parseBoundaryRow(row);
    if (!parsed) return;

    if (parsed.invalid) {
      invalidMessage = parsed.message;
      return;
    }

    boundaries.push(parsed);
  });

  return { boundaries, invalidMessage };
}

gradingSystemSelect.addEventListener("change", function () {
  const system = this.value;
  boundaryContainer.innerHTML = "";
  hideGradingSuccessAlert();

  if (!system) {
    hideSection(gradingFields);
    hideSection(gradingPlaceholder);
    hideSection(classesSection);
    return;
  }

  showSection(classesSection);

  if (system === "CBC") {
    showSection(gradingFields);
    hideSection(gradingPlaceholder);
    addBoundaryRow();
  } else {
    hideSection(gradingFields);
    showSection(gradingPlaceholder);
  }
});

addBoundaryBtn.addEventListener("click", () => addBoundaryRow());

saveGradingBtn.addEventListener("click", function () {
  if (isSavingGrading) return;

  const system = gradingSystemSelect.value;
  if (!system) return alert("Please select a grading system.");

  const boundaries = [];
  if (system === "CBC") {
    const result = collectBoundaries();
    if (result.invalidMessage) {
      return alert(result.invalidMessage);
    }
    boundaries.push(...result.boundaries);
  } else if (system === "8-4-4") {
    alert("Grading for 8-4-4 uses the default KNEC scale and cannot be changed.");
    return;
  }

  if (boundaries.length === 0) {
    return alert(
      "Please enter at least one complete grading boundary before saving.",
    );
  }

  if (boundaries.some((b) => b.min_score > b.max_score)) {
    return alert("Min score cannot be greater than max score in any boundary.");
  }

  const selectedClasses = [];
  classesSection.querySelectorAll("input[type=checkbox]").forEach((chk) => {
    if (chk.checked) selectedClasses.push(chk.value);
  });

  if (selectedClasses.length === 0) {
    return alert("Please select at least one class.");
  }

  isSavingGrading = true;
  hideGradingSuccessAlert();
  saveGradingBtn.disabled = true;

  if (typeof blockUI === "function") {
    blockUI("Saving grading configuration", "Applying rules to selected classes…");
  }

  fetch("/admin/save_grading_config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system,
      boundaries,
      selected_classes: selectedClasses,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      forceHideLoadingOverlay();

      if (data.success) {
        boundaryContainer.innerHTML = "";
        if (system === "CBC") addBoundaryRow();
        showGradingSuccessAlert();
      } else {
        alert(data.error || "Failed to save grading configuration.");
      }
    })
    .catch((err) => {
      console.error(err);
      forceHideLoadingOverlay();
      alert("An error occurred while saving the configuration.");
    })
    .finally(() => {
      isSavingGrading = false;
      saveGradingBtn.disabled = false;
      forceHideLoadingOverlay();
    });
});
