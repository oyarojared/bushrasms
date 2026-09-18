from ..bushra.modules.admin.services.report import (
    compute_full_analysis,
    exam_rank_sort_key,
)
from ..bushra.modules.admin.utils.class_teacher import _learner_rank_rows


def _cbe_student(student_id, name, marks, gender="M"):
    return {
        "id": student_id,
        "full_name": name,
        "admission_number": str(student_id),
        "gender": gender,
        "marks": {1: {"marks": marks, "grade": "ME"}},
    }


def _cbe_analysis_data(students):
    return {
        "grading_type": "cbc",
        "subjects": [{"id": 1, "name": "Mathematics"}],
        "students": students,
    }


def test_exam_rank_sort_key_breaks_ties_alphabetically():
    rows = [
        {"id": 4, "name": "ZURI WAMBUI", "score": 48},
        {"id": 1, "name": "ANN NJERI", "score": 48},
        {"id": 2, "name": "BRIAN OTIENO", "score": 51},
    ]
    ranked = sorted(
        rows,
        key=lambda row: exam_rank_sort_key(row["score"], row["name"], row["id"]),
    )
    assert [row["name"] for row in ranked] == [
        "BRIAN OTIENO",
        "ANN NJERI",
        "ZURI WAMBUI",
    ]


def test_full_analysis_no_longer_reverses_tied_names():
    analysis = compute_full_analysis(
        _cbe_analysis_data(
            [
                _cbe_student(4, "ZURI WAMBUI", 80),
                _cbe_student(1, "ANN NJERI", 80),
            ]
        )
    )
    names = [row["name"] for row in analysis["top_students"]]
    assert names == ["ANN NJERI", "ZURI WAMBUI"]
    assert [row["position"] for row in analysis["top_students"]] == [1, 2]


def test_full_analysis_still_ranks_higher_score_first():
    analysis = compute_full_analysis(
        _cbe_analysis_data(
            [
                _cbe_student(1, "ANN NJERI", 70),
                _cbe_student(4, "ZURI WAMBUI", 90),
            ]
        )
    )
    assert [row["name"] for row in analysis["top_students"]] == [
        "ZURI WAMBUI",
        "ANN NJERI",
    ]


def test_report_card_sort_matches_full_analysis_on_ties():
    students = [
        {"id": 4, "name": "ZURI WAMBUI", "score": 54},
        {"id": 9, "name": "BRIAN OTIENO", "score": 54},
        {"id": 1, "name": "ANN NJERI", "score": 60},
    ]
    card_order = [
        row["name"]
        for row in sorted(
            students,
            key=lambda row: exam_rank_sort_key(row["score"], row["name"], row["id"]),
        )
    ]
    analysis = compute_full_analysis(
        _cbe_analysis_data(
            [
                _cbe_student(4, "ZURI WAMBUI", 54),
                _cbe_student(9, "BRIAN OTIENO", 54),
                _cbe_student(1, "ANN NJERI", 60),
            ]
        )
    )
    assert [row["name"] for row in analysis["top_students"]] == card_order
    assert card_order == ["ANN NJERI", "BRIAN OTIENO", "ZURI WAMBUI"]


def test_class_teacher_ranks_tied_learners_alphabetically():
    ranked = _learner_rank_rows(
        {
            "grading_type": "cbc",
            "students": [
                _cbe_student(4, "ZURI WAMBUI", 80),
                _cbe_student(1, "ANN NJERI", 80),
            ],
        },
        missing_marks=[],
    )
    assert [row["name"] for row in ranked] == ["ANN NJERI", "ZURI WAMBUI"]
    assert [row["position"] for row in ranked] == [1, 2]
