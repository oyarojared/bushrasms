document.addEventListener("DOMContentLoaded", function() {
    const uploadBtn = document.getElementById("uploadPassportBtn");
    const fileInput = document.querySelector("#passportUploadForm input[type='file']");
    const form = document.getElementById("passportUploadForm");

    // When the link/button is clicked, trigger the file input
    uploadBtn.addEventListener("click", function(e) {
        e.preventDefault();
        fileInput.click();
    });

    // When a file is selected, submit the form automatically
    fileInput.addEventListener("change", function() {
        if (fileInput.files.length > 0) {
            form.submit();
        }
    });
});