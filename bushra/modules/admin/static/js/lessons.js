document.addEventListener("DOMContentLoaded", function () {

    const branchSelect = document.querySelector(".branch-select");
    const branchNameSpan = document.getElementById("selected-branch-name");
    const targetBranch = document.getElementById("target-branch");

    if (!branchSelect) return;

    branchSelect.addEventListener("change", function () {
        const branchId = this.value;

        /* ---------- HEADER TEXT ---------- */
        if (branchId) {
            branchNameSpan.classList.remove("text-danger", "fw-bold");
            branchNameSpan.textContent =
                `Choose a class, then assign ${this.options[this.selectedIndex]?.text || "this school"} teachers to each subject.`;
        } else {
            branchNameSpan.classList.remove("text-danger", "fw-bold");
            branchNameSpan.textContent =
                "Choose a class, then assign a teacher to each subject.";

            document.getElementById("grade-container").innerHTML =
                `<div class="sa-empty">Select a school to load classes.</div>`;
            document.getElementById("stream-container").innerHTML = "";
            document.getElementById("proceed-btn-container").innerHTML = "";
            document.getElementById("grade-container-2").innerHTML = "";
            document.getElementById("stream-container-2").innerHTML = "";
            return;
        }

        targetBranch.value = branchId;

        /* ---------- TAB THREE ---------- */
        initGradeStreamSelector({
            branchId,
            gradeContainerId: "grade-container",
            streamContainerId: "stream-container",
            proceedContainerId: "proceed-btn-container",
            theme: "lessons",
            onProceed: ({ class_id, stream }) => {
                fetchClassSubjectsTeachers({
                    branch_id: Number(branchId),
                    class_id,
                    stream
                });
            }
        });

        /* ---------- TAB FOUR ---------- */
        initGradeStreamSelector({
            branchId,
            gradeContainerId: "grade-container-2",
            streamContainerId: "stream-container-2",
            proceedContainerId: "class-manage-btn-container",
            theme: "classteachers",
            proceedLabel: "Assign class teacher",
            onProceed: ({ class_id, class_name, stream }) => {
                openClassTeacherModal({
                    branch_id: Number(branchId),
                    class_id,
                    class_name,
                    stream
                });
            }
        });
    });

    branchSelect.dispatchEvent(new Event("change"));
});


/* ============================================================
   UTILITIES
============================================================ */

function showSpinner(container, theme) {
    const isCardTheme = theme === "lessons" || theme === "classteachers";
    const loadingClass = isCardTheme ? "sa-loading" : "text-center py-3";
    container.innerHTML = `
        <div class="${loadingClass}">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            ${isCardTheme ? "<span>Loading classes…</span>" : ""}
        </div>
    `;
}

function scrollActionIntoView(el) {
    const scroller = document.querySelector(".main-content");
    if (!el || !scroller) return;

    requestAnimationFrame(() => {
        const elRect = el.getBoundingClientRect();
        const scrollerRect = scroller.getBoundingClientRect();
        const pad = 28;
        if (
            elRect.bottom <= scrollerRect.bottom - pad &&
            elRect.top >= scrollerRect.top + pad
        ) {
            return;
        }

        const nextTop =
            scroller.scrollTop + (elRect.bottom - scrollerRect.bottom) + pad;
        scroller.scrollTo({
            top: Math.max(0, nextTop),
            behavior: "smooth",
        });
    });
}

function revealActionButton(actionBtn) {
    if (!actionBtn) return;
    actionBtn.classList.remove("d-none");
    requestAnimationFrame(() => scrollActionIntoView(actionBtn));
}

function clearContainer(container) {
    if (container) container.innerHTML = "";
}


/* ============================================================
   REUSABLE GRADE + STREAM ENGINE
============================================================ */

