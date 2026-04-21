   function renderAcademicData(data) {
        // Branch header
        let html = `
            <div class="mb-3">
                <h6 class="fw-bold text-secondary">
                    <i class="bi bi-building me-2"></i>${data.branch_name}
                </h6>
            </div>
        `;

        if (!data.grades || !data.grades.length) {
            container.innerHTML = `
                <div class="text-danger fw-bold">
                    <i class="bi bi-x-circle-fill me-2"></i>No academic records found for this branch.
                </div>
            `;
            branchClassesDiv.innerHTML = `
                <small class='text-danger fw-bold'>
                    <i class="bi bi-x-circle-fill me-2"></i>No classes found!
                </small>
            `;
            subjectContainer.innerHTML = "";
            return;
        }

        html += `<div class="row g-3 fix-top-customized">`;
 
        // Render grades and streams
        data.grades.forEach(g => {
            html += `
                <div class="col-md-6 col-lg-4">
                    <div class="p-3 border rounded-3 shadow-sm h-100 bg-white">
                        <div class="container orange-line mb-2"></div>
                        <!-- Grade Header -->
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <h5 class="fw-bold mb-0 text-orange text-uppercase">
                                <i class="bi bi-journal-text me-2"></i>${g.grade_form}
                            </h5>
                            <span class="badge bg-info p-2">Total: ${g.totals.total}</span>
                        </div>

                        <!-- Totals -->
                        <div class="d-flex justify-content-between small text-muted mb-3">
                            <div><i class="bi bi-gender-male me-1 h5"></i>Boys: <strong class="text-primary">${g.totals.boys}</strong></div>
                            <div><i class="bi bi-gender-female me-1 h5"></i>Girls: <strong class="text-success">${g.totals.girls}</strong></div>
                        </div>

                        <!-- Streams -->
                        <div>
                            <div class="fw-semibold small text-secondary mb-1">Streams</div>
                            <button class="btn btn-sm btn-outline-danger mb-2" type="button" 
                            data-grade="${g.class_id}" data-branch="${data.branch_id}" id="deleteGradeBtn">
                                <i class="bi bi-trash me-1"></i>Delete
                            </button>
            `

            if (g.streams && g.streams.length) {
                g.streams.forEach(s => {
                    html += `
                        <div class="border rounded-2 p-2 mb-1 bg-light">
                            <div class="d-flex justify-content-between align-items-center">
                                <strong class="small text-dark">${s.name}</strong>
                                <span class="badge bg-light text-dark border">${s.total}</span>
                            </div>
                            <div class="d-flex justify-content-between small text-muted mt-1">
                                <span>B: ${s.boys}</span>
                                <span>G: ${s.girls}</span>
                            </div>
                        </div>
                        <div>
                            <h6 class="small text-center mt-2 text-success">Classteacher: <span class="text-muted text-uppercase">
                             ${s.teacher?.name || "Not assigned"}</span>
                        </div>
                        <button class="btn btn-sm btn-outline-danger mb-2" type="button" 
                        data-grade="${g.class_id}" data-stream="${s.name}" data-branch="${data.branch_id}" id="deleteGradeBtn">
                            <i class="bi bi-trash me-1"></i>Delete
                        </button>
                    `;
                });
            } else {
                html += `
                    <div class="text-muted small fst-italic">No streams available</div>
                    <div>
                        <h6 class="small text-center mt-2 text-success">Classteacher: <span class="text-muted text-uppercase">
                       ${g.teacher?.name || "Not assigned"}</span>
                        </h6>
                    </div>
                    `;
            }
            console.log(g.teacher)

            html += `</div></div></div>`;
        });

        html += `</div>`;
        container.innerHTML = html;

        // ---------------------- BUILD GRADE SELECT ----------------------
        buildGradeSelect(data);
    }