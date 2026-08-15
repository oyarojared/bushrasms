// Display searched student(s) in a bootstrap modal.
(function () {
  const form = document.getElementById("studentSearchForm");
  const modalEl = document.getElementById("searchResultsModal");
  const modalBody = document.getElementById("modalBodyContent");
  const submitBtn = form?.querySelector('button[type="submit"]');

  if (!form || !modalEl || !modalBody) {
    return;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function showModal() {
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function setModalContent(html) {
    modalBody.innerHTML = html;
    showModal();
  }

  function setLoading(isLoading) {
    if (!submitBtn) {
      return;
    }

    submitBtn.disabled = isLoading;
    submitBtn.setAttribute("aria-busy", String(isLoading));
  }

  function renderLoadingState() {
    modalBody.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-orange" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 mb-0 text-muted">Searching for students...</p>
      </div>
    `;
    showModal();
  }

  function renderNoResults() {
    return `
      <div class="alert alert-warning text-center">
        <i class="bi bi-exclamation-triangle me-2" style="font-size: 1.5rem;"></i>
        <strong>No student found!</strong>
      </div>
    `;
  }

  function renderError() {
    return `
      <div class="alert alert-danger text-center">
        <i class="bi bi-exclamation-triangle me-2" style="font-size: 1.5rem;"></i>
        <strong>Error fetching data. Please try again later!</strong>
      </div>
    `;
  }

  function renderStudentsTable(students) {
    let rows = "";

    students.forEach((stu) => {
      const studentId = encodeURIComponent(stu.id ?? "");

      rows += `
        <tr>
          <td>${escapeHtml(String(stu.fullname ?? "").toUpperCase())}</td>
          <td>${escapeHtml(stu.admission_number)}</td>
          <td>${escapeHtml(stu.branch)}</td>
          <td>${escapeHtml(stu.grade_form)}</td>
          <td>${escapeHtml(stu.stream || "---")}</td>
          <td>
            <a href="/admin/student_profile/${studentId}" class="text-orange fw-bold">
              <i class="bi bi-eye me-2"></i>View
            </a>
          </td>
        </tr>
      `;
    });

    return `
      <table class="table table-bordered table-striped small">
        <caption style="caption-side: top; margin-left: 5px">
          ${students.length} student(s) found
        </caption>
        <thead>
          <tr>
            <th>Full Name</th>
            <th>Adm No</th>
            <th>School</th>
            <th>Grade/Form</th>
            <th>Stream</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(this);

    setLoading(true);
    renderLoadingState();

    fetch(this.action, {
      method: "POST",
      body: formData,
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        return res.json();
      })
      .then((data) => {
        const students = Array.isArray(data?.students) ? data.students : [];

        if (data?.status === "success" && students.length > 0) {
          setModalContent(renderStudentsTable(students));
        } else {
          setModalContent(renderNoResults());
        }
      })
      .catch((err) => {
        console.error(err);
        setModalContent(renderError());
      })
      .finally(() => {
        setLoading(false);
      });
  });
})();
