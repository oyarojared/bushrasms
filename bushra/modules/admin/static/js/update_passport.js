
// Work on updating the passport

document.addEventListener("DOMContentLoaded", function() {
    const triggerBtn = document.getElementById("triggerPassportUpload");
    const fileInput  = document.getElementById("passportInput");
    const form       = document.getElementById("photoUploadForm");

    // 1️⃣ Click button → opens file chooser
    triggerBtn.addEventListener("click", function() {
        fileInput.click();
    });

    // 2️⃣ File chosen → auto-submit form
    fileInput.addEventListener("change", function() {
        if (fileInput.files.length > 0) {
            form.submit();
        }
    });
}); 