const bsBranch = document.getElementById("bs-branch");
const bsGrade = document.getElementById("bs-grade");
const bsStream = document.getElementById("bs-stream");
const bsExam = document.getElementById("bs-exam");
const bsBtn = document.getElementById("load-broadsheet");
const bsContainer = document.getElementById("broadsheetContainer");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderErrorState(message) {
  bsContainer.innerHTML = `
    <div class="bs-state bs-state-error">
      <i class="bi bi-exclamation-triangle"></i>
      <p class="mb-0">${escapeHtml(message)}</p>
    </div>
  `;
}

function scrollToBroadsheetView() {
  const target = bsContainer.querySelector(".bs-document");
  const scrollContainer = document.querySelector(".main-content");
  if (!target || !scrollContainer) return;

  requestAnimationFrame(() => {
    const offset = 14;
    const containerTop = scrollContainer.getBoundingClientRect().top;
    const targetTop = target.getBoundingClientRect().top;
    const nextScrollTop =
      scrollContainer.scrollTop + (targetTop - containerTop) - offset;

    scrollContainer.scrollTo({
      top: Math.max(0, nextScrollTop),
      behavior: "smooth",
    });
  });
}

function gradeHasStreams() {
  return bsStream.options.length > 1;
}

function requireStreamSelection() {
  if (gradeHasStreams() && !bsStream.value) {
    alert("Please select a stream before continuing.");
    return false;
  }
  return true;
}

function gradeBadge(grade, gradingType = "cbc") {
  if (!grade) return "";

  if (gradingType === "844") {
    const first = String(grade).toUpperCase().trim()[0];
    const map = {
      A: "bs-grade-a",
      B: "bs-grade-b",
      C: "bs-grade-c",
      D: "bs-grade-d",
      E: "bs-grade-e",
    };
    return `<span class="bs-grade-pill ${map[first] || "bs-grade-neutral"}">${escapeHtml(grade)}</span>`;
  }

  const key = String(grade).toUpperCase().slice(0, 2);
  const map = {
    EE: "bs-grade-ee",
    ME: "bs-grade-me",
    AE: "bs-grade-ae",
    BE: "bs-grade-be",
  };
  return `<span class="bs-grade-pill ${map[key] || "bs-grade-neutral"}">${escapeHtml(grade)}</span>`;
}

function getGradeChartColor(label, gradingType) {
  if (gradingType === "844") {
    const map = {
      A: "#198754",
      B: "#0d6efd",
      C: "#ffc107",
      D: "#fd7e14",
      E: "#dc3545",
    };
    return map[String(label).toUpperCase()] || "#adb5bd";
  }

  const map = {
    EE: "#198754",
    ME: "#0d6efd",
    AE: "#ffc107",
    BE: "#dc3545",
  };
  return map[String(label).toUpperCase()] || "#adb5bd";
}

function formatMarkValue(value) {
  if (value === "-" || value == null || value === "") return "—";
  const num = Number(value);
  if (!Number.isNaN(num) && Number.isFinite(num)) {
    return String(Math.round(num));
  }
  return String(value);
}

function formatMarkCell(mark, gradingType) {
  if (!mark || mark.marks === "-") {
    return "<td>—</td>";
  }

  const gradeHtml = gradeBadge(mark.grade, gradingType);
  return `<td><span class="bs-mark-value">${escapeHtml(formatMarkValue(mark.marks))}</span>${gradeHtml}</td>`;
}

function renderPerformanceLegend(gradingType) {
  if (gradingType === "844") {
    return `
      <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-a"></span> A</span>
      <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-b"></span> B</span>
      <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-c"></span> C</span>
      <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-d"></span> D</span>
      <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-e"></span> E</span>
    `;
  }

  return `
    <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-ee"></span> EE</span>
    <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-me"></span> ME</span>
    <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-ae"></span> AE</span>
    <span class="bs-legend-item"><span class="bs-legend-dot bs-progress-be"></span> BE</span>
  `;
}

const GRADE_ORDER_844 = [
  "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "E",
];
const GRADE_ORDER_CBC = ["EE", "ME", "AE", "BE"];

function sortGradeEntries(analysis, gradingType) {
  const order = gradingType === "844" ? GRADE_ORDER_844 : GRADE_ORDER_CBC;
  return order.filter((grade) => analysis[grade]).map((grade) => [grade, analysis[grade]]);
}