function initGradeStreamSelector({
    branchId,
    gradeContainerId,
    streamContainerId,
    proceedContainerId = null,
    onProceed = null,
    theme = "",
    proceedLabel = ""
}) {
    if (!branchId) return;

    const gradeContainer = document.getElementById(gradeContainerId);
    const streamContainer = document.getElementById(streamContainerId);
    const proceedContainer = proceedContainerId
        ? document.getElementById(proceedContainerId)
        : null;

    showSpinner(gradeContainer, theme);
    clearContainer(streamContainer);
    if (proceedContainer) clearContainer(proceedContainer);

    fetch(`/admin/api/grades/${branchId}`)
        .then(res => {
            if (!res.ok) throw new Error();
            return res.json();
        })
        .then(data => {
            renderGradesAndStreamsReusable(
                data,
                gradeContainer,
                streamContainer,
                proceedContainer,
                onProceed,
                theme,
                proceedLabel
            );
        })
        .catch(() => {
            const isCardTheme = theme === "lessons" || theme === "classteachers";
            gradeContainer.innerHTML = isCardTheme
                ? `<div class="sa-empty">Failed to load classes.</div>`
                : `<small class="text-danger fw-bold">Failed to load classes.</small>`;
        });
}


function renderGradesAndStreamsReusable(
    data,
    gradeContainer,
    streamContainer,
    proceedContainer,
    onProceed,
    theme = "",
    proceedLabel = ""
) {
    const isCardTheme = theme === "lessons" || theme === "classteachers";
    const gradeSelectId = theme === "classteachers" ? "ct-grade-select" : "lesson-grade-select";
    const streamSelectId = theme === "classteachers" ? "ct-stream-select" : "lesson-stream-select";
    gradeContainer.innerHTML = "";
    streamContainer.innerHTML = "";
    if (proceedContainer) proceedContainer.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {
        gradeContainer.innerHTML = isCardTheme
            ? `<div class="sa-empty">No classes available.</div>`
            : `<small class="text-danger fw-bold">No classes available.</small>`;
        return;
    }

    const gradeSelect = document.createElement("select");
    gradeSelect.className = isCardTheme
        ? "form-select form-select-sm sa-control"
        : "form-select form-select-sm mb-2";
    gradeSelect.innerHTML = `<option value="">Select class</option>`;

    const grades = typeof sortSchoolGrades === "function"
        ? sortSchoolGrades(data)
        : data;

    grades.forEach(cls => {
        const opt = document.createElement("option");
        opt.value = cls.id;
        opt.textContent = cls.grade_form;
        opt.dataset.streams = JSON.stringify(cls.streams || []);
        gradeSelect.appendChild(opt);
    });

    if (isCardTheme) {
        const gradeLabel = document.createElement("label");
        gradeLabel.className = "sa-label";
        gradeLabel.setAttribute("for", gradeSelectId);
        gradeLabel.textContent = "Grade / Form";
        gradeSelect.id = gradeSelectId;
        gradeContainer.appendChild(gradeLabel);
    }
    gradeContainer.appendChild(gradeSelect);

    let actionBtn = null;

    if (proceedContainer && onProceed) {
        actionBtn = document.createElement("button");
        actionBtn.type = "button";
        actionBtn.className = isCardTheme
            ? "sa-btn sa-btn-primary d-none"
            : "btn btn-sm btn-secondary d-none";
        actionBtn.innerHTML = proceedLabel || (isCardTheme
            ? `Assign teachers`
            : `<i class="bi bi-arrow-right me-2"></i>Proceed`);
        proceedContainer.appendChild(actionBtn);
    }

    gradeSelect.addEventListener("change", () => {
        streamContainer.innerHTML = "";
        if (actionBtn) actionBtn.classList.add("d-none");

        const opt = gradeSelect.options[gradeSelect.selectedIndex];
        if (!opt || !gradeSelect.value) return;

        const streams = JSON.parse(opt.dataset.streams || "[]");

        if (!streams.length) {
            revealActionButton(actionBtn);
            return;
        }

        const streamSelect = document.createElement("select");
        streamSelect.className = isCardTheme
            ? "form-select form-select-sm sa-control"
            : "form-select form-select-sm";
        streamSelect.innerHTML = `<option value="">Select stream</option>`;

        streams.forEach(s => {
            const o = document.createElement("option");
            o.value = s;
            o.textContent = s;
            streamSelect.appendChild(o);
        });

        if (isCardTheme) {
            const streamLabel = document.createElement("label");
            streamLabel.className = "sa-label";
            streamLabel.setAttribute("for", streamSelectId);
            streamLabel.textContent = "Stream";
            streamSelect.id = streamSelectId;
            streamContainer.appendChild(streamLabel);
        }
        streamContainer.appendChild(streamSelect);

        streamSelect.addEventListener("change", () => {
            if (!actionBtn) return;
            if (streamSelect.value) {
                revealActionButton(actionBtn);
            } else {
                actionBtn.classList.add("d-none");
            }
        });
    });

    if (actionBtn) {
        actionBtn.addEventListener("click", () => {
            const streamSelect = streamContainer.querySelector("select");
            const classOpt = gradeSelect.options[gradeSelect.selectedIndex];
            onProceed({
                class_id: Number(gradeSelect.value),
                class_name: classOpt ? classOpt.textContent : "",
                stream: streamSelect ? streamSelect.value : null
            });
        });
    }
}


