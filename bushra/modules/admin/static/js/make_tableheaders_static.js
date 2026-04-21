document.addEventListener("DOMContentLoaded", function() {
    const tableContainers = document.querySelectorAll('.table-scroll-container');
    const offset = 70; // distance from top

    function adjustHeight() {
        const viewportHeight = window.innerHeight;
        tableContainers.forEach(tableContainer => {
            const containerTop = tableContainer.getBoundingClientRect().top;
            if (containerTop <= offset) {
                tableContainer.style.maxHeight = (viewportHeight - offset - 20) + 'px';
                tableContainer.style.overflowY = 'auto';
            } else {
                tableContainer.style.maxHeight = '388px';
                tableContainer.style.overflowY = 'visible';
            }
        });
    }

    window.addEventListener('scroll', adjustHeight);
    window.addEventListener('resize', adjustHeight);
    adjustHeight();

});
