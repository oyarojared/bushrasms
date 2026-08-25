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
    gradingType: lastLoadedGradingType,
  };
}

let lastLoadedGradingType = "cbc";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function is844Grading(context) {
  return context.gradingType === "844";
}

function performanceBadgeClass(level) {
  const value = Number(level);
  if (Number.isNaN(value)) return "level-neutral";
  if (value >= 7) return "level-exceeds";
  if (value >= 5) return "level-meets";
  if (value >= 3) return "level-approaching";
  return "level-below";
}

function grade844BadgeClass(grade) {
  const value = String(grade || "").toUpperCase();
  if (value.startsWith("A")) return "grade-844-a";
  if (value.startsWith("B")) return "grade-844-b";
  if (value.startsWith("C")) return "grade-844-c";
  if (value.startsWith("D")) return "grade-844-d";
  if (value === "E") return "grade-844-e";
  return "grade-844-neutral";
}

function renderCbcSubjectRows(subjects) {
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

function render844SubjectRows(subjects) {
  return subjects
    .map(
      (sub) => `
      <tr>
        <td class="text-center subject-code">${escapeHtml(sub.code || "-")}</td>
        <td class="subject-name text-uppercase">${escapeHtml(sub.name || "-")}</td>
        <td class="text-center subject-marks">${sub.marks ?? "-"}</td>
        <td class="text-center">
          <span class="grade-844-badge ${grade844BadgeClass(sub.performance_level)}">
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

function renderSubjectTable(student, context) {
  if (is844Grading(context)) {
    return `
      <table class="student-result-table student-result-table-844">
        <thead>
          <tr>
            <th class="text-center">Code</th>
            <th>Subject</th>
            <th class="text-center">Marks</th>
            <th class="text-center">Grade</th>
            <th class="text-center">Pts</th>
            <th>Comment</th>
            <th class="text-center">Teacher</th>
          </tr>
        </thead>
        <tbody>
          ${render844SubjectRows(student.subjects)}
        </tbody>
      </table>
    `;
  }

  return `
    <table class="student-result-table student-result-table-cbc">
      <thead>
        <tr>
          <th class="text-center">Code</th>
          <th>Subject / Learning Area</th>
          <th class="text-center">Marks</th>
          <th class="text-center">Perf. Lvl</th>
          <th class="text-center">Pts</th>
          <th>Descriptor</th>
          <th class="text-center">Teacher</th>
        </tr>
      </thead>
      <tbody>
        ${renderCbcSubjectRows(student.subjects)}
      </tbody>
    </table>
  `;
}

function renderScoreSummary(student, context) {
  if (is844Grading(context)) {
    const summary = student.summary || {};
    const totalPoints = summary.total_points ?? 0;
    const meanGrade = summary.mean_grade ?? "—";
    return `
      <div class="student-result-score">
        <strong>${totalPoints}</strong>
        <span>pts · Mean Grade <strong class="mean-grade-value">${escapeHtml(meanGrade)}</strong></span>
      </div>
    `;
  }

  const totalPoints = student.subjects.reduce(
    (sum, sub) => sum + (sub.points || 0),
    0,
  );
  const maxPoints = student.subjects.length * 8;
  const percentage =
    maxPoints > 0 ? Math.round((totalPoints / maxPoints) * 100) : 0;

  return `
    <div class="student-result-score">
      <strong>${totalPoints}</strong>
      <span>/ ${maxPoints} pts (${percentage}%)</span>
    </div>
  `;
}

function renderStudentMetaDetails(student, context) {
  if (is844Grading(context)) {
    const streamItem = student.stream
      ? `<span class="result-meta-item">Stream <strong>${escapeHtml(student.stream)}</strong></span>`
      : "";

    return `
      <span class="result-meta-item">Adm <strong>${escapeHtml(student.admission_number || "-")}</strong></span>
      ${streamItem}
      <span class="result-meta-item">${escapeHtml(context.examName)}</span>
      <span class="result-meta-item">${escapeHtml(context.className)}</span>
      <span class="result-meta-item">${escapeHtml(context.streamLabel)}</span>
    `;
  }

  const pathwayItem = student.pathway
    ? `<span class="result-meta-item">Pathway <strong>${escapeHtml(student.pathway)}</strong></span>`
    : "";

  return `
    <span class="result-meta-item">Adm <strong>${escapeHtml(student.admission_number || "-")}</strong></span>
    <span class="result-meta-item">Assess <strong>${escapeHtml(student.assessment_no || "-")}</strong></span>
    ${pathwayItem}
    <span class="result-meta-item">${escapeHtml(context.examName)}</span>
    <span class="result-meta-item">${escapeHtml(context.className)}</span>
    <span class="result-meta-item">${escapeHtml(context.streamLabel)}</span>
  `;
}

function renderStudentResultCard(student, context) {
  const cardClass = is844Grading(context)
    ? "student-result-card student-result-card-844"
    : "student-result-card student-result-card-cbc";

  return `
    <article class="${cardClass}">
      <header class="student-result-header">
        <div class="student-result-top">
          <h6 class="student-result-name">${escapeHtml(student.full_name)}</h6>
          ${renderScoreSummary(student, context)}
        </div>
        <div class="student-result-details">
          ${renderStudentMetaDetails(student, context)}
        </div>
      </header>

      <div class="student-result-body">
        <div class="table-responsive student-result-table-wrap">
          ${renderSubjectTable(student, context)}
        </div>
      </div>

      <footer class="student-result-footer">
        <span class="result-footer-item">
          <span class="result-footer-label">Class Teacher</span>
          <span class="result-footer-value">${escapeHtml(student.class_teacher || "Not assigned")}</span>
        </span>
        ${
          student.remarks
            ? `<span class="result-footer-item result-footer-item-remarks"><span class="result-footer-label">Remarks</span><span class="result-footer-value">${escapeHtml(student.remarks)}</span></span>`
            : ""
        }
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

    context.gradingType = data.grading_type === "844" ? "844" : "cbc";
    lastLoadedGradingType = context.gradingType;

    if (students.length === 0) {
      container.innerHTML = `
        <div class="results-state results-state-empty">
          <i class="bi bi-inbox"></i>
          <p>No students found for this selection.</p>
        </div>
      `;
      return;
    }

    const gradingLabel = is844Grading(context) ? "8-4-4" : "CBE";

    container.innerHTML = `
      <div class="results-summary-bar">
        <div class="results-summary-meta">
          <span>Total Students: <strong>${students.length}</strong></span>
          <span>Grading system: <strong>${gradingLabel}</strong></span>
        </div>
        <span class="results-summary-context">${escapeHtml(context.examName)} · ${escapeHtml(context.className)}</span>
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
    scrollResultsIntoView();
  }
}

function scrollResultsIntoView() {
  const container = document.getElementById("resultsContainer");
  if (!container || !container.innerHTML.trim()) return;

  const target =
    container.querySelector(".results-summary-bar") || container;

  window.setTimeout(() => {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 60);
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

function resultsGradeHasStreams() {
  const streamSelect = document.getElementById("results-stream");
  return streamSelect && streamSelect.options.length > 1;
}

function requireResultsStreamForDownload() {
  const streamSelect = document.getElementById("results-stream");
  if (resultsGradeHasStreams() && !streamSelect.value) {
    alert("Please select a stream before downloading report cards.");
    return false;
  }
  return true;
}

document.getElementById("generate-pdf-btn").addEventListener("click", () => {
  const branchId = document.getElementById("results-branch").value;
  const classId = document.getElementById("results-grade").value;
  const examId = document.getElementById("results-exam").value;
  const stream = document.getElementById("results-stream").value || null;

  if (!branchId || !classId || !examId) {
    alert("Please select school, grade, and exam.");
    return;
  }

  if (!requireResultsStreamForDownload()) return;

  if (lastLoadedGradingType === "844") {
    generatePDF(branchId, classId, examId, stream);
    return;
  }

  if (typeof bindCbeReportCardOptionsModal !== "function") {
    generatePDF(branchId, classId, examId, stream);
    return;
  }

  if (!window.__cbeReportOptionsModal) {
    window.__cbeReportOptionsModal = bindCbeReportCardOptionsModal((options) => {
      const currentBranchId = document.getElementById("results-branch").value;
      const currentClassId = document.getElementById("results-grade").value;
      const currentExamId = document.getElementById("results-exam").value;
      const currentStream =
        document.getElementById("results-stream").value || null;
      generatePDF(
        currentBranchId,
        currentClassId,
        currentExamId,
        currentStream,
        options,
      );
    });
  }

  window.__cbeReportOptionsModal?.show();
});

function generatePDF(branchId, classId, examId, stream, printOptions = {}) {
  blockUI(
    "Generating report cards",
    "This may take 1–2 minutes for a full class. Please keep this tab open.",
    { progress: true },
  );

  let simulatedProgress = 0;
  const simulationTimer = window.setInterval(() => {
    if (simulatedProgress < 82) {
      simulatedProgress = Math.min(
        82,
        simulatedProgress + Math.random() * 4 + 1,
      );
      setUIProgress(
        simulatedProgress,
        simulatedProgress < 35
          ? "Preparing report data…"
          : "Generating PDF on server…",
      );
    }
  }, 450);

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
      include_ranking: Boolean(printOptions.include_ranking),
      include_opening_date: Boolean(printOptions.include_opening_date),
      opening_date: printOptions.opening_date || "",
    }),
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }

      window.clearInterval(simulationTimer);
      setUIProgress(85, "Downloading report cards…");

      const blob = await readResponseBlobWithProgress(response, (downloadPercent) => {
        const overall = 85 + Math.round(downloadPercent * 0.15);
        setUIProgress(overall, "Downloading report cards…");
      });

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

      setUIProgress(100, "Download complete");
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
      window.clearInterval(simulationTimer);
      unblockUI();
    });
}
