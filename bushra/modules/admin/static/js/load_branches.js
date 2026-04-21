$(document).ready(function(){
    // Load branches (client-only)
    $.getJSON(branchesUrl, function(data){
        let branchSelect = $("#branch");
        branchSelect.empty();                     // <-- clear any server-provided options
        branchSelect.append('<option value="">--- Select Branch ---</option>');
        data.forEach(b => branchSelect.append(`<option value="${b.id}">${b.name}</option>`));
    });

    // Load grades/forms when branch changes
    $("#branch").change(function(){
        let branchId = $(this).val();
        let gradeSelect = $("#grade_form");
        gradeSelect.empty();
        $("#stream-container").hide();

        if(branchId){
            $.getJSON(`${gradesUrlBase}${branchId}`, function(data){
                gradeSelect.append('<option value="">--- Select Grade/Form ---</option>');
                data.forEach(c => {
                    // store streams JSON on option
                    gradeSelect.append(`<option value="${c.id}" data-streams='${JSON.stringify(c.streams)}'>${c.grade_form}</option>`);
                });
            });
        }
    });

    // Load streams if available
    $("#grade_form").change(function(){
        let streams = $("#grade_form option:selected").data("streams");
        let streamSelect = $("#stream");
        streamSelect.empty();

        if(streams && streams.length > 0){
            $("#stream-container").show();
            streamSelect.append('<option value="">--- Select Stream ---</option>');
            streams.forEach(s => streamSelect.append(`<option value="${s}">${s}</option>`));
        } else {
            $("#stream-container").hide();
        }
    });
});
