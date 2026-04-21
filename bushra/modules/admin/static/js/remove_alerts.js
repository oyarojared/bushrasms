// Remover flashed messages alerts automtically

document.addEventListener("DOMContentLoaded", function() {
    const editBtn = document.getElementById("editStudentBtn");
    const studentInfoTab = document.getElementById("student-info");
    const studentInfoNav = document.querySelector('a[href="#student-info"]');

    editBtn.addEventListener("click", function(e) {
        e.preventDefault();

        // Switch to Student Info tab if not active
        if (!studentInfoNav.classList.contains("active")) {
            const tab = new bootstrap.Tab(studentInfoNav);
            tab.show();
        }

        // Scroll to the top of the student info tab
        studentInfoTab.scrollIntoView({ behavior: "smooth", block: "start" });
    });
}); 