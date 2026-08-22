const excelBtn = document.getElementById("excel-btn");
const excelForm = document.getElementById("excel-download-form");

if (excelBtn) {
  excelBtn.addEventListener("click", () => {
    if (!excelForm) {
      alert("Load a class list first, then export it.");
      return;
    }
    exportStudentList(excelForm, excelBtn);
  });
}

function exportStudentList(form, button) {
  if (typeof blockUI === "function") {
    blockUI("Exporting class list", "Preparing your Excel file…", {
      progress: true,
    });
  }
  if (typeof setUIProgress === "function") {
    setUIProgress(4, "Preparing spreadsheet…");
  }

  button.disabled = true;

  let simulated = 4;
  const timer = window.setInterval(() => {
    if (simulated < 38) {
      simulated = Math.min(38, simulated + Math.random() * 5 + 2);
      if (typeof setUIProgress === "function") {
        setUIProgress(simulated, "Building spreadsheet…");
      }
    }
  }, 220);

  fetch(form.action, {
    method: "POST",
    body: new FormData(form),
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then(async (response) => {
      const type = (response.headers.get("Content-Type") || "").toLowerCase();
      const isSpreadsheet =
        type.includes("spreadsheet") ||
        type.includes("excel") ||
        type.includes("octet-stream");

      if (!response.ok || !isSpreadsheet) {
        throw new Error("Export failed");
      }

      window.clearInterval(timer);
      if (typeof setUIProgress === "function") {
        setUIProgress(42, "Downloading…");
      }

      const readBlob =
        typeof readResponseBlobWithProgress === "function"
          ? readResponseBlobWithProgress
          : async (res, onProgress) => {
              const blob = await res.blob();
              onProgress?.(100);
              return blob;
            };

      const blob = await readBlob(response, (downloadPercent) => {
        const overall = 42 + Math.round(downloadPercent * 0.58);
        if (typeof setUIProgress === "function") {
          setUIProgress(overall, "Downloading…");
        }
      });

      let filename = "students.xlsx";
      const disposition = response.headers.get("Content-Disposition");
      if (disposition) {
        const match = disposition.match(
          /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i,
        );
        if (match && match[1]) {
          filename = decodeURIComponent(match[1]);
        }
      }

      if (typeof setUIProgress === "function") {
        setUIProgress(100, "Download complete");
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((err) => {
      console.error(err);
      alert("Could not export the class list. Please try again.");
    })
    .finally(() => {
      window.clearInterval(timer);
      button.disabled = false;
      window.setTimeout(() => {
        if (typeof unblockUI === "function") {
          unblockUI();
        }
      }, 450);
    });
}
