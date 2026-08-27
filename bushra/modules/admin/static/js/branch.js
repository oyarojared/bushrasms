document.addEventListener("DOMContentLoaded", function () {
  const select = document.getElementById("branchSelect");
  const branchform = document.getElementById("branchForm");

  if (typeof data !== "undefined" && data && select) {
    select.value = String(data.id);
  }

  select?.addEventListener("change", function () {
    const branchId = this.value;
    if (!branchId || !branchform) return;
    const template = typeof baseUrl === "string" ? baseUrl : "";
    branchform.action = template.replace(/\/\d+(?:\/)?$/, "/" + branchId);
    branchform.submit();
  });

  const editBtn = document.getElementById("editBranchBtn");
  const addBtn = document.getElementById("add-branch-link");
  const addModalEl = document.getElementById("addModal");
  const form = document.getElementById("addBranchForm");
  const modalHeaderTitle = document.getElementById("modal-header-title");
  const formHeader = document.getElementById("form-header");
  const submitBtn = document.getElementById("submit-btn");

  if (!addModalEl || !form) return;

  const addModal = new bootstrap.Modal(addModalEl);

  addModalEl.addEventListener("hidden.bs.modal", () => {
    document.querySelectorAll("#addBranchForm .form-control, #addBranchForm .form-select")
      .forEach((input) => (input.style.backgroundColor = ""));
  });

  addBtn?.addEventListener("click", function () {
    modalHeaderTitle.innerHTML = "ADD BRANCH / SCHOOL";
    formHeader.innerHTML = "Branch / School Data Entry";
    submitBtn.innerHTML = `<i class="bi bi-plus-circle me-1"></i> Add`;
    form.reset();
    document.querySelectorAll("#addBranchForm .form-control, #addBranchForm .form-select")
      .forEach((input) => (input.style.backgroundColor = ""));
    form.action = add_branch_url;
  });

  function setSelectValue(select, value) {
    if (!select) return;
    const raw = value == null ? "" : String(value).trim();
    if (!raw) {
      select.value = "";
      return;
    }
    const byValue = [...select.options].find((opt) => opt.value === raw);
    if (byValue) {
      select.value = byValue.value;
      return;
    }
    const needle = raw.toLowerCase();
    const byLabel = [...select.options].find(
      (opt) => opt.text.trim().toLowerCase() === needle
    );
    select.value = byLabel ? byLabel.value : "";
  }

  editBtn?.addEventListener("click", function () {
    if (typeof data === "undefined" || !data) return;

    modalHeaderTitle.innerHTML = "UPDATE BRANCH / SCHOOL INFO";
    formHeader.innerHTML = "Branch / School Info Update";
    submitBtn.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i> Update`;

    document.querySelectorAll("#addBranchForm .form-control, #addBranchForm .form-select")
      .forEach((input) => {
        input.style.backgroundColor = "rgb(241 240 236)";
      });

    form.querySelector("[name='branch_name']").value = data.branch_name || "";
    form.querySelector("[name='school_code']").value = data.school_code || "";
    form.querySelector("[name='branch_manager']").value = data.branch_manager || "";
    setSelectValue(form.querySelector("[name='branch_level']"), data.branch_level);
    setSelectValue(
      form.querySelector("[name='branch_head']"),
      data.branch_head_id || data.branch_head
    );
    setSelectValue(form.querySelector("[name='school_gender']"), data.school_gender);
    setSelectValue(form.querySelector("[name='school_type']"), data.school_type);
    form.querySelector("[name='email']").value = data.email || "";
    const mottoField = form.querySelector("[name='motto']");
    if (mottoField) mottoField.value = data.motto || "";

    addModal.show();
    form.action = update_branch_url;
  });

  if (typeof Chart === "undefined") return;
  if (typeof studentGender === "undefined") return;

  const genderColors = ["#0d6efd", "#dc3545"];
  const classColors = [
    "#0d6efd",
    "#198754",
    "#ffc107",
    "#dc3545",
    "#6f42c1",
    "#20c997",
  ];

  const studentEl = document.getElementById("studentGenderChart");
  const teacherEl = document.getElementById("teacherGenderChart");
  const classEl = document.getElementById("studentsPerClassChart");

  if (studentEl) {
    new Chart(studentEl, {
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
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  if (teacherEl && typeof teacherGender !== "undefined") {
    new Chart(teacherEl, {
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
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  if (classEl && typeof studentsPerClass !== "undefined") {
    new Chart(classEl, {
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
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 5 } },
        },
      },
    });
  }
});
