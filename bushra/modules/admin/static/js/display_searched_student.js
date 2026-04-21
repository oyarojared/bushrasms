// Display searched student(s) in a bootstrap modal.
document.getElementById("studentSearchForm").addEventListener("submit", function(e) {
    e.preventDefault(); // prevent normal submission

    const formData = new FormData(this);

    fetch(this.action, {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        const modalBody = document.getElementById("modalBodyContent");

        if (data.status === "success" && data.students.length > 0) {
            let table = `
                <table class="table table-bordered table-striped small">
                    <thead>
                        <tr>
                            <th>Full Name</th>
                            <th>Adm No</th> 
                            <th>Branch</th>
                            <th>Grade/Form</th>
                            <th>Stream</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            data.students.forEach(stu => {
                table += `
                    <tr>
                        <td>${stu.fullname.toUpperCase()}</td>
                        <td>${stu.admission_number}</td> 
                        <td>${stu.branch}</td>
                        <td>${stu.grade_form}</td>
                        <td>${stu.stream || "---"}</td>
                        <td>
                            <a href="/admin/student_profile/${stu.id}" class="text-orange fw-bold">
                                <i class="bi bi-eye me-2"></i>View
                            </a>
                        </td>
                    </tr>
                `;
            });
            table += "</tbody></table>"; 
            modalBody.innerHTML = table;
        } else {
            modalBody.innerHTML = `
                <div class="alert alert-warning text-center">
                   <i class="bi bi-exclamation-triangle me-2" style="font-size: 1.5rem;"></i>
                    <strong>No student found!</strong>
                </div>
            `;
        }

        // Show modal
        const myModal = new bootstrap.Modal(document.getElementById("searchResultsModal"));
        myModal.show();

    })
    .catch(err => {
        console.error(err);
        const modalBody = document.getElementById("modalBodyContent");
        modalBody.innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="bi bi-exclamation-triangle me-2" style="font-size: 1.5rem;"></i>
                <strong>Error fetching data. Please try again later!</strong>
            </div>
        `;
        const myModal = new bootstrap.Modal(document.getElementById("searchResultsModal"));
        myModal.show();
    });
});