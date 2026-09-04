import pytest

from jarvis.tools import eval_math, safe_path


def test_calculator():
    assert eval_math("2 + 3 * 4") == 14


def test_calculator_rejects_code():
    with pytest.raises(ValueError):
        eval_math("__import__('os').system('echo bad')")


def test_safe_path_rejects_escape():
    with pytest.raises(ValueError):
        safe_path("../outside.txt")
