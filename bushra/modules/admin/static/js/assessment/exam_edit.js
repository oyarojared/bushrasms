(function () {
  const TERM_LABELS = { I: "Term I", II: "Term II", III: "Term III" };

  function initExamEdit() {
    const editModalEl = document.getElementById("editExamModal");
    const warningModalEl = document.getElementById("editExamWarningModal");
    const successModalEl = document.getElementById("editExamSuccessModal");
    const form = document.getElementById("editExamForm");
    if (!editModalEl || !warningModalEl || !successModalEl || !form) return;

    const errorEl = document.getElementById("editExamFormError");
    const infoEl = document.getElementById("editExamFormInfo");
    const warningChangesEl = document.getElementById("editExamWarningChanges");
    const warningTitleEl = document.getElementById("editExamWarningTitle");
    const warningCopyEl = document.getElementById("editExamWarningCopy");
    const warningBackBtn = document.getElementById("editExamWarningBackBtn");
    const warningConfirmBtn = document.getElementById("editExamWarningConfirmBtn");
    const successMessageEl = document.getElementById("editExamSuccessMessage");
    const successChangesEl = document.getElementById("editExamSuccessChanges");
    const prefix = form.dataset.prefix || "edit";

    let original = null;
    let pendingChanges = [];
    let applying = false;
    let reloadOnSuccessClose = false;

    function field(name) {
      return form.elements[`${prefix}-${name}`] || form.elements[name];
    }

    function modalInstance(el) {
      return bootstrap.Modal.getOrCreateInstance(el);
    }

    function swapModals(fromEl, toEl) {
      const onHidden = function () {
        fromEl.removeEventListener("hidden.bs.modal", onHidden);
        modalInstance(toEl).show();
      };
      fromEl.addEventListener("hidden.bs.modal", onHidden);
      modalInstance(fromEl).hide();
    }

    function hideAlert(el) {
      if (!el) return;
      el.classList.add("d-none");
      el.textContent = "";
    }

    function showAlert(el, message) {
      if (!el) return;
      el.textContent = message || "";
      el.classList.toggle("d-none", !message);
    }

    function flattenErrors(fieldErrors) {
      return Object.values(fieldErrors || {})
        .flat()
        .filter(Boolean)
        .join(" ");
    }

    function branchSelect() {
      return field("branch_id");
    }

    function currentValues() {
      const branch = branchSelect();
      const branchOption = branch?.selectedOptions?.[0];
      return {
        name: (field("name")?.value || "").trim(),
        year: field("year")?.value || "",
        term: field("term")?.value || "",
        branch_id: branch?.value || "",
        branch_name: branchOption ? branchOption.textContent.trim() : "",
      };
    }

    function termLabel(term) {
      return TERM_LABELS[term] || term || "—";
    }

    function diffFromOriginal() {
      if (!original) return [];
      const next = currentValues();
      const diffs = [];

      if (next.name !== original.name) {
        diffs.push({
          field: "name",
          label: "Name",
          from: original.name,
          to: next.name,
        });
      }
      if (String(next.year) !== String(original.year)) {
        diffs.push({
          field: "year",
          label: "Year",
          from: String(original.year),
          to: String(next.year),
        });
      }
      if (next.term !== original.term) {
        diffs.push({
          field: "term",
          label: "Term",
          from: termLabel(original.term),
          to: termLabel(next.term),
        });
      }
      if (
        original.branch_id != null &&
        String(next.branch_id) !== String(original.branch_id)
      ) {
        diffs.push({
          field: "branch",
          label: "School",
          from: original.branch_name || "—",
          to: next.branch_name || "—",
        });
      }
      return diffs;
    }

    function renderChanges(listEl, changes) {
      if (!listEl) return;
      listEl.innerHTML = "";
      (changes || []).forEach((change) => {
        const item = document.createElement("li");
        item.innerHTML =
          `<span class="edit-exam-change-label">${escapeHtml(change.label)}</span>` +
          `<span>` +
          `<span class="edit-exam-change-from">${escapeHtml(change.from)}</span>` +
          ` → ` +
          `<span class="edit-exam-change-to">${escapeHtml(change.to)}</span>` +
          `</span>`;
        listEl.appendChild(item);
      });
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function fillForm(exam) {
      const nameInput = field("name");
      const yearInput = field("year");
      const termInput = field("term");
      const branchInput = branchSelect();

      if (nameInput) nameInput.value = exam.name || "";
      if (yearInput) yearInput.value = String(exam.year ?? "");
      if (termInput) termInput.value = exam.term || "";
      if (branchInput && exam.branch_id != null) {
        branchInput.value = String(exam.branch_id);
        branchInput.disabled = !exam.can_change_branch;
      }

      original = {
        name: exam.name || "",
        year: String(exam.year ?? ""),
        term: exam.term || "",
        branch_id: exam.branch_id,
        branch_name: exam.branch_name || "",
        has_papers: Boolean(exam.has_papers),
        has_marks: Boolean(exam.has_marks),
        is_locked: Boolean(exam.is_locked),
      };
    }

    async function readJson(response) {
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error(
          "Your session may have expired. Refresh the page and try again."
        );
      }
      return response.json();
    }

    document.querySelectorAll(".edit-exam-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const url = button.getAttribute("data-edit-url") || "";
        if (!url) return;

        hideAlert(errorEl);
        hideAlert(infoEl);
        form.action = url;
        original = null;

        try {
          const response = await fetch(url, {
            headers: { Accept: "application/json" },
          });
          const data = await readJson(response);
          if (!response.ok || !data.success || !data.exam) {
            throw new Error(data.error || "Could not load this exam.");
          }
          fillForm(data.exam);
          modalInstance(editModalEl).show();
        } catch (err) {
          window.alert(err.message || "Could not open the exam editor.");
        }
      });
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      hideAlert(errorEl);
      hideAlert(infoEl);

      const nameInput = field("name");
      if (nameInput && !nameInput.value.trim()) {
        showAlert(errorEl, "Exam name is required.");
        return;
      }

      pendingChanges = diffFromOriginal();
      if (!pendingChanges.length) {
        showAlert(infoEl, "No changes were made.");
        return;
      }

      renderChanges(warningChangesEl, pendingChanges);

      if (original?.has_marks) {
        if (warningTitleEl) warningTitleEl.textContent = "This exam already has marks";
        if (warningCopyEl) {
          warningCopyEl.textContent =
            "Marks already entered stay attached to this exam. Reports and teacher views will use the new name, year, term, or school.";
        }
      } else if (original?.is_locked) {
        if (warningTitleEl) warningTitleEl.textContent = "This exam is locked";
        if (warningCopyEl) {
          warningCopyEl.textContent =
            "You can still change these details. Marks entry stays closed until the exam is unlocked.";
        }
      } else {
        if (warningTitleEl) warningTitleEl.textContent = "Marks stay on this exam";
        if (warningCopyEl) {
          warningCopyEl.textContent =
            "Existing papers and marks remain attached. The new name, year, term, or school will appear on reports, class views, and marks entry.";
        }
      }

      swapModals(editModalEl, warningModalEl);
    });

    warningBackBtn?.addEventListener("click", () => {
      if (applying) return;
      swapModals(warningModalEl, editModalEl);
    });

    warningConfirmBtn?.addEventListener("click", async () => {
      if (applying) return;
      applying = true;
      warningConfirmBtn.disabled = true;
      warningConfirmBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Applying…';

      const branchInput = branchSelect();
      const wasDisabled = Boolean(branchInput?.disabled);
      if (branchInput) branchInput.disabled = false;

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "application/json" },
        });
        const data = await readJson(response);

        if (!response.ok || !data.success) {
          throw new Error(
            data.error || flattenErrors(data.field_errors) || "Could not update the exam."
          );
        }

        if (data.unchanged) {
          showAlert(infoEl, data.message || "No changes were made.");
          swapModals(warningModalEl, editModalEl);
          return;
        }

        reloadOnSuccessClose = true;
        if (successMessageEl) {
          successMessageEl.textContent =
            data.message || "Exam updated successfully.";
        }
        renderChanges(successChangesEl, data.changes || pendingChanges);
        swapModals(warningModalEl, successModalEl);
      } catch (err) {
        showAlert(errorEl, err.message || "Could not update the exam.");
        swapModals(warningModalEl, editModalEl);
      } finally {
        if (branchInput && wasDisabled) branchInput.disabled = true;
        applying = false;
        warningConfirmBtn.disabled = false;
        warningConfirmBtn.innerHTML =
          '<i class="bi bi-check2-circle me-1"></i>Apply changes';
      }
    });

    successModalEl.addEventListener("hidden.bs.modal", () => {
      if (reloadOnSuccessClose) {
        window.location.reload();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initExamEdit);
  } else {
    initExamEdit();
  }
})();
