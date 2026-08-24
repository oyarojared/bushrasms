document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("deleteSubjectModal");
  const deleteForm = document.getElementById("deleteSubjectForm");
  const accordionBtn = document.getElementById("accordionBtn");
  const accordionCollapse = document.getElementById("flush-collapseOne");
  const formPanel = accordionCollapse;
  const formTitle = document.getElementById("subFormTitle");
  const addSubjectForm = document.getElementById("addSubjectForm");
  const nameInput = addSubjectForm?.querySelector("[name='name']");
  const codeInput = addSubjectForm?.querySelector("[name='code']");
  const categoryInput = addSubjectForm?.querySelector("[name='category']");
  const examinableInput = addSubjectForm?.querySelector("[name='is_examinable']");
  const compulsoryInput = addSubjectForm?.querySelector("[name='is_compulsory']");
  const subjectIdInput = document.getElementById("subject_id");
  const submitBtn = document.getElementById("submit-btn");
  const formBtns = document.getElementById("formbtns");
  const gradeCheckboxes = document.querySelectorAll(".grade-checkbox");
  const checkAll = document.getElementById("checkAllGrades");
  const searchInput = document.getElementById("sub-search");
  const navButtons = document.querySelectorAll(".sub-nav-btn");
  const rows = document.querySelectorAll(".sub-row");
  const emptyFilter = document.getElementById("sub-filter-empty");
  const countEl = document.getElementById("sub-count");
  const tableWrap = document.querySelector(".sub-table-wrap");
  const gradeSelect = document.getElementById("grades");
  const tableContainer = document.getElementById("subjectsTableContainer");
  const gradePickerBtns = document.querySelectorAll(".sub-grade-picker-btn");

  let activeCategory = "all";

  function collapseInstance() {
    if (!accordionCollapse || typeof bootstrap === "undefined") return null;
    return bootstrap.Collapse.getOrCreateInstance(accordionCollapse, {
      toggle: false,
    });
  }

  function openForm() {
    collapseInstance()?.show();
  }

  function scrollToForm() {
    if (!accordionCollapse) return;
    accordionCollapse.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function setAddModeCopy() {
    if (formTitle) {
      formTitle.innerHTML =
        '<i class="bi bi-plus-circle"></i> Add learning area / subject';
    }
    if (accordionBtn) {
      accordionBtn.innerHTML = "Add Learning Area/Subject";
    }
    if (submitBtn) {
      submitBtn.innerHTML =
        '<i class="bi bi-plus-circle"></i> Save subject';
    }
    formPanel?.classList.remove("is-editing");
  }

  function setEditModeCopy() {
    if (formTitle) {
      formTitle.innerHTML =
        '<i class="bi bi-pencil-square"></i> Edit learning area / subject';
    }
    if (accordionBtn) {
      accordionBtn.innerHTML =
        '<span><i class="bi bi-pencil-square h5 me-2"></i></span>Edit Learning Area/Subject';
    }
    if (submitBtn) {
      submitBtn.innerHTML =
        '<i class="bi bi-pencil-square"></i> Update changes';
    }
    formPanel?.classList.add("is-editing");
  }

  function syncCheckAll() {
    if (!checkAll || !gradeCheckboxes.length) return;
    checkAll.checked = [...gradeCheckboxes].every((cb) => cb.checked);
  }

  function applyFilter() {
    if (!rows.length) return;
    const query = (searchInput?.value || "").trim().toLowerCase();
    let visible = 0;

    rows.forEach((row) => {
      const category = row.dataset.category || "";
      const haystack = row.dataset.search || "";
      const categoryOk =
        activeCategory === "all" || category === activeCategory;
      const queryOk = !query || haystack.includes(query);
      const show = categoryOk && queryOk;
      row.classList.toggle("d-none", !show);
      if (show) visible += 1;
    });

    if (countEl) {
      countEl.textContent = `${visible} subject${visible === 1 ? "" : "s"}`;
    }
    tableWrap?.classList.toggle("d-none", visible === 0);
    emptyFilter?.classList.toggle("d-none", visible > 0);
  }

  if (deleteModal && deleteForm) {
    deleteModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      if (!button) return;
      const subjectId = button.getAttribute("data-subject-id");
      deleteForm.action = "/admin/delete_subject/" + subjectId;
    });
  }

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const target = document.getElementById("target-subject");
      if (target) target.textContent = this.dataset.name || "";
    });
  });

  if (checkAll && gradeCheckboxes.length) {
    checkAll.addEventListener("change", function () {
      gradeCheckboxes.forEach((cb) => {
        cb.checked = this.checked;
      });
    });

    gradeCheckboxes.forEach((cb) => {
      cb.addEventListener("change", syncCheckAll);
    });
  }

  document.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const wasClosed = !accordionCollapse?.classList.contains("show");
      openForm();

      if (subjectIdInput) subjectIdInput.value = this.dataset.id || "";
      if (nameInput) nameInput.value = this.dataset.name || "";
      if (codeInput) codeInput.value = this.dataset.code || "";
      if (categoryInput) categoryInput.value = this.dataset.category || "";
      if (examinableInput) {
        examinableInput.checked = this.dataset.examinable === "1";
      }
      if (compulsoryInput) {
        compulsoryInput.checked = this.dataset.compulsory === "1";
      }

      gradeCheckboxes.forEach((cb) => {
        cb.checked = false;
      });

      let grades = [];
      try {
        grades = JSON.parse(this.dataset.grades || "[]");
      } catch (err) {
        grades = [];
      }

      gradeCheckboxes.forEach((cb) => {
        if (grades.includes(cb.value)) cb.checked = true;
      });
      syncCheckAll();
      setEditModeCopy();

      if (formBtns) {
        document.getElementById("resetBtn")?.remove();
        const resetBtn = document.createElement("button");
        resetBtn.id = "resetBtn";
        resetBtn.type = "button";
        resetBtn.className = "sa-btn sa-btn-outline";
        resetBtn.innerHTML =
          '<i class="bi bi-plus-circle"></i> Add new instead';
        resetBtn.addEventListener("click", () => {
          window.location.reload();
        });
        formBtns.prepend(resetBtn);
      }

      if (wasClosed) {
        setTimeout(scrollToForm, 280);
      } else {
        scrollToForm();
      }
    });
  });

  if (window.SUBJECTS_FORM_HAS_ERRORS) {
    openForm();
  }

  addSubjectForm?.addEventListener("submit", (e) => {
    const checked = document.querySelectorAll(
      "input[name='subject_grades']:checked"
    );
    if (checked.length === 0) {
      e.preventDefault();
      document.getElementById("grade-error")?.classList.remove("d-none");
    }
  });

  searchInput?.addEventListener("input", applyFilter);

  navButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      activeCategory = this.dataset.category || "all";
      navButtons.forEach((other) => {
        const isActive = other === this;
        other.classList.toggle("is-active", isActive);
        other.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
      applyFilter();
    });
  });

  function loadSubjectsForGrade(selectedGrade) {
    if (!tableContainer) return;

    if (!selectedGrade) {
      tableContainer.innerHTML = `
        <div class="sub-grade-placeholder">
          Select a grade to view assigned subjects.
        </div>
      `;
      return;
    }

    tableContainer.innerHTML = `
      <div class="sub-grade-placeholder">Loading subjects…</div>
    `;

    fetch(
      `/admin/subjects/by-grade?grade_form=${encodeURIComponent(selectedGrade)}`
    )
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load subjects");
        return res.text();
      })
      .then((html) => {
        tableContainer.innerHTML = html;
      })
      .catch((err) => {
        console.error(err);
        tableContainer.innerHTML = `
          <div class="sub-grade-placeholder text-danger">
            Failed to load subjects.
          </div>
        `;
      });
  }

  gradeSelect?.addEventListener("change", function () {
    const selectedGrade = this.value;
    gradePickerBtns.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.grade === selectedGrade);
    });
    loadSubjectsForGrade(selectedGrade);
  });

  gradePickerBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      if (!gradeSelect) return;
      gradeSelect.value = this.dataset.grade || "";
      gradeSelect.dispatchEvent(new Event("change"));
    });
  });
});
