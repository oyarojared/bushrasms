document.addEventListener("DOMContentLoaded", function () {
  // ---------------------- DOM ELEMENTS ----------------------
  const branchSelect = document.querySelector("form select[name='branches']");
  const container = document.getElementById("academicDataContainer");
  const branchClassesDiv = document.querySelector(".form-select-div");
  const subjectContainer = document.querySelector(".subject-select-div");

  function clearStudentsList() {
    const studentContainer = document.querySelector(".students-allocation-div");
    if (studentContainer) {
      studentContainer.innerHTML = "";
    }
  }

  function scrollAssignmentIntoView() {
    const target = document.querySelector("#tab-two > .sa-card");
    const scroller = document.querySelector(".main-content");
    if (!target || !scroller) return;

    requestAnimationFrame(() => {
      const offset = 12;
      const nextTop =
        scroller.scrollTop +
        (target.getBoundingClientRect().top -
          scroller.getBoundingClientRect().top) -
        offset;

      scroller.scrollTo({
        top: Math.max(0, nextTop),
        behavior: "smooth",
      });
    });
  }

  function showAssignmentNotice({ success, title, message }) {
    const noticeEl = document.getElementById("assignTeachersNoticeModal");
    const card = document.getElementById("assignTeachersNoticeCard");
    const icon = document.getElementById("assignTeachersNoticeIcon");
    const titleEl = document.getElementById("assignTeachersNoticeTitle");
    const messageEl = document.getElementById("assignTeachersNoticeMessage");
    if (!noticeEl || !card) return;

    card.classList.toggle("is-success", success);
    card.classList.toggle("is-error", !success);
    if (icon) {
      icon.innerHTML = success
        ? '<i class="bi bi-check-circle-fill"></i>'
        : '<i class="bi bi-exclamation-triangle-fill"></i>';
    }
    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;

    bootstrap.Modal.getOrCreateInstance(noticeEl).show();
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
      container.innerHTML = `<div class="grade-board-empty">Select a school to view class data.</div>`;
      return;
    }

    container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center py-4 text-success">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span class="h6">Loading school data…</span>
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
                        Failed to load school data! Something went wrong.
                    </div>
                `;
      });
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function gradeActionButtons(kind, data, extraAttrs) {
    const attrs = extraAttrs || "";
    return `
      <div class="grade-card-actions">
        <button class="grade-card-btn rename-${kind}-btn"
                type="button"
                title="Edit"
                ${attrs}
                data-grade="${data.classId}"
                data-grade-name="${data.gradeName}"
                data-branch="${data.branchId}">
          <i class="bi bi-pencil"></i>
          <span>Edit</span>
        </button>
        <button class="grade-card-btn is-danger delete-${kind}-btn"
                type="button"
                title="Delete"
                ${attrs}
                data-grade="${data.classId}"
                data-grade-name="${data.gradeName}"
                data-branch="${data.branchId}">
          <i class="bi bi-trash"></i>
          <span>Delete</span>
        </button>
      </div>
    `;
  }

  // ---------------------- RENDER ACADEMIC DATA ----------------------
  function renderAcademicData(data) {
    const branchName = escapeHtml(data.branch_name);
    let html = `
            <div class="grade-board-title">${branchName}</div>
            <div class="grade-list">
        `;

    if (!data.grades || !data.grades.length) {
      container.innerHTML = `
                <div class="grade-board-empty">
                    No classes found for this school.
                </div>
            `;
      branchClassesDiv.innerHTML = `
                <div class="sa-empty">No classes found for this school.</div>
            `;
      subjectContainer.innerHTML = "";
      return;
    }

    data.grades.forEach((g) => {
      const gradeName = escapeHtml(g.grade_form);
      const actionData = {
        classId: g.class_id,
        gradeName,
        branchId: data.branch_id,
      };
      const boys = g.totals?.boys ?? 0;
      const girls = g.totals?.girls ?? 0;
      const total = g.totals?.total ?? 0;
      const unsigned = g.totals?.unsigned ?? Math.max(0, total - boys - girls);

      const streamCount = g.streams?.length || 0;
      const streamMeta = streamCount
        ? `${streamCount} stream${streamCount === 1 ? "" : "s"}`
        : "No streams";

      html += `
                    <article class="grade-card">
                        <div class="grade-card-head">
                            <div class="grade-card-title">
                                <div class="grade-card-name">${gradeName}</div>
                                <div class="grade-card-meta">${streamMeta}</div>
                            </div>
                            <div class="grade-card-stats">
                                <div class="grade-stat">
                                    <span class="grade-stat-n">${total}</span>
                                    <span class="grade-stat-l">Total</span>
                                </div>
                                <div class="grade-stat">
                                    <span class="grade-stat-n is-boys">${boys}</span>
                                    <span class="grade-stat-l">Boys</span>
                                </div>
                                <div class="grade-stat">
                                    <span class="grade-stat-n is-girls">${girls}</span>
                                    <span class="grade-stat-l">Girls</span>
                                </div>
                                ${
                                  unsigned
                                    ? `<div class="grade-stat">
                                    <span class="grade-stat-n is-unsigned">${unsigned}</span>
                                    <span class="grade-stat-l">Unsigned</span>
                                </div>`
                                    : ""
                                }
                            </div>
                            ${gradeActionButtons("grade", actionData)}
                        </div>
                        <div class="grade-card-body">
            `;

      if (g.streams && g.streams.length) {
        html += `<div class="grade-streams-title">Streams</div>`;
        g.streams.forEach((s) => {
          const streamName = escapeHtml(s.name);
          const teacherAssigned = Boolean(s.teacher?.name);
          const teacherName = escapeHtml(s.teacher?.name || "Unassigned");
          const streamUnsigned =
            s.unsigned ?? Math.max(0, (s.total || 0) - (s.boys || 0) - (s.girls || 0));
          html += `
                        <div class="grade-stream-row">
                            <div class="grade-stream-main">
                                <span class="grade-stream-name">${streamName}</span>
                                <span class="grade-stream-teacher">
                                  <span class="grade-teacher-label">Class Teacher:</span>
                                  <span class="${teacherAssigned ? "" : "is-empty"}" title="${teacherName}">${teacherName}</span>
                                </span>
                            </div>
                            <div class="grade-stream-stats-strip">
                                <div class="grade-stat">
                                    <span class="grade-stat-n">${s.total || 0}</span>
                                    <span class="grade-stat-l">Total</span>
                                </div>
                                <div class="grade-stat">
                                    <span class="grade-stat-n is-boys">${s.boys || 0}</span>
                                    <span class="grade-stat-l">Boys</span>
                                </div>
                                <div class="grade-stat">
                                    <span class="grade-stat-n is-girls">${s.girls || 0}</span>
                                    <span class="grade-stat-l">Girls</span>
                                </div>
                                ${
                                  streamUnsigned
                                    ? `<div class="grade-stat">
                                    <span class="grade-stat-n is-unsigned">${streamUnsigned}</span>
                                    <span class="grade-stat-l">Unsigned</span>
                                </div>`
                                    : ""
                                }
                            </div>
                            ${gradeActionButtons(
                              "stream",
                              actionData,
                              `data-stream="${streamName}"`
                            )}
                        </div>
                    `;
        });
      } else {
        const teacherAssigned = Boolean(g.teacher?.name);
        const teacherName = escapeHtml(g.teacher?.name || "Unassigned");
        html += `
                    <div class="grade-stream-row is-plain">
                        <div class="grade-stream-main">
                            <span class="grade-stream-teacher">
                              <span class="grade-teacher-label">Class Teacher:</span>
                              <span class="${teacherAssigned ? "" : "is-empty"}">${teacherName}</span>
                            </span>
                        </div>
                    </div>
                    `;
      }

      html += `</div></article>`;
    });

    html += `</div>`;
    container.innerHTML = html;

    // ---------------------- BUILD GRADE SELECT ----------------------
    buildGradeSelect(data);

  }

  const classDeleteModalEl = document.getElementById("classDeleteModal");
  const classDeleteModal = classDeleteModalEl
    ? bootstrap.Modal.getOrCreateInstance(classDeleteModalEl)
    : null;
  const classDeleteCard = document.getElementById("classDeleteCard");
  const classDeleteIcon = document.getElementById("classDeleteIcon");
  const classDeleteNoteIcon = document.getElementById("classDeleteNoteIcon");
  const classDeleteTitle = document.getElementById("classDeleteTitle");
  const classDeleteSubtitle = document.getElementById("classDeleteSubtitle");
  const classDeleteLead = document.getElementById("classDeleteLead");
  const classDeleteTarget = document.getElementById("classDeleteTarget");
  const classDeleteMessage = document.getElementById("classDeleteMessage");
  const classDeleteHint = document.getElementById("classDeleteHint");
  const classDeleteCancel = document.getElementById("classDeleteCancel");
  const classDeleteConfirm = document.getElementById("classDeleteConfirm");
  const classDeleteOk = document.getElementById("classDeleteOk");
  let pendingClassDelete = null;
  let classDeleteReloadOnClose = false;

  function classTargetLabel(gradeName, streamName) {
    if (gradeName && streamName) return `${gradeName} · ${streamName}`;
    return gradeName || streamName || "this class";
  }

  function refreshAcademicData() {
    if (branchSelect) {
      branchSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function setClassDeleteMode(mode) {
    if (!classDeleteCard) return;

    classDeleteCard.classList.remove("is-warning", "is-success");
    classDeleteCancel.classList.add("d-none");
    classDeleteConfirm.classList.add("d-none");
    classDeleteOk.classList.add("d-none");
    classDeleteConfirm.disabled = false;
    classDeleteConfirm.innerHTML = '<i class="bi bi-trash-fill me-1"></i>Delete';

    if (mode === "confirm") {
      classDeleteIcon.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i>';
      classDeleteNoteIcon.innerHTML = '<i class="bi bi-info-circle"></i>';
      classDeleteCancel.classList.remove("d-none");
      classDeleteConfirm.classList.remove("d-none");
    } else if (mode === "blocked") {
      classDeleteCard.classList.add("is-warning");
      classDeleteIcon.innerHTML = '<i class="bi bi-shield-exclamation"></i>';
      classDeleteNoteIcon.innerHTML = '<i class="bi bi-exclamation-circle"></i>';
      classDeleteOk.classList.remove("d-none");
    } else {
      classDeleteCard.classList.add("is-success");
      classDeleteIcon.innerHTML = '<i class="bi bi-check-circle-fill"></i>';
      classDeleteNoteIcon.innerHTML = '<i class="bi bi-check2-circle"></i>';
      classDeleteOk.classList.remove("d-none");
    }
  }

  function openClassDeleteModal({ mode, title, subtitle, lead, target, message, hint }) {
    if (!classDeleteModal) return;
    setClassDeleteMode(mode);
    classDeleteTitle.textContent = title;
    classDeleteSubtitle.textContent = subtitle || "";
    classDeleteLead.textContent = lead || "";
    classDeleteTarget.textContent = target || "";
    classDeleteMessage.textContent = message || "";
    classDeleteHint.textContent = hint || "";
    classDeleteModal.show();
  }

  if (container && classDeleteModal) {
    container.addEventListener("click", function (e) {
      const gradeBtn = e.target.closest(".delete-grade-btn");
      const streamBtn = e.target.closest(".delete-stream-btn");

      if (gradeBtn) {
        const gradeName = gradeBtn.dataset.gradeName || "this class";
        pendingClassDelete = {
          kind: "grade",
          branchId: gradeBtn.dataset.branch,
          gradeId: gradeBtn.dataset.grade,
          gradeName,
        };
        openClassDeleteModal({
          mode: "confirm",
          title: "Delete this class?",
          subtitle: "Students and exam results are kept",
          lead: "You are about to remove:",
          target: gradeName,
          message: "Only the empty class structure is removed.",
          hint: "If learners or exam papers still use this class, deletion will be stopped.",
        });
        return;
      }

      if (streamBtn) {
        const gradeName = streamBtn.dataset.gradeName || "this class";
        const streamName = streamBtn.dataset.stream;
        pendingClassDelete = {
          kind: "stream",
          branchId: streamBtn.dataset.branch,
          gradeId: streamBtn.dataset.grade,
          gradeName,
          stream: streamName,
        };
        openClassDeleteModal({
          mode: "confirm",
          title: "Remove this stream?",
          subtitle: "Students and exam results are kept",
          lead: "You are about to remove:",
          target: classTargetLabel(gradeName, streamName),
          message: `Only stream ${streamName} will be removed from ${gradeName}.`,
          hint: `Learners currently in ${classTargetLabel(gradeName, streamName)} are not deleted.`,
        });
      }
    });

    classDeleteConfirm.addEventListener("click", function () {
      if (!pendingClassDelete) return;

      const action = pendingClassDelete;
      const isGrade = action.kind === "grade";
      const target = classTargetLabel(action.gradeName, action.stream);
      const url = isGrade
        ? "/admin/grades/force-delete"
        : "/admin/streams/force-delete";
      const payload = isGrade
        ? { branch_id: action.branchId, grade_id: action.gradeId }
        : {
            branch_id: action.branchId,
            grade_id: action.gradeId,
            stream_name: action.stream,
          };

      classDeleteConfirm.disabled = true;
      classDeleteConfirm.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1"></span>Deleting';

      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) {
            classDeleteReloadOnClose = false;
            openClassDeleteModal({
              mode: "blocked",
              title: isGrade ? "Class was not deleted" : "Stream was not removed",
              subtitle: "Nothing was changed",
              lead: "Still in use:",
              target: data.target || target,
              message: data.error || `${target} is still in use.`,
              hint: data.detail || "Move the students first, then try again.",
            });
            return;
          }

          classDeleteReloadOnClose = true;
          const archived = Boolean(data.archived);
          openClassDeleteModal({
            mode: "success",
            title: archived
              ? "Class hidden"
              : isGrade
                ? "Class deleted"
                : "Stream removed",
            subtitle: archived
              ? "Exam records were kept"
              : "The school structure was updated",
            lead: archived ? "Hidden:" : "Removed:",
            target: data.target || target,
            message:
              data.message ||
              (archived
                ? `${target} was hidden. The original name can be used again.`
                : `${target} was removed.`),
            hint: archived
              ? "It no longer appears in class lists or dropdowns."
              : "Students and exam results were not deleted.",
          });
        })
        .catch(() => {
          classDeleteReloadOnClose = false;
          openClassDeleteModal({
            mode: "blocked",
            title: "Could not complete delete",
            subtitle: "Please try again",
            lead: "Target:",
            target,
            message: "The request failed. Nothing was deleted.",
            hint: "",
          });
        });
    });

    classDeleteModalEl.addEventListener("hidden.bs.modal", function () {
      pendingClassDelete = null;
      if (classDeleteReloadOnClose) {
        classDeleteReloadOnClose = false;
        refreshAcademicData();
      }
    });
  }

  const classRenameModalEl = document.getElementById("classRenameModal");
  const classRenameModal = classRenameModalEl
    ? bootstrap.Modal.getOrCreateInstance(classRenameModalEl)
    : null;
  const classRenameCard = document.getElementById("classRenameCard");
  const classRenameIcon = document.getElementById("classRenameIcon");
  const classRenameNoteIcon = document.getElementById("classRenameNoteIcon");
  const classRenameTitle = document.getElementById("classRenameTitle");
  const classRenameSubtitle = document.getElementById("classRenameSubtitle");
  const classRenameLead = document.getElementById("classRenameLead");
  const classRenameCurrent = document.getElementById("classRenameCurrent");
  const classRenameInput = document.getElementById("classRenameInput");
  const classRenameMessage = document.getElementById("classRenameMessage");
  const classRenameHint = document.getElementById("classRenameHint");
  const classRenameCancel = document.getElementById("classRenameCancel");
  const classRenameSave = document.getElementById("classRenameSave");
  const classRenameOk = document.getElementById("classRenameOk");
  let pendingClassRename = null;
  let classRenameReloadOnClose = false;

  function setClassRenameMode(mode) {
    if (!classRenameCard) return;

    classRenameCard.classList.remove("is-warning", "is-success");
    classRenameCancel.classList.add("d-none");
    classRenameSave.classList.add("d-none");
    classRenameOk.classList.add("d-none");
    classRenameSave.disabled = false;
    classRenameSave.innerHTML = '<i class="bi bi-check2 me-1"></i>Save';
    if (classRenameInput) classRenameInput.disabled = mode !== "edit";

    if (mode === "edit") {
      classRenameIcon.innerHTML = '<i class="bi bi-pencil-square"></i>';
      classRenameNoteIcon.innerHTML = '<i class="bi bi-info-circle"></i>';
      classRenameCancel.classList.remove("d-none");
      classRenameSave.classList.remove("d-none");
    } else if (mode === "blocked") {
      classRenameCard.classList.add("is-warning");
      classRenameIcon.innerHTML = '<i class="bi bi-shield-exclamation"></i>';
      classRenameNoteIcon.innerHTML = '<i class="bi bi-exclamation-circle"></i>';
      classRenameOk.classList.remove("d-none");
    } else {
      classRenameCard.classList.add("is-success");
      classRenameIcon.innerHTML = '<i class="bi bi-check-circle-fill"></i>';
      classRenameNoteIcon.innerHTML = '<i class="bi bi-check2-circle"></i>';
      classRenameOk.classList.remove("d-none");
    }
  }

  function openClassRenameModal({ mode, title, subtitle, lead, current, value, message, hint }) {
    if (!classRenameModal) return;
    setClassRenameMode(mode);
    classRenameTitle.textContent = title;
    classRenameSubtitle.textContent = subtitle || "";
    classRenameLead.textContent = lead || "";
    classRenameCurrent.textContent = current || "";
    classRenameMessage.textContent = message || "";
    classRenameHint.textContent = hint || "";
    if (typeof value === "string") classRenameInput.value = value;
    classRenameModal.show();
    if (mode === "edit") {
      setTimeout(() => {
        classRenameInput.focus();
        classRenameInput.select();
      }, 200);
    }
  }

  if (container && classRenameModal) {
    container.addEventListener("click", function (e) {
      const gradeBtn = e.target.closest(".rename-grade-btn");
      const streamBtn = e.target.closest(".rename-stream-btn");

      if (gradeBtn) {
        const gradeName = gradeBtn.dataset.gradeName || "";
        pendingClassRename = {
          kind: "grade",
          branchId: gradeBtn.dataset.branch,
          gradeId: gradeBtn.dataset.grade,
          gradeName,
        };
        openClassRenameModal({
          mode: "edit",
          title: "Rename this class?",
          subtitle: "Students stay in the same class",
          lead: "Currently named:",
          current: gradeName,
          value: gradeName,
          message: "Only the class name changes.",
          hint: "Marks and learners stay attached to this class.",
        });
        return;
      }

      if (streamBtn) {
        const gradeName = streamBtn.dataset.gradeName || "this class";
        const streamName = streamBtn.dataset.stream;
        pendingClassRename = {
          kind: "stream",
          branchId: streamBtn.dataset.branch,
          gradeId: streamBtn.dataset.grade,
          gradeName,
          stream: streamName,
        };
        openClassRenameModal({
          mode: "edit",
          title: "Rename this stream?",
          subtitle: "Learners in this stream keep their records",
          lead: "Currently named:",
          current: classTargetLabel(gradeName, streamName),
          value: streamName,
          message: `This will rename ${streamName} inside ${gradeName}.`,
          hint: "Students, lessons, and exam papers in this stream are updated to the new name.",
        });
      }
    });

    function submitClassRename() {
      if (!pendingClassRename || classRenameSave.disabled) return;

      const action = pendingClassRename;
      const isGrade = action.kind === "grade";
      const newName = (classRenameInput.value || "").trim();
      const current = isGrade
        ? action.gradeName
        : classTargetLabel(action.gradeName, action.stream);

      if (!newName) {
        openClassRenameModal({
          mode: "blocked",
          title: "Name required",
          subtitle: "Nothing was changed",
          lead: "Currently named:",
          current,
          value: newName,
          message: "Enter a new name before saving.",
          hint: "",
        });
        return;
      }

      const url = isGrade ? "/admin/grades/rename" : "/admin/streams/rename";
      const payload = isGrade
        ? {
            branch_id: action.branchId,
            grade_id: action.gradeId,
            new_name: newName,
          }
        : {
            branch_id: action.branchId,
            grade_id: action.gradeId,
            old_name: action.stream,
            new_name: newName,
          };

      classRenameSave.disabled = true;
      classRenameSave.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1"></span>Saving';

      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) {
            classRenameReloadOnClose = false;
            openClassRenameModal({
              mode: "blocked",
              title: isGrade ? "Class was not renamed" : "Stream was not renamed",
              subtitle: "Nothing was changed",
              lead: "Still named:",
              current: data.target || current,
              value: newName,
              message: data.error || "Could not rename.",
              hint: "Choose a name that is not already in use.",
            });
            return;
          }

          classRenameReloadOnClose = true;
          openClassRenameModal({
            mode: "success",
            title: isGrade ? "Class renamed" : "Stream renamed",
            subtitle: "The school structure was updated",
            lead: "Now named:",
            current: data.target || newName,
            value: newName,
            message: data.message,
            hint: "Open students, marks, or report cards to confirm they still match.",
          });
        })
        .catch(() => {
          classRenameReloadOnClose = false;
          openClassRenameModal({
            mode: "blocked",
            title: "Could not complete rename",
            subtitle: "Please try again",
            lead: "Currently named:",
            current,
            value: newName,
            message: "The request failed. Nothing was changed.",
            hint: "",
          });
        });
    }

    classRenameSave.addEventListener("click", submitClassRename);
    classRenameInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        submitClassRename();
      }
    });

    classRenameModalEl.addEventListener("hidden.bs.modal", function () {
      pendingClassRename = null;
      if (classRenameReloadOnClose) {
        classRenameReloadOnClose = false;
        refreshAcademicData();
      }
    });
  }

  // ---------------------- BUILD GRADE SELECT ----------------------
  function buildGradeSelect(data) {
    branchClassesDiv.innerHTML = "";

    const label = document.createElement("label");
    label.setAttribute("for", "classSelect");
    label.className = "sa-label";
    label.textContent = "Grade / Form";

    const select = document.createElement("select");
    select.className = "form-select form-select-sm sa-control";
    select.name = "class_id";
    select.id = "classSelect";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select class";
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    (typeof sortSchoolGrades === "function"
      ? sortSchoolGrades(data.grades)
      : data.grades
    ).forEach((grade) => {
      const option = document.createElement("option");
      option.value = grade.class_id;
      option.textContent = grade.grade_form;
      option.dataset.gradeForm = grade.grade_form;
      select.appendChild(option);
    });

    branchClassesDiv.appendChild(label);
    branchClassesDiv.appendChild(select);

    // Save hidden branch id
    const hiddenBranchIdInput = document.getElementById("selected-branch-id");
    if (hiddenBranchIdInput) hiddenBranchIdInput.value = data.branch_id;

    // Add grade change listener
    select.addEventListener("change", function () {
      clearStudentsList();

      const gradeForm = this.options[this.selectedIndex]?.dataset.gradeForm;
      if (!gradeForm) return;

      subjectContainer.innerHTML = `
                <div class="sa-loading">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span>Loading subjects…</span>
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
                <div class="sa-empty">
                    No subjects for this class. Add them under Subjects first.
                </div>
            `;
      return;
    }

    const label = document.createElement("label");
    label.setAttribute("for", "subjectSelect");
    label.className = "sa-label";
    label.textContent = "Subject";

    const select = document.createElement("select");
    select.className = "form-select form-select-sm sa-control";
    select.id = "subjectSelect";
    select.name = "subject_id";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select subject";
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    subjects.forEach((sub) => {
      const option = document.createElement("option");
      option.value = sub.id;
      option.textContent = sub.name;
      select.appendChild(option);
    });

    subjectContainer.appendChild(label);
    subjectContainer.appendChild(select);

    // Add subject change listener
    select.addEventListener("change", function () {
      // Add spinner has student data is loaded
      const studentContainer = document.querySelector(
        ".students-allocation-div",
      );
      studentContainer.innerHTML = `
                <div class="sa-loading">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span>Loading students…</span>
                </div>
            `;
      const subjectId = this.value;
      if (!subjectId) return;

      const classSelect = document.getElementById("classSelect");
      const branchId = document.getElementById("selected-branch-id").value;
      const classId = classSelect?.value;
      const gradeForm = classSelect?.selectedOptions[0]?.dataset.gradeForm;

      fetch("/admin/students/by-class-subject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branch_id: branchId,
          class_id: classId,
          grade_form: gradeForm,
          subject_id: subjectId,
        }),
      })
        .then((res) => res.json())
        .then((students) => {
          renderStudentsTable(students);
          scrollAssignmentIntoView();
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
            <div class="sa-empty">No students found for this class.</div>
        `;
      return;
    }

    let html = `
        <div class="sa-results">
            <div class="sa-results-head">
                <div class="sa-counts">
                    <span>Total students <strong>${students["students"].length}</strong></span>
                    <span>Done by <strong id="doneByStudentsCount">${students["allocated_count"]}</strong></span>
                </div>
                <div class="sa-results-actions">
                    <button type="button" class="sa-btn sa-btn-outline" id="allocateAllBtn">
                      <i class="bi bi-check2-square"></i>Check all
                    </button>
                    <button type="button" class="sa-btn sa-btn-outline" id="clearAllBtn">
                      <i class="bi bi-square"></i>Uncheck all
                    </button>
                    <button type="button" class="sa-btn sa-btn-primary sa-save-btn" id="applyAllocationBtn">
                      <i class="bi bi-save"></i>Save
                    </button>
                </div>
            </div>
            <div id="student-table" class="sa-table-wrap">
                <table class="sa-table">
                    <thead>
                        <tr>
                            <th class="sa-col-adm">Adm</th>
                            <th>Student</th>
                            <th class="sa-col-assign">Assign</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

    students["students"].forEach((student) => {
      html += `
            <tr class="${student.allocated ? "is-assigned" : ""}">
                <td class="sa-col-adm">${student.admission_number}</td>
                <td class="sa-name">${student.fullname}</td>
                <td class="sa-col-assign">
                  <input
                    type="checkbox"
                    class="form-check-input student-checkbox"
                    data-student-id="${student.id}"
                    ${student.allocated ? "checked" : ""}
                  >
                </td>
            </tr>
        `;
    });

    html += `
                    </tbody>
                </table>
            </div>
            <div class="sa-results-foot">
                <button type="button" class="sa-btn sa-btn-primary sa-save-btn">
                  <i class="bi bi-save"></i>Save
                </button>
            </div>
        </div>`;
    container.innerHTML = html;

    function setRowAssigned(checkbox) {
      const row = checkbox.closest("tr");
      if (!row) return;
      row.classList.toggle("is-assigned", checkbox.checked);
    }

    function setAllAssigned(checked) {
      document.querySelectorAll(".student-checkbox").forEach((cb) => {
        cb.checked = checked;
        setRowAssigned(cb);
      });
    }

    container.querySelectorAll(".student-checkbox").forEach((cb) => {
      cb.addEventListener("change", () => setRowAssigned(cb));
    });

    container.querySelectorAll(".sa-table tbody tr").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("input")) return;
        const checkbox = row.querySelector(".student-checkbox");
        if (!checkbox) return;
        checkbox.checked = !checkbox.checked;
        setRowAssigned(checkbox);
      });
    });

    const allocateAllBtn = document.getElementById("allocateAllBtn");
    if (allocateAllBtn) {
      allocateAllBtn.addEventListener("click", () => setAllAssigned(true));
    }

    const clearAllBtn = document.getElementById("clearAllBtn");
    if (clearAllBtn) {
      clearAllBtn.addEventListener("click", () => setAllAssigned(false));
    }

    function applySubjectAllocation() {
      const classSelect = document.getElementById("classSelect");
      const branchId = document.getElementById("selected-branch-id")?.value;
      const classId = classSelect?.value;
      const gradeForm = classSelect?.selectedOptions[0]?.dataset.gradeForm;
      const subjectId = document.getElementById("subjectSelect")?.value;
      const saveButtons = container.querySelectorAll(".sa-save-btn");

      if (!branchId || !classId || !subjectId) {
        showAssignmentNotice({
          success: false,
          title: "Could not save",
          message: "Choose a class and subject first.",
        });
        return;
      }

      const selectedStudents = Array.from(
        document.querySelectorAll(".student-checkbox:checked"),
      ).map((cb) => parseInt(cb.dataset.studentId));

      const payload = {
        branch_id: branchId,
        class_id: classId,
        grade_form: gradeForm,
        subject_id: parseInt(subjectId),
        students: selectedStudents,
      };

      saveButtons.forEach((btn) => {
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm" role="status"></span>Saving…';
      });

      fetch("/admin/subjects/allocate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "success") {
            selectedStudents.forEach((sid) => {
              const checkbox = document.querySelector(
                `.student-checkbox[data-student-id='${sid}']`,
              );
              if (checkbox) checkbox.checked = true;
            });

            const added = Number(data["added_count"] || 0);
            const already = Number(data.already_allocated_count || 0);
            document.getElementById("doneByStudentsCount").textContent =
              added + already;

            showAssignmentNotice({
              success: true,
              title: "Assignments saved",
              message: added
                ? `${added} student${added === 1 ? " was" : "s were"} assigned. ${already} already had this subject.`
                : `No new students were assigned. ${already} already had this subject.`,
            });
          } else {
            showAssignmentNotice({
              success: false,
              title: "Could not save",
              message: "Subject assignments could not be updated. Please try again.",
            });
          }
        })
        .catch((err) => {
          console.error(err);
          showAssignmentNotice({
            success: false,
            title: "Could not save",
            message: "Please check your connection and try again.",
          });
        })
        .finally(() => {
          saveButtons.forEach((btn) => {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-save"></i>Save';
          });
        });
    }

    container.querySelectorAll(".sa-save-btn").forEach((btn) => {
      btn.addEventListener("click", applySubjectAllocation);
    });
  }
});