/* ============================================================
   FETCH CLASS CONTEXT + ASSIGNMENT MODAL
============================================================ */

function fetchClassSubjectsTeachers(data) {
    fetch("/admin/api/class-context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(res => {
            if (!res.ok) throw new Error();
            return res.json();
        })
        .then(renderAssignTeachersModal)
        .catch(console.error);
}


/* ============================================================
   MODAL + SAVE (UNCHANGED CORE LOGIC)
============================================================ */

function renderAssignTeachersModal(data) {
    const existing = document.getElementById("assignTeachersModal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.className = "modal fade";
    modal.id = "assignTeachersModal";
    modal.setAttribute("data-bs-backdrop", "static");
    modal.setAttribute("data-bs-keyboard", "false");

    const classLabel = [data.class_name, data.stream].filter(Boolean).join(" · ");
    const teachers = [...(data.teachers || [])].sort((a, b) => {
        const left = String(a.fullname || "").trim().toLocaleLowerCase();
        const right = String(b.fullname || "").trim().toLocaleLowerCase();
        return left.localeCompare(right);
    });
    const teacherOptions = (selectedId) =>
        teachers
            .map(
                (t) => `
                    <option value="${t.id}" ${t.id === selectedId ? "selected" : ""}>
                        ${t.title ? `${t.title} ` : ""}${t.fullname}
                    </option>
                `
            )
            .join("");

    if (!data.subjects.length) {
        modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered at-dialog">
            <div class="modal-content at-modal">
                <div class="at-modal-header">
                    <div>
                        <h6 class="at-modal-title">
                          <i class="bi bi-person-badge"></i>
                          Assign teachers
                        </h6>
                        <p class="at-modal-copy">${classLabel || "Choose a teacher for each subject."}</p>
                    </div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="at-modal-body">
                    <div class="at-empty">
                        No subjects found for this class. Assign students and subjects first.
                    </div>
                </div>
                <div class="at-modal-footer">
                    <div class="at-modal-actions">
                        <button type="button" class="sa-btn sa-btn-outline" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>`;
        document.body.appendChild(modal);
        new bootstrap.Modal(modal).show();
        return;
    }

    modal.innerHTML = `
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable at-dialog">
        <div class="modal-content at-modal">
            <div class="at-modal-header">
                <div>
                    <h6 class="at-modal-title">
                      <i class="bi bi-person-badge"></i>
                      Assign teachers
                    </h6>
                    <p class="at-modal-copy">${classLabel || "Choose a teacher for each subject."}</p>
                </div>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="at-modal-body">
                <form id="assignTeachersForm">
                    <div class="at-table-wrap">
                        <table class="at-table">
                            <thead>
                                <tr>
                                    <th>Code</th>
                                    <th>Subject</th>
                                    <th class="at-col-count">Students</th>
                                    <th>Teacher</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.subjects.map(s => `
                                    <tr class="${s.assigned_teacher_id ? "" : "is-unassigned"}">
                                        <td class="at-col-code">${s.code || ""}</td>
                                        <td class="at-subject">${s.name}</td>
                                        <td class="at-col-count">${s.student_count}</td>
                                        <td>
                                            <select class="form-select form-select-sm at-teacher-select" name="subject_${s.id}">
                                                <option value="">Select teacher</option>
                                                ${teacherOptions(s.assigned_teacher_id)}
                                            </select>
                                        </td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </form>
            </div>
            <div class="at-modal-footer">
                <div class="at-modal-actions">
                    <button type="button" class="sa-btn sa-btn-outline" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" id="saveAssignmentsBtn" class="sa-btn sa-btn-primary">
                      <i class="bi bi-save"></i>Save
                    </button>
                </div>
            </div>
        </div>
    </div>`;

    document.body.appendChild(modal);
    new bootstrap.Modal(modal).show();

    modal.querySelectorAll(".at-teacher-select").forEach((select) => {
        select.addEventListener("change", () => {
            const row = select.closest("tr");
            if (row) row.classList.toggle("is-unassigned", !select.value);
        });
    });

    document.getElementById("saveAssignmentsBtn").onclick = () =>
        saveTeacherAssignments(data.branch_id, data.class_id, data.stream);
}


/* ============================================================
   SAVE ASSIGNMENTS
============================================================ */

function saveTeacherAssignments(branch_id, class_id, stream) {
    const form = document.getElementById("assignTeachersForm");
    const saveBtn = document.getElementById("saveAssignmentsBtn");
    const payload = {
        branch_id,
        class_id,
        stream,
        assignments: [...form.querySelectorAll("select")].map(s => ({
            subject_id: Number(s.name.split("_")[1]),
            teacher_id: s.value ? Number(s.value) : null
        }))
    };

    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving…";
    }

    fetch("/admin/api/save-teacher-assignments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
        .then(async (res) => {
            let data = {};
            try {
                data = await res.json();
            } catch (err) {
                data = {};
            }
            if (!res.ok || data.success === false) {
                throw new Error(data.error || "Could not save teacher assignments.");
            }
            showAssignmentNotice({
                success: true,
                title: "Assignments saved",
                message: "Teachers for this class have been updated.",
                closeForm: true,
            });
        })
        .catch((err) => {
            showAssignmentNotice({
                success: false,
                title: "Could not save",
                message: "The teacher list could not be updated. Please try again.",
                closeForm: false,
            });
        })
        .finally(() => {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="bi bi-save"></i>Save';
            }
        });
}

function showAssignmentNotice({ success, title, message, closeForm }) {
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

    const noticeModal = bootstrap.Modal.getOrCreateInstance(noticeEl);
    const assignEl = document.getElementById("assignTeachersModal");
    const assignModal = assignEl ? bootstrap.Modal.getInstance(assignEl) : null;

    if (closeForm && assignModal) {
        assignEl.addEventListener(
            "hidden.bs.modal",
            () => noticeModal.show(),
            { once: true }
        );
        assignModal.hide();
        return;
    }

    noticeModal.show();
}


// Ensure Class Management tab loads grades when activated
document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener("shown.bs.tab", function (e) {
        if (e.target.id !== "tab-four-tab") return;

        const branchId = document.getElementById("target-branch")?.value;
        if (!branchId) return;

        initGradeStreamSelector({
            branchId,
            gradeContainerId: "grade-container-2",
            streamContainerId: "stream-container-2",
            proceedContainerId: "class-manage-btn-container",
            theme: "classteachers",
            proceedLabel: "Assign class teacher",
            onProceed: ({ class_id, class_name, stream }) => {
                openClassTeacherModal({
                    branch_id: Number(branchId),
                    class_id,
                    class_name,
                    stream
                });
            }
        });
    });
});


