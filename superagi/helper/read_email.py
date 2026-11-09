import os
import re
from email.header import decode_header

from bs4 import BeautifulSoup

EMAIL_ATTACHMENTS_DIR = os.path.join("workspace", "email_attachments")


class ReadEmail:
    def clean_email_body(self, email_body):
        """
        Function to clean the email body.

        Args:
            email_body (str): The email body to be cleaned.

        Returns:
            str: The cleaned email body.
        """
        if email_body is None: email_body = ""
        email_body = BeautifulSoup(email_body, "html.parser")
        email_body = email_body.get_text()
        email_body = "".join(email_body.splitlines())
        email_body = " ".join(email_body.split())
        email_body = email_body.encode("ascii", "ignore")
        email_body = email_body.decode("utf-8", "ignore")
        email_body = re.sub(r"http\S+", "", email_body)
        return email_body

    def clean(self, text):
        """
        Function to clean the text.

        Args:
            text (str): The text to be cleaned.

        Returns:
            str: The cleaned text.
        """
        return "".join(c if c.isalnum() else "_" for c in text)

    def obtain_header(self, msg):
        """
        Function to obtain the header of the email.

        Args:
            msg (email.message.Message): The email message.

        Returns:
            str: The From field of the email.
        """
        if msg["Subject"] is not None:
            Subject, encoding = decode_header(msg["Subject"])[0]
        else:
            Subject = ""
            encoding = ""
        if isinstance(Subject, bytes):
            try:
                if encoding is not None:
                    Subject = Subject.decode(encoding)
                else:
                    Subject = ""
            except[LookupError] as err:
                pass
        From = msg["From"]
        To = msg["To"]
        Date = msg["Date"]
        return From, To, Date, Subject

    def download_attachment(self, part, subject):
        """
        Function to download the attachment from the email.

        Args:
            part (email.message.Message): The email message.
            subject (str): The subject of the email.

        Returns:
            str: The path of the saved attachment, or None if it was skipped.
        """
        filename = self.sanitize_filename(part.get_filename())
        if not filename:
            return None
        base_dir = os.path.realpath(EMAIL_ATTACHMENTS_DIR)
        folder_name = self.clean(subject or "") or "no_subject"
        folder_path = os.path.realpath(os.path.join(base_dir, folder_name))
        filepath = os.path.realpath(os.path.join(folder_path, filename))
        if os.path.commonpath([base_dir, folder_path]) != base_dir or os.path.dirname(filepath) != folder_path:
            return None
        os.makedirs(folder_path, exist_ok=True)
        with open(filepath, "wb") as file:
            file.write(part.get_payload(decode=True) or b"")
        return filepath

    def sanitize_filename(self, filename):
        """
        Function to reduce a sender supplied attachment filename to a safe base name.

        Args:
            filename (str): The raw attachment filename.

        Returns:
            str: The sanitized filename, or None if it is unsafe.
        """
        if not filename:
            return None
        filename = os.path.basename(filename.replace("\\", "/")).strip()
        if not filename or filename.startswith(".") or "\x00" in filename:
            return None
        return filename
