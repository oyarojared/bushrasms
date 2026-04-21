const marksheetBranchSelect = document.getElementById('marksheet-branch');
const marksheetGradeSelect = document.getElementById('marksheet-grade');
const marksheetStreamSelect = document.getElementById('marksheet-stream');
const marksheetStreamWrapper = document.getElementById('marksheet-stream-wrapper');
const marksheetSubjectSelect = document.getElementById('marksheet-subject');
const loadMarksBtn = document.getElementById('load-marksheet-students');
const marksContainer = document.getElementById('marksheetStudentsContainer');

// Disable subject initially
marksheetSubjectSelect.disabled = true;

// Utility to populate a select
function populateSelect(selectEl, items, placeholder = '--Select--', textKey = 'name') {
    selectEl.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item[textKey] || item.name || item.grade_form;
        selectEl.appendChild(opt);
    });
}

// Load branches
fetch('/admin/api/branches')
    .then(res => res.json())
    .then(data => populateSelect(marksheetBranchSelect, data, 'Select Branch'));

// =======================
// BRANCH CHANGE
// =======================
marksheetBranchSelect.addEventListener('change', function() {
    const branchId = this.value;

    // Reset everything
    marksheetGradeSelect.innerHTML = '<option value="">--Select Grade--</option>';
    marksheetStreamSelect.innerHTML = '<option value="">All</option>';
    marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';

    marksheetSubjectSelect.disabled = true; 
    marksheetStreamWrapper.classList.add('d-none');

    if (!branchId) return;

    fetch(`/admin/api/grades/${branchId}`)
        .then(res => res.json())
        .then(data => populateSelect(marksheetGradeSelect, data, 'Select Grade', 'grade_form'));
});

// =======================
// GRADE CHANGE
// =======================
marksheetGradeSelect.addEventListener('change', function() {
    const branchId = marksheetBranchSelect.value;
    const classId = this.value;

    marksheetStreamSelect.innerHTML = '<option value="">All</option>';
    marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';
    marksheetSubjectSelect.disabled = true; 
    marksheetStreamWrapper.classList.add('d-none');

    if (!branchId || !classId) return;

    // Fetch grade info
    fetch(`/admin/api/grades/${branchId}`)
        .then(res => res.json())
        .then(data => {
            const gradeObj = data.find(g => g.id == classId);

            if (gradeObj?.streams?.length) {
                // Has streams → wait for stream
                populateSelect(
                    marksheetStreamSelect,
                    gradeObj.streams.map(s => ({ id: s, name: s })),
                    'Select Stream'
                );
                marksheetStreamWrapper.classList.remove('d-none');

                // Keep subject disabled
            } else {
                // No streams → enable + load subjects
                marksheetSubjectSelect.disabled = false; 
                loadSubjects(branchId, classId, '');
            }
        });
});

// =======================
// STREAM CHANGE
// =======================
marksheetStreamSelect.addEventListener('change', function() {
    const branchId = marksheetBranchSelect.value;
    const classId = marksheetGradeSelect.value;
    const stream = this.value || '';

    if (!stream) {
        marksheetSubjectSelect.disabled = true; 
        return;
    }

    marksheetSubjectSelect.disabled = false; 
    loadSubjects(branchId, classId, stream);
});

// =======================
// LOAD SUBJECTS
// =======================
function loadSubjects(branchId, classId, stream) {
    marksheetSubjectSelect.innerHTML = '<option value="">--Select Subject--</option>';

    fetch(`/admin/api/subjects?branch_id=${branchId}&class_id=${classId}&stream=${stream}`)
        .then(res => res.json())
        .then(data => populateSelect(marksheetSubjectSelect, data, '--Select Subject--'));
}

