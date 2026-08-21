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
            streamContainerId: "stream-container-2"
        });
    });

    branchSelect.dispatchEvent(new Event("change"));
});


/* ============================================================
   UTILITIES
============================================================ */

function showSpinner(container, theme) {
    const loadingClass = theme === "lessons" ? "sa-loading" : "text-center py-3";
    container.innerHTML = `
        <div class="${loadingClass}">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            ${theme === "lessons" ? "<span>Loading classes…</span>" : ""}
        </div>
    `;
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
    theme = ""
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
                theme
            );
        })
        .catch(() => {
            gradeContainer.innerHTML =
                theme === "lessons"
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
    theme = ""
) {
    const isLessons = theme === "lessons";
    gradeContainer.innerHTML = "";
    streamContainer.innerHTML = "";
    if (proceedContainer) proceedContainer.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {
        gradeContainer.innerHTML = isLessons
            ? `<div class="sa-empty">No classes available.</div>`
            : `<small class="text-danger fw-bold">No classes available.</small>`;
        return;
    }

    const gradeSelect = document.createElement("select");
    gradeSelect.className = isLessons
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

    if (isLessons) {
        const gradeLabel = document.createElement("label");
        gradeLabel.className = "sa-label";
        gradeLabel.setAttribute("for", "lesson-grade-select");
        gradeLabel.textContent = "Grade / Form";
        gradeSelect.id = "lesson-grade-select";
        gradeContainer.appendChild(gradeLabel);
    }
    gradeContainer.appendChild(gradeSelect);

    let actionBtn = null;

    if (proceedContainer && onProceed) {
        actionBtn = document.createElement("button");
        actionBtn.type = "button";
        actionBtn.className = isLessons
            ? "sa-btn sa-btn-primary d-none"
            : "btn btn-sm btn-secondary d-none";
        actionBtn.innerHTML = isLessons
            ? `Assign teachers`
            : `<i class="bi bi-arrow-right me-2"></i>Proceed`;
        proceedContainer.appendChild(actionBtn);
    }

    gradeSelect.addEventListener("change", () => {
        streamContainer.innerHTML = "";
        if (actionBtn) actionBtn.classList.add("d-none");

        const opt = gradeSelect.options[gradeSelect.selectedIndex];
        if (!opt || !gradeSelect.value) return;

        const streams = JSON.parse(opt.dataset.streams || "[]");

        if (!streams.length) {
            if (actionBtn) actionBtn.classList.remove("d-none");
            return;
        }

        const streamSelect = document.createElement("select");
        streamSelect.className = isLessons
            ? "form-select form-select-sm sa-control"
            : "form-select form-select-sm";
        streamSelect.innerHTML = `<option value="">Select stream</option>`;

        streams.forEach(s => {
            const o = document.createElement("option");
            o.value = s;
            o.textContent = s;
            streamSelect.appendChild(o);
        });

        if (isLessons) {
            const streamLabel = document.createElement("label");
            streamLabel.className = "sa-label";
            streamLabel.setAttribute("for", "lesson-stream-select");
            streamLabel.textContent = "Stream";
            streamSelect.id = "lesson-stream-select";
            streamContainer.appendChild(streamLabel);
        }
        streamContainer.appendChild(streamSelect);

        streamSelect.addEventListener("change", () => {
            if (actionBtn) {
                actionBtn.classList.toggle("d-none", !streamSelect.value);
            }
        });
    });

    if (actionBtn) {
        actionBtn.addEventListener("click", () => {
            const streamSelect = streamContainer.querySelector("select");
            onProceed({
                class_id: Number(gradeSelect.value),
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
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content at-modal">
                <div class="modal-header at-modal-header">
                    <div>
                        <h6 class="at-modal-title">Assign teachers</h6>
                        <p class="at-modal-copy">${classLabel}</p>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body at-modal-body">
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
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
        <div class="modal-content at-modal">
            <div class="modal-header at-modal-header">
                <div>
                    <h6 class="at-modal-title">Assign teachers</h6>
                    <p class="at-modal-copy">${classLabel || "Choose a teacher for each subject."}</p>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body at-modal-body">
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
                                    <tr>
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
                    <button type="button" id="saveAssignmentsBtn" class="sa-btn sa-btn-primary">Save</button>
                </div>
            </div>
        </div>
    </div>`;

    document.body.appendChild(modal);
    new bootstrap.Modal(modal).show();

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
                saveBtn.textContent = "Save";
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
            onProceed: ({ class_id, stream }) => {
                openClassManagementModal({
                    branch_id: Number(branchId),
                    class_id,
                    stream
                });
            }
        });
        
    });
});


function openClassManagementModal({ branch_id, class_id, stream }) {

    window.currentClassContext = {
        branch_id,
        class_id,
        stream
    };



    const existing = document.getElementById("classManagementModal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.className = "modal fade";
    modal.id = "classManagementModal";
    modal.tabIndex = -1;

    modal.innerHTML = `
    <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white px-3 pt-1 pb-1">
                <h6 class="modal-title">
                    <i class="bi bi-gear me-2"></i>Manage Class
                </h6>
                <button class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
           <div class="modal-body border m-3">
                <!-- Context (always visible) --> 
                <div class="alert alert-light small mb-2">
                    <strong>Branch:</strong> <span id="ctx-branch"></span> |
                    <strong>Class:</strong> <span id="ctx-class"></span> |
                    <strong>Stream:</strong> <span id="ctx-stream"></span>
                </div>

                <!-- Tabs -->
                <ul class="nav nav-tabs mb-3" role="tablist">
                    <li class="nav-item">
                         
                    </li>
                    <li class="nav-item">
                        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-teacher">
                            <i class="bi bi-person me-2"></i>Class Teacher
                        </button>
                    </li>
                    <li class="nav-item">
                        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-streams">
                            <i class="bi bi-house me-2"></i>Streams
                        </button>
                    </li>
                    <li class="nav-item">
                        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-move-students">
                            <i class="bi bi-arrow-left-right me-2"></i>Move Students
                        </button>
                    </li>
                </ul>

                <div class="tab-content"> 
                    <div class="tab-pane fade" id="tab-teacher">
                            <div class="mb-2 small text-muted">
                                Assign or change the class teacher for this class.
                            </div>

                            <div class="mb-3">
                                <label class="form-label small fw-bold">Current Class Teacher</label>
                                <div id="current-class-teacher" class="small text-primary">
                                    Loading...
                                </div>
                            </div>

                            <div class="mb-3">
                                <label class="form-label small fw-bold">Select Teacher</label>
                                <select id="class-teacher-select" class="form-select form-select-sm">
                                    <option value="">-- Select Teacher --</option>
                                </select>
                            </div>

                            <div class="text-end">
                                <button id="save-class-teacher-btn"
                                        class="btn btn-primary btn-sm"
                                        disabled>
                                    Save Class Teacher
                                </button>
                            </div>
                    </div>

                    <div class="tab-pane fade" id="tab-streams"></div>
                    <div class="tab-pane fade" id="tab-move-students"></div>
                </div>
            </div>

            <hr class="mx-4">

        </div>
      
    </div>
    `;

    document.body.appendChild(modal);
    new bootstrap.Modal(modal).show();

    document.getElementById("ctx-branch").textContent = branch_id;
    document.getElementById("ctx-class").textContent = class_id;
    document.getElementById("ctx-stream").textContent = stream || "N/A";

}


document.addEventListener("shown.bs.tab", function (e) {
    if (!e.target.matches('[data-bs-target="#tab-teacher"]')) return;
    loadClassTeacherTab();
});
 
function loadClassTeacherTab() {
    const ctx = window.currentClassContext;
    if (!ctx) return;

    const currentDiv = document.getElementById("current-class-teacher");
    const select = document.getElementById("class-teacher-select");
    const saveBtn = document.getElementById("save-class-teacher-btn");

    // Reset UI
    currentDiv.textContent = "Loading...";
    select.innerHTML = `<option value="">-- Select Teacher --</option>`;
    saveBtn.disabled = true;

    const params = new URLSearchParams({
        branch_id: ctx.branch_id,
        class_id: ctx.class_id,
        stream: ctx.stream || ""
    });

    fetch(`/admin/api/class-teacher-context?${params}`)
        .then(res => {
            if (!res.ok) throw new Error("Failed to fetch class teacher data");
            return res.json();
        })
        .then(data => {
            // Show current teacher
            currentDiv.textContent = data.current_teacher
                ? data.current_teacher.name
                : "Not assigned";

            // Populate dropdown
            data.teachers.forEach(t => {
                const opt = document.createElement("option");
                opt.value = t.id;
                opt.textContent = t.name;
                if (data.current_teacher && t.id === data.current_teacher.id) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });

            saveBtn.disabled = false;

            // Attach click handler **after elements exist**
            saveBtn.onclick = () => {
                const teacherId = select.value;
                if (!teacherId) {
                    currentDiv.textContent = "Please select a teacher";
                    return;
                }

                saveBtn.disabled = true;
                saveBtn.textContent = "Saving...";

                fetch("/admin/api/save-class-teacher", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        branch_id: ctx.branch_id,
                        class_id: ctx.class_id,
                        stream: ctx.stream || "",
                        teacher_id: Number(teacherId)
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        currentDiv.textContent = data.teacher_name;
                    } else {
                        currentDiv.textContent = data.message || "Failed to save";
                    }
                })
                .catch(err => {
                    console.error(err);
                    currentDiv.textContent = "An unexpected error occurred";
                })
                .finally(() => {
                    saveBtn.disabled = false;
                    saveBtn.textContent = "Save Class Teacher";
                });
            };
        })
        .catch(err => {
            console.error(err);
            currentDiv.textContent = "Failed to load data";
        });
}
