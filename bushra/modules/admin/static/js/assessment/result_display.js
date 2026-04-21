async function loadReportCards(branchId, classId, examId, stream = null) {
    const container = document.getElementById("resultsContainer");
    container.innerHTML = `<p class="text-center">Loading report cards...</p>`;

    try {
        const res = await fetch(`/admin/api/exam-students-with-grades-all-subjects?branch_id=${branchId}&class_id=${classId}&exam_id=${examId}&stream=${stream}`);
        const data = await res.json();
        const students = data.students || [];

        if (students.length === 0) {
            container.innerHTML = `<p class="text-center text-muted">No students found for this selection.</p>`;
            return;
        }
        // No results found
        container.innerHTML = ""; // Clear loading text

        students.forEach(s => {
            const card = document.createElement("div");
            card.className = "mb-4 px-3"; // full width, separated by margin

            const passportUrl = s.passport
                ? `${STATIC_URL}uploads/passports/${s.passport}`
                : `${STATIC_URL}uploads/passports/default.jpg`;


            // Calculate total points
            const totalPoints = s.subjects.reduce((sum, sub) => sum + (sub.points || 0), 0);
            const maxPoints = s.subjects.length * 8;

            card.innerHTML = `
        <div class="card shadow border-0 mb-4 report-card">

            <!-- ===== SCHOOL HEADER ===== -->
            <div class="header-primary text-white py-3 px-3 rounded-top">
                <div class="row align-items-center">
                    <div class="col-3 text-center">
                <img src=""
                    alt="Logo"
                    class="img-fluid"
                    style="max-width: 120px; max-height: 120px;">
            </div>


                    <div class="col-6 text-center">
                        <h5 class="mb-1 fw-bold text-uppercase">${data.branch_name}</h5>
                        <small class="d-block">P.O. BOX 28-70100 GARISSA, KENYA</small>
                        <small class="d-block">Email: bushraschools2021@gmail.com | Tel: 0722339494</small>
                    </div>

                    <div class="col-3 text-center">
                        <img src="${passportUrl}"
                            class="rounded border"
                            style="width:70px;height:70px;object-fit:cover"
                            alt="Student Photo">
                        <small class="d-block mt-1">Student</small>
                    </div>
                </div>
            </div>

            <!-- ===== STUDENT INFO BAR ===== -->
            <div class="px-3 py-2 border-bottom bg-light">
                <div class="row">
                    <div class="col-md-6">
                        <strong>${s.full_name}</strong><br>
                        <small class="text-muted">
                            Admission No: ${s.admission_number}
                        </small>
                    </div>
                    <div class="col-md-6 text-md-end">
                        <small class="text-muted">
                            Assessment No: <strong>${s.assessment_no || '-'}</strong>
                        </small>
                    </div>
                </div>
            </div>

            <!-- ===== SUBJECT TABLE ===== -->
            <div class="card-body pt-3">
                <div class="table-responsive">
                    <table class="table table-sm align-middle table-bordered">
                        <thead class="table-secondary text-center">
                            <tr>
                                <th>Code</th>
                                <th class="text-start">Subject</th>
                                <th>Marks</th>
                                <th>Level</th>
                                <th>Points</th>
                                <th class="text-start">Descriptor</th>
                                <th class="text-start">Teacher</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${s.subjects.map(sub => `
                                <tr>
                                    <td class="text-center">${sub.code}</td>
                                    <td class="text-uppercase">${sub.name}</td>
                                    <td class="text-center fw-semibold">${sub.marks ?? '-'}</td>
                                    <td class="text-center">
                                        <span class="badge bg-info text-dark">
                                            ${sub.performance_level ?? '-'}
                                        </span>
                                    </td>
                                    <td class="text-center">${sub.points ?? '-'}</td>
                                    <td>${sub.descriptor ?? '-'}</td>
                                    <td>${sub.teacher ?? '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <!-- ===== TOTAL POINTS ===== -->
                <div class="mb-3 px-2">
                    <h6 class="fw-bold">Total Points</h6>
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span>${totalPoints}</span>
                    </div>

                </div>

                <!-- ===== CLASS TEACHER & STAMP PLACEHOLDER ===== -->
                <div class="mt-3 px-1">

                    <!-- Class Teacher -->
                    <div class="mb-2">
                        <strong>Class Teacher:</strong>
                        <span class="text-uppercase">${s.class_teacher || '____________________'}</span>
                    </div>

                    <div class="row g-3 align-items-stretch">

                        <!-- Optional Remarks / Additional Info -->
                        <div class="col-md-8">
                            <div class="border rounded p-2 h-100">
                                <h6 class="text-center mb-2 fw-bold">Remarks / Comments</h6>
                                <p class="m-0">${s.remarks || ""}</p>
                            </div>
                        </div>

                        <!-- School Stamp Placeholder -->
                        <div class="col-md-4">
                            <div class="border rounded h-100 d-flex align-items-center justify-content-center">
                                <div class="text-center text-muted">
                                    <small>Official School Stamp</small><br><br>
                                    <div style="
                                        width:140px;
                                        height:90px;
                                        border:2px dashed #999;
                                    "></div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <!-- ===== FOOTER ===== -->
            <div class="bg-light px-3 py-2 text-end border-top">
                <small class="text-muted">
                    Generated on ${new Date().toLocaleDateString()}
                </small>
            </div>

        </div>
        `;

            container.appendChild(card);
        });

    } catch (err) {
        console.error(err);
        container.innerHTML = `<p class="text-center text-danger">Failed to load report cards.</p>`;
    }
}



// Trigger example
document.getElementById("load-results").addEventListener("click", () => {
    const branchId = document.getElementById("results-branch").value;
    const classId = document.getElementById("results-grade").value;
    const examId = document.getElementById("results-exam").value;
    const stream = document.getElementById("results-stream").value || null;

    if (!branchId || !classId || !examId) {
        alert("Please select branch, grade, and exam.");
        return;
    }

    loadReportCards(branchId, classId, examId, stream);

    // Create Generate PDF button only once
    let existingBtn = document.getElementById("generate-pdf-btn");
    if (existingBtn) return;

    const generatePdfBtn = document.createElement("button");
    generatePdfBtn.id = "generate-pdf-btn";
    generatePdfBtn.className = "btn btn-sm btn-danger mb-3 w-25";
    generatePdfBtn.innerHTML = `<i class="bi bi-download me-1"></i> Download Report Cards`;

    generatePdfBtn.addEventListener("click", () => {
        const branchId = document.getElementById("results-branch").value;
        const classId = document.getElementById("results-grade").value;
        const examId = document.getElementById("results-exam").value;
        const stream = document.getElementById("results-stream").value || null;
        generatePDF(branchId, classId, examId, stream);
    });

    document.getElementById("fetchResultsDiv").appendChild(generatePdfBtn);
});


function generatePDF(branchId, classId, examId, stream) {
    blockUI(
        "Please wait…This may take upto 1 minute",
        "Generating report cards PDF"
    );

    fetch("/admin/generate-reportcards-pdf", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({
            branch_id: branchId,
            class_id: classId,
            exam_id: examId,
            stream: stream
        })
    })
    .then(async (response) => {
        if (!response.ok) {
            throw new Error("Failed to generate PDF");
        }

        const blob = await response.blob();

        // 🔥 Extract filename from Content-Disposition header
        const contentDisposition = response.headers.get("Content-Disposition");

        let filename = "report.pdf"; // fallback

        if (contentDisposition) {
            const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/);
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
        a.download = filename;  // ✅ Uses backend filename

        document.body.appendChild(a);
        a.click();

        a.remove();
        window.URL.revokeObjectURL(url);
    })
    .catch(err => {
        console.error(err);
        alert("PDF generation failed.");
    })
    .finally(() => {
        unblockUI();
    });
}