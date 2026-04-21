// Highlight selected row for visibility reasons

document.addEventListener('DOMContentLoaded', function () {
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

    dropdownToggles.forEach(button => {
        // Highlight row when dropdown opens
        button.addEventListener('show.bs.dropdown', function () {
            const row = button.closest('tr');
            if (row) row.classList.add('bg-light-green');
        });

        // Remove highlight when dropdown closes
        button.addEventListener('hide.bs.dropdown', function () {
            const row = button.closest('tr');
            if (row) row.classList.remove('bg-light-green');
        });
    });
}); 