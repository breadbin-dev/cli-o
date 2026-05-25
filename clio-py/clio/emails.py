import os

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from typing import Iterable

from clio import is_iterable, dttms, BDOffset


def add_attachment(fpath, msg):
    if fpath:
        attachment = MIMEApplication(open(fpath, "rb").read())
        attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(fpath))
        msg.attach(attachment)


def send_report(name, content, to, dttm=..., subject=...):
    if dttm is ...:
        dttm = dttms.format_dt_sql(dttms.today() - BDOffset(1))
    if subject is ...:
        subject = f"[Report {dttm}] {name}"

    send_email(subject=subject, body=content, to_emails=to)


def send_email(
    server: str,
    from_email: str,
    to_emails: str | list[str],
    port: int = 25,
    cc_emails: str | list[str] = None,
    subject: str = None,
    body: str = None,
    content_type: str = "html",
    attachments: str | Iterable[str] = None,
):
    try:
        if from_email is None or to_emails is None:
            raise Exception("Provide or configure email address")

        if to_emails == "/dev/null":
            return

        message = MIMEMultipart()

        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = ",".join(to_emails) if is_iterable(to_emails) else to_emails

        if cc_emails:
            message["Cc"] = ",".join(cc_emails) if is_iterable(cc_emails) else cc_emails

        message.attach(MIMEText(body, content_type))

        if attachments is not None:
            if isinstance(attachments, str):
                attachments = (attachments,)
            for fpath in attachments:
                add_attachment(fpath=fpath, msg=message)

        all_recipients = []
        if is_iterable(to_emails):
            all_recipients.extend(to_emails)
        else:
            all_recipients.append(to_emails)

        if cc_emails:
            if is_iterable(cc_emails):
                all_recipients.extend(cc_emails)
            else:
                all_recipients.append(cc_emails)

        with SMTP(host=server, port=port) as server:
            server.sendmail(from_addr=from_email, to_addrs=all_recipients, msg=message.as_string())
    except Exception as e:
        raise Exception(f"Error while sending email with subject: {subject}") from e


if __name__ == "__main__":
    send_email(subject="Test Subject", body="<html><b>Test</b> Body</html>")
