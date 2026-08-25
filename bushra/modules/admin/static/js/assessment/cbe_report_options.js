function syncCbeReportOptionChoices(root) {
  root.querySelectorAll(".cbe-report-options-choice").forEach((label) => {
    const input = label.querySelector("input");
    label.classList.toggle("is-selected", Boolean(input?.checked));
  });
}

function readCbeReportCardOptions(root) {
  const ranking = root.querySelector('input[name="cbeIncludeRanking"]:checked');
  const includeOpening = root.querySelector("#cbeIncludeOpeningDate");
  const openingDate = root.querySelector("#cbeOpeningDate");
  const includeOpeningChecked = Boolean(includeOpening?.checked);
  const dateValue = (openingDate?.value || "").trim();

  if (includeOpeningChecked && !dateValue) {
    return { error: "Select the school opening date." };
  }

  return {
    include_ranking: ranking ? ranking.value === "yes" : true,
    include_opening_date: includeOpeningChecked,
    opening_date: includeOpeningChecked ? dateValue : "",
  };
}

function resetCbeReportCardOptions(root) {
  const yes = root.querySelector("#cbeIncludeRankingYes");
  const no = root.querySelector("#cbeIncludeRankingNo");
  const includeOpening = root.querySelector("#cbeIncludeOpeningDate");
  const openingDate = root.querySelector("#cbeOpeningDate");
  const errorEl = root.querySelector("#cbeReportOptionsError");

  if (yes) yes.checked = true;
  if (no) no.checked = false;
  if (includeOpening) includeOpening.checked = false;
  if (openingDate) {
    openingDate.value = "";
    openingDate.disabled = true;
  }
  if (errorEl) {
    errorEl.textContent = "";
    errorEl.classList.add("d-none");
  }
  syncCbeReportOptionChoices(root);
}

function bindCbeReportCardOptionsModal(onConfirm) {
  const modalEl = document.getElementById("cbeReportOptionsModal");
  if (!modalEl || typeof bootstrap === "undefined") return null;

  const includeOpening = modalEl.querySelector("#cbeIncludeOpeningDate");
  const openingDate = modalEl.querySelector("#cbeOpeningDate");
  const confirmBtn = modalEl.querySelector("#cbeReportOptionsConfirm");
  const errorEl = modalEl.querySelector("#cbeReportOptionsError");

  includeOpening?.addEventListener("change", () => {
    if (!openingDate) return;
    openingDate.disabled = !includeOpening.checked;
    if (includeOpening.checked) {
      openingDate.focus();
    } else {
      openingDate.value = "";
    }
    syncCbeReportOptionChoices(modalEl);
  });

  modalEl.querySelectorAll('input[name="cbeIncludeRanking"]').forEach((input) => {
    input.addEventListener("change", () => syncCbeReportOptionChoices(modalEl));
  });

  confirmBtn?.addEventListener("click", () => {
    const options = readCbeReportCardOptions(modalEl);
    if (options.error) {
      if (errorEl) {
        errorEl.textContent = options.error;
        errorEl.classList.remove("d-none");
      }
      return;
    }
    if (errorEl) {
      errorEl.textContent = "";
      errorEl.classList.add("d-none");
    }
    bootstrap.Modal.getInstance(modalEl)?.hide();
    onConfirm(options);
  });

  modalEl.addEventListener("hidden.bs.modal", () => {
    resetCbeReportCardOptions(modalEl);
  });

  return {
    show() {
      resetCbeReportCardOptions(modalEl);
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    },
  };
}