function renderSubjectAnalysis(subjects, subjectAnalysis, gradingType) {
  return subjects
    .map((subj) => {
      const analysis = subjectAnalysis[subj.id] || {};
      const entries = sortGradeEntries(analysis, gradingType);

      if (!entries.length) {
        return `
          <div class="bs-bar-card">
            <div class="bs-bar-card-head">
              <span class="bs-bar-title">${escapeHtml(subj.name)}</span>
            </div>
            <div class="bs-bar-empty">No grade data</div>
          </div>
        `;
      }

      const total = entries.reduce((sum, [, count]) => sum + count, 0);
      const maxCount = Math.max(...entries.map(([, count]) => count));
      const stacked = entries
        .map(([grade, count]) => {
          const width = total ? (count / total) * 100 : 0;
          return `<span class="bs-stack-seg bs-grade-${grade.replace("+", "p").replace("-", "m")}" style="width:${width}%" title="${escapeHtml(grade)}: ${count}"></span>`;
        })
        .join("");

      const bars = entries
        .map(([grade, count]) => {
          const width = maxCount ? (count / maxCount) * 100 : 0;
          const gradeClass = `bs-grade-${grade.replace("+", "p").replace("-", "m")}`;
          return `
            <div class="bs-grade-bar-row">
              <span class="bs-grade-bar-label ${gradeClass}">${escapeHtml(grade)}</span>
              <div class="bs-grade-bar-track">
                <div class="bs-grade-bar-fill ${gradeClass}" style="width:${width}%"></div>
              </div>
              <span class="bs-grade-bar-count">${count}</span>
            </div>
          `;
        })
        .join("");

      return `
        <div class="bs-bar-card">
          <div class="bs-bar-card-head">
            <span class="bs-bar-title">${escapeHtml(subj.name)}</span>
            <span class="bs-bar-meta">${total} learner${total === 1 ? "" : "s"}</span>
          </div>
          <div class="bs-stack-bar" aria-hidden="true">${stacked}</div>
          <div class="bs-grade-bars">${bars}</div>
        </div>
      `;
    })
    .join("");
}

function renderAtRiskAlert(atRisk) {
  if (!atRisk.length) return "";

  const visibleItems = atRisk
    .slice(0, 2)
    .map((student) => `<li>${escapeHtml(student.name)} (${escapeHtml(student.low_subjects)})</li>`)
    .join("");

  const hiddenItems = atRisk
    .slice(2)
    .map((student) => `<li>${escapeHtml(student.name)} (${escapeHtml(student.low_subjects)})</li>`)
    .join("");

  const showMore =
    atRisk.length > 2
      ? `
        <li id="showMoreAtRisk" class="bs-show-more">Show ${atRisk.length - 2} more…</li>
        <div id="hiddenAtRisk" style="display:none;">${hiddenItems}</div>
      `
      : "";

  return `
    <div class="bs-alert-risk">
      <strong><i class="bi bi-exclamation-octagon me-1"></i> Learners Needing Attention</strong>
      <ul>${visibleItems}${showMore}</ul>
    </div>
  `;
}

