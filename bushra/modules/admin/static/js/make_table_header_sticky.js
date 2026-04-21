/* Sticky table header CSS applied dynamically */
const style = document.createElement('style');
    style.innerHTML = `
    .scroll-table-wrapper {
        max-height: 400px;
        overflow-y: auto;
    }
    .sticky-header {
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .sticky-header th {
        background-color: #6c757d; /* match bg-secondary */
        color: white;
    }
    `;
document.head.appendChild(style);
