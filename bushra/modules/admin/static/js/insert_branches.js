const selectedBranch = document.getElementById("selected-branch");
const gradeContainer = document.getElementById("grade-container");  
const streamContainer = document.getElementById("stream-container-2"); 

selectedBranch.addEventListener("change", () => {
    const branchId = selectedBranch.value;
    if (!branchId) return;

    const url = gradesUrlBase + branchId;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            // Remove old grade select if it exists
            let oldGradeSelect = document.getElementById("grade-form-select");
            if (oldGradeSelect) oldGradeSelect.remove();

            // Create grade select
            const gradeSelect = document.createElement("select");
            gradeSelect.id = "grade-form-select";
            gradeSelect.name = "grade_form";
            gradeSelect.className = "form-select";
            gradeSelect.setAttribute("required", "true");
            gradeSelect.innerHTML = '<option value="">--- Select grade/form ---</option>';

            data.forEach(item => {
                const option = document.createElement("option");
                option.value = item.id;
                option.textContent = item.grade_form;
                option.dataset.streams = JSON.stringify(item.streams); // store streams
                gradeSelect.appendChild(option);
            });

            gradeContainer.appendChild(gradeSelect);

            // Remove stream select if previously there
            streamContainer.innerHTML = "";

            // Listen to grade change
            gradeSelect.addEventListener("change", () => {
                const selectedOption = gradeSelect.selectedOptions[0];
                const streams = JSON.parse(selectedOption.dataset.streams || "[]");

                // Clear previous stream select
                streamContainer.innerHTML = "";

                if (streams.length > 0) {
                    // Create stream select dynamically
                    const streamSelect = document.createElement("select");
                    streamSelect.name = "stream";
                    streamSelect.className = "form-select";
                    streamSelect.setAttribute("required", "true");
                    streamSelect.innerHTML = '<option value="">--- Select Stream ---</option>';

                    streams.forEach(s => {
                        const opt = document.createElement("option");
                        opt.value = s;
                        opt.textContent = s;
                        streamSelect.appendChild(opt);
                    });

                    streamContainer.appendChild(streamSelect);
                }
            });
        })
        .catch(err => console.error(err));
});

 