const selectedBranch = document.getElementById("selected-branch");
const gradeContainer = document.getElementById("grade-container");
const streamContainer = document.getElementById("stream-container-2");

function buildLabeledSelect(id, name, labelText, required = false, iconClass = "bi bi-list") {
  const wrapper = document.createDocumentFragment();
  const label = document.createElement("label");
  label.className = "cls-add-label";
  label.setAttribute("for", id);
  label.textContent = labelText;

  const group = document.createElement("div");
  group.className = "input-group input-group-sm";

  const iconWrap = document.createElement("span");
  iconWrap.className = "input-group-text";
  const icon = document.createElement("i");
  icon.className = iconClass;
  iconWrap.appendChild(icon);

  const select = document.createElement("select");
  select.id = id;
  select.name = name;
  select.className = "form-select form-select-sm";
  if (required) {
    select.required = true;
  }

  group.appendChild(iconWrap);
  group.appendChild(select);
  wrapper.appendChild(label);
  wrapper.appendChild(group);
  return { wrapper, select };
}

if (selectedBranch && gradeContainer && streamContainer) {
  selectedBranch.addEventListener("change", () => {
    const branchId = selectedBranch.value;
    gradeContainer.innerHTML = "";
    streamContainer.innerHTML = "";

    if (!branchId) return;

    fetch(`${gradesUrlBase}${branchId}`)
      .then((res) => res.json())
      .then((data) => {
        const { wrapper, select: gradeSelect } = buildLabeledSelect(
          "grade-form-select",
          "grade_form",
          "Grade / Form",
          true,
          "bi bi-journal-text",
        );

        gradeSelect.innerHTML = '<option value="">Select grade / form</option>';
        data.forEach((item) => {
          const option = document.createElement("option");
          option.value = item.id;
          option.textContent = item.grade_form;
          option.dataset.streams = JSON.stringify(item.streams || []);
          gradeSelect.appendChild(option);
        });

        gradeContainer.appendChild(wrapper);

        gradeSelect.addEventListener("change", () => {
          streamContainer.innerHTML = "";
          const selectedOption = gradeSelect.selectedOptions[0];
          const streams = JSON.parse(selectedOption?.dataset.streams || "[]");

          if (!streams.length) return;

          const streamField = buildLabeledSelect(
            "student-stream-select",
            "stream",
            "Stream",
            true,
            "bi bi-layers",
          );
          const streamSelect = streamField.select;
          streamSelect.innerHTML = '<option value="">Select stream</option>';

          streams.forEach((stream) => {
            const opt = document.createElement("option");
            opt.value = stream;
            opt.textContent = stream;
            streamSelect.appendChild(opt);
          });

          streamContainer.appendChild(streamField.wrapper);
        });
      })
      .catch((err) => console.error(err));

    fetch(`/admin/get_next_admission_no/${branchId}`)
      .then((res) => res.json())
      .then((data) => {
        const admInput = document.querySelector("input[name='admission_number']");
        if (admInput) {
          admInput.value = data.admission_no;
          if (typeof setAdmissionNumber === "function") {
            setAdmissionNumber(data.admission_no);
          }
        }
      })
      .catch((err) => console.error(err));
  });

  const addStudentModal = document.getElementById("addStudentModal");
  if (addStudentModal) {
    addStudentModal.addEventListener("shown.bs.modal", () => {
      if (selectedBranch.value) {
        selectedBranch.dispatchEvent(new Event("change"));
      }
    });
  }
}
