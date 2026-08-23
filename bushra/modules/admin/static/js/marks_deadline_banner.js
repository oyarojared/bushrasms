(function () {
  const banner = document.querySelector("[data-marks-deadline-due]");
  if (!banner) return;

  function syncBannerHeight() {
    document.documentElement.style.setProperty(
      "--marks-deadline-banner-height",
      `${banner.offsetHeight}px`
    );
  }

  syncBannerHeight();
  window.addEventListener("resize", syncBannerHeight);

  const due = new Date(banner.getAttribute("data-marks-deadline-due"));
  const remainingEl = banner.querySelector("[data-deadline-remaining]");
  const openCopy = banner.querySelector("[data-deadline-open-copy]");
  const closedCopy = banner.querySelector("[data-deadline-closed-copy]");
  if (Number.isNaN(due.getTime())) return;

  function formatRemaining(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    }
    return `${hours}h ${minutes}m ${String(seconds).padStart(2, "0")}s`;
  }

  function markClosed() {
    banner.classList.add("is-closed");
    if (openCopy) openCopy.classList.add("d-none");
    if (closedCopy) closedCopy.classList.remove("d-none");
    if (remainingEl) remainingEl.textContent = "Closed";
    syncBannerHeight();
  }

  function tick() {
    const remaining = due.getTime() - Date.now();
    if (remaining <= 0) {
      markClosed();
      return false;
    }
    if (remainingEl) remainingEl.textContent = formatRemaining(remaining);
    return true;
  }

  if (banner.classList.contains("is-closed")) {
    markClosed();
    return;
  }

  if (!tick()) return;
  const timer = window.setInterval(function () {
    if (!tick()) {
      window.clearInterval(timer);
    }
  }, 1000);
})();
