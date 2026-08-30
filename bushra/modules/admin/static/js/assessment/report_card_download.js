function filenameFromPdfResponse(response, fallback = "report.pdf") {
  const contentDisposition = response.headers.get("Content-Disposition");
  if (!contentDisposition) return fallback;
  const match = contentDisposition.match(
    /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i,
  );
  if (!match || !match[1]) return fallback;
  try {
    return decodeURIComponent(match[1]);
  } catch (error) {
    return match[1];
  }
}

function triggerPdfDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function pollReportCardJob(jobId, onProgress) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const maxWaitMs = 20 * 60 * 1000;

    const tick = () => {
      if (Date.now() - started > maxWaitMs) {
        reject(new Error("PDF generation is taking too long. Please try again."));
        return;
      }
      fetch(`/admin/reportcards-pdf-status/${encodeURIComponent(jobId)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(async (response) => {
          const body = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(body.error || "Failed to generate PDF");
          }
          const total = Number(body.total) || 0;
          const done = Number(body.done) || 0;
          if (total > 0) {
            onProgress?.(
              Math.min(90, Math.round((done / total) * 90)),
              body.message || `Generating PDF (${done} of ${total})…`,
            );
          } else {
            onProgress?.(12, body.message || "Preparing report data…");
          }
          if (body.status === "ready") {
            onProgress?.(92, "Downloading report card…");
            return fetch(
              `/admin/reportcards-pdf-download/${encodeURIComponent(jobId)}`,
              { headers: { "X-Requested-With": "XMLHttpRequest" } },
            ).then(async (download) => {
              if (!download.ok) {
                throw new Error("Failed to download the PDF.");
              }
              const blob = await download.blob();
              onProgress?.(100, "Download complete");
              return {
                blob,
                filename:
                  filenameFromPdfResponse(download) ||
                  body.filename ||
                  "report.pdf",
              };
            });
          }
          if (body.status === "error") {
            throw new Error(body.error || "Failed to generate PDF");
          }
          window.setTimeout(tick, body.status === "running" ? 400 : 1000);
          return null;
        })
        .then((result) => {
          if (result) resolve(result);
        })
        .catch(reject);
    };

    tick();
  });
}

function downloadReportCardPdf(payload, options = {}) {
  const onProgress = options.onProgress || (() => {});
  return fetch("/admin/generate-reportcards-pdf", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify(payload),
  })
    .then(async (response) => {
      const contentType = response.headers.get("Content-Type") || "";
      if (contentType.includes("application/pdf")) {
        if (!response.ok) throw new Error("Failed to generate PDF");
        onProgress(85, "Downloading report card…");
        const blob = await response.blob();
        onProgress(100, "Download complete");
        return {
          blob,
          filename: filenameFromPdfResponse(response),
        };
      }

      let body = {};
      try {
        body = await response.json();
      } catch (error) {
        throw new Error(
          response.status === 504 || response.status === 502
            ? "The server timed out. Please try again."
            : "Failed to generate PDF",
        );
      }
      if (!response.ok || !body.job_id) {
        throw new Error(body.error || "Failed to generate PDF");
      }
      return pollReportCardJob(body.job_id, onProgress);
    })
    .then(({ blob, filename }) => {
      triggerPdfDownload(blob, filename);
      return { blob, filename };
    });
}
