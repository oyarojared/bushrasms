const marksheetBranchSelect = document.getElementById("marksheet-branch");
const marksheetGradeSelect = document.getElementById("marksheet-grade");
const marksheetStreamSelect = document.getElementById("marksheet-stream");
const marksheetStreamWrapper = document.getElementById("marksheet-stream-wrapper");
const marksheetSubjectSelect = document.getElementById("marksheet-subject");
const marksheetSubjectWrapper = document.getElementById("marksheet-subject-wrapper");
const marksheetFilterHint = document.getElementById("marksheet-filter-hint");
const loadMarksBtn = document.getElementById("load-marksheet-students");
const loadMarkIcon = document.getElementById("load-marksheet-icon");
const loadMarkLabel = document.getElementById("load-marksheet-label");
const marksContainer = document.getElementById("marksheetStudentsContainer");
const modeButtons = document.querySelectorAll(".marksheet-mode-btn");

marksheetSubjectSelect.disabled = true;
let marksheetMode = "classlist";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

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

function renderLoadingState(message) {
  marksContainer.innerHTML = `
    <div class="marksheet-state">
      <div class="spinner-border spinner-border-sm text-secondary" role="status" aria-hidden="true"></div>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function renderEmptyState(message) {
  marksContainer.innerHTML = `
    <div class="marksheet-state">
      <i class="bi bi-inbox"></i>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function renderErrorState(message) {
  marksContainer.innerHTML = `
    <div class="marksheet-state marksheet-state-error">
      <i class="bi bi-exclamation-triangle"></i>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function getGradeOnly(student) {
  return student.class_name || "—";
}

function classHasStreams() {
  return !marksheetStreamWrapper.classList.contains("d-none");
}

function getSelectedStream() {
  if (!classHasStreams()) return "";
  return marksheetStreamSelect.value || "";
}

function getSheetOptions(studentCount) {
  const hasStreams = classHasStreams();
  const selectedStream = getSelectedStream();

  return {
    studentCount,
    stream: selectedStream || "",
    showStreamInHeader: hasStreams && Boolean(selectedStream),
    showStreamColumn: hasStreams && !selectedStream,
  };
}

function populateStreamSelect(streams) {
  marksheetStreamSelect.innerHTML = '<option value="">All</option>';
  streams.forEach((stream) => {
    const opt = document.createElement("option");
    opt.value = stream;
    opt.textContent = stream;
    marksheetStreamSelect.appendChild(opt);
  });
}

function buildMetaCell(label, value) {
  return `
    <div class="marksheet-meta-cell">
      <span class="marksheet-meta-label">${escapeHtml(label)}</span>
      <span class="marksheet-meta-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function buildSheetHeader(student, options = {}) {
  const type = options.type || "marksheet";
  const studentCount = options.studentCount ?? 0;
  const docTitle = type === "marksheet" ? "MARKSHEET" : "CLASS LIST";
  const teacherLabel =
    type === "marksheet" ? "Subject Teacher" : "Class Teacher";
  const teacherName =
    type === "marksheet"
      ? student.subject_teacher || "Not assigned"
      : student.class_teacher || "Not assigned";

  const metaCells = [buildMetaCell("Grade/Form", getGradeOnly(student))];

  if (options.showStreamInHeader) {
    const streamValue = options.stream || student.stream || "—";
    metaCells.push(buildMetaCell("Stream", streamValue));
  }

  if (type === "marksheet") {
    metaCells.push(buildMetaCell("Subject", student.subject_name || "N/A"));
  }

  metaCells.push(
    buildMetaCell("Students", String(studentCount)),
    buildMetaCell(teacherLabel, teacherName),
  );

  return `
    <header class="marksheet-sheet-header">
      <h2 class="marksheet-school-name">${escapeHtml((student.branch_name || "").toUpperCase())}</h2>
      <p class="marksheet-doc-title">${docTitle}</p>
      <div class="marksheet-meta-panel">
        ${metaCells.join("")}
      </div>
    </header>
  `;
}

function buildTableRows(students, includeMarks = false, showStream = false) {
  return students
    .map((student, index) => {
      const marksCell = includeMarks
        ? '<td class="marksheet-col-marks"></td>'
        : "";
      const streamCell = showStream
        ? `<td class="marksheet-col-stream">${escapeHtml(student.stream || "—")}</td>`
        : "";
      return `
        <tr>
          <td class="marksheet-col-no">${index + 1}</td>
          <td class="marksheet-col-adm">${escapeHtml(student.admission_number)}</td>
          <td class="marksheet-col-name">${escapeHtml(student.full_name)}</td>
          ${streamCell}
          ${marksCell}
        </tr>
      `;
    })
    .join("");
}

function buildTableHead(includeMarks = false, showStream = false) {
  const streamHeader = showStream
    ? '<th class="marksheet-col-stream">Stream</th>'
    : "";
  const marksHeader = includeMarks
    ? '<th class="marksheet-col-marks">Marks</th>'
    : "";
  return `
    <thead>
      <tr>
        <th class="marksheet-col-no">#</th>
        <th class="marksheet-col-adm">Adm No</th>
        <th class="marksheet-col-name">Full Name</th>
        ${streamHeader}
        ${marksHeader}
      </tr>
    </thead>
  `;
}

function buildMarksheetDocument(students, sheetOptions = {}) {
  const options = { type: "marksheet", ...sheetOptions };
  return buildSheetContent(students, options, true, "marksheetDocument");
}

function buildClasslistDocument(students, sheetOptions = {}) {
  const options = { type: "classlist", ...sheetOptions };
  return buildSheetContent(students, options, false, "marksheetDocument");
}

function buildSheetContent(students, options, includeMarks, docId = null) {
  const first = students[0];
  const schoolName = (first.branch_name || "").toUpperCase();
  const showStreamColumn = options.showStreamColumn;
  const idAttr = docId ? ` id="${docId}"` : "";

  return `
    <div class="marksheet-sheet"${idAttr}>
      <div class="marksheet-watermark" aria-hidden="true">${escapeHtml(schoolName)}</div>
      ${buildSheetHeader(first, options)}
      <div class="marksheet-table-wrap">
        <table class="marksheet-table">
          ${buildTableHead(includeMarks, showStreamColumn)}
          <tbody>
            ${buildTableRows(students, includeMarks, showStreamColumn)}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function buildDocumentMarkup(students, type) {
  const sheetOptions = getSheetOptions(students.length);
  const isMarksheet = type === "marksheet";
  const sheet = isMarksheet
    ? buildMarksheetDocument(students, sheetOptions)
    : buildClasslistDocument(students, sheetOptions);
  const pdfSuffix = isMarksheet ? "Marksheet" : "Classlist";

  return `
    <section class="marksheet-document">
      <div class="marksheet-action-bar marksheet-no-print">
        <span class="marksheet-action-label">
          <i class="bi bi-file-earmark-text me-1"></i> ${
            isMarksheet ? "Marksheet" : "Class list"
          }
        </span>
        <div class="marksheet-action-group">
          <button type="button" class="marksheet-btn marksheet-btn-outline" id="printMarksheetBtn">
            <i class="bi bi-printer"></i> Print
          </button>
          <button
            type="button"
            class="marksheet-btn marksheet-btn-primary"
            id="downloadBtn"
            data-pdf-suffix="${pdfSuffix}"
          >
            <i class="bi bi-download"></i> PDF
          </button>
        </div>
      </div>
      ${sheet}
    </section>
  `;
}

function buildMarksheetMarkup(students) {
  return buildDocumentMarkup(students, "marksheet");
}

function buildClasslistMarkup(students) {
  return buildDocumentMarkup(students, "classlist");
}

function getMarksheetFileName(suffix) {
  const gradeText =
    marksheetGradeSelect.options[marksheetGradeSelect.selectedIndex]?.text ||
    "Class";
  const streamText = marksheetStreamSelect.value
    ? marksheetStreamSelect.options[marksheetStreamSelect.selectedIndex]?.text
    : "";
  const subjectText =
    marksheetSubjectSelect.options[marksheetSubjectSelect.selectedIndex]?.text ||
    "Subject";

  let fileName = gradeText;
  if (streamText) fileName += ` ${streamText}`;
  if (suffix === "Marksheet") {
    fileName += ` - ${subjectText} Marksheet.pdf`;
  } else {
    fileName += " Classlist.pdf";
  }

  return fileName.replace(/[<>:"/\\|?*]+/g, "");
}

function formatPdfGeneratedDate() {
  return new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function addPdfPageFooter(pdf) {
  const totalPages = pdf.internal.getNumberOfPages();
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const generatedOn = formatPdfGeneratedDate();
  const footerY = pageHeight - 0.22;

  for (let page = 1; page <= totalPages; page += 1) {
    pdf.setPage(page);
    pdf.setFont("times", "normal");
    pdf.setFontSize(8);
    pdf.setTextColor(90, 90, 90);

    pdf.text(`Generated: ${generatedOn}`, 0.35, footerY, { align: "left" });
    pdf.text(`Page ${page} of ${totalPages}`, pageWidth / 2, footerY, {
      align: "center",
    });
  }
}

function createPdfExportNode(sourceElement) {
  const clone = sourceElement.cloneNode(true);
  clone.removeAttribute("id");

  const rowCount = clone.querySelectorAll(".marksheet-table tbody tr").length;
  clone.classList.add("marksheet-pdf-export");

  if (rowCount > 50) {
    clone.classList.add("marksheet-pdf-dense");
  } else if (rowCount > 32) {
    clone.classList.add("marksheet-pdf-compact");
  } else {
    clone.classList.add("marksheet-pdf-normal");
  }

  clone.querySelectorAll(".marksheet-table tbody tr").forEach((row) => {
    row.classList.add("marksheet-pdf-row");
  });

  const wrapper = document.createElement("div");
  wrapper.className = "marksheet-pdf-root";
  wrapper.appendChild(clone);
  document.body.appendChild(wrapper);

  return { node: clone, wrapper };
}

function downloadPdfFromElement(element, filename) {
  const { node, wrapper } = createPdfExportNode(element);
  const cleanup = () => wrapper.remove();

  return html2pdf()
    .set({
      margin: [0.3, 0.35, 0.55, 0.35],
      filename,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        letterRendering: true,
        scrollX: 0,
        scrollY: 0,
        backgroundColor: "#ffffff",
      },
      jsPDF: {
        unit: "in",
        format: "a4",
        orientation: "portrait",
        compress: true,
      },
      pagebreak: {
        mode: ["css", "legacy"],
        avoid: ".marksheet-pdf-row",
      },
    })
    .from(node)
    .toPdf()
    .get("pdf")
    .then((pdf) => {
      addPdfPageFooter(pdf);
    })
    .save()
    .then(
      () => cleanup(),
      (err) => {
        cleanup();
        return Promise.reject(err);
      },
    );
}

function scrollToMarksheetView() {
  const target = marksContainer.querySelector(".marksheet-document");
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

function bindMarksheetActions() {
  document.getElementById("printMarksheetBtn")?.addEventListener("click", () => {
    window.print();
  });

  document.getElementById("downloadBtn")?.addEventListener("click", () => {
    const element = document.getElementById("marksheetDocument");
    if (!element) return;
    const suffix =
      document.getElementById("downloadBtn")?.dataset.pdfSuffix || "Marksheet";

    if (typeof blockUI === "function") {
      blockUI("Generating PDF", "Preparing download…");
    }

    downloadPdfFromElement(element, getMarksheetFileName(suffix))
      .catch((err) => {
        console.error(err);
        alert("Failed to generate PDF.");
      })
      .finally(() => {
        if (typeof unblockUI === "function") unblockUI();
      });
  });
}

fetch("/admin/api/branches")
  .then((res) => res.json())
  .then((data) => populateSelect(marksheetBranchSelect, data, "Select School"));

marksheetBranchSelect.addEventListener("change", function () {
  const branchId = this.value;

  marksheetGradeSelect.innerHTML = '<option value="">--Select Grade--</option>';
  marksheetStreamSelect.innerHTML = '<option value="">All</option>';
  marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';
  marksheetSubjectSelect.disabled = true;
  marksheetStreamWrapper.classList.add("d-none");
  marksContainer.innerHTML = "";
  updateLoadButton();

  if (!branchId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      populateSelect(marksheetGradeSelect, data, "Select Grade", "grade_form");
      updateLoadButton();
    });
});

marksheetGradeSelect.addEventListener("change", function () {
  const branchId = marksheetBranchSelect.value;
  const classId = this.value;

  marksheetStreamSelect.innerHTML = '<option value="">All</option>';
  marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';
  marksheetSubjectSelect.disabled = true;
  marksheetStreamWrapper.classList.add("d-none");
  marksContainer.innerHTML = "";
  updateLoadButton();

  if (!branchId || !classId) return;

  fetch(`/admin/api/grades/${branchId}`)
    .then((res) => res.json())
    .then((data) => {
      const gradeObj = data.find((g) => g.id == classId);

      if (gradeObj?.streams?.length) {
        populateStreamSelect(gradeObj.streams);
        marksheetStreamWrapper.classList.remove("d-none");
        marksheetSubjectSelect.disabled = false;
        loadSubjects(branchId, classId, "");
      } else {
        marksheetSubjectSelect.disabled = false;
        loadSubjects(branchId, classId, "");
      }
      updateLoadButton();
    });
});

marksheetStreamSelect.addEventListener("change", function () {
  const branchId = marksheetBranchSelect.value;
  const classId = marksheetGradeSelect.value;
  const stream = this.value || "";

  marksContainer.innerHTML = "";
  marksheetSubjectSelect.disabled = false;
  loadSubjects(branchId, classId, stream);
  updateLoadButton();
});

function loadSubjects(branchId, classId, stream) {
  marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';
  if (marksheetMode !== "marksheet") {
    updateLoadButton();
    return;
  }

  fetch(
    `/admin/api/subjects?branch_id=${branchId}&class_id=${classId}&stream=${stream}`,
  )
    .then((res) => res.json())
    .then((data) => populateSelect(marksheetSubjectSelect, data, "--Select Subject--"))
    .finally(() => updateLoadButton());
}

function canLoadCurrentView() {
  const hasSchool = Boolean(marksheetBranchSelect.value);
  const hasClass = Boolean(marksheetGradeSelect.value);
  if (marksheetMode === "marksheet") {
    return hasSchool && hasClass && Boolean(marksheetSubjectSelect.value);
  }
  return hasSchool && hasClass;
}

function updateLoadButton() {
  const isMarksheet = marksheetMode === "marksheet";
  if (loadMarkIcon) {
    loadMarkIcon.className = isMarksheet ? "bi bi-table" : "bi bi-people";
  }
  if (loadMarkLabel) {
    loadMarkLabel.textContent = isMarksheet ? "Load marksheet" : "View class list";
  }
  if (!loadMarksBtn) return;
  loadMarksBtn.disabled = !canLoadCurrentView();
  loadMarksBtn.title = isMarksheet
    ? canLoadCurrentView()
      ? "Load this subject's marksheet"
      : "Select school, class, and subject first"
    : canLoadCurrentView()
      ? "View the class list"
      : "Select school and class first";
}

function setMarksheetMode(mode) {
  marksheetMode = mode === "marksheet" ? "marksheet" : "classlist";
  modeButtons.forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.mode === marksheetMode);
  });

  if (marksheetSubjectWrapper) {
    marksheetSubjectWrapper.classList.toggle("d-none", marksheetMode !== "marksheet");
  }

  if (marksheetFilterHint) {
    marksheetFilterHint.textContent =
      marksheetMode === "marksheet"
        ? "Select school, class, stream, and subject to load a marksheet"
        : "Select school, class, and stream to view the class list";
  }

  marksContainer.innerHTML = "";

  if (marksheetMode === "marksheet") {
    const branchId = marksheetBranchSelect.value;
    const classId = marksheetGradeSelect.value;
    if (branchId && classId) {
      marksheetSubjectSelect.disabled = false;
      loadSubjects(branchId, classId, marksheetStreamSelect.value || "");
    }
  }

  updateLoadButton();
}

function loadClasslist() {
  const branchId = marksheetBranchSelect.value;
  const classId = marksheetGradeSelect.value;
  const stream = marksheetStreamSelect.value || "";

  if (!branchId || !classId) {
    alert("Please select school and grade.");
    return;
  }

  renderLoadingState("Loading class list…");

  fetch(
    `/admin/api/students-by-class?branch_id=${branchId}&class_id=${classId}&stream=${stream}`,
  )
    .then((res) => res.json())
    .then((data) => {
      if (!data.students?.length) {
        renderEmptyState("No students found for this class.");
        return;
      }

      marksContainer.innerHTML = buildClasslistMarkup(data.students);
      bindMarksheetActions();
      scrollToMarksheetView();
    })
    .catch((err) => {
      console.error(err);
      renderErrorState("Failed to load class list.");
    });
}

function loadMarksheet() {
  const branchId = marksheetBranchSelect.value;
  const classId = marksheetGradeSelect.value;
  const stream = marksheetStreamSelect.value || "";
  const subjectId = marksheetSubjectSelect.value;

  if (!branchId || !classId || !subjectId) {
    alert("Please select school, grade, and subject.");
    return;
  }

  renderLoadingState("Loading students…");

  fetch(
    `/admin/api/students-by-subject?branch_id=${branchId}&class_id=${classId}&subject_id=${subjectId}&stream=${stream}`,
  )
    .then((res) => res.json())
    .then((data) => {
      if (!data.students?.length) {
        renderEmptyState("No students found for this selection.");
        return;
      }

      marksContainer.innerHTML = buildMarksheetMarkup(data.students);
      bindMarksheetActions();
      scrollToMarksheetView();
    })
    .catch((err) => {
      console.error(err);
      renderErrorState("Failed to load students.");
    });
}

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => setMarksheetMode(btn.dataset.mode));
});

loadMarksBtn.addEventListener("click", function () {
  if (!canLoadCurrentView()) return;
  if (marksheetMode === "classlist") {
    loadClasslist();
    return;
  }
  loadMarksheet();
});

marksheetSubjectSelect.addEventListener("change", updateLoadButton);
updateLoadButton();
