document.addEventListener("DOMContentLoaded", function () {

    // SEND SUBJECT DELETE REQUEST TO THE SERVER
    const deleteModal = document.getElementById("deleteSubjectModal");
    const deleteForm = document.getElementById("deleteSubjectForm");

    deleteModal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        const subjectId = button.getAttribute("data-subject-id");

        deleteForm.action = `/admin/delete_subject/` + subjectId;
    });


    // CHECKING ALL GRADES / FORMS / CLASSES FOR THE TARGET SUBJECT
    const checkAll = document.getElementById("checkAllGrades");
    const gradeCheckboxes = document.querySelectorAll(".grade-checkbox");

    if (!checkAll || gradeCheckboxes.length === 0) return;

    checkAll.addEventListener("change", function () {
        gradeCheckboxes.forEach(cb => cb.checked = this.checked);
    });

    gradeCheckboxes.forEach(cb => {
        cb.addEventListener("change", function () {
            checkAll.checked = [...gradeCheckboxes].every(c => c.checked);
        });
    });


    // MODIFY DELETE CONFIRMATION MODAL
    const deleteBtns = document.querySelectorAll(".delete-btn");
    deleteBtns.forEach(btn => {
        btn.addEventListener("click", function() {
            document.getElementById("target-subject").textContent = this.dataset.name
        });
    });
    

    
    // SEND AJAX REQUEST TO GET SUBJECTS DATA TO DISPLAY
    const gradeSelect = document.getElementById("grades");
    const tableContainer = document.getElementById("subjectsTableContainer");

    if (!gradeSelect || !tableContainer) return;

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
                if (!res.ok) {
                    throw new Error("Failed to load subjects");
                }
                return res.text();    
            })
            .then(html => {
                tableContainer.innerHTML = html;
            })
            .catch(err => {
                console.error(err);
                tableContainer.innerHTML = `
                    <div class="text-danger small">
                        Failed to load subjects.
                    </div>
                `;
            });
    });
    

});