function openClassTeacherModal({ branch_id, class_id, class_name, stream }) {
    const existing = document.getElementById("classTeacherModal");
    if (existing) existing.remove();

    const classLabel = [class_name, stream].filter(Boolean).join(" · ");
    const modal = document.createElement("div");
    modal.className = "modal fade";
    modal.id = "classTeacherModal";
    modal.setAttribute("data-bs-backdrop", "static");
    modal.setAttribute("data-bs-keyboard", "false");

    modal.innerHTML = `
    <div class="modal-dialog modal-dialog-centered cls-add-dialog">
        <div class="modal-content cls-add-modal">
            <div class="cls-add-header">
                <div>
                    <h6 class="cls-add-title">
                        <i class="bi bi-person-video3"></i>
                        Assign class teacher
                    </h6>
                    <p class="at-modal-copy">${classLabel || "Choose the class teacher."}</p>
                </div>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="cls-add-body">
                <div id="class-teacher-status" class="sa-loading">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span>Loading teachers…</span>
                </div>
                <div id="class-teacher-form" class="d-none">
                    <div class="cls-add-field">
                        <label class="cls-add-label">Current class teacher</label>
                        <div id="current-class-teacher" class="ct-current"></div>
                    </div>
                    <div class="cls-add-field">
                        <label class="cls-add-label" for="class-teacher-select">Class teacher</label>
                        <select id="class-teacher-select" class="form-select form-select-sm">
                            <option value="">Select teacher</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="cls-add-footer">
                <button type="button" class="sa-btn sa-btn-outline" data-bs-dismiss="modal">Cancel</button>
                <button type="button" id="save-class-teacher-btn" class="sa-btn sa-btn-primary" disabled>
                    <i class="bi bi-save"></i>Save
                </button>
            </div>
        </div>
    </div>`;

    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();

    loadClassTeacherForm({ branch_id, class_id, stream });
}


