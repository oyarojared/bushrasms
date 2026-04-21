document.addEventListener("DOMContentLoaded", function () {

    // Clear grade, stream for class management.
    const gradeContainer2 = document.getElementById("grade-container-2")
    const streamContainer2 = document.getElementById("stream-container-2")

    const branchSelect = document.querySelector(".branch-select"); 


    function showSpinner(container) {
        container.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            </div>
        `;
    }

    function clearContainer(container) {
        container.innerHTML = "";
    }


    branchSelect.addEventListener("change", function () {
        // Work on selected branch.
        const branchId = this.value; 

        if (branchId === ""){
            gradeContainer2.innerHTML = `
                <small class="fw-bold text-danger">Please select branch to manage classes</small>
            `; 
        }else {
            // Valid branch selected. Fetch branch grade + (streams) data.
            fetchGradesForBranch(
                branchId,
                "grade-container-2",
                "stream-container-2"
            );
        }
            
    });


    // AJAX FETCH FUNCTION
    function fetchGradesForBranch(branchId, gradeContainerId, streamContainerId) {
        if (!branchId) return;

        const gradeContainer = document.getElementById(gradeContainerId);
        const streamContainer = document.getElementById(streamContainerId);
        
        showSpinner(gradeContainer);
        clearContainer(streamContainer);

        fetch(`/admin/api/grades/${branchId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch grades");
                return res.json();
            })
            .then(data => {
                renderGradesAndStreams(data, gradeContainerId, streamContainerId, "proceed-btn-container");
            })
            .catch(err => {
                console.error(err);
                gradeContainer.innerHTML =
                    `<small class="text-danger">
                        <i class="bi bi-x-circle-fill me-2"></i>Failed to load grades.
                    </small>`;
            });
    }




})