const branchSelect = document.getElementById("results-branch");
const gradeSelect = document.getElementById("results-grade");
const streamSelect = document.getElementById("results-stream");
const examSelect = document.getElementById("results-exam");
const subjectSelect = document.getElementById("results-subject");

function hideDownloadButton() {
  const downloadBtn = document.getElementById("generate-pdf-btn");
  if (downloadBtn) downloadBtn.classList.add("d-none");
}

// Populate a select element
function populateSelect(
  selectEl,
  items,
  placeholder = "--Select--",
  textKey = "name",
) {
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item[textKey] || item.name || item.grade_form;
    selectEl.appendChild(opt);
  });
}

// Fetch grades when branch changes
branchSelect.addEventListener("change", function () {
  hideDownloadButton();
  const branchId = this.value;
  gradeSelect.innerHTML = '<option value="">--Select Grade--</option>';
  streamSelect.innerHTML = '<option value="">All</option>';
  examSelect.innerHTML = '<option value="">--Select Exam--</option>';
  subjectSelect.innerHTML = '<option value="">--Select Subject--</option>';

  if (!branchId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) =>
      populateSelect(gradeSelect, data, "Select Grade", "grade_form"),
    );
});

// When grade changes, fetch streams and exams
gradeSelect.addEventListener("change", function () {
  hideDownloadButton();
  const branchId = branchSelect.value;
  const classId = this.value;
  streamSelect.innerHTML = '<option value="">All</option>';
  examSelect.innerHTML = '<option value="">--Select Exam--</option>';
  subjectSelect.innerHTML = '<option value="">--Select Subject--</option>';

  if (!branchId || !classId) return;

  // Streams are part of grade object from /api/grades
  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      const gradeObj = data.find((g) => g.id == classId);
      const streams = gradeObj?.streams || [];
      populateSelect(
        streamSelect,
        streams.map((s) => ({ id: s, name: s })),
        "All",
      );
    });

  // Exams
  fetch(`/admin/api/exams?branch_id=${branchId}&class_id=${classId}`)
    .then((res) => res.json())
    .then((data) => populateSelect(examSelect, data, "--Select Exam--"));
});

streamSelect.addEventListener("change", hideDownloadButton);

// When exam changes, fetch subjects
examSelect.addEventListener("change", function () {
  hideDownloadButton();
  const branchId = branchSelect.value;
  const classId = gradeSelect.value;
  const stream = streamSelect.value || null;
  const examId = this.value;

  subjectSelect.innerHTML = '<option value="">--Select Subject--</option>';

  if (!branchId || !classId || !examId) return;

  fetch(
    `/admin/api/subjects?branch_id=${branchId}&class_id=${classId}&stream=${stream}`,
  )
    .then((res) => res.json())
    .then((data) => populateSelect(subjectSelect, data, "--Select Subject--"));
});

fetch("/admin/api/branches")
  .then((res) => res.json())
  .then((data) => {
    if (!branchSelect) return;
    if (window.BushraSchoolSelect) {
      window.BushraSchoolSelect.fill(branchSelect, data, "Select School");
    } else {
      populateSelect(branchSelect, data, "Select School");
    }
  });
