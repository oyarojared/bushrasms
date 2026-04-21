// branchData is available from the template
const branchLabels = branchData.map(b => b.name);
const branchPopulation = branchData.map(b => b.population);

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
    // Branch overview chart
    const ctxBranch = document.getElementById(`branchChart${branch.id}`).getContext('2d');
    new Chart(ctxBranch, {
        type: 'bar',
        data: {
            labels: ['Students','Teachers','Staff'],
            datasets: [{
                label: `${branch.name} Overview`,
                data: [branch.population, branch.teacher_count, branch.staff_count],
                backgroundColor: ['#af1313ff','#1cc88a','#f6c23e']
            }]
        },
        options: { responsive:true, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true } } }
    });

    // Class distribution chart
    const ctxClass = document.getElementById(`classChart${branch.id}`).getContext('2d');
    const classLabels = branch.classes.map(c => c.grade_form + (c.class_year ? ' ' + c.class_year : ''));
    const classPopulation = branch.classes.map(c => c.population);

    new Chart(ctxClass, {
        type: 'bar',
        data: {
            labels: classLabels,
            datasets: [{
                label: 'Students per Class',
                data: classPopulation,
                backgroundColor: '#a3173aff'
            }]
        },
        options: { responsive:true, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true } } }
    });
});
