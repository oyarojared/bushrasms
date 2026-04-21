document.addEventListener("DOMContentLoaded", function() { 
     const filterBranchesForm = document.getElementById("filter-branches-form");
     const excelBtn = document.getElementById("excel-btn");


     excelBtn.addEventListener("click", () => {
        filterBranchesForm.action = `/admin/download_teachers_excel_file`
        filterBranchesForm.submit();
     });
}); 