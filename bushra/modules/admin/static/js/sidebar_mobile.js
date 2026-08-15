(function () {
  const MOBILE_QUERY = window.matchMedia("(max-width: 768px)");

  function getScrollContainer() {
    return document.querySelector(".sidebar-nav");
  }

  function scrollActiveNavIntoView(behavior = "smooth") {
    if (!MOBILE_QUERY.matches) return;

    const container = getScrollContainer();
    const activeLink = container?.querySelector(".nav-link.active");
    if (!container || !activeLink) return;

    const activeItem = activeLink.closest(".nav-item") || activeLink;
    const containerRect = container.getBoundingClientRect();
    const itemRect = activeItem.getBoundingClientRect();
    const targetLeft =
      container.scrollLeft +
      (itemRect.left - containerRect.left) -
      containerRect.width / 2 +
      itemRect.width / 2;

    container.scrollTo({
      left: Math.max(0, targetLeft),
      behavior,
    });
  }

  function bindNavTapScroll() {
    const container = getScrollContainer();
    if (!container) return;

    container.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => {
        if (!MOBILE_QUERY.matches) return;

        const item = link.closest(".nav-item");
        if (!item) return;

        const containerRect = container.getBoundingClientRect();
        const itemRect = item.getBoundingClientRect();
        const targetLeft =
          container.scrollLeft +
          (itemRect.left - containerRect.left) -
          containerRect.width / 2 +
          itemRect.width / 2;

        container.scrollTo({
          left: Math.max(0, targetLeft),
          behavior: "smooth",
        });
      });
    });
  }

  function initSidebarMobile() {
    scrollActiveNavIntoView("auto");
    bindNavTapScroll();

    requestAnimationFrame(() => scrollActiveNavIntoView("smooth"));
    window.setTimeout(() => scrollActiveNavIntoView("smooth"), 180);
  }

  document.addEventListener("DOMContentLoaded", initSidebarMobile);

  window.addEventListener("resize", () => {
    scrollActiveNavIntoView(MOBILE_QUERY.matches ? "smooth" : "auto");
  });

  window.addEventListener("orientationchange", () => {
    window.setTimeout(() => scrollActiveNavIntoView("smooth"), 120);
  });
})();