function loadClassTeacherForm({ branch_id, class_id, stream }) {
    const statusEl = document.getElementById("class-teacher-status");
    const formEl = document.getElementById("class-teacher-form");
    const currentDiv = document.getElementById("current-class-teacher");
    const select = document.getElementById("class-teacher-select");
    const saveBtn = document.getElementById("save-class-teacher-btn");
    if (!select || !saveBtn) return;

    const params = new URLSearchParams({
        branch_id,
        class_id
    });
    if (stream) params.set("stream", stream);

    fetch(`/admin/api/class-teacher-context?${params}`)
        .then((res) => {
            if (!res.ok) throw new Error("Failed to fetch class teacher data");
            return res.json();
        })
        .then((data) => {
            const teachers = [...(data.teachers || [])].sort((a, b) =>
                String(a.name || "").localeCompare(String(b.name || ""), undefined, {
                    sensitivity: "base"
                })
            );

            currentDiv.textContent = data.current_teacher
                ? data.current_teacher.name
                : "Not assigned";
            currentDiv.classList.toggle("is-empty", !data.current_teacher);

            select.innerHTML = `<option value="">Select teacher</option>`;
            teachers.forEach((t) => {
                const opt = document.createElement("option");
                opt.value = t.id;
                opt.textContent = t.name;
                if (data.current_teacher && t.id === data.current_teacher.id) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });

            const markSelect = () => {
                select.classList.toggle("is-unassigned", !select.value);
            };
            markSelect();
            select.addEventListener("change", markSelect);

            statusEl.classList.add("d-none");
            formEl.classList.remove("d-none");
            saveBtn.disabled = false;

            saveBtn.onclick = () => {
                const teacherId = select.value;
                if (!teacherId) {
                    currentDiv.textContent = "Please select a teacher";
                    currentDiv.classList.add("is-empty");
                    return;
                }

                saveBtn.disabled = true;
                saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>Saving…';

                fetch("/admin/api/save-class-teacher", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        branch_id,
                        class_id,
                        stream: stream || null,
                        teacher_id: Number(teacherId)
                    })
                })
                    .then((res) => res.json())
                    .then((result) => {
                        if (!result.success) {
                            showAssignmentNotice({
                                success: false,
                                title: "Could not save",
                                message: result.message || "The class teacher could not be updated.",
                                closeForm: false
                            });
                            return;
                        }

                        const modalEl = document.getElementById("classTeacherModal");
                        const modalInstance = modalEl
                            ? bootstrap.Modal.getInstance(modalEl)
                            : null;
                        const notice = {
                            success: true,
                            title: "Class teacher saved",
                            message: `${result.teacher_name} is now the class teacher.`,
                            closeForm: false
                        };
                        if (modalInstance && modalEl) {
                            modalEl.addEventListener(
                                "hidden.bs.modal",
                                () => showAssignmentNotice(notice),
                                { once: true }
                            );
                            modalInstance.hide();
                        } else {
                            showAssignmentNotice(notice);
                        }
                    })
                    .catch(() => {
                        showAssignmentNotice({
                            success: false,
                            title: "Could not save",
                            message: "Please check your connection and try again.",
                            closeForm: false
                        });
                    })
                    .finally(() => {
                        saveBtn.disabled = false;
                        saveBtn.innerHTML = '<i class="bi bi-save"></i>Save';
                    });
            };
        })
        .catch(() => {
            statusEl.className = "sa-empty";
            statusEl.textContent = "Failed to load teachers.";
        });
}
