from ..bushra.modules.admin.services.sms import (
    kenya_mobile,
    leftover_tokens,
    render_body,
    sms_parts,
)


def test_kenya_mobile_normalises_local_numbers():
    assert kenya_mobile("0712 345 678") == "254712345678"
    assert kenya_mobile("+254712345678") == "254712345678"
    assert kenya_mobile("712345678") == "254712345678"
    assert kenya_mobile("0112345678") == "254112345678"


def test_kenya_mobile_rejects_invalid():
    assert kenya_mobile("") == ""
    assert kenya_mobile(None) == ""
    assert kenya_mobile("12345") == ""
    assert kenya_mobile("0202222222") == ""


def test_sms_parts_gsm_single_and_concat():
    parts, gsm, length = sms_parts("Hello parent")
    assert gsm is True
    assert parts == 1
    assert length == len("Hello parent")

    long_text = "A" * 161
    parts, gsm, length = sms_parts(long_text)
    assert gsm is True
    assert parts == 2
    assert length == 161


def test_sms_parts_unicode_uses_shorter_limit():
    parts, gsm, length = sms_parts("مرحبا")
    assert gsm is False
    assert length == 5
    assert parts == 1


def test_render_body_fills_and_strips_tokens():
    text = render_body(
        "Hi {parent_name}, {student_name} is in {class}.",
        {
            "parent_name": "Amina",
            "student_name": "Ali",
            "class": "Grade 4 A",
        },
    )
    assert text == "Hi Amina, Ali is in Grade 4 A."
    assert leftover_tokens(text) == []


def test_render_body_parent_fallback_left_to_caller():
    text = render_body("{school}: {student_name}", {"school": "Bushra", "student_name": "Ali"})
    assert text == "Bushra: Ali"
