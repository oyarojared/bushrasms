const gradingSystemSelect = document.getElementById('grading-system');
const gradingFields = document.getElementById('grading-fields');
const gradingPlaceholder = document.getElementById('grading-placeholder');
const boundaryContainer = document.getElementById('boundary-container');
const addBoundaryBtn = document.getElementById('add-boundary-btn');
const classesSection = document.getElementById('classes-section');

// ---------------------
// Add CBC row
// ---------------------
function addBoundaryRow() {
    const row = document.createElement('div');
    row.className = 'card p-3 shadow-sm boundary-row position-relative';
    row.innerHTML = `
        <div class="row g-2 align-items-center">
            <div class="col-md-2">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-arrow-down-right-circle"></i></span>
                    <input type="number" class="form-control" placeholder="Min Score" min="0" max="100">
                </div>
            </div>
            <div class="col-md-2">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-arrow-up-right-circle"></i></span>
                    <input type="number" class="form-control" placeholder="Max Score" min="0" max="100">
                </div>
            </div>
            <div class="col-md-2">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-award"></i></span>
                    <input type="text" class="form-control" placeholder="Performance Level (EE1, EE2)">
                </div>
            </div>
            <div class="col-md-2">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-star"></i></span>
                    <input type="number" class="form-control" placeholder="Points" min="0">
                </div>
            </div>
            <div class="col-md-3">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-journal-text"></i></span>
                    <input type="text" class="form-control" placeholder="Descriptor (Exceeding Expectation 1)">
                </div>
            </div>
            <div class="col-md-1 d-flex justify-content-end">
                <button type="button" class="btn btn-danger btn-sm remove-row" title="Remove">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    boundaryContainer.appendChild(row);

    // Remove button
    row.querySelector('.remove-row').addEventListener('click', () => {
        row.remove();
    });
}

// ---------------------
// Grading system change
// ---------------------
gradingSystemSelect.addEventListener('change', function() {
    const system = this.value;
    boundaryContainer.innerHTML = ''; // clear existing CBC rows

    if (!system) {
        gradingFields.style.display = 'none';
        gradingPlaceholder.style.display = 'none';
        classesSection.style.display = 'none';
        return;
    }

    classesSection.style.display = 'block';

    if (system === 'CBC') {
        gradingFields.style.display = 'block';
        gradingPlaceholder.style.display = 'none';
        addBoundaryRow(); // add first CBC row
    } else {
        gradingFields.style.display = 'none';
        gradingPlaceholder.style.display = 'block';
    }
});

// ---------------------
// Add boundary button
// ---------------------
addBoundaryBtn.addEventListener('click', addBoundaryRow);

// ---------------------
// Save grading configuration
// ---------------------
document.getElementById('save-grading').addEventListener('click', function() {
    const system = gradingSystemSelect.value;
    if (!system) return alert('Please select a grading system.');

    const boundaries = [];
    if (system === 'CBC') {
        boundaryContainer.querySelectorAll('.boundary-row').forEach(row => {
            const inputs = row.querySelectorAll('input');
            boundaries.push({
                min_score: Number(inputs[0].value),
                max_score: Number(inputs[1].value),
                performance_level: inputs[2].value,
                points: inputs[3].value ? Number(inputs[3].value) : null,
                descriptor: inputs[4].value || null
            });
        });
    }
    // Validate boundaries
    if (boundaries.some(b => b.min_score > b.max_score)) {
        return alert('Min score cannot be greater than max score in any boundary.');
    }

    if (boundaries.length === 0) {
        return alert('Please add at least one grading boundary.');
    }

    const selectedClasses = [];
    classesSection.querySelectorAll('input[type=checkbox]').forEach(chk => {
        if (chk.checked) selectedClasses.push(chk.value);
    });

    if (selectedClasses.length === 0) {
        return alert('Please select at least one class.');
    }

    // ---------------------
    // Send to backend
    // ---------------------
    fetch('/admin/save_grading_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            system,
            boundaries,
            selected_classes: selectedClasses
        })
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            alert('Grading configuration saved successfully.');
            boundaryContainer.innerHTML = ''; // optional: clear after save
        } else {
            alert(data.error || 'Failed to save grading configuration.');
        }
    })
    .catch(err => {
        console.error(err);
        alert('An error occurred while saving the configuration.');
    });
});