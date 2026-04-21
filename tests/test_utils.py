import pytest
from werkzeug.security import check_password_hash

from ..bushra.modules.admin.utils import (allowed_file,
                                          generate_initial_password,
                                          generate_username)

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
    """Basic expected behavior with typical full names."""
    assert generate_username("Oyaro Jared", "0701948782") == "ojared782"
    assert generate_username("Oyaro", "0701948782") == "oyaro782"


def test_generate_username_whitespace_handling():
    """Names with leading/trailing/multiple spaces should normalize correctly."""
    assert generate_username("  Oyaro   ", "0712345678") == "oyaro678"
    assert generate_username("   Oyaro   Jared   ", "0712345678") == "ojared678"


def test_generate_username_case_insensitivity():
    """Upper/lowercase letters in names should not affect final output."""
    assert generate_username("oYaRo JaReD", "0712345678") == "ojared678"


def test_generate_username_special_characters():
    """
    Special characters in the name should be removed.
    Example: "@a#red" → "ared"
    """
    assert generate_username("Oyaro Jared Mon'gare", "0701948782") == "omongare782"
    assert generate_username("O'Ya@ro @a#red", "0712345678") == "oared678"


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
