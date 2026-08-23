"""Module for sending emails using SMTP."""

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from logging import getLogger
from typing import TYPE_CHECKING

from aiofiles import open as aio_open
from aiosmtplib import SMTP, SMTPException
from jinja2 import Environment, FileSystemLoader
from jinja2.ext import i18n

from app.app_config import APP_SETTINGS
from app.core.smtp.config import SMTP_SETTINGS
from app.i18n.context_translations import ContextVarTranslations

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = getLogger(__name__)
"""Logger for the Mailer module."""

JINJA_ENV = Environment(
    loader=FileSystemLoader(APP_SETTINGS.endpoints_root),
    cache_size=0,  # Disable caching as all templates are loaded in __init__ of Mailer class
    autoescape=True,
    auto_reload=APP_SETTINGS.in_development,
)
"""Secondary Jinja2 Environment for rendering email templates."""

JINJA_ENV.add_extension(i18n)
JINJA_ENV.install_gettext_translations(  # type: ignore
    ContextVarTranslations,
    newstyle=True,
)


class Mailer:
    """Class for sending emails using SMTP."""

    route_root: Path = APP_SETTINGS.endpoints_root

    def __init__(
        self,
        subject_template: str,
        body_template: str,
        private_email: bool = False,
    ) -> None:
        """Initialize the Mailer.

        Args:
            subject_template (str): A Jinja2 template for the email subject.
            body_template (str): A Jinja2 template for the email body.
            private_email (bool): Whether the email will be CCed to the sender (default: False).

        """
        self.subject_template = JINJA_ENV.from_string(subject_template)
        self.body_template = JINJA_ENV.get_template((self.route_root / body_template).as_posix())
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
