function buildUploadSelect(id, name, labelText, required = false, options = {}) {
  const { iconClass = "bi bi-list", addStyle = false } = options;
  const fragment = document.createDocumentFragment();

  const label = document.createElement("label");
  label.className = addStyle
    ? "cls-add-label"
    : required
      ? "stu-label stu-label-required"
      : "stu-label";
  label.setAttribute("for", id);
  label.textContent = labelText;

  const select = document.createElement("select");
  select.id = id;
  select.name = name;
  select.className = addStyle
    ? "form-select form-select-sm"
    : "form-select form-select-sm stu-control";
  if (required) {
    select.required = true;
  }

  if (addStyle) {
    const group = document.createElement("div");
    group.className = "input-group input-group-sm";

    const iconWrap = document.createElement("span");
    iconWrap.className = "input-group-text";
    const icon = document.createElement("i");
    icon.className = iconClass;
    iconWrap.appendChild(icon);

    group.appendChild(iconWrap);
    group.appendChild(select);
    fragment.appendChild(label);
    fragment.appendChild(group);
  } else {
    fragment.appendChild(label);
    fragment.appendChild(select);
  }

  return { fragment, select };
}

async function loadGradesStreams(branchId, gradeContainerId, streamContainerId) {
  const gradeContainer = document.getElementById(gradeContainerId);
  const streamContainer = document.getElementById(streamContainerId);

  if (!gradeContainer || !streamContainer) return;

  const addStyle = gradeContainer.classList.contains("cls-add-field");

  gradeContainer.innerHTML = "";
  streamContainer.innerHTML = "";

  if (!branchId) return;

  try {
    const response = await fetch(`/admin/api/grades/${branchId}`);
    const classes = await response.json();

    if (!classes || classes.length === 0) return;

    const gradeField = buildUploadSelect(
      "select-grade-dynamic",
      "grade_form",
      "Grade / Form",
      true,
      { iconClass: "bi bi-journal-text", addStyle },
    );
    const gradeSelect = gradeField.select;

    gradeSelect.innerHTML = '<option value="">Select grade / form</option>';

    classes.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.grade_form;
      option.dataset.streams = JSON.stringify(item.streams || []);
      gradeSelect.appendChild(option);
    });

    gradeContainer.appendChild(gradeField.fragment);

    gradeSelect.addEventListener("change", () => {
      streamContainer.innerHTML = "";
      const selectedOption = gradeSelect.selectedOptions[0];
      const streams = JSON.parse(selectedOption?.dataset.streams || "[]");

      if (!streams.length) return;

      const streamField = buildUploadSelect(
        "select-stream-dynamic",
        "stream",
        "Stream",
        true,
        { iconClass: "bi bi-layers", addStyle },
      );
      const streamSelect = streamField.select;

      streamSelect.innerHTML = '<option value="">Select stream</option>';

      streams.forEach((stream) => {
        const option = document.createElement("option");
        option.value = stream;
        option.textContent = stream;
        streamSelect.appendChild(option);
      });

      streamContainer.appendChild(streamField.fragment);
    });
  } catch (error) {
    console.error("Error loading grades/forms:", error);
  }
}

const uploadBranchSelect = document.getElementById("select-branch-element");

if (uploadBranchSelect) {
  uploadBranchSelect.addEventListener("change", () => {
    loadGradesStreams(
      uploadBranchSelect.value,
      "grade-forms-container",
      "stream-select-container",
    );
    updateUploadAdmStart(uploadBranchSelect.value);
  });

  const uploadModal = document.getElementById("uploadModal");
  if (uploadModal) {
    uploadModal.addEventListener("shown.bs.modal", () => {
      if (uploadBranchSelect.value) {
        uploadBranchSelect.dispatchEvent(new Event("change"));
      } else {
        updateUploadAdmStart("");
      }
    });
  }
}

function updateUploadAdmStart(branchId) {
  const box = document.getElementById("upload-adm-start");
  const valueEl = document.getElementById("upload-adm-start-value");
  const copyEl = document.getElementById("upload-adm-start-copy");
  const sampleLink = document.getElementById("upload-sample-link");

  if (!box || !valueEl || !copyEl) return;

  if (!branchId) {
    box.classList.add("is-pending");
    valueEl.textContent = "—";
    copyEl.textContent =
      "Select a school to see which Adm No to start with.";
    return;
  }

  box.classList.add("is-pending");
  valueEl.textContent = "…";
  copyEl.textContent = "Checking the next admission number…";

  fetch(`/admin/get_next_admission_no/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      const nextNo = Number(data.admission_no);
      if (!nextNo) {
        throw new Error("Missing admission number");
      }

      box.classList.remove("is-pending");
      valueEl.textContent = String(nextNo);
      copyEl.textContent =
        `Start column A at ${nextNo}, then ${nextNo + 1}, ${nextNo + 2}… Duplicates are skipped.`;

      if (sampleLink) {
        const url = new URL(sampleLink.href, window.location.origin);
        url.searchParams.set("start", String(nextNo));
        sampleLink.href = `${url.pathname}?${url.searchParams.toString()}`;
      }
    })
    .catch(() => {
      box.classList.add("is-pending");
      valueEl.textContent = "—";
      copyEl.textContent = "Could not load the next admission number. Try selecting the school again.";
    });
}