// =======================
// LOAD STUDENTS TABLE
// =======================
loadMarksBtn.addEventListener('click', function() {
    const branchId = marksheetBranchSelect.value;
    const classId = marksheetGradeSelect.value;
    const stream = marksheetStreamSelect.value || '';
    const subjectId = marksheetSubjectSelect.value;

    if (!branchId || !classId || !subjectId) {
        alert('Please select branch, grade, and subject.');
        return;
    }

    marksContainer.innerHTML = `<p class="text-center">Loading students…</p>`;

    fetch(`/admin/api/students-by-subject?branch_id=${branchId}&class_id=${classId}&subject_id=${subjectId}&stream=${stream}`)
        .then(res => res.json())
        .then(data => {
            if (!data.students?.length) {
                marksContainer.innerHTML = `<p class="text-center text-muted">No students found for this selection.</p>`;
                return;
            }

            let tableHtml = `
                <div class="d-flex justify-content-end align-items-center mb-2 gap-2">
                    <button class="btn btn-secondary btn-sm" id="downloadClasslistBtn">
                        <i class="bi bi-people me-1"></i> Classlist
                    </button>
                    <button class="btn btn-danger btn-sm" id="downloadBtn">
                        <i class="bi bi-download me-1"></i> Marksheet
                    </button>
                </div>
                <div id="marksheetstoprint">
                    <h4 class="text-center mb-1 fw-bold text-uppercase">${data.students[0].branch_name}</h4>
                    <h5 class="text-center text-uppercase">
                        ${data.students[0].class_name} ${data.students[0].stream} Marksheet
                    </h5>
                    <div class="w-100 text-center border-bottom pb-2 mb-3">
                        <strong class="text-center">Subject:</strong> ${data.students[0]?.subject_name || 'N/A'} 
                        <strong class="text-center">Teacher:</strong> ${data.students[0]?.subject_teacher || 'Not assigned'}
                    </div>
                    <table class="table table-bordered table-sm" style="border: solid 2px black !important;">
                        <thead class="table-light">
                            <tr>
                                <th style="width: 3%;">#</th>
                                <th style="width: 15%;">ADM NO</th>
                                <th style="width: 45%;">FULLNAME</th>
                                <th style="width: 20%;">MARKS</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.students.forEach((s, index) => {
                tableHtml += `
                    <tr style="font-size: 0.78em;">
                        <td>${index + 1}</td>
                        <td>${s.admission_number}</td>
                        <td>${s.full_name}</td>
                        <td></td>
                    </tr>
                `;
            });

            tableHtml += `</tbody></table></div>`;
            marksContainer.innerHTML = tableHtml;

            document.getElementById('downloadBtn').addEventListener('click', () => {
                const element = document.getElementById('marksheetstoprint');

                // Get selected texts
                const gradeText = marksheetGradeSelect.options[marksheetGradeSelect.selectedIndex]?.text || 'Class';
                const streamText = marksheetStreamSelect.value
                    ? marksheetStreamSelect.options[marksheetStreamSelect.selectedIndex]?.text
                    : '';
                const subjectText = marksheetSubjectSelect.options[marksheetSubjectSelect.selectedIndex]?.text || 'Subject';

                // Build filename
                let fileName = gradeText;

                if (streamText) {
                    fileName += ` ${streamText}`;
                }

                fileName += ` - ${subjectText} Marksheet.pdf`;

                // Clean invalid filename characters
                fileName = fileName.replace(/[<>:"/\\|?*]+/g, '');

                html2pdf().from(element).set({
                    margin: 0.5,
                    filename: fileName,
                    html2canvas: { scale: 2 },
                    jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
                }).save();
            });

            document.getElementById('downloadClasslistBtn').addEventListener('click', () => {
    const branchId = marksheetBranchSelect.value;
    const classId = marksheetGradeSelect.value;
    const stream = marksheetStreamSelect.value || '';

    if (!branchId || !classId) {
        alert('Please select branch and grade.');
        return;
    }

    // Show loading
    marksContainer.innerHTML = `<p class="text-center">Loading classlist…</p>`;

    fetch(`/admin/api/students-by-class?branch_id=${branchId}&class_id=${classId}&stream=${stream}`)
        .then(res => res.json())
        .then(data => {

            if (!data.students?.length) {
                marksContainer.innerHTML = `<p class="text-center text-muted">No students found.</p>`;
                return;
            }

            // Build classlist HTML
            let html = `
                <div id="classlisttoprint">
                    <h4 class="text-center fw-bold text-uppercase">${data.students[0].branch_name}</h4>
                    <h5 class="text-center text-uppercase">
                        ${data.students[0].class_name} ${data.students[0].stream} Class List
                    </h5>
                    <div class="text-center border-bottom pb-2 mb-3">
                        <strong>Class Teacher:</strong> ${data.students[0].class_teacher}
                    </div>

                    <table class="table table-bordered table-sm" style="border: solid 2px black !important;">
                        <thead class="table-light">
                            <tr>
                                <th style="width:5%">#</th>
                                <th style="width:20%">ADM NO</th>
                                <th>FULL NAME</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.students.forEach((s, i) => {
                html += `
                    <tr style="font-size: 0.78em;">
                        <td>${i + 1}</td>
                        <td>${s.admission_number}</td>
                        <td>${s.full_name}</td>
                    </tr>
                `;
            });

            html += `</tbody></table></div>`;

            marksContainer.innerHTML = html;

            // Auto download PDF
            const element = document.getElementById('classlisttoprint');

            // Build filename
            const gradeText = marksheetGradeSelect.options[marksheetGradeSelect.selectedIndex]?.text || 'Class';
            const streamText = marksheetStreamSelect.value
                ? marksheetStreamSelect.options[marksheetStreamSelect.selectedIndex]?.text
                : '';

            let fileName = gradeText;
            if (streamText) fileName += ` ${streamText}`;
            fileName += ` Classlist.pdf`;

            fileName = fileName.replace(/[<>:"/\\|?*]+/g, '');

            html2pdf().from(element).set({
                margin: 0.5,
                filename: fileName,
                html2canvas: { scale: 2 },
                jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
            }).save();
        })
        .catch(err => {
            console.error(err);
            marksContainer.innerHTML = `<p class="text-danger text-center">Failed to load classlist.</p>`;
        });
});
        })
        .catch(err => {
            console.error(err);
            marksContainer.innerHTML = `<p class="text-center text-danger">Failed to load students.</p>`;
        });
});