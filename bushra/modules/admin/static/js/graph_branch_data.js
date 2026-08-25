// branchData is available from the template
const branchLabels = branchData.map(b => b.name);
const branchPopulation = branchData.map(b => b.population);

const shuleka = {
    brand: '#ff7979',
    brandHover: '#f56868',
    chrome: '#3f4854',
    ink: '#6c757d',
    muted: '#98a1ad',
    grid: '#f0f1f3',
    students: '#0d6efd',
    teachers: '#198754',
    staff: '#f0ad00',
    font: "Inter, 'Open Sans', system-ui, sans-serif",
};

function barChartOptions(extra = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        layout: { padding: { top: 6, right: 4 } },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: shuleka.chrome,
                titleColor: '#eef1f4',
                bodyColor: '#b8c0ca',
                padding: 10,
                cornerRadius: 8,
                displayColors: false,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                border: { display: false },
                ticks: {
                    color: shuleka.ink,
                    font: { family: shuleka.font, size: 11, weight: '600' },
                    maxRotation: 45,
                    autoSkip: true,
                },
            },
            y: {
                beginAtZero: true,
                grace: '10%',
                grid: { color: shuleka.grid, drawBorder: false },
                border: { display: false },
                ticks: {
                    color: shuleka.muted,
                    precision: 0,
                    font: { family: shuleka.font, size: 11 },
                },
            },
        },
        ...extra,
    };
}

// Main branch population pie chart
new Chart(document.getElementById('branchPopulationChart').getContext('2d'), {
    type: 'pie',
    data: {
        labels: branchLabels,
        datasets: [{
            data: branchPopulation,
            backgroundColor: ['#c02510ff','#1cc88a','#36b9cc','#f6c23e','#e74a3b']
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position:'bottom' },
            title: { display:true, text:'Branches Population Distribution' }
        }
    }
});

// Individual branch charts
branchData.forEach(branch => {
    const ctxBranch = document.getElementById(`branchChart${branch.id}`).getContext('2d');
    new Chart(ctxBranch, {
        type: 'bar',
        data: {
            labels: ['Students','Teachers','Staff'],
            datasets: [{
                label: `${branch.name} Overview`,
                data: [branch.population, branch.teacher_count, branch.staff_count],
                backgroundColor: [shuleka.students, shuleka.teachers, shuleka.staff],
                hoverBackgroundColor: ['#0b5ed7', '#157347', '#d39e00'],
                borderRadius: 6,
                borderSkipped: 'bottom',
                maxBarThickness: 48,
            }]
        },
        options: barChartOptions(),
    });

    const classCanvas = document.getElementById(`classChart${branch.id}`);
    const classContainer = classCanvas?.parentElement;
    const classLabels = branch.classes.map(c => c.grade_form + (c.class_year ? ' ' + c.class_year : ''));
    const classPopulation = branch.classes.map(c => c.population);

    if (!classLabels.length) {
        if (classContainer) {
            classContainer.innerHTML = '<div class="class-chart-empty">No class enrolment yet.</div>';
        }
        return;
    }

    new Chart(classCanvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: classLabels,
            datasets: [{
                label: 'Students per Class',
                data: classPopulation,
                backgroundColor: shuleka.brand,
                hoverBackgroundColor: shuleka.brandHover,
                borderRadius: 6,
                borderSkipped: 'bottom',
                maxBarThickness: 42,
                categoryPercentage: 0.68,
                barPercentage: 0.78,
            }]
        },
        options: barChartOptions({
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: shuleka.chrome,
                    titleColor: '#eef1f4',
                    bodyColor: '#b8c0ca',
                    padding: 10,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: (ctx) => {
                            const n = ctx.parsed.y || 0;
                            return `${n} student${n === 1 ? '' : 's'}`;
                        },
                    },
                },
            },
        }),
    });
});

document.querySelectorAll('.branch-more-stats .accordion-collapse').forEach((panel) => {
    panel.addEventListener('shown.bs.collapse', () => {
        const canvas = panel.querySelector('canvas');
        if (!canvas) return;
        Chart.getChart(canvas)?.resize();
    });
});
