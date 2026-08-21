"""Module for sending emails using SMTP."""

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from logging import getLogger
from typing import TYPE_CHECKING

from aiofiles import open as aio_open
from aiosmtplib import SMTP, SMTPException
from config import SMTP_SETTINGS
from jinja2 import Template

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = getLogger(__name__)
"""Logger for the EmailSender module."""


class EmailSender:
    """Class for sending emails using SMTP."""

    def __init__(
        self,
        subject_template: Template,
        body_template: Template,
        private_email: bool = False,
    ) -> None:
        """Initialize the EmailSender.

        Args:
            subject_template (Template): A Jinja2 template for the email subject.
            body_template (Template): A Jinja2 template for the email body.
            private_email (bool): Whether the email will be CCed to the sender (default: False).

        """
        self.subject_template = subject_template
        self.body_template = body_template
        self.private_email = private_email

    async def send_email(
        self,
        send_to: set[str],
        render_context: dict,
        attachments: list[Path] | None = None,
    ) -> None:
        """Send an email using the configured SMTP settings.

        Args:
            send_to (set[str]): A set of recipient email addresses.
            render_context (dict): A dictionary containing context variables for rendering the email subject and body.
            attachments (list[Path] | None): A list of file paths to attach to the email (default: None).

        """
        message = MIMEMultipart()

        # Set the email headers
        message["from"] = formataddr((SMTP_SETTINGS.from_name, SMTP_SETTINGS.from_email))
        message["to"] = ", ".join(send_to)
        message["subject"] = self.subject_template.render(render_context)

        # If the email is not private and a CC email is configured, add the CC header
        if not self.private_email and SMTP_SETTINGS.cc_email and SMTP_SETTINGS.cc_email not in send_to:
            message["cc"] = SMTP_SETTINGS.cc_email

        # Render Jinja2 template for the email body and attach it as HTML
        message.attach(MIMEText(self.body_template.render(render_context), "html"))

        # Attach files if provided
        if attachments:
            for attachment in attachments:
                # Use aiofiles to read the attachment asynchronously and attach it to the email
                async with aio_open(attachment, "rb") as f:
                    part = MIMEApplication(await f.read(), name=attachment.name)
                    part["content-disposition"] = f'attachment; filename="{attachment.name}"'
                    message.attach(part)

        try:
            # Using a context manager for the SMTP connection
            async with SMTP(hostname=SMTP_SETTINGS.host, port=SMTP_SETTINGS.port) as server:
                if SMTP_SETTINGS.starttls:
                    await server.starttls()

                if SMTP_SETTINGS.user and SMTP_SETTINGS.password:
                    await server.login(SMTP_SETTINGS.user, SMTP_SETTINGS.password.get_secret_value())

                await server.send_message(message)

            LOGGER.info("Email sent successfully to %s", ", ".join(send_to))

        except SMTPException:
            LOGGER.exception("Failed to send email to %s.", ", ".join(send_to))


if __name__ == "__main__":
    import asyncio

    from jinja2 import Template

    SENDER = EmailSender(
        subject_template=Template("Test Email"),
        body_template=Template("<h1>Hello, {{ name }}!</h1>"),
        private_email=True
    )

    async def _main() -> None:
        await SENDER.send_email(
            send_to={"vojtakuthan@seznam.cz"},
            render_context={"name": "Vojta"},
        )

    asyncio.run(_main())
