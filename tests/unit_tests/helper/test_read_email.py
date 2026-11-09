import os
from email.message import EmailMessage

import pytest

from superagi.helper import read_email
from superagi.helper.read_email import ReadEmail


def _attachment(filename, payload=b"data"):
    msg = EmailMessage()
    msg.add_attachment(payload, maintype="application", subtype="octet-stream", filename=filename)
    return [part for part in msg.walk() if part.get_filename()][0]


@pytest.fixture
def attachments_dir(tmp_path, monkeypatch):
    base = tmp_path / "attachments"
    monkeypatch.setattr(read_email, "EMAIL_ATTACHMENTS_DIR", str(base))
    return base


@pytest.mark.parametrize("filename", ["../x.txt", "/tmp/x.txt", "..\\..\\x.txt", "a/../../x.txt"])
def test_download_attachment_stays_in_attachments_dir(attachments_dir, filename):
    path = ReadEmail().download_attachment(_attachment(filename), "Hello World")
    expected = os.path.realpath(str(attachments_dir / "Hello_World" / "x.txt"))
    assert path == expected
    assert open(path, "rb").read() == b"data"
    assert not (attachments_dir.parent / "x.txt").exists()


@pytest.mark.parametrize("filename", ["..", ".", ".bashrc", "../", "/"])
def test_download_attachment_rejects_unsafe_names(attachments_dir, filename):
    assert ReadEmail().download_attachment(_attachment(filename), "subject") is None
    assert not attachments_dir.exists() or not any(attachments_dir.rglob("*"))


def test_download_attachment_existing_folder_and_empty_subject(attachments_dir):
    first = ReadEmail().download_attachment(_attachment("a.txt"), "")
    second = ReadEmail().download_attachment(_attachment("b.txt"), "")
    assert os.path.dirname(first) == os.path.realpath(str(attachments_dir / "no_subject"))
    assert os.path.exists(first) and os.path.exists(second)
