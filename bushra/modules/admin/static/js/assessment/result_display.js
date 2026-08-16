function getResultsContext() {
  const gradeSelect = document.getElementById("results-grade");
  const examSelect = document.getElementById("results-exam");
  const streamSelect = document.getElementById("results-stream");
  const branchSelect = document.getElementById("results-branch");

  const streamValue = streamSelect.value;
  const streamLabel =
    streamValue && streamValue !== ""
      ? streamValue
      : streamSelect.selectedOptions[0]?.textContent?.trim() || "All Streams";

  return {
    schoolName: branchSelect.selectedOptions[0]?.textContent?.trim() || "",
    className: gradeSelect.selectedOptions[0]?.textContent?.trim() || "",
    examName: examSelect.selectedOptions[0]?.textContent?.trim() || "",
    streamLabel,
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function performanceBadgeClass(level) {
  const value = Number(level);
  if (Number.isNaN(value)) return "level-neutral";
  if (value >= 7) return "level-exceeds";
  if (value >= 5) return "level-meets";
  if (value >= 3) return "level-approaching";
  return "level-below";
}

function renderSubjectRows(subjects) {
  return subjects
    .map(
      (sub) => `
      <tr>
        <td class="text-center subject-code">${escapeHtml(sub.code || "-")}</td>
        <td class="subject-name">${escapeHtml(sub.name || "-")}</td>
        <td class="text-center subject-marks">${sub.marks ?? "-"}</td>
        <td class="text-center">
          <span class="performance-badge ${performanceBadgeClass(sub.performance_level)}">
            ${escapeHtml(sub.performance_level ?? "-")}
          </span>
        </td>
        <td class="text-center">${sub.points ?? "-"}</td>
        <td class="subject-descriptor">${escapeHtml(sub.descriptor || "-")}</td>
        <td class="text-center subject-teacher">${escapeHtml(sub.teacher || "-")}</td>
      </tr>
    `,
    )
    .join("");
}

function renderSubjectCards(subjects) {
  return subjects
    .map(
      (sub) => `
      <div class="subject-score-card">
        <div class="subject-score-card-head">
          <div>
            <div class="subject-score-card-code">${escapeHtml(sub.code || "-")}</div>
            <div class="subject-score-card-name">${escapeHtml(sub.name || "-")}</div>
          </div>
          <span class="performance-badge ${performanceBadgeClass(sub.performance_level)}">
            L${escapeHtml(sub.performance_level ?? "-")}
          </span>
        </div>
        <div class="subject-score-card-grid">
          <div class="score-metric">
            <span>Marks</span>
            <strong>${sub.marks ?? "-"}</strong>
          </div>
          <div class="score-metric">
            <span>Points</span>
            <strong>${sub.points ?? "-"}</strong>
          </div>
          <div class="score-metric score-metric-wide">
            <span>Descriptor</span>
            <strong>${escapeHtml(sub.descriptor || "-")}</strong>
          </div>
          <div class="score-metric">
            <span>Teacher</span>
            <strong>${escapeHtml(sub.teacher || "-")}</strong>
          </div>
        </div>
      </div>
    `,
    )
    .join("");
}

function renderStudentResultCard(student, context) {
  const totalPoints = student.subjects.reduce(
    (sum, sub) => sum + (sub.points || 0),
    0,
  );
  const maxPoints = student.subjects.length * 8;
  const percentage =
    maxPoints > 0 ? Math.round((totalPoints / maxPoints) * 100) : 0;

  return `
    <article class="student-result-card">
      <header class="student-result-header">
        <div class="student-result-heading">
          <p class="student-result-kicker">Academic Performance</p>
          <h5 class="student-result-name">${escapeHtml(student.full_name)}</h5>
          <p class="student-result-context">
            ${escapeHtml(context.examName)}
            <span class="context-separator">•</span>
            ${escapeHtml(context.className)}
            <span class="context-separator">•</span>
            ${escapeHtml(context.streamLabel)}
          </p>
        </div>
        <div class="student-result-summary">
          <div class="summary-pill">
            <span class="summary-value">${totalPoints}</span>
            <span class="summary-label">Total Points</span>
          </div>
          <div class="summary-pill summary-pill-muted">
            <span class="summary-value">${percentage}%</span>
            <span class="summary-label">of ${maxPoints} max</span>
          </div>
        </div>
      </header>

      <div class="student-result-meta">
        <div class="meta-chip">
          <i class="bi bi-hash"></i>
          <span>Adm No: <strong>${escapeHtml(student.admission_number || "-")}</strong></span>
        </div>
        <div class="meta-chip">
          <i class="bi bi-card-text"></i>
          <span>Assessment No: <strong>${escapeHtml(student.assessment_no || "-")}</strong></span>
        </div>
        ${
          student.pathway
            ? `<div class="meta-chip"><i class="bi bi-signpost-split"></i><span>Pathway: <strong>${escapeHtml(student.pathway)}</strong></span></div>`
            : ""
        }
        <div class="meta-chip">
          <i class="bi bi-house-door"></i>
          <span>School: <strong>${escapeHtml(context.schoolName)}</strong></span>
        </div>
      </div>

      <div class="student-result-body">
        <div class="student-result-section-title">
          <i class="bi bi-table me-1"></i> Subject Performance
        </div>

        <div class="d-none d-md-block table-responsive student-result-table-wrap">
          <table class="table table-sm student-result-table">
            <thead>
              <tr>
                <th class="text-center">Code</th>
                <th>Subject</th>
                <th class="text-center">Marks</th>
                <th class="text-center">Level</th>
                <th class="text-center">Points</th>
                <th>Descriptor</th>
                <th class="text-center">Teacher</th>
              </tr>
            </thead>
            <tbody>
              ${renderSubjectRows(student.subjects)}
            </tbody>
          </table>
        </div>

        <div class="d-md-none student-subject-cards">
          ${renderSubjectCards(student.subjects)}
        </div>
      </div>

      <footer class="student-result-footer">
        <div class="footer-item">
          <span class="footer-label">Class Teacher</span>
          <span class="footer-value">${escapeHtml(student.class_teacher || "Not assigned")}</span>
        </div>
        ${
          student.remarks
            ? `<div class="footer-item footer-item-remarks"><span class="footer-label">Remarks</span><span class="footer-value">${escapeHtml(student.remarks)}</span></div>`
            : ""
        }
        <div class="footer-generated">
          Generated on ${new Date().toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </div>
      </footer>
    </article>
  `;
}

function setDownloadButtonVisible(visible) {
  const downloadBtn = document.getElementById("generate-pdf-btn");
  if (!downloadBtn) return;
  downloadBtn.classList.toggle("d-none", !visible);
}

async function loadReportCards(branchId, classId, examId, stream = null) {
  const container = document.getElementById("resultsContainer");
  const context = getResultsContext();

  setDownloadButtonVisible(false);
  blockUI("Fetching student results", "Loading academic performance data…");

  try {
    const res = await fetch(
      `/admin/api/exam-students-with-grades-all-subjects?branch_id=${branchId}&class_id=${classId}&exam_id=${examId}&stream=${stream}`,
    );
    const data = await res.json();
    const students = data.students || [];

    if (students.length === 0) {
      container.innerHTML = `
        <div class="results-state results-state-empty">
          <i class="bi bi-inbox"></i>
          <p>No students found for this selection.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="results-summary-bar">
        <div>
          <strong>${students.length}</strong>
          <span>student${students.length === 1 ? "" : "s"} loaded</span>
        </div>
        <div class="results-summary-context">
          ${escapeHtml(context.examName)} · ${escapeHtml(context.className)}
        </div>
      </div>
      <div class="student-results-list">
        ${students.map((student) => renderStudentResultCard(student, context)).join("")}
      </div>
    `;

    setDownloadButtonVisible(true);
  } catch (err) {
    console.error(err);
    container.innerHTML = `
      <div class="results-state results-state-error">
        <i class="bi bi-exclamation-triangle"></i>
        <p>Failed to load results. Please try again.</p>
      </div>
    `;
  } finally {
    unblockUI();
  }
}

document.getElementById("load-results").addEventListener("click", () => {
  const branchId = document.getElementById("results-branch").value;
  const classId = document.getElementById("results-grade").value;
  const examId = document.getElementById("results-exam").value;
  const stream = document.getElementById("results-stream").value || null;

  if (!branchId || !classId || !examId) {
    alert("Please select school, grade, and exam.");
    return;
  }

  loadReportCards(branchId, classId, examId, stream);
});

document.getElementById("generate-pdf-btn").addEventListener("click", () => {
  const branchId = document.getElementById("results-branch").value;
  const classId = document.getElementById("results-grade").value;
  const examId = document.getElementById("results-exam").value;
  const stream = document.getElementById("results-stream").value || null;

  if (!branchId || !classId || !examId) {
    alert("Please select school, grade, and exam.");
    return;
  }

  generatePDF(branchId, classId, examId, stream);
});

function generatePDF(branchId, classId, examId, stream) {
  blockUI(
    "Generating report cards",
    "This may take up to a minute. Please keep this tab open.",
  );

  fetch("/admin/generate-reportcards-pdf", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({
      branch_id: branchId,
      class_id: classId,
      exam_id: examId,
      stream: stream,
    }),
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("Content-Disposition");
      let filename = "report.pdf";

      if (contentDisposition) {
        const match = contentDisposition.match(
          /filename\*?=(?:UTF-8'')?["']?([^"';]+)/,
        );
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }

      return { blob, filename };
    })
    .then(({ blob, filename }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((err) => {
      console.error(err);
      alert("PDF generation failed.");
    })
    .finally(() => {
      unblockUI();
    });
}
