import os

import pytest
from fastapi import HTTPException

from superagi.controllers.resources import sanitize_file_name, is_path_within_directory


@pytest.mark.parametrize("file_name, expected", [
    ("report.pdf", "report.pdf"),
    ("../../x.txt", "x.txt"),
    ("/app/superagi/evil.txt", "evil.txt"),
    ("..\..\evil.csv", "evil.csv"),
])
def test_sanitize_file_name_strips_directories(file_name, expected):
    assert sanitize_file_name(file_name) == expected


@pytest.mark.parametrize("file_name", ["", "..", "../", "/", "a/..", "evil\x00.txt"])
def test_sanitize_file_name_rejects_invalid_names(file_name):
    with pytest.raises(HTTPException) as exc:
        sanitize_file_name(file_name)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("file_name", ["../../app/superagi/evil.py", "/app/main.py", "x.txt.py"])
def test_sanitize_file_name_rejects_unsupported_extensions(file_name):
    with pytest.raises(HTTPException) as exc:
        sanitize_file_name(file_name)
    assert exc.value.status_code == 400


def test_is_path_within_directory(tmp_path):
    save_directory = str(tmp_path / "resources")
    assert is_path_within_directory(os.path.join(save_directory, "x.txt"), save_directory)
    assert not is_path_within_directory(os.path.join(save_directory, "..", "x.txt"), save_directory)
    assert not is_path_within_directory("/app/main.py", save_directory)
