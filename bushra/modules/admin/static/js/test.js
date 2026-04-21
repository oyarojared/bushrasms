document.addEventListener("DOMContentLoaded", function () {

    /* ===========================
       DELETE MODAL LOGIC
    ============================ */
    const deleteModal = document.getElementById("deleteSubjectModal");
    const deleteForm = document.getElementById("deleteSubjectForm");

    if (deleteModal && deleteForm) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const subjectId = button.getAttribute("data-subject-id");
            deleteForm.action = `/admin/delete_subject/` + subjectId;
        });
    }

    /* ===========================
       CHECK ALL GRADES
    ============================ */
    const checkAll = document.getElementById("checkAllGrades");
    const gradeCheckboxes = document.querySelectorAll(".grade-checkbox");

    if (checkAll && gradeCheckboxes.length) {
        checkAll.addEventListener("change", function () {
            gradeCheckboxes.forEach(cb => cb.checked = this.checked);
        });

        gradeCheckboxes.forEach(cb => {
            cb.addEventListener("change", function () {
                checkAll.checked = [...gradeCheckboxes].every(c => c.checked);
            });
        });
    }

    /* ===========================
       DELETE CONFIRMATION TEXT
    ============================ */
    document.querySelectorAll(".delete-btn").forEach(btn => {
        btn.addEventListener("click", function () {
            const target = document.getElementById("target-subject");
            if (target) {
                target.textContent = this.dataset.name;
            }
        });
    });

    /* ===========================
       LOAD SUBJECTS BY GRADE (AJAX)
    ============================ */
    const gradeSelect = document.getElementById("grades");
    const tableContainer = document.getElementById("subjectsTableContainer");

    if (gradeSelect && tableContainer) {
        gradeSelect.addEventListener("change", function () {
            const selectedGrade = this.value;

            if (!selectedGrade) {
                tableContainer.innerHTML = `
                    <div class="text-muted small">
                        Select a grade to view assigned subjects.
                    </div>
                `;
                return;
            }

            fetch(`/admin/subjects/by-grade?grade_form=${encodeURIComponent(selectedGrade)}`)
                .then(res => {
                    if (!res.ok) throw new Error("Failed to load subjects");
                    return res.text();
                })
                .then(html => {
                    tableContainer.innerHTML = html;
                })
                .catch(() => {
                    tableContainer.innerHTML = `
                        <div class="text-danger small">
                            Failed to load subjects.
                        </div>
                    `;
                });
        });
    }

});
