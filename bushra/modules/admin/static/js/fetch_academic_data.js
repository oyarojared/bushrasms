document.addEventListener("DOMContentLoaded", function () {
  // ---------------------- DOM ELEMENTS ----------------------
  const branchSelect = document.querySelector("form select[name='branches']");
  const container = document.getElementById("academicDataContainer");
  const branchClassesDiv = document.querySelector(".form-select-div");
  const subjectContainer = document.querySelector(".subject-select-div");

  const statusBox = document.getElementById("statusBox");
  const statusText = document.getElementById("statusText");
  const spinner = document.getElementById("statusSpinner");

  function clearStudentsList() {
    const studentContainer = document.querySelector(".students-allocation-div");
    if (studentContainer) {
      studentContainer.innerHTML = "";
    }
  }

  function scrollPageUp() {
    statusBox.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  // SHOW STATUS FUNCTIONS
  function showloading(message = "Loading...") {
    statusBox.className = "alert alert-info d-flex";
    statusText.textContent = message;
    spinner.classList.remove("d-none");
    scrollPageUp();
  }

  function showsuccess(
    message = "Operation was successfully.",
    category = "success",
  ) {
    statusBox.className = `alert alert-${category} d-flex`;
    statusText.textContent = message;
    spinner.classList.add("d-none");
    scrollPageUp();

    setTimeout(() => {
      statusBox.classList.add("d-none");
    }, 3000);
  }

  function showserror(message = "Something went wrong") {
    statusBox.className = "alert alert-danger d-danger";
    statusText.textContent = message;
    spinner.classList.add("d-none");
    scrollPageUp();

    setTimeout(() => {
      statusBox.classList.add("d-none");
    }, 4000);
  }

  if (!branchSelect || !container) return;

  // ---------------------- BRANCH SELECTION ----------------------
  branchSelect.addEventListener("change", function () {
    subjectContainer.innerHTML = ""; // Clear subjects input
    clearStudentsList();

    const branchId = this.value;

    if (branchId === "") {
      branchClassesDiv.innerHTML = `
                <h6 class='small fw-bold text-danger'>Please select a valid branch!</h6>
            `;
    }

    if (!branchId) {
      container.innerHTML = `<div class="text-danger fw-bold">Select a branch to view academic data.</div>`;
      return;
    }

    container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center py-4 text-success">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span class="h6">Loading branch data…</span>
            </div>
        `;

    fetch(`/admin/branches/${branchId}/academic-data`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch data");
        return res.json();
      })
      .then((response) => {
        if (response.status !== "success")
          throw new Error(response.message || "Error loading data");
        renderAcademicData(response.data);
      })
      .catch((err) => {
        console.error(err);
        container.innerHTML = `
                    <div class="text-danger">
                       <i class="bi bi-x-circle-fill me-2"></i>
                        Failed to load branch data! Something went wrong.
                    </div>
                `;
      });
  });

  // ---------------------- RENDER ACADEMIC DATA ----------------------
  function renderAcademicData(data) {
    // Branch header
    let html = `
            <div class="mb-3">
                <h6 class="fw-bold text-secondary">
                    <i class="bi bi-building me-2"></i>${data.branch_name}
                </h6>
            </div>
        `;

    if (!data.grades || !data.grades.length) {
      container.innerHTML = `
                <div class="text-danger fw-bold">
                    <i class="bi bi-x-circle-fill me-2"></i>No academic records found for this branch.
                </div>
            `;
      branchClassesDiv.innerHTML = `
                <small class='text-danger fw-bold'>
                    <i class="bi bi-x-circle-fill me-2"></i>No classes found!
                </small>
            `;
      subjectContainer.innerHTML = "";
      return;
    }

    html += `<div class="row g-3 fix-top-customized">`;

    // Render grades and streams
    data.grades.forEach((g) => {
      html += `
                <div class="col-md-6 col-lg-4">
                    <div class="p-3 border rounded-3 shadow-sm h-100 bg-white">
                        <div class="container orange-line mb-2"></div>
                        <!-- Grade Header -->
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <h5 class="fw-bold mb-0 text-orange text-uppercase">
                                <i class="bi bi-journal-text me-2"></i>${g.grade_form}
                            </h5>
                            <span class="badge bg-info p-2">Total: ${g.totals.total}</span>
                        </div>

                        <!-- Totals -->
                        <div class="d-flex justify-content-between small text-muted mb-3">
                            <div><i class="bi bi-gender-male me-1 h5"></i>Boys: <strong class="text-primary">${g.totals.boys}</strong></div>
                            <div><i class="bi bi-gender-female me-1 h5"></i>Girls: <strong class="text-success">${g.totals.girls}</strong></div>
                        </div>

                        <!-- Streams -->
                        <div>
                            <div class="fw-semibold small text-secondary mb-1">Streams</div>
                            <button class="btn btn-sm btn-outline-danger mb-2 delete-grade-btn"
                                    type="button"
                                    data-grade="${g.class_id}"
                                    data-branch="${data.branch_id}">
                                <i class="bi bi-trash me-1"></i>Delete Grade/Form
                            </button>

            `;

      if (g.streams && g.streams.length) {
        g.streams.forEach((s) => {
          html += `
                        <div class="border rounded-2 p-2 mb-1 bg-light">
                            <div class="d-flex justify-content-between align-items-center">
                                <strong class="small text-dark">${s.name}</strong>
                                <span class="badge bg-light text-dark border">${s.total}</span>
                            </div>
                            <div class="d-flex justify-content-between small text-muted mt-1">
                                <span>B: ${s.boys}</span>
                                <span>G: ${s.girls}</span>
                            </div>
                        </div>
                        <div>
                            <h6 class="small text-center mt-2 text-success">Classteacher: <span class="text-muted text-uppercase">
                             ${s.teacher?.name || "Not assigned"}</span>
                        </div>
                        <button class="btn btn-sm btn-outline-danger mb-2 delete-stream-btn"
                                type="button"
                                data-grade="${g.class_id}"
                                data-stream="${s.name}"
                                data-branch="${data.branch_id}">
                            <i class="bi bi-trash me-1"></i>Delete Stream
                        </button>

                    `;
        });
      } else {
        html += `
                    <div class="text-muted small fst-italic">No streams available</div>
                    <div>
                        <h6 class="small text-center mt-2 text-success">Classteacher: <span class="text-muted text-uppercase">
                       ${g.teacher?.name || "Not assigned"}</span>
                        </h6>
                    </div>
                    `;
      }

      html += `</div></div></div>`;
    });

    html += `</div>`;
    container.innerHTML = html;

    // ---------------------- BUILD GRADE SELECT ----------------------
    buildGradeSelect(data);

    container.addEventListener("click", function (e) {
      // ---------------------- DELETE GRADE ----------------------
      function deleteGrade(branchId, gradeId) {
        fetch(`/admin/grades/force-delete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            branch_id: branchId,
            grade_id: gradeId,
          }),
        })
          .then((res) => res.json())
          .then((data) => {
            alert(data.message);
            // loadAcademicData(branchId); // refresh UI
            window.location.reload();
          });
      }

      // DELETE GRADE
      if (e.target.closest(".delete-grade-btn")) {
        const btn = e.target.closest(".delete-grade-btn");

        const branchId = btn.dataset.branch;
        const gradeId = btn.dataset.grade;

        if (!confirm("Delete this grade and all its streams?")) return;

        deleteGrade(branchId, gradeId);
      }

      // ---------------------- DELETE STREAM ----------------------
      function deleteStream(branchId, gradeId, streamName) {
        fetch(`/admin/streams/force-delete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            branch_id: branchId,
            grade_id: gradeId,
            stream_name: streamName,
          }),
        })
          .then((res) => res.json())
          .then((data) => {
            alert(data.message);
            loadAcademicData(branchId);
          });
      }

      // DELETE STREAM
      if (e.target.closest(".delete-stream-btn")) {
        const btn = e.target.closest(".delete-stream-btn");

        const branchId = btn.dataset.branch;
        const gradeId = btn.dataset.grade;
        const stream = btn.dataset.stream;

        if (!confirm(`Delete stream "${stream}"?`)) return;

        deleteStream(branchId, gradeId, stream);
      }
    });
  }

  // ---------------------- BUILD GRADE SELECT ----------------------
  function buildGradeSelect(data) {
    branchClassesDiv.innerHTML = "";
    const inputGroup = document.createElement("div");
    inputGroup.classList.add("input-group", "mb-3");

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("input-group-text");
    iconSpan.innerHTML = '<i class="bi bi-mortarboard"></i>';

    const label = document.createElement("label");
    label.setAttribute("for", "classSelect");
    label.classList.add("form-label", "me-2", "small");
    label.textContent = "Grade / Form:";

    const select = document.createElement("select");
    select.classList.add("form-select");
    select.name = "class_id";
    select.id = "classSelect";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "-- Select Class --";
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    data.grades.forEach((grade) => {
      const option = document.createElement("option");
      option.value = grade.grade_form;
      option.textContent = grade.grade_form;
      select.appendChild(option);
    });

    inputGroup.appendChild(iconSpan);
    inputGroup.appendChild(select);
    branchClassesDiv.appendChild(label);
    branchClassesDiv.appendChild(inputGroup);

    // Save hidden branch id
    const hiddenBranchIdInput = document.getElementById("selected-branch-id");
    if (hiddenBranchIdInput) hiddenBranchIdInput.value = data.branch_id;

    // Add grade change listener
    select.addEventListener("change", function () {
      clearStudentsList();

      const gradeForm = this.value;
      if (!gradeForm) return;

      subjectContainer.innerHTML = `
                <div class="d-flex justify-content-center align-items-center py-4 text-success">
                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                    <span class="h6">Loading subjects…</span>
                </div>
            `;

      fetch(
        `/admin/subjects/by-grade-json?grade_form=${encodeURIComponent(gradeForm)}`,
      )
        .then((res) => res.json())
        .then((subjects) => buildSubjectSelect(subjects))
        .catch((err) => console.error(err));
    });
  }

  // ---------------------- BUILD SUBJECT SELECT ----------------------
  function buildSubjectSelect(subjects) {
    if (!subjectContainer) return;
    subjectContainer.innerHTML = "";

    if (!subjects || subjects.length === 0) {
      subjectContainer.innerHTML = `
                <div class="text-danger mt-5 small fw-bold">
                    <i class="bi bi-x-circle-fill me-2"></i>No subjects found
                    .<span class="fw-light">(Go to subjects and assign some subjects/L. Areas to this class.)</span>
                </div>
            `;
      return;
    }

    const label = document.createElement("label");
    label.setAttribute("for", "subjectSelect");
    label.classList.add("form-label", "fw-semibold", "mb-1", "small");
    label.textContent = "Select Subject";

    const inputGroup = document.createElement("div");
    inputGroup.classList.add("input-group", "mb-3");

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("input-group-text");
    iconSpan.innerHTML = '<i class="bi bi-book"></i>';

    const select = document.createElement("select");
    select.classList.add("form-select");
    select.id = "subjectSelect";
    select.name = "subject_id";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "-- Select Subject --";
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    subjects.forEach((sub) => {
      const option = document.createElement("option");
      option.value = sub.id;
      option.textContent = sub.name;
      select.appendChild(option);
    });

    inputGroup.appendChild(iconSpan);
    inputGroup.appendChild(select);
    subjectContainer.appendChild(label);
    subjectContainer.appendChild(inputGroup);

    // Add subject change listener
    select.addEventListener("change", function () {
      // Add spinner has student data is loaded
      const studentContainer = document.querySelector(
        ".students-allocation-div",
      );
      studentContainer.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                </div>
            `;
      const subjectId = this.value;
      if (!subjectId) return;

      const branchId = document.getElementById("selected-branch-id").value;
      const gradeForm = document.getElementById("classSelect").value;

      fetch("/admin/students/by-class-subject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branch_id: branchId,
          grade_form: gradeForm,
          subject_id: subjectId,
        }),
      })
        .then((res) => res.json())
        .then((students) => {
          renderStudentsTable(students);
          // Scroll page up
          document.getElementById("student-table").scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        })
        .catch((err) => console.error(err));
    });
  }

  // ---------------------- RENDER STUDENTS TABLE ----------------------
  function renderStudentsTable(students) {
    const container = document.querySelector(".students-allocation-div");
    if (!container) return;

    // Clear previous content
    container.innerHTML = "";

    if (!students["students"] || students["students"].length === 0) {
      container.innerHTML = `
            <div class="text-danger small">
                <i class="bi bi-x-circle-fill me-2"></i>No students found for this class.
            </div>
        `;
      return;
    }

    // Table header + buttons
    let html = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="row w-75">
                <div class="col-md-6 small text-secondary">
                    Total: 
                    <span class="badge bg-primary small fw-bold mx-2">
                        ${students["students"].length} students
                    </span>
                </div>
                <div class="col-md-6 small text-secondary">
                    Done by:<span id="doneByStudentsCount" class="badge bg-success small fw-bold mx-2">
                        ${students["allocated_count"]} students
                    </span>
                </div>
            </div>
           
            <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-danger mx-2" id="allocateAllBtn">Allocate to ALL</button>
                <button type="button" class="btn btn-danger" id="applyAllocationBtn">Apply Allocation</button>
            </div>
        </div>
        <div id="student-table" class="fix-top-customized-lg">
            <table class="table table-sm table-bordered align-middle small">
                <thead class="bg-secondary text-white">
                    <tr>
                        <th style="width:80px;" class="text-center">ADM NO</th>
                        <th>STUDENT FULL NAME</th>
                        <th style="width:40px;" class="text-center">ASSIGN</th>
                    </tr>
                </thead>
                <tbody style="background: #f3f3f3 !important">
    `;

    // Add rows for each student
    students["students"].forEach((student) => {
      html += `
            <tr>
                <td class="text-center">${student.admission_number}</td>
                <td class="text-uppercase">${student.fullname}</td>
                <td class="text-center">
                <input
                    type="checkbox"
                    class="form-check-input student-checkbox"
                    data-student-id="${student.id}"
                    ${student.allocated ? "checked" : ""}
                    style="transform: scale(1.5);"
                >
                </td>
            </tr>
        `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;

    // ---------------------- ALLOCATE ALL BUTTON ----------------------
    const allocateAllBtn = document.getElementById("allocateAllBtn");
    if (allocateAllBtn) {
      allocateAllBtn.addEventListener("click", () => {
        document
          .querySelectorAll(".student-checkbox")
          .forEach((cb) => (cb.checked = true));
      });
    }

    // ---------------------- APPLY ALLOCATION BUTTON ----------------------
    const applyBtn = document.getElementById("applyAllocationBtn");
    if (applyBtn) {
      applyBtn.addEventListener("click", () => {
        const branchId = document.getElementById("selected-branch-id")?.value;
        const gradeForm = document.getElementById("classSelect")?.value;
        const subjectId = document.getElementById("subjectSelect")?.value;

        if (!branchId || !gradeForm || !subjectId) {
          alert(
            "One of the following is not selectd: Branch, Class or Subject",
          );
          return;
        }

        // Collect selected students
        const selectedStudents = Array.from(
          document.querySelectorAll(".student-checkbox:checked"),
        ).map((cb) => parseInt(cb.dataset.studentId));

        const payload = {
          branch_id: branchId,
          grade_form: gradeForm,
          subject_id: parseInt(subjectId),
          students: selectedStudents,
        };

        console.log("Allocation payload:", payload);

        showloading((message = "Applying allocations..."));

        fetch("/admin/subjects/allocate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
          .then((res) => res.json())
          .then((data) => {
            if (data.status === "success") {
              if (data["added_count"]) {
                showsuccess(
                  (message = `${data["added_count"]} students allocated successfully! (${data.already_allocated_count} were already allocated)`),
                );
              } else {
                showsuccess(
                  (message = `No new student(s) allocation! (${data.already_allocated_count} were already allocated)`),
                  (category = "warning"),
                );
              }

              // Ensure allocated students are checked
              selectedStudents.forEach((sid) => {
                const checkbox = document.querySelector(
                  `.student-checkbox[data-student-id='${sid}']`,
                );
                if (checkbox) checkbox.checked = true;
              });

              document.getElementById("doneByStudentsCount").textContent = `
                        ${Number(data["added_count"]) + Number(data.already_allocated_count)}
                    students.
                    `;
            } else {
              showserror(
                (message = "Failed to allocate subjects. Please try again."),
              );
            }
          })
          .catch((err) => {
            console.error(err);
            showserror(
              "Error while allocating subjects. Please check your internet connection.",
            );
          });
      });
    }
  }
});
