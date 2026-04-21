// Load Grades / Forms Dynamically
async function loadGradesStreams(branchId, gradeContainerId, streamContainerId) {

        const gradeContainer = document.getElementById(gradeContainerId);
        const streamContainer = document.getElementById(streamContainerId);

        // Clear previous content
        gradeContainer.innerHTML = '';
        streamContainer.innerHTML = '';
        streamContainer.style.display = 'none';

        if (!branchId) return;

        try {
            // Load grades from API
            const response = await fetch(`/admin/api/grades/${branchId}`);
            const classes = await response.json();


            if (!classes || classes.length === 0) return;

            // -------------------------------
            // LABEL: Grades / Forms
            // -------------------------------
            const gradeLabel = document.createElement('label');
            gradeLabel.textContent = "Grade / Form";
            gradeLabel.classList.add('form-label', 'fw-bold');
            gradeLabel.setAttribute("for", "select-grade-dynamic");
            gradeContainer.appendChild(gradeLabel);

            // -------------------------------
            // SELECT: Grades / Forms
            // -------------------------------
            const gradeSelect = document.createElement('select');
            gradeSelect.classList.add('form-select');
            gradeSelect.id = 'select-grade-dynamic';
            gradeSelect.name = 'grade_form';
            gradeSelect.required = true;

            gradeSelect.innerHTML = `<option value="">Select Grade/Form</option>`;

            classes.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.grade_form;
                option.dataset.streams = JSON.stringify(c.streams || []);
                gradeSelect.appendChild(option);
            });

            gradeContainer.appendChild(gradeSelect);

            // -------------------------------
            // STREAM HANDLER
            // -------------------------------
            gradeSelect.addEventListener('change', () => {
                const selectedOption = gradeSelect.selectedOptions[0];
                const streams = JSON.parse(selectedOption.dataset.streams || '[]');

                // Reset streams container
                streamContainer.innerHTML = '';
                streamContainer.style.display = 'none';

                if (streams.length > 0) {

                    // LABEL: Stream
                    const streamLabel = document.createElement('label');
                    streamLabel.textContent = "Stream";
                    streamLabel.classList.add('form-label', 'fw-bold');
                    streamLabel.setAttribute("for", "select-stream-dynamic");
                    streamContainer.appendChild(streamLabel);

                    // SELECT: Stream
                    const streamSelect = document.createElement('select');
                    streamSelect.classList.add('form-select');
                    streamSelect.id = 'select-stream-dynamic';
                    streamSelect.name = 'stream';
                    streamSelect.required = true;

                    streamSelect.innerHTML = `<option value="">Select Stream</option>`;

                    streams.forEach(s => {
                        const option = document.createElement('option');
                        option.value = s;
                        option.textContent = s;
                        streamSelect.appendChild(option);
                    });

                    streamContainer.appendChild(streamSelect);
                    streamContainer.style.display = 'block';
                }
            });

        } catch (error) {
            console.error("Error loading grades/forms:", error);
        }
}

// -----------------------------------
// Listen for branch selection
// -----------------------------------
const branchSelect = document.getElementById('select-branch-element');

branchSelect.addEventListener('change', () => {
    const branchId = branchSelect.value;
    loadGradesStreams(branchId, 'grade-forms-container', 'stream-select-container');
});