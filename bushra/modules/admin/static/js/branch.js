document.addEventListener("DOMContentLoaded", function () {
  const select = document.getElementById("branchSelect");
  const branchform = document.getElementById("branchForm");
  const branchSelect = document.getElementById("branchSelect");

  if (data) {
    branchSelect.value = data.id;
  }

  select.addEventListener("change", function () {
    const branchId = this.value;
    if (branchId) {
      // dynamically set form action
      branchform.action = baseUrl.replace("1", branchId);
      branchform.submit();
    }
  });

  // ------ UPDATE AND ADD BRANCH MODAL FUNCTIONALITY------ //
  const editBtn = document.getElementById("editBranchBtn");
  const addBtn = document.getElementById("add-branch-link");

  const addModalEl = document.getElementById("addModal");
  const addModal = new bootstrap.Modal(addModalEl);

  const modalHeaderTitle = document.getElementById("modal-header-title");
  const formHeader = document.getElementById("form-header");
  const submitBtn = document.getElementById("submit-btn");
  const form = document.getElementById("addBranchForm");

  /* ============================================================
       RESET BACKGROUND COLORS WHEN MODAL CLOSES
    ============================================================ */
  addModalEl.addEventListener("hidden.bs.modal", () => {
    const inputs = document.querySelectorAll(".form-control, .form-select");
    inputs.forEach((input) => (input.style.backgroundColor = ""));
  });

  /* ============================================================
       ADD MODE
    ============================================================ */
  addBtn.addEventListener("click", function () {
    modalHeaderTitle.innerHTML = "ADD BRANCH / SCHOOL";
    formHeader.innerHTML = "Branch / School Data Entry";
    submitBtn.innerHTML = `
            <i class="bi bi-plus-circle me-1"></i> Add
        `;

    // Clear inputs when adding
    form.reset();

    // Reset highlights also when opening in ADD mode
    const inputs = document.querySelectorAll(".form-control, .form-select");
    inputs.forEach((input) => (input.style.backgroundColor = ""));

    form.action = add_branch_url;
    console.log(add_branch_url);
  });

  /* ============================================================
       EDIT MODE
    ============================================================ */
  editBtn.addEventListener("click", function () {
    modalHeaderTitle.innerHTML = "UPDATE BRANCH / SCHOOL INFO";
    formHeader.innerHTML = "Branch / School Info Update";
    submitBtn.innerHTML = `
            <i class="bi bi-arrow-repeat me-1"></i> Update
        `;

    // Highlight fields in light yellow for update mode
    const inputs = document.querySelectorAll(".form-control, .form-select");
    inputs.forEach((input) => {
      input.style.backgroundColor = "rgb(241 240 236)";
    });

    // Prefill from Jinja
    const branch = data;

    form.querySelector("[name='branch_name']").value = branch.branch_name || "";
    form.querySelector("[name='school_code']").value = branch.school_code || "";
    form.querySelector("[name='branch_manager']").value =
      branch.branch_manager || "";
    form.querySelector("[name='branch_level']").value =
      branch.branch_level || "";
    form.querySelector("[name='branch_head']").value = branch.branch_head || "";
    form.querySelector("[name='school_gender']").value =
      branch.school_gender || "";
    form.querySelector("[name='school_type']").value = branch.school_type || "";
    form.querySelector("[name='email']").value = branch.email || "";

    // Open modal
    addModal.show();

    form.action = update_branch_url;
  });

  // COLORS
  const genderColors = ["#0d6efd", "#dc3545"]; // Blue (M), Red (F)
  const classColors = [
    "#0d6efd",
    "#198754",
    "#ffc107",
    "#dc3545",
    "#6f42c1",
    "#20c997",
  ];

  // STUDENT GENDER CHART
  new Chart(document.getElementById("studentGenderChart"), {
    type: "doughnut",
    data: {
      labels: ["Male", "Female"],
      datasets: [
        {
          data: studentGender,
          backgroundColor: genderColors,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });

  // TEACHER GENDER CHART
  new Chart(document.getElementById("teacherGenderChart"), {
    type: "doughnut",
    data: {
      labels: ["Male", "Female"],
      datasets: [
        {
          data: teacherGender,
          backgroundColor: genderColors,
          hoverOffset: 8,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });

  // STUDENTS PER CLASS BAR CHART
  new Chart(document.getElementById("studentsPerClassChart"), {
    type: "bar",
    data: {
      labels: Object.keys(studentsPerClass),
      datasets: [
        {
          label: "Students",
          data: Object.values(studentsPerClass),
          backgroundColor: classColors,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 5 },
        },
      },
    },
  });
});
