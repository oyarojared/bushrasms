import pytest
from werkzeug.security import check_password_hash

from ..bushra.modules.admin.utils import (allowed_file,
                                          generate_initial_password,
                                          generate_username,
                                          next_available_username,
                                          score_for_boundary_lookup)

# ---------- allowed_file Tests ---------- #

def test_allowed_file_valid():
    assert allowed_file("photo.jpg") is True
    assert allowed_file("image.PNG") is True
    assert allowed_file("selfie.jpeg") is True
    assert allowed_file("icon.GIF") is True


def test_allowed_file_invalid():
    assert allowed_file("document.pdf") is False
    assert allowed_file("script.exe") is False
    assert allowed_file("archive.zip") is False


def test_allowed_file_no_extension():
    assert allowed_file("photo") is False
    assert allowed_file(".hiddenfile") is False


def test_allowed_file_edge_cases():
    assert allowed_file("my.photo.jpg") is True
    assert allowed_file("UPPERCASE.JPG") is True


# ---------- generate_username Tests ---------- #

def test_generate_username_basic_cases():
    """New accounts use last 4 phone digits. Pass [] so no DB lookup."""
    assert generate_username("Oyaro Jared", "0701948782", existing_usernames=[]) == "ojared8782"
    assert generate_username("Oyaro", "0701948782", existing_usernames=[]) == "oyaro8782"


def test_generate_username_whitespace_handling():
    """Names with leading/trailing/multiple spaces should normalize correctly."""
    assert generate_username("  Oyaro   ", "0712345678", existing_usernames=[]) == "oyaro5678"
    assert generate_username("   Oyaro   Jared   ", "0712345678", existing_usernames=[]) == "ojared5678"


def test_generate_username_case_insensitivity():
    """Upper/lowercase letters in names should not affect final output."""
    assert generate_username("oYaRo JaReD", "0712345678", existing_usernames=[]) == "ojared5678"


def test_generate_username_special_characters():
    """Special characters in the name should be removed."""
    assert generate_username("Oyaro Jared Mon'gare", "0701948782", existing_usernames=[]) == "omongare8782"
    assert generate_username("O'Ya@ro @a#red", "0712345678", existing_usernames=[]) == "oared5678"


def test_generate_username_skips_taken_names():
    """If the preferred name is already used, append 2, 3, ... Existing accounts stay put."""
    taken = ["ojared8782", "ojared87822"]
    assert generate_username("Oyaro Jared", "0701948782", existing_usernames=taken) == "ojared87823"


def test_next_available_username_keeps_first_free_stem():
    assert next_available_username("ojared8782", []) == "ojared8782"
    assert next_available_username("ojared8782", ["ojared8782"]) == "ojared87822"


# ---------- generate_initial_password Tests ---------- #

def test_generate_initial_password_return_type():
    """Ensure function returns a non-empty hashed string."""
    pw = generate_initial_password("0712345678")
    assert isinstance(pw, str)
    assert len(pw) > 20  # safer than checking exact length


def test_generate_initial_password_wrong_arg_type():
    """Should raise TypeError if non-string argument is passed."""
    with pytest.raises(TypeError):
        generate_initial_password(34)


def test_generate_initial_password_return_start_value():
    """Hashed password should start with the expected scheme prefix."""
    pw = generate_initial_password("0712345678")
    assert pw.startswith("pbkdf2:sha256")


def test_generate_initial_password_correct_raw_digits():
    """Ensure the last 4 digits of the phone are the raw password."""
    pw = generate_initial_password("0712345678")
    assert check_password_hash(pw, "5678")


def test_score_for_boundary_lookup_rounds_gap_percentages():
    """39.6% sits between 39 and 40; round so integer bands can match."""
    assert score_for_boundary_lookup(39.6) == 40
    assert score_for_boundary_lookup(39.4) == 39
    assert score_for_boundary_lookup(40) == 40
    assert score_for_boundary_lookup(None) is None
