(function (window, document) {
  function lockedId() {
    const value = window.BUSHRA_LOCKED_BRANCH_ID;
    if (value === null || value === undefined || value === "") return null;
    return String(value);
  }

  function hide(selectEl) {
    if (!selectEl) return;
    const wrap =
      selectEl.closest("[data-school-picker]") ||
      selectEl.closest(".js-school-picker") ||
      selectEl.closest(".col-md-6, .col-lg-3, .col-lg-4, .col-md-4, .col-sm-6");
    if (wrap) wrap.classList.add("d-none");
  }

  function fill(selectEl, branches, placeholder) {
    if (!selectEl) return null;

    const items = Array.isArray(branches) ? branches : [];
    const locked = lockedId();
    const only = items.length === 1 ? String(items[0].id) : null;
    const autoId = locked && items.some((b) => String(b.id) === locked)
      ? locked
      : only;

    selectEl.innerHTML = "";
    if (!autoId) {
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = placeholder || "Select School";
      selectEl.appendChild(blank);
    }

    items.forEach((branch) => {
      const opt = document.createElement("option");
      opt.value = branch.id;
      opt.textContent = branch.name || branch.branch_name || branch.grade_form;
      selectEl.appendChild(opt);
    });

    if (autoId) {
      selectEl.value = autoId;
      hide(selectEl);
      selectEl.dispatchEvent(new Event("change", { bubbles: true }));
    }

    return autoId;
  }

  window.BushraSchoolSelect = {
    lockedId,
    hide,
    fill,
  };
})(window, document);
