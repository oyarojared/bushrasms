
let excelBtn = document.getElementById('excel-btn');
let excelForm = document.getElementById('excel-download-form');
let branchId = document.getElementById('branch-id');
let gradeId = document.getElementById('grade-id');

excelBtn.addEventListener("click", () => {
    if (!excelForm){
        alert("Adjust Filters and click 'Fetch Data' to generate excel file!")
    }
    excelForm.submit();
}); 