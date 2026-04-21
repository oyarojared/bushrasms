const branchSelect = document.getElementById("results-branch");
const gradeSelect = document.getElementById("results-grade");
const streamSelect = document.getElementById("results-stream");
const examSelect = document.getElementById("results-exam");
const subjectSelect = document.getElementById("results-subject");
const loadResultsBtn = document.getElementById("load-results");
const resultsContainer = document.querySelector("#resultsContainer");

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

// Fetch branches
fetch("/admin/api/branches")
  .then((res) => res.json())
  .then((data) => populateSelect(branchSelect, data, "Select Branch"));

// Fetch grades when branch changes
branchSelect.addEventListener("change", function () {
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

// When exam changes, fetch subjects
examSelect.addEventListener("change", function () {
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

// Load results on button click
loadResultsBtn.addEventListener("click", function () {
  const branchId = branchSelect.value;
  const classId = gradeSelect.value;
  const stream = streamSelect.value || null;
  const examId = examSelect.value;
  const subjectId = subjectSelect.value;

  if (!branchId || !classId || !examId) {
    alert("Please select branch, grade, and exam.");
    return;
  }

  resultsContainer.innerHTML = `<tr><td colspan="6" class="text-center">Loading...</td></tr>`;

  // Use your API that returns students with resolved grades
  fetch(
    `/admin/api/exam-students-with-grades?branch_id=${branchId}&class_id=${classId}&exam_id=${examId}&subject_id=${subjectId}&stream=${stream}`,
  )
    .then((res) => res.json())
    .then((data) => {
      resultsContainer.innerHTML = "";
      const students = data.students || [];

      if (students.length === 0) {
        resultsContainer.innerHTML = `
                    <tr><td colspan="6" class="text-center">
                       <div class="d-flex justify-content-center align-items-center py-4 text-success">
                            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                            <span class="h6">Please wait, Generating result…</span>
                        </div>
                    </td></tr>
                `;
        return;
      }

      students.forEach((s) => {
        // report cards here
      });
    })
    .catch((err) => {
      console.error(err);
      resultsContainer.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading results.</td></tr>`;
    });
});
