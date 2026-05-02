const bsBranch = document.getElementById("bs-branch");
const bsGrade = document.getElementById("bs-grade");
const bsStream = document.getElementById("bs-stream");
const bsExam = document.getElementById("bs-exam");
const bsBtn = document.getElementById("load-broadsheet");
const bsContainer = document.getElementById("broadsheetContainer");

let currentBroadsheetData = null; // store fetched data for PDF generation

// Load branches
fetch("/admin/api/branches")
  .then((res) => res.json())
  .then((data) => populateSelect(bsBranch, data, "Select Branch"));

// Branch → Grades
bsBranch.addEventListener("change", function () {
  const branchId = this.value;

  bsGrade.innerHTML = '<option value="">--Select Grade--</option>';
  bsStream.innerHTML = '<option value="">All</option>';
  bsExam.innerHTML = '<option value="">--Select Exam--</option>';

  if (!branchId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) =>
      populateSelect(bsGrade, data, "Select Grade", "grade_form"),
    );
});

// Grade → Streams + Exams
bsGrade.addEventListener("change", function () {
  const branchId = bsBranch.value;
  const classId = this.value;

  bsStream.innerHTML = '<option value="">All</option>';
  bsExam.innerHTML = '<option value="">--Select Exam--</option>';

  if (!branchId || !classId) return;

  // Streams
  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      const gradeObj = data.find((g) => g.id == classId);
      const streams = gradeObj?.streams || [];
      populateSelect(
        bsStream,
        streams.map((s) => ({ id: s, name: s })),
        "All",
      );
    });

  // Exams
  fetch(`/admin/api/exams?branch_id=${branchId}&class_id=${classId}`)
    .then((res) => res.json())
    .then((data) => populateSelect(bsExam, data, "--Select Exam--"));
});

