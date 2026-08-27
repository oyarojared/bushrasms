(function (window) {
  function renderSubjectMeansLine(canvas, charts) {
    if (!canvas || typeof Chart === "undefined" || !charts) return null;
    const labels = charts.subject_labels || [];
    const values = charts.subject_values || [];
    if (!labels.length) return null;

    const narrow = window.innerWidth < 768;
    const count = labels.length;
    const rotate = count > 5 || narrow;
    const tickSize = count > 10 ? 8 : narrow ? 9 : 11;
    const tick = {
      color: "#6b7280",
      font: { size: tickSize, family: "Inter, sans-serif" },
    };
    const grid = { color: "rgba(15, 23, 42, 0.06)" };

    if (canvas.parentElement) {
      const base = narrow ? 180 : 200;
      canvas.parentElement.style.height = rotate ? base + 36 + "px" : base + "px";
    }

    return new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Mean",
            data: values,
            borderColor: "#ff7979",
            backgroundColor: "rgba(255, 121, 121, 0.14)",
            fill: true,
            tension: 0.35,
            borderWidth: 2.25,
            pointRadius: narrow ? 2.5 : 3.5,
            pointHoverRadius: 5,
            pointBackgroundColor: "#fff",
            pointBorderColor: "#ff7979",
            pointBorderWidth: 2,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        events: ["mousemove", "mouseout", "click", "touchstart"],
        layout: {
          padding: { top: 8, right: 10, left: 2, bottom: rotate ? 2 : 0 },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: function (items) {
                if (!items.length) return "";
                const index = items[0].dataIndex;
                return (charts.subject_names && charts.subject_names[index]) || items[0].label;
              },
              label: function (ctx) {
                if (ctx.parsed.y == null) return " No mean yet";
                return " Mean " + ctx.parsed.y;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            suggestedMax: 100,
            grid: grid,
            ticks: tick,
            border: { display: false },
          },
          x: {
            offset: true,
            grid: { display: false },
            border: { display: false },
            ticks: {
              color: tick.color,
              font: tick.font,
              autoSkip: false,
              includeBounds: true,
              maxRotation: rotate ? 50 : 0,
              minRotation: rotate ? 40 : 0,
            },
          },
        },
      },
    });
  }

  window.renderSubjectMeansLine = renderSubjectMeansLine;
})(window);
