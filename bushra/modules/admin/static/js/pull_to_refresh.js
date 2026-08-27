(function () {
  const MOBILE_QUERY = window.matchMedia("(max-width: 767.98px)");
  const THRESHOLD = 72;
  const MAX_PULL = 120;

  function isIgnoredTarget(el) {
    return Boolean(
      el.closest(
        "input, textarea, select, [contenteditable='true'], .sidebar-nav, .modal, .offcanvas, .marks-save-bar, .ui-blocker"
      )
    );
  }

  function nestedScrollerNotAtTop(el, scroller) {
    let node = el;
    while (node && node !== scroller && node !== document.body) {
      const style = window.getComputedStyle(node);
      const overflowY = style.overflowY;
      if (
        (overflowY === "auto" || overflowY === "scroll") &&
        node.scrollTop > 0
      ) {
        return true;
      }
      node = node.parentElement;
    }
    return false;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const scroller = document.querySelector(".main-content");
    if (!scroller) return;

    const indicator = document.createElement("div");
    indicator.className = "ptr-indicator";
    indicator.setAttribute("aria-hidden", "true");
    indicator.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
    document.body.appendChild(indicator);

    let startY = 0;
    let pulling = false;
    let distance = 0;
    let refreshing = false;

    function headerOffset() {
      const bar = document.querySelector(".fixed-top-bar");
      const bottom = bar ? bar.getBoundingClientRect().bottom : 56;
      return Math.max(48, bottom + 10);
    }

    function setPull(px) {
      distance = Math.max(0, Math.min(MAX_PULL, px));
      const progress = distance / THRESHOLD;
      indicator.style.top = `${headerOffset()}px`;
      indicator.style.opacity = String(Math.min(1, progress));
      indicator.style.transform = `translateX(-50%) scale(${0.75 + Math.min(0.3, progress * 0.25)})`;
      indicator.querySelector("i").style.transform = `rotate(${Math.min(210, progress * 180)}deg)`;
      indicator.classList.toggle("is-visible", distance > 8);
      indicator.classList.toggle("is-armed", distance >= THRESHOLD);
    }

    function reset() {
      pulling = false;
      distance = 0;
      if (refreshing) return;
      indicator.classList.remove("is-visible", "is-armed", "is-refreshing");
      indicator.style.opacity = "0";
      indicator.style.transform = "translateX(-50%) scale(0.75)";
      const icon = indicator.querySelector("i");
      if (icon) icon.style.transform = "";
    }

    function canStart(event) {
      if (!MOBILE_QUERY.matches || refreshing) return false;
      if (document.body.classList.contains("ui-blocker-active")) return false;
      if (document.querySelector(".modal.show")) return false;
      if (scroller.scrollTop > 1) return false;
      if (isIgnoredTarget(event.target)) return false;
      if (nestedScrollerNotAtTop(event.target, scroller)) return false;
      return true;
    }

    document.addEventListener(
      "touchstart",
      function (event) {
        if (!canStart(event)) return;
        startY = event.touches[0].clientY;
        pulling = true;
        setPull(0);
      },
      { passive: true }
    );

    document.addEventListener(
      "touchmove",
      function (event) {
        if (!pulling || refreshing) return;
        const dy = event.touches[0].clientY - startY;
        if (dy <= 0 || scroller.scrollTop > 1) {
          if (dy <= 0) reset();
          return;
        }
        setPull(dy * 0.45);
      },
      { passive: true }
    );

    document.addEventListener("touchend", function () {
      if (!pulling || refreshing) return;
      if (distance >= THRESHOLD) {
        refreshing = true;
        const icon = indicator.querySelector("i");
        if (icon) icon.style.transform = "";
        indicator.classList.add("is-visible", "is-armed", "is-refreshing");
        indicator.style.opacity = "1";
        window.setTimeout(function () {
          window.location.reload();
        }, 160);
        return;
      }
      reset();
    });

    document.addEventListener("touchcancel", reset);
  });
})();
