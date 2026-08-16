function buildUploadSelect(id, name, labelText, required = false) {
  const fragment = document.createDocumentFragment();

  const label = document.createElement("label");
  label.className = required ? "stu-label stu-label-required" : "stu-label";
  label.setAttribute("for", id);
  label.textContent = labelText;

  const select = document.createElement("select");
  select.id = id;
  select.name = name;
  select.className = "form-select form-select-sm stu-control";
  if (required) {
    select.required = true;
  }

  fragment.appendChild(label);
  fragment.appendChild(select);
  return { fragment, select };
}

async function loadGradesStreams(branchId, gradeContainerId, streamContainerId) {
  const gradeContainer = document.getElementById(gradeContainerId);
  const streamContainer = document.getElementById(streamContainerId);

  if (!gradeContainer || !streamContainer) return;

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
  });

  const uploadModal = document.getElementById("uploadModal");
  if (uploadModal) {
    uploadModal.addEventListener("shown.bs.modal", () => {
      if (uploadBranchSelect.value) {
        uploadBranchSelect.dispatchEvent(new Event("change"));
      }
    });
  }
}
