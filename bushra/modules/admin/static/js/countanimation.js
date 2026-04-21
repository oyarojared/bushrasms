document.addEventListener("DOMContentLoaded", () => {
  const duration = 1500; // 1.5 seconds

  document.querySelectorAll(".count").forEach((counter) => {
    const target = Number(counter.dataset.count);
    const startTime = performance.now();

    function animate(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const value = Math.floor(progress * target);
      counter.textContent = value.toLocaleString();

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    }

    requestAnimationFrame(animate);
  });
});
