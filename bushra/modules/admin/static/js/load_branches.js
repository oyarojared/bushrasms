$(document).ready(function(){
    const nativeSelect = document.getElementById("branch");
    if (!nativeSelect) return;

    $("#branch").on("change.schoolSelect", function(){
        let branchId = $(this).val();
        let gradeSelect = $("#grade_form");
        gradeSelect.empty();
        $("#stream-container").hide();

        if(branchId){
            $.getJSON(`${gradesUrlBase}${branchId}`, function(data){
                gradeSelect.append('<option value="">--- Select Grade/Form ---</option>');
                data.forEach(c => {
                    gradeSelect.append(`<option value="${c.id}" data-streams='${JSON.stringify(c.streams)}'>${c.grade_form}</option>`);
                });
            });
        }
    });

    $("#grade_form").on("change", function(){
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

    const lockedId = window.BushraSchoolSelect && window.BushraSchoolSelect.lockedId();
    if (lockedId) {
        if (!nativeSelect.value) nativeSelect.value = lockedId;
        window.BushraSchoolSelect.hide(nativeSelect);
        if (!$("#grade_form").val()) {
            $("#branch").trigger("change");
        }
        return;
    }

    $.getJSON(branchesUrl, function(data){
        if (window.BushraSchoolSelect) {
            window.BushraSchoolSelect.fill(nativeSelect, data, "--- Select Branch ---");
        } else {
            const branchSelect = $("#branch");
            branchSelect.empty();
            branchSelect.append('<option value="">--- Select Branch ---</option>');
            data.forEach(b => branchSelect.append(`<option value="${b.id}">${b.name}</option>`));
        }
    });
});