bsBtn.addEventListener("click", function () {
  const branchId = bsBranch.value;
  const classId = bsGrade.value;
  const examId = bsExam.value;
  const stream = bsStream.value || null;

  if (!branchId || !classId || !examId) {
    alert("Please select branch, grade and exam.");
    return;
  }

  bsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary mb-2"></div>
            <p class="text-muted">Generating broadsheet...</p>
        </div>
    `;

  fetch(
    `/admin/api/broadsheet?branch_id=${branchId}&class_id=${classId}&exam_id=${examId}&stream=${stream || ""}`,
  )
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        bsContainer.innerHTML = `<p class="text-danger">${data.error}</p>`;
        return;
      }

      currentBroadsheetData = data; // store for PDF generation

      const students = data.students || [];
      const subjects = data.subjects || [];
      const total = data.total_learners || 0;
      const teacher = data.class_teacher || "N/A";
      const subjectAnalysis = data.subject_analysis || {};
      const atRisk = data.at_risk_learners || [];
      const averages = data.subject_averages || {};
      const missing = data.missing_marks || [];

      const gradeName = data.class_name || "";

      function gradeBadge(grade) {
        if (!grade) return "";
        const map = {
          EE: "success",
          ME: "primary",
          AE: "warning",
          BE: "danger",
        };
        return `<span class="badge bg-${map[grade] || "secondary"}">${grade}</span>`;
      }

      function performanceBar(analysis) {
        let totalCount = Object.values(analysis).reduce((a, b) => a + b, 0);
        if (!totalCount) return "";
        let bars = "";
        const colors = {
          EE: "bg-success",
          ME: "bg-primary",
          AE: "bg-warning",
          BE: "bg-danger",
        };
        Object.entries(analysis).forEach(([grade, count]) => {
          const percent = (count / totalCount) * 100;
          bars += `<div class="progress-bar ${colors[grade] || "bg-secondary"}" style="width:${percent}%">${count}</div>`;
        });
        return `<div class="progress" style="height:18px;">${bars}</div>`;
      }

      // ---------------- Header & Cards ----------------
      let html = `
           <div class="card shadow-sm border mb-2">
            <div class="card-body text-center py-4">

                <!-- Branch Name -->
                <h5 class="fw-bold text-uppercase mb-1" style="letter-spacing: 0.78px;">
                <i class="bi bi-mortarboard-fill text-primary me-2"></i>
                ${data.branch_name}
                </h5>

                <!-- Exam Title -->
                <p class="text-muted mb-2" style="font-size: 0.95rem;">
                ${data.exam_name} Broadsheet & Analytics
                </p>

                <!-- Grade + Stream -->
                <div class="fw-semibold text-dark" style="font-size: 0.95rem;">
                <span class="badge bg-light text-dark border px-3 py-2">
                 GRADE/FORM:   ${gradeName} ${stream ? "• " + stream : ""}
                </span>
                </div>

            </div>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-md-3 col-6"><div class="card shadow-sm text-center"><div class="card-body"><i class="bi bi-people-fill text-primary fs-3"></i><h6>Total Learners</h6><h4>${total}</h4></div></div></div>
                <div class="col-md-3 col-6"><div class="card shadow-sm text-center"><div class="card-body"><i class="bi bi-person-badge-fill text-success fs-3"></i><h6>Class Teacher</h6><small>${teacher}</small></div></div></div>
                <div class="col-md-3 col-6"><div class="card shadow-sm text-center"><div class="card-body"><i class="bi bi-exclamation-triangle-fill text-danger fs-3"></i><h6>Needs supports</h6><h4>${atRisk.length}</h4></div></div></div>
                <div class="col-md-3 col-6"><div class="card shadow-sm text-center"><div class="card-body"><i class="bi bi-book-fill text-warning fs-3"></i><h6>Total L. Areas / Subjects</h6><h4>${subjects.length}</h4></div></div></div>
            </div>

            <!-- PDF Buttons -->
            <div class="mb-3 d-flex gap-2 justify-content-end">
                <button id="fullPDFBtn" class="btn btn-sm btn-primary"><i class="bi bi-file-earmark-pdf-fill"></i> Export Full Analysis PDF</button>
                <button id="tablePDFBtn" class="btn btn-sm btn-secondary"><i class="bi bi-file-earmark-pdf"></i> Export Missing Marks Checksheet</button>
            </div>

            <!-- Subject Analysis & Chart -->
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-light fw-bold">
                    <i class="bi bi-bar-chart-fill"></i> Subject Performance Analysis
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-lg-8">`;

      subjects.forEach((subj) => {
        const analysis = subjectAnalysis[subj.id] || {};
        let breakdown = Object.entries(analysis)
          .map(([g, c]) => `${g} (${c})`)
          .join(", ");
        html += `
                    <div class="mb-3">
                        <div class="d-flex justify-content-between">
                            <strong>${subj.name}</strong>
                            <small class="text-muted">${breakdown || "No data"}</small>
                        </div>
                        ${performanceBar(analysis)}
                    </div>`;
      });

      html += `</div><div class="col-lg-4"><canvas id="subjectMeansChart" height="200"></canvas></div></div></div>`;

      // ---------------- At-risk Students Alert ----------------
      if (atRisk.length) {
        html += `<div class="alert alert-danger mx-3">
                    <strong><i class="bi bi-exclamation-octagon-fill"></i> Learners Needing Attention</strong>
                    <ul class="mb-0 mt-2">`;
        atRisk.slice(0, 2).forEach((s) => {
          html += `<li>${s.name} (${s.low_subjects})</li>`;
        });
        if (atRisk.length > 2) {
          html += `<li id="showMoreAtRisk" style="cursor:pointer;"><small class="text-primary">Show more...</small></li>`;
          html += `<div id="hiddenAtRisk" style="display:none;">`;
          atRisk.slice(2).forEach((s) => {
            html += `<li>${s.name} (${s.low_subjects})</li>`;
          });
          html += `</div>`;
        }
        html += `</ul></div>`;
      }

      // ---------------- Table ----------------
      html += `<div class="table-responsive px-3" style="overflow-x:auto; max-height:600px;">
                <table class="table table-bordered table-sm align-middle text-center" style="font-size:0.7rem;">
                    <thead class="table-dark position-sticky top-0">
                        <tr>
                            <th>Adm</th>
                            <th class="text-start">Name</th>`;
      subjects.forEach((subj) => {
        html += `<th>${subj.name}<br><small class="text-warning">${subj.teacher}</small></th>`;
      });
      html += `</tr></thead><tbody>`;

      students.forEach((student) => {
        const isAtRisk = atRisk.some((s) => s.id === student.id);
        html += `<tr ${isAtRisk ? 'class="table-danger"' : ""}>
                    <td>${student.admission_number}</td>
                    <td class="text-start">${student.full_name}</td>`;
        subjects.forEach((subj) => {
          const s = student.marks[subj.id];
          let display = "-";
          if (s && s.marks != "-")
            display = `${s.marks}<br>${gradeBadge(s.grade)}`;
          html += `<td>${display}</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table></div>`;

      // ---------------- Missing Assessment (AFTER TABLE) ----------------
      if (missing.length) {
        html += `
                <div class="card shadow-sm mt-4 mb-4 p-3">
                    <div class="card-header bg-warning fw-bold text-dark">
                        <i class="bi bi-exclamation-circle-fill"></i> Missing Learners Marks
                    </div>
                    <div class="card-body p-2">
                        <div class="table-responsive" style="max-height:300px; overflow-y:auto;">
                            <table class="table table-bordered table-striped table-sm align-middle text-center mb-0" style="font-size:0.8rem;">
                                <thead class="table-dark sticky-top">
                                    <tr">
                                        <th>#</th>
                                        <th>Student Name</th>
                                        <th>No. Missing Marks</th>
                                        <th>Missing Subjects / Learning Areas</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${missing
                                      .map(
                                        (s, index) => `
                                        <tr>
                                            <td>${index + 1}</td>
                                            <td class="text-start">${s.student}</td>
                                            <td>${s.subjects.length}</td>
                                            <td class="text-start text-uppercase">${s.subjects.join(", ")}</td>
                                        </tr>
                                    `,
                                      )
                                      .join("")}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                `;
      }

      bsContainer.innerHTML = html;

      // ---------------- Chart ----------------
      const ctx = document.getElementById("subjectMeansChart").getContext("2d");
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: subjects.map((s) => s.name),
          datasets: [
            {
              label: "Mean Score",
              data: subjects.map((s) => averages[s.id] || 0),
              backgroundColor: "rgba(54,162,235,0.7)",
              borderColor: "rgba(54,162,235,1)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              title: { display: true, text: "Score" },
            },
            x: { title: { display: true, text: "Subjects" } },
          },
        },
      });

      // ---------------- Event Listeners ----------------
      if (atRisk.length > 2) {
        document
          .getElementById("showMoreAtRisk")
          .addEventListener("click", () => {
            const hidden = document.getElementById("hiddenAtRisk");
            hidden.style.display =
              hidden.style.display === "none" ? "block" : "none";
          });
      }

      // PDF Buttons
      document.getElementById("fullPDFBtn").addEventListener("click", () => {
        const branchId = bsBranch.value;
        const classId = bsGrade.value;
        const examId = bsExam.value;
        const stream = bsStream.value || "";

        if (!branchId || !classId || !examId) {
          alert("Please select branch, grade and exam.");
          return;
        }

        // Build query string safely
        const params = new URLSearchParams({
          branch_id: branchId,
          class_id: classId,
          exam_id: examId,
        });

        if (stream) {
          params.append("stream", stream);
        }

        const url = `/admin/api/broadsheet/pdf?${params.toString()}`;

        // ✅ Open PDF in new tab (best UX)
        window.open(url, "_blank");
      });
      document.getElementById("tablePDFBtn").addEventListener("click", () => {
        const branchId = bsBranch.value;
        const classId = bsGrade.value;
        const examId = bsExam.value;
        const stream = bsStream.value || "";

        if (!branchId || !classId || !examId) {
          alert("Please select branch, grade and exam.");
          return;
        }

        const params = new URLSearchParams({
          branch_id: branchId,
          class_id: classId,
          exam_id: examId,
        });

        if (stream) params.append("stream", stream);

        const url = `/admin/api/broadsheet/missing-pdf?${params.toString()}`;

        window.open(url, "_blank");
      });
    })
    .catch((err) => {
      console.error(err);
      bsContainer.innerHTML = `<p class="text-danger">Failed to load broadsheet</p>`;
    });
});