function renderBroadsheetTable(students, subjects, atRisk, gradingType) {
  const headerCells = subjects
    .map(
      (subj) => `
        <th>
          ${escapeHtml(subj.name)}
          ${subj.teacher ? `<span class="bs-teacher">${escapeHtml(subj.teacher)}</span>` : ""}
        </th>
      `,
    )
    .join("");

  const bodyRows = students
    .map((student) => {
      const isAtRisk = atRisk.some((entry) => entry.id === student.id);
      const subjectCells = subjects
        .map((subj) => formatMarkCell(student.marks[subj.id], gradingType))
        .join("");

      return `
        <tr class="${isAtRisk ? "bs-row-risk" : ""}">
          <td>${escapeHtml(student.admission_number)}</td>
          <td class="bs-col-name">${escapeHtml(student.full_name)}</td>
          ${subjectCells}
        </tr>
      `;
    })
    .join("");

  return `
    <div class="bs-section">
      <div class="bs-section-header">
        <h6><i class="bi bi-table me-1"></i> Learner Broadsheet</h6>
        <span class="bs-legend">
          <span class="bs-legend-item"><span class="bs-legend-dot" style="background:#dc3545;"></span> At-risk row</span>
        </span>
      </div>
      <div class="bs-section-body" style="padding:0.55rem;">
        <div class="bs-table-wrap">
          <table class="bs-table">
            <thead>
              <tr>
                <th>Adm</th>
                <th class="text-start">Name</th>
                ${headerCells}
              </tr>
            </thead>
            <tbody>${bodyRows}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderMissingMarks(missing) {
  if (!missing.length) return "";

  const rows = missing
    .map(
      (entry, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${escapeHtml(entry.student)}</td>
          <td class="text-center">${entry.subjects.length}</td>
          <td>${escapeHtml(entry.subjects.join(", "))}</td>
        </tr>
      `,
    )
    .join("");

  return `
    <div class="bs-section">
      <div class="bs-section-header">
        <h6><i class="bi bi-exclamation-circle me-1"></i> Missing Learner Marks</h6>
      </div>
      <div class="bs-section-body">
        <div class="bs-missing-wrap">
          <table class="bs-missing-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Missing</th>
                <th>Subjects / Learning Areas</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderBroadsheetDocument(data, stream) {
  const gradingType = data.grading_type === "844" ? "844" : "cbc";
  const gradingLabel = gradingType === "844" ? "8-4-4" : "CBC";
  const students = data.students || [];
  const subjects = data.subjects || [];
  const total = data.total_learners || 0;
  const teacher = data.class_teacher || "Not assigned";
  const subjectAnalysis = data.subject_analysis || {};
  const atRisk = data.at_risk_learners || [];
  const averages = data.subject_averages || {};
  const missing = data.missing_marks || [];
  const gradeName = data.class_name || "";
  const streamLabel = stream ? ` · ${stream}` : "";

  return `
    <div class="bs-document">
      <header class="bs-doc-header">
        <h2 class="bs-school-name">${escapeHtml(data.branch_name || "")}</h2>
        <p class="bs-doc-subtitle">${escapeHtml(data.exam_name || "")} · Broadsheet &amp; Analytics</p>
        <div class="bs-doc-meta">
          <span>Grade/Form <strong>${escapeHtml(gradeName)}${escapeHtml(streamLabel)}</strong></span>
          <span>System <strong>${gradingLabel}</strong></span>
          <span>Learners <strong>${total}</strong></span>
          <span>Subjects <strong>${subjects.length}</strong></span>
        </div>
      </header>

      <div class="bs-stats-grid">
        <div class="bs-stat-card">
          <span class="bs-stat-icon bs-stat-icon-primary"><i class="bi bi-people"></i></span>
          <div>
            <span class="bs-stat-label">Total Learners</span>
            <span class="bs-stat-value">${total}</span>
          </div>
        </div>
        <div class="bs-stat-card">
          <span class="bs-stat-icon bs-stat-icon-success"><i class="bi bi-person-badge"></i></span>
          <div>
            <span class="bs-stat-label">Class Teacher</span>
            <span class="bs-stat-value bs-stat-value-sm">${escapeHtml(teacher)}</span>
          </div>
        </div>
        <div class="bs-stat-card">
          <span class="bs-stat-icon bs-stat-icon-danger"><i class="bi bi-exclamation-triangle"></i></span>
          <div>
            <span class="bs-stat-label">Needs Support</span>
            <span class="bs-stat-value">${atRisk.length}</span>
          </div>
        </div>
        <div class="bs-stat-card">
          <span class="bs-stat-icon bs-stat-icon-warning"><i class="bi bi-book"></i></span>
          <div>
            <span class="bs-stat-label">Learning Areas</span>
            <span class="bs-stat-value">${subjects.length}</span>
          </div>
        </div>
      </div>

      <div class="bs-action-bar">
        <button type="button" id="fullPDFBtn" class="bs-btn bs-btn-primary">
          <i class="bi bi-file-earmark-pdf"></i> Full Analysis PDF
        </button>
        <button type="button" id="tablePDFBtn" class="bs-btn bs-btn-outline">
          <i class="bi bi-clipboard-check"></i> Missing Marks PDF
        </button>
      </div>

      ${renderAtRiskAlert(atRisk)}
      ${renderBroadsheetTable(students, subjects, atRisk, gradingType)}
      ${renderMissingMarks(missing)}
      ${renderSubjectPerformanceSection(subjects, subjectAnalysis, gradingType)}
    </div>
  `;
}

function renderSubjectPerformanceSection(subjects, subjectAnalysis, gradingType) {
  return `
      <div class="bs-section">
        <div class="bs-section-header">
          <h6><i class="bi bi-bar-chart me-1"></i> Subject Performance Analysis</h6>
          <div class="bs-legend">${renderPerformanceLegend(gradingType)}</div>
        </div>
        <div class="bs-section-body">
          <div class="bs-analysis-layout">
            <div class="bs-bar-grid">
              ${renderSubjectAnalysis(subjects, subjectAnalysis, gradingType)}
            </div>
            <div class="bs-means-section">
              <div class="bs-means-title">Mean Scores by Subject</div>
              <div class="bs-chart-panel">
                <canvas id="subjectMeansChart"></canvas>
              </div>
            </div>
          </div>
        </div>
      </div>
  `;
}

function bindBroadsheetActions(averages, subjects, subjectAnalysis, gradingType) {
  if (atRiskToggleNeeded()) {
    document.getElementById("showMoreAtRisk")?.addEventListener("click", () => {
      const hidden = document.getElementById("hiddenAtRisk");
      if (!hidden) return;
      hidden.style.display = hidden.style.display === "none" ? "block" : "none";
    });
  }

  document.getElementById("fullPDFBtn")?.addEventListener("click", () => {
    openBroadsheetPdf("/admin/api/broadsheet/pdf");
  });

  document.getElementById("tablePDFBtn")?.addEventListener("click", () => {
    openBroadsheetPdf("/admin/api/broadsheet/missing-pdf");
  });

  const chartCanvas = document.getElementById("subjectMeansChart");
  if (!chartCanvas || typeof Chart === "undefined") return;

  new Chart(chartCanvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: subjects.map((subject) => subject.name),
      datasets: [
        {
          label: "Mean Score",
          data: subjects.map((subject) => Math.round(averages[subject.id] || 0)),
          backgroundColor: "rgba(255, 121, 121, 0.75)",
          borderColor: "rgba(255, 121, 121, 1)",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: "rgba(0,0,0,0.06)" },
          ticks: {
            font: { size: 10 },
            callback: (value) => Math.round(value),
          },
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 9 }, maxRotation: 45, minRotation: 0 },
        },
      },
    },
  });
}

function atRiskToggleNeeded() {
  return Boolean(document.getElementById("showMoreAtRisk"));
}

function openBroadsheetPdf(path) {
  const branchId = bsBranch.value;
  const classId = bsGrade.value;
  const examId = bsExam.value;
  const stream = bsStream.value || "";

  if (!branchId || !classId || !examId) {
    alert("Please select school, grade, and exam.");
    return;
  }

  if (!requireStreamSelection()) return;

  if (typeof blockUI === "function") {
    blockUI("Generating PDF", "Preparing analysis report…");
  }

  const params = new URLSearchParams({
    branch_id: branchId,
    class_id: classId,
    exam_id: examId,
  });

  if (stream) {
    params.append("stream", stream);
  }

  window.open(`${path}?${params.toString()}`, "_blank");

  window.setTimeout(() => {
    if (typeof unblockUI === "function") unblockUI();
  }, 1500);
}

fetch("/admin/api/branches")
  .then((res) => res.json())
  .then((data) => populateSelect(bsBranch, data, "Select School"));

bsBranch.addEventListener("change", function () {
  const branchId = this.value;

  bsGrade.innerHTML = '<option value="">--Select Grade--</option>';
  bsStream.innerHTML = '<option value="">All</option>';
  bsExam.innerHTML = '<option value="">--Select Exam--</option>';
  bsContainer.innerHTML = "";

  if (!branchId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => populateSelect(bsGrade, data, "Select Grade", "grade_form"));
});

bsGrade.addEventListener("change", function () {
  const branchId = bsBranch.value;
  const classId = this.value;

  bsStream.innerHTML = '<option value="">All</option>';
  bsExam.innerHTML = '<option value="">--Select Exam--</option>';
  bsContainer.innerHTML = "";

  if (!branchId || !classId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      const gradeObj = data.find((grade) => grade.id == classId);
      const streams = gradeObj?.streams || [];
      populateSelect(
        bsStream,
        streams.map((stream) => ({ id: stream, name: stream })),
        streams.length ? "--Select Stream--" : "All",
      );
    });

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
    alert("Please select school, grade, and exam.");
    return;
  }

  if (!requireStreamSelection()) return;

  if (typeof blockUI === "function") {
    blockUI("Generating broadsheet", "Loading analytics and performance data…");
  }

  fetch(
    `/admin/api/broadsheet?branch_id=${branchId}&class_id=${classId}&exam_id=${examId}&stream=${stream || ""}`,
  )
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        renderErrorState(data.error);
        return;
      }

      const subjects = data.subjects || [];
      const averages = data.subject_averages || {};
      const gradingType = data.grading_type === "844" ? "844" : "cbc";

      bsContainer.innerHTML = renderBroadsheetDocument(data, stream);
      bindBroadsheetActions(
        averages,
        subjects,
        data.subject_analysis || {},
        gradingType,
      );
      scrollToBroadsheetView();
    })
    .catch((err) => {
      console.error(err);
      renderErrorState("Failed to load broadsheet. Please try again.");
    })
    .finally(() => {
      if (typeof unblockUI === "function") unblockUI();
    });
});